from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ALIASES_CSV = DATA_DIR / "brand_aliases.csv"


def load_aliases() -> Dict[str, str]:
    
    mapping: Dict[str, str] = {}

    if not ALIASES_CSV.exists():
        return mapping

    with ALIASES_CSV.open("r", encoding="utf-8") as f:
        filtered_lines = (
            line
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        )

        reader = csv.DictReader(filtered_lines)
        for row in reader:
            alias = row.get("alias")
            ticker = row.get("ticker")

            if not alias or not ticker:
                continue

            alias_clean = alias.strip().lower()
            ticker_clean = ticker.strip().upper()

            if alias_clean and ticker_clean:
                mapping[alias_clean] = ticker_clean

    return mapping


BRAND_ALIAS_TO_TICKER: Dict[str, str] = load_aliases()
