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


def is_ticker_delimited(text: str, start: int, end: int) -> bool:
    """
    Vérifie si un ticker est entouré par un délimiteur valide.
    Délimiteurs acceptés: espace, apostrophe, parenthèses, guillemets, crochets, etc.
    """
    # Caractères considérés comme délimiteurs
    delimiters = {' ', "'", '"', '(', ')', '[', ']', '{', '}', '<', '>', '«', '»', '"', '"', ''', ''', '`', '~', ',', ';', ':', '.', '!', '?'}
    
    # Vérifier le caractère avant
    if start > 0:
        char_before = text[start - 1]
        if char_before not in delimiters:
            return False
    
    # Vérifier le caractère après
    if end < len(text):
        char_after = text[end]
        if char_after not in delimiters:
            return False
    
    return True


def detect_tickers_in_text(text: str) -> list[str]:
    """
    Détecte les symboles de ticker (2-5 lettres majuscules, optionnellement avec un point et une lettre)
    entourés par des espaces ou apostrophes pour éviter les faux positifs.
    Exemples: AAPL, GOOGL, BRK.B
    """
    tickers = []
    # Regex pour trouver les séquences de 2-5 lettres majuscules, optionnellement suivies d'un point et d'une lettre
    pattern = r'[A-Z]{2,5}(?:\.[A-Z])?'
    
    for match in re.finditer(pattern, text):
        ticker = match.group()
        if is_ticker_delimited(text, match.start(), match.end()):
            tickers.append(ticker)
    
    return tickers


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

    # 3) Détection des tickers par symbole (2-4 lettres majuscules)
    # Tickers doivent être délimités par espaces ou apostrophes
    detected_tickers = detect_tickers_in_text(text)
    if detected_tickers:
        return detected_tickers[0]  # Retourner le premier ticker détecté

    return None
