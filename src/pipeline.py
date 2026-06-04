import logging
from src.extract import fetch_top_coins
from src.transform import transform_coins
from src.load import init_db, load_coins, log_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline():
    logger.info("=" * 40)
    logger.info("Pipeline started")
    init_db()

    try:
        raw = fetch_top_coins()
        df = transform_coins(raw)
        load_coins(df)
        log_run(records_loaded=len(df), status="SUCCESS")
        logger.info(f"Pipeline completed — {len(df)} records loaded")
        logger.info("=" * 40)
        return df
    except Exception as exc:
        log_run(records_loaded=0, status="FAILED", error_message=str(exc))
        logger.error(f"Pipeline failed: {exc}")
        raise
