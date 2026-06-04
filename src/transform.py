import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

COLUMNS = [
    "id", "symbol", "name", "current_price", "market_cap",
    "market_cap_rank", "total_volume", "high_24h", "low_24h",
    "price_change_percentage_24h",
    "price_change_percentage_7d_in_currency",
    "circulating_supply", "last_updated",
]


def transform_coins(raw_data: list) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)[COLUMNS].copy()

    df.rename(columns={
        "price_change_percentage_7d_in_currency": "price_change_percentage_7d"
    }, inplace=True)

    df["price_range_24h"] = (df["high_24h"] - df["low_24h"]).round(4)
    df["price_range_pct"] = (df["price_range_24h"] / df["current_price"] * 100).round(2)
    df["volume_to_market_cap_pct"] = (df["total_volume"] / df["market_cap"] * 100).round(4)
    df["ingested_at"] = datetime.utcnow().isoformat()

    for col in ["current_price", "price_change_percentage_24h", "price_change_percentage_7d"]:
        df[col] = df[col].round(4)

    logger.info(f"Transformed {len(df)} records — added 3 computed columns")
    return df
