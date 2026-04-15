import requests
import json
from config import GAMMA_API_URL, GAMMA_API_PARAMS, MIN_VOLUME, MIN_VOLUME_24HR


def fetch_markets():
    """
    Fetch active markets from Gamma API and filter by criteria.
    
    Returns:
        List of market objects with keys: market_id, market_name, price, volume, slug
    """
    try:
        response = requests.get(GAMMA_API_URL, params=GAMMA_API_PARAMS, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            print(f"[WARNING] Unexpected API response format: {type(data)}")
            return []

        filtered_markets = []

        for market in data:
            # Apply filters
            if not market.get("active"):
                continue
            if market.get("closed"):
                continue
            if not market.get("acceptingOrders"):
                continue

            volume_num = market.get("volumeNum", 0)
            volume_24hr = market.get("volume24hr", 0)

            if volume_num < MIN_VOLUME:
                continue
            if volume_24hr < MIN_VOLUME_24HR:
                continue

            # Extract data
            try:
                outcome_prices = market.get("outcomePrices", [])
                if isinstance(outcome_prices, str):
                    outcome_prices = json.loads(outcome_prices)

                price = float(outcome_prices[0]) if outcome_prices else 0.5

                clean_market = {
                    "market_id": market.get("id"),
                    "market_name": market.get("question"),
                    "price": price,
                    "volume": volume_num,
                    "slug": market.get("slug"),
                }

                filtered_markets.append(clean_market)

            except (ValueError, IndexError, TypeError) as e:
                print(f"[WARNING] Failed to parse market {market.get('id')}: {e}")
                continue

        return filtered_markets

    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch markets from Gamma API: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error in fetch_markets: {e}")
        return []