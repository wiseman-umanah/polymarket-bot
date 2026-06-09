SYSTEM_PROMPT = """You are PolyShock, a Telegram assistant for Polymarket prediction markets.
Fetch live data with your tools — never invent prices, volumes, or market names.

FORMAT (Telegram plain text — no Markdown, no tables):
• Lists: bullet points (•) only.
• Prices: "16% chance" (implied probability, whole percent).
• Volumes: "$32.3M traded" (abbreviated).
• Each market: "Name — X% chance — $YM traded"

EMPTY SEARCH: call get_top_movers(5) as fallback, show those, then add "Search directly: polymarket.com"

RECOMMENDATIONS: Call get_recommendations() when the user asks what to watch, wants suggestions,
or seems to be exploring. It scores active markets against their past searches and preferences.
When a market has matched_interests in the result, mention the connection naturally
(e.g. "Since you asked about elections earlier..."). If no interests are tracked yet, just show
the top movers and invite them to search for topics they care about.

SETTINGS: You can read and update the user's preferences.
• Apply changes immediately — no need to confirm first.
• After a successful write, confirm in one line: "✅ Alert filter set to strong."
• If the request is ambiguous (e.g. "change my settings"), ask which setting before calling a write tool.
• Quiet hours are always UTC — mention this when setting them.
• A null value for volume/price/quiet hours means "use the global default / turn off". """

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_markets",
            "description": "Search markets by keyword. Returns name, price, volume per match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword, e.g. 'election' or 'World Cup'"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_movers",
            "description": "Markets with the largest recent price changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "1–10, default 5"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_detail",
            "description": "Recent price history for a specific market (use market_id from search or top movers).",
            "parameters": {
                "type": "object",
                "properties": {
                    "market_id": {"type": "string"},
                    "snapshots": {"type": "integer", "description": "1–10, default 5"},
                },
                "required": ["market_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_alerts",
            "description": "Most recent alerts fired by the bot (price, volume, or strong signal).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "1–10, default 5"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_settings",
            "description": "The calling user's alert preferences (signal filter, quiet hours, min volume, price threshold).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Write tools — chat_id is injected by the dispatcher, never from LLM output ──
    {
        "type": "function",
        "function": {
            "name": "set_alert_filter",
            "description": "Set which signal types the user receives alerts for.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                        "enum": ["all", "price", "volume", "strong"],
                        "description": "all=every signal, price=price moves only, volume=volume spikes only, strong=both together",
                    }
                },
                "required": ["value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_quiet_hours",
            "description": "Set or disable the user's quiet hours (UTC). Pass start=null and end=null to turn off.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {
                        "anyOf": [{"type": "integer", "minimum": 0, "maximum": 23}, {"type": "null"}],
                        "description": "Start hour UTC (0–23), or null to disable quiet hours",
                    },
                    "end": {
                        "anyOf": [{"type": "integer", "minimum": 0, "maximum": 23}, {"type": "null"}],
                        "description": "End hour UTC (0–23), or null to disable quiet hours",
                    },
                },
                "required": ["start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_min_volume",
            "description": "Set the user's minimum market volume for alerts. Pass null to reset to the global default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "anyOf": [{"type": "number", "minimum": 0}, {"type": "null"}],
                        "description": "Minimum volume in USD (e.g. 50000), or null to use global default",
                    }
                },
                "required": ["value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_price_threshold",
            "description": "Set the user's minimum price move % to trigger an alert. Pass null to reset to global default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "anyOf": [{"type": "number"}, {"type": "null"}],
                        "description": "Threshold as a percentage (e.g. 8 for 8%) or decimal (e.g. 0.08), or null to reset",
                    }
                },
                "required": ["value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reset_all_settings",
            "description": "Reset ALL of the user's preferences to global defaults.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": (
                "Returns personalized market suggestions based on the user's past searches "
                "and their alert preferences (min volume, signal filter). "
                "Call this when the user asks what to watch, wants suggestions, or seems to be exploring."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
