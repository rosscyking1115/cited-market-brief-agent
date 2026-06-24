"""Disk persistence for the fund-attribution daily automation.

Family-pilot scale: one fund, two small JSON files in the backend data volume —
the saved holdings/config and the latest computed result. No database table is
needed for a single pilot fund; this keeps the automation self-contained.
"""

import logging
from pathlib import Path

from app.core.config import settings
from app.fund_attribution.schemas import FundAttributionOut, FundConfig, SectorConfig

logger = logging.getLogger(__name__)


def _store_dir() -> Path:
    path = Path(settings.fund_attribution_store_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, payload: str) -> None:
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def save_config(config: FundConfig) -> None:
    _write(_store_dir() / "config.json", config.model_dump_json(indent=2))


def load_config() -> FundConfig | None:
    path = _store_dir() / "config.json"
    if not path.exists():
        return None
    try:
        return FundConfig.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Fund config read failed: %s", exc)
        return None


def save_sector_config(config: SectorConfig) -> None:
    _write(_store_dir() / "sector_config.json", config.model_dump_json(indent=2))


def load_sector_config() -> SectorConfig:
    path = _store_dir() / "sector_config.json"
    if not path.exists():
        return SectorConfig()
    try:
        return SectorConfig.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Sector config read failed: %s", exc)
        return SectorConfig()


def save_result(result: FundAttributionOut) -> None:
    _write(_store_dir() / "latest.json", result.model_dump_json(indent=2))


def load_result() -> FundAttributionOut | None:
    path = _store_dir() / "latest.json"
    if not path.exists():
        return None
    try:
        return FundAttributionOut.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Fund result read failed: %s", exc)
        return None
