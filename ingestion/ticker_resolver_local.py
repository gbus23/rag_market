from __future__ import annotations
import re
from typing import Optional

from .tickers_db import NAME_TO_TICKER
from .brand_aliases import BRAND_ALIAS_TO_TICKER


# Tokenisation robuste : mots, chiffres, accents, apostrophes
TOKEN_REGEX = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+")


def tokenize(text: str):
    """Return a list of normalized tokens."""
    return [t.lower() for t in TOKEN_REGEX.findall(text)]


def resolve_ticker_from_text(text: str) -> Optional[str]:
    if not text:
        return None

    tokens = tokenize(text)
    text_lower = " " + text.lower() + " "   # pour rechercher par limites propres

    # 1) Match alias exacts comme mots entiers
    for alias, ticker in BRAND_ALIAS_TO_TICKER.items():
        alias_norm = alias.lower()

        # Cas 1 : alias est un seul mot → match sur tokens
        if " " not in alias_norm:
            if alias_norm in tokens:
                return ticker

        # Cas 2 : alias multi-mots → on utilise recherche avec limites
        else:
            # Ajout d'espaces autour pour éviter sous-matching
            pattern = fr"(?<!\w){re.escape(alias_norm)}(?!\w)"
            if re.search(pattern, text_lower):
                return ticker

    # 2) Match par nom de société (NAME_TO_TICKER)
    for company_name, ticker in NAME_TO_TICKER.items():
        name_norm = company_name.lower()

        if " " not in name_norm:
            if name_norm in tokens:
                return ticker
        else:
            pattern = fr"(?<!\w){re.escape(name_norm)}(?!\w)"
            if re.search(pattern, text_lower):
                return ticker

    return None
