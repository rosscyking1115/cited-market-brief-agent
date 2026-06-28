"""Disk persistence for the fund-attribution daily automation.

Family-pilot scale: one fund, two small JSON files in the backend data volume —
the saved holdings/config and the latest computed result. No database table is
needed for a single pilot fund; this keeps the automation self-contained.
"""

import logging
from pathlib import Path

from app.core.config import settings
from app.fund_attribution.schemas import FundAttributionOut, FundConfig, SectorConfig, SectorWeight

logger = logging.getLogger(__name__)

# Approximate TAIEX sector weights so the 產業配置比較 shows out-of-the-box. These are
# a rough snapshot to be calibrated from TAIFEX/TWSE in the editor (names match the
# TWSE sector indices after canonicalisation).
DEFAULT_TAIEX_WEIGHTS: list[SectorWeight] = [
    SectorWeight(sector="半導體", weight_pct=38.0),
    SectorWeight(sector="金融保險", weight_pct=16.0),
    SectorWeight(sector="電子零組件", weight_pct=6.0),
    SectorWeight(sector="電腦及週邊設備", weight_pct=5.0),
    SectorWeight(sector="其他電子", weight_pct=3.0),
    SectorWeight(sector="通信網路", weight_pct=3.0),
    SectorWeight(sector="航運", weight_pct=3.0),
    SectorWeight(sector="電機機械", weight_pct=2.5),
    SectorWeight(sector="光電", weight_pct=2.5),
    SectorWeight(sector="塑膠", weight_pct=2.0),
    SectorWeight(sector="鋼鐵", weight_pct=2.0),
    SectorWeight(sector="生技醫療", weight_pct=2.0),
    SectorWeight(sector="食品", weight_pct=1.5),
    SectorWeight(sector="油電燃氣", weight_pct=1.5),
    SectorWeight(sector="建材營造", weight_pct=1.5),
    SectorWeight(sector="貿易百貨", weight_pct=1.5),
    SectorWeight(sector="化學", weight_pct=1.5),
    SectorWeight(sector="電子通路", weight_pct=1.0),
    SectorWeight(sector="汽車", weight_pct=1.0),
    SectorWeight(sector="水泥", weight_pct=1.0),
    SectorWeight(sector="其他", weight_pct=1.5),
]


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
    """Saved sector config, or sensible defaults: ship approximate TAIEX weights so
    the comparison renders before the user calibrates them in the editor."""
    path = _store_dir() / "sector_config.json"
    if not path.exists():
        return SectorConfig(taiex_weights=list(DEFAULT_TAIEX_WEIGHTS))
    try:
        cfg = SectorConfig.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Sector config read failed: %s", exc)
        return SectorConfig(taiex_weights=list(DEFAULT_TAIEX_WEIGHTS))
    if cfg.taiex_weights:
        return cfg
    return SectorConfig(taiex_weights=list(DEFAULT_TAIEX_WEIGHTS), sector_map=cfg.sector_map)


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
