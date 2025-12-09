from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
TICKERS_CSV = DATA_DIR / "tickers.csv"


def load_name_to_ticker() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    with TICKERS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"].strip().lower()
            sym = row["sym"].strip().upper()
            mapping[name] = sym
    return mapping


NAME_TO_TICKER: Dict[str, str] = load_name_to_ticker()
