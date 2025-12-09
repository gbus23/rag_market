from __future__ import annotations

from typing import Optional

from .tickers_db import NAME_TO_TICKER
from .brand_aliases import BRAND_ALIAS_TO_TICKER


def resolve_ticker_from_text(text: str) -> Optional[str]:
    
    if not text:
        return None

    t = text.lower()

    for alias, ticker in BRAND_ALIAS_TO_TICKER.items():
        if alias in t:
            return ticker

    for company_name, ticker in NAME_TO_TICKER.items():
        if company_name in t:
            return ticker

    return None
