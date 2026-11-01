"""Normalização de texto usada tanto na busca quanto nos títulos dos anúncios.

A ideia é transformar variações como "i7-13700H", "i713th", "13ª Geração",
"32GB", "32 Gb" em uma forma única e fácil de casar com regex:
    "i7 13700h", "i7 13 gen", "13 gen", "32 gb", "32 gb"
"""

from __future__ import annotations

import re
import unicodedata

_ORDINAL_MARKS = re.compile(r"(\d)\s*[ªº°]")
_INCH_MARKS = re.compile(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:\"|”|“|''|′′|polegadas|polegada|pol\b|inch(?:es)?\b)")
_GLUED_ILINE = re.compile(r"\bi([3579])(?=\d)")
_GLUED_RYZEN = re.compile(r"\b(ryzen|ultra)(x?[3579])\b")  # "ryzen7", "ultra7", "ultrax9"
_ENGLISH_ORDINAL = re.compile(r"\b(\d{1,2})\s*(?:th|st|nd|rd)\b")
_GEN_WORDS = re.compile(r"\b(?:geracao|geracoes|generation|gen\.?|ger\.?|g)\b(?=\s|$)")
_UNITS = re.compile(r"(\d)\s*(gb|tb|mb|ghz|mhz|hz|w|gen)(?=[a-z]|\b)")
_GPU_GLUED = re.compile(r"\b(rtx|gtx|rx|mx|arc)(?=\d)")
_PUNCT = re.compile(r"[,;:|/\\()\[\]{}+*!?#\"'`´~^®™©•–—_=<>]")
_DOT_NOT_DECIMAL = re.compile(r"(?<!\d)\.|\.(?!\d)")
_DASH = re.compile(r"-")
_SPACES = re.compile(r"\s+")

# "decima terceira geracao" -> "13 gen" (depois de remover acentos)
_ORDINAL_WORDS = [
    ("decima quarta", 14), ("decima terceira", 13), ("decima segunda", 12), ("decima primeira", 11),
    ("decima", 10), ("nona", 9), ("oitava", 8), ("setima", 7), ("sexta", 6), ("quinta", 5), ("quarta", 4),
]
_ORDINAL_WORDS_RE = [
    (re.compile(rf"\b{w}\s(?=geracao|geracoes|gen\b|ger\b)"), f"{n} ") for w, n in _ORDINAL_WORDS
]


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Normaliza um texto livre (busca ou título) para extração de specs."""
    if not text:
        return ""
    # ™ ® © viram "tm"/"r" no NFKD, então saem antes de tudo.
    t = re.sub(r"[™®©]", " ", text.lower())
    # Antes de remover acentos: "13ª" vira "13 gen" (NFKD transformaria ª em "a").
    t = _ORDINAL_MARKS.sub(r"\1 gen ", t)
    t = _INCH_MARKS.sub(r"\1 pol ", t)
    t = strip_accents(t)
    t = t.replace(" ", " ")
    for rx, repl in _ORDINAL_WORDS_RE:
        t = rx.sub(repl, t)
    # "i713th" -> "i7 13th", "i71355u" -> "i7 1355u"
    t = _GLUED_ILINE.sub(r"i\1 ", t)
    t = _GLUED_RYZEN.sub(r"\1 \2", t)
    t = _GPU_GLUED.sub(r"\1 ", t)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)  # decimal brasileiro: "15,6" -> "15.6"
    t = _PUNCT.sub(" ", t)
    t = _DOT_NOT_DECIMAL.sub(" ", t)
    t = _DASH.sub(" ", t)
    t = _ENGLISH_ORDINAL.sub(r"\1 gen", t)
    t = _UNITS.sub(r"\1 \2 ", t)
    t = _GEN_WORDS.sub("gen", t)
    t = re.sub(r"\bgen(?:\s+gen\b)+", "gen", t)  # "13ª geração" -> "13 gen gen" -> "13 gen"
    # "gbram" / "gb ram" já separados acima; garante "gb" isolado de palavras grudadas
    t = re.sub(r"\b(gb|tb)(ram|ssd|nvme|hd|emmc|ddr\d)\b", r"\1 \2", t)
    t = _SPACES.sub(" ", t).strip()
    return t
