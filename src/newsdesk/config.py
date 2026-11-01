from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("config.yaml")


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not cfg.get("tickers"):
        raise ValueError("config.yaml must define at least one ticker")
    return cfg
