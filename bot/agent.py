import json
import time
from collections import defaultdict

from groq import AsyncGroq

from bot.config import GROQ_API_KEY, AGENT_MODEL, AGENT_RATE_LIMIT
from bot.agent_tools import SYSTEM_PROMPT as _SYSTEM_PROMPT, TOOLS as _TOOLS
from bot.db import (
    search_market_snapshot,
    get_top_movers as _db_top_movers,
    get_recent_snapshots,
    get_recent_alerts as _db_recent_alerts,
    get_preferences,
    upsert_preference,
)
from bot.handlers.preferences import parse_price_filter, parse_min_volume, parse_quiet_hour

_ALERT_FILTER_VALUES = {"all", "price", "volume", "strong"}

# Per-user sliding-window rate limiter
_rate_windows: dict[int, list[float]] = defaultdict(list)
_WINDOW_SECS = 60.0
_MAX_TOOL_ITERS = 4

# Per-user interest tracker — populated automatically when search_markets is called
_user_interests: dict[int, list[str]] = defaultdict(list)
_MAX_INTERESTS = 10

# Fields sent to the LLM per tool — strips DB noise (id, slug, raw market_id) to save tokens
_MARKET_FIELDS = {"market_id", "market_name", "price", "volume", "price_change"}
_DETAIL_FIELDS = {"price", "volume", "timestamp"}
_ALERT_FIELDS  = {"market_name", "signal_type", "sent_at"}
_PREFS_FIELDS  = {"signal_filter", "quiet_start", "quiet_end", "min_volume", "price_threshold"}


def _pick(row: dict, fields: set) -> dict:
    return {k: v for k, v in row.items() if k in fields}


def check_rate_limit(chat_id: int) -> bool:
    """Return True if the user may make a request; consumes one slot if so."""
    now = time.monotonic()
    _rate_windows[chat_id] = [t for t in _rate_windows[chat_id] if now - t < _WINDOW_SECS]
    if len(_rate_windows[chat_id]) >= AGENT_RATE_LIMIT:
        return False
    _rate_windows[chat_id].append(now)
    return True


async def _get_recommendations(chat_id: int) -> list[dict]:
    """Score a pool of active markets against the user's tracked interests and preferences."""
    interests = _user_interests.get(chat_id, [])
    prefs = await get_preferences(chat_id)
    min_vol = prefs.get("min_volume") or 0

    pool = await _db_top_movers(n=40)

    if min_vol:
        pool = [r for r in pool if r.get("volume", 0) >= min_vol]

    scored = []
    for r in pool:
        name_lower = r.get("market_name", "").lower()
        matched = [kw for kw in interests if kw.lower() in name_lower]
        scored.append((len(matched), abs(r.get("price_change", 0)), matched, r))

    # Markets matching tracked interests first, then by price movement
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    results = []
    for _, _, matched, r in scored[:5]:
        item = _pick(r, _MARKET_FIELDS)
        if matched:
            item["matched_interests"] = matched
        results.append(item)

    return results


async def _dispatch(chat_id: int, name: str, args: dict):
    """Execute a tool call. chat_id is always injected here — never from LLM output."""
    if name == "search_markets":
        query = str(args.get("query", ""))
        # Record this keyword so get_recommendations can surface related markets later
        if query and query not in _user_interests[chat_id]:
            _user_interests[chat_id].append(query)
            _user_interests[chat_id] = _user_interests[chat_id][-_MAX_INTERESTS:]
        rows = await search_market_snapshot(f"%{query}%")
        return [_pick(r, _MARKET_FIELDS) for r in rows]

    if name == "get_top_movers":
        limit = min(max(int(args.get("limit", 5)), 1), 10)
        rows = await _db_top_movers(n=limit)
        return [_pick(r, _MARKET_FIELDS) for r in rows]

    if name == "get_market_detail":
        market_id = str(args.get("market_id", ""))
        n = min(max(int(args.get("snapshots", 5)), 1), 10)
        rows = await get_recent_snapshots(market_id, n)
        return [_pick(r, _DETAIL_FIELDS) for r in rows]

    if name == "get_recent_alerts":
        limit = min(max(int(args.get("limit", 5)), 1), 10)
        rows = await _db_recent_alerts(n=limit)
        return [_pick(r, _ALERT_FIELDS) for r in rows]

    if name == "get_my_settings":
        prefs = await get_preferences(chat_id)
        return _pick(prefs, _PREFS_FIELDS)

    if name == "get_recommendations":
        return await _get_recommendations(chat_id)

    # ── Write tools ───────────────────────────────────────────────────────────

    if name == "set_alert_filter":
        value = str(args.get("value", "")).lower()
        if value not in _ALERT_FILTER_VALUES:
            return {"ok": False, "error": f"Invalid filter '{value}' — must be one of: all, price, volume, strong"}
        await upsert_preference(chat_id, "signal_filter", value)
        return {"ok": True, "message": f"Alert filter set to {value}"}

    if name == "set_quiet_hours":
        start, end = args.get("start"), args.get("end")
        if start is None and end is None:
            await upsert_preference(chat_id, "quiet_start", None)
            await upsert_preference(chat_id, "quiet_end", None)
            return {"ok": True, "message": "Quiet hours disabled"}
        s = parse_quiet_hour(str(int(start))) if start is not None else None
        e = parse_quiet_hour(str(int(end))) if end is not None else None
        if s is None or e is None:
            return {"ok": False, "error": "Hours must be integers 0–23"}
        await upsert_preference(chat_id, "quiet_start", s)
        await upsert_preference(chat_id, "quiet_end", e)
        return {"ok": True, "message": f"Quiet hours set to {s:02d}:00–{e:02d}:00 UTC"}

    if name == "set_min_volume":
        raw = args.get("value")
        if raw is None:
            await upsert_preference(chat_id, "min_volume", None)
            return {"ok": True, "message": "Min volume reset to global default"}
        val = parse_min_volume(str(raw))
        if val is None:
            return {"ok": False, "error": "Volume must be a positive number"}
        await upsert_preference(chat_id, "min_volume", val)
        return {"ok": True, "message": f"Min volume set to ${val:,.0f}"}

    if name == "set_price_threshold":
        raw = args.get("value")
        if raw is None:
            await upsert_preference(chat_id, "price_threshold", None)
            return {"ok": True, "message": "Price threshold reset to global default"}
        val = parse_price_filter(str(raw))
        if val is None:
            return {"ok": False, "error": "Enter a percentage like 8 (for 8%) or a decimal like 0.08"}
        await upsert_preference(chat_id, "price_threshold", val)
        return {"ok": True, "message": f"Price threshold set to {val:.0%}"}

    if name == "reset_all_settings":
        for field, default in [
            ("signal_filter", "all"), ("quiet_start", None), ("quiet_end", None),
            ("min_volume", None), ("price_threshold", None),
        ]:
            await upsert_preference(chat_id, field, default)
        return {"ok": True, "message": "All settings reset to global defaults"}

    return {"error": f"Unknown tool: {name}"}


async def run_agent(chat_id: int, user_message: str, history: list[dict]) -> str:
    """
    Run the LLM tool-calling loop for one user turn.

    `history` is a list of plain {"role": "user"|"assistant", "content": "..."} dicts
    covering recent exchanges (caller manages trimming). Returns the final text reply.
    """
    if not GROQ_API_KEY:
        return "The AI assistant isn't configured yet — ask the bot admin to add a GROQ_API_KEY."

    client = AsyncGroq(api_key=GROQ_API_KEY)
    messages: list = (
        [{"role": "system", "content": _SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": user_message}]
    )

    for _ in range(_MAX_TOOL_ITERS):
        response = await client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            tool_calls = choice.message.tool_calls
            # Append assistant message with tool_calls explicitly as a dict so
            # we don't depend on SDK-specific serialization in follow-up calls.
            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                result = await _dispatch(chat_id, tc.function.name, json.loads(tc.function.arguments))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                })
        else:
            return choice.message.content or "No response."

    return "I wasn't able to finish that — please try again."
