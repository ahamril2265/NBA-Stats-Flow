import json
from datetime import datetime
from src.common.logger import get_logger

logger = get_logger("ALERT_MANAGER")


def emit_alert(
    severity: str,
    source: str,
    snapshot_date: str,
    message: str,
    details: dict | None = None
):
    alert = {
        "severity": severity,
        "source": source,
        "snapshot_date": snapshot_date,
        "message": message,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }

    if severity == "CRITICAL":
        logger.error(f"ALERT | {json.dumps(alert)}")
    elif severity == "WARN":
        logger.warning(f"ALERT | {json.dumps(alert)}")
    else:
        logger.info(f"ALERT | {json.dumps(alert)}")
