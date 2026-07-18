import os
from pathlib import Path
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(_REPO_ROOT / ".env")

ENV_BASE_URL = "API_BASE_URL"
ENV_REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
ENV_SETTLEMENT_TIMEOUT = "SETTLEMENT_TIMEOUT"
ENV_SETTLEMENT_POLL_INTERVAL = "SETTLEMENT_POLL_INTERVAL"

DEFAULT_REQUEST_TIMEOUT = 30.0
DEFAULT_SETTLEMENT_TIMEOUT = 30.0
DEFAULT_SETTLEMENT_POLL_INTERVAL = 1.5


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in, "
            f"or export {name} in the environment.",
        )
    return value


def _float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


BASE_URL: str = _require(ENV_BASE_URL).rstrip("/")
REQUEST_TIMEOUT: float = _float(ENV_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
SETTLEMENT_TIMEOUT: float = _float(ENV_SETTLEMENT_TIMEOUT, DEFAULT_SETTLEMENT_TIMEOUT)
SETTLEMENT_POLL_INTERVAL: float = _float(
    ENV_SETTLEMENT_POLL_INTERVAL,
    DEFAULT_SETTLEMENT_POLL_INTERVAL,
)
