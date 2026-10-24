import json
import logging
import math

logger = logging.getLogger(__name__)

MISSING = {"", "nan", "null", "none", "--", "-999", "na", "n/a"}


def _number(value, low, high):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().lower() in MISSING:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number == -999 or not low <= number <= high:
        return None
    return number


def parse_reading(source):
    """Return sensor values, using None for failed sensors."""
    try:
        if isinstance(source, dict):
            values = source
        elif isinstance(source, str):
            text = source.strip()
            if text.startswith("{"):
                values = json.loads(text)
            else:
                parts = text.split(",")
                if len(parts) != 3:
                    raise ValueError("expected three fields")
                values = dict(zip(("temperature", "humidity", "moisture"), parts))
        else:
            raise TypeError("unsupported reading")
        if not isinstance(values, dict):
            raise ValueError("expected an object")
    except (ValueError, TypeError):
        logger.warning("Ignoring malformed reading: %r", source)
        return None
    reading = (
        _number(values.get("temperature"), -50, 100),
        _number(values.get("humidity"), 0, 100),
        _number(values.get("moisture"), 0, 100),
    )
    return None if all(value is None for value in reading) else reading
