import requests
import logging
from config import API_BASE_URL, TOP_N_COINS, VS_CURRENCY

logger = logging.getLogger(__name__)


def fetch_top_coins() -> list:
    url = f"{API_BASE_URL}/coins/markets"
    params = {
        "vs_currency": VS_CURRENCY,
        "order": "market_cap_desc",
        "per_page": TOP_N_COINS,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h,7d",
    }
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    logger.info(f"Extracted {len(data)} coins from CoinGecko API")
    return data


def fetch_global_stats() -> dict:
    url = f"{API_BASE_URL}/global"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()["data"]
