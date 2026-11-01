"""Compara as specs pedidas com as specs de um anúncio.

Regras:
- Spec pedida e DIFERENTE no anúncio  -> anúncio excluído (com motivo, para log/debug).
- Spec pedida e IGUAL                 -> soma o peso inteiro.
- Spec pedida e AUSENTE no título     -> soma metade do peso e gera um aviso
                                         ("RAM não informada no título").
- RAM/armazenamento MAIOR que o pedido -> aceito, com aviso e pequena penalidade.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .accessories import is_accessory
from .normalize import normalize
from .specs import Specs, extract_specs

WEIGHTS = {
    "category": 10,
    "ram_gb": 25,
    "storage_gb": 12,
    "cpu_line": 20,
    "cpu_generation": 20,
    "cpu_model": 15,
    "gpu": 20,
    "screen_in": 5,
    "brand": 8,
}

LABELS = {
    "category": "categoria",
    "ram_gb": "RAM",
    "storage_gb": "armazenamento",
    "cpu_line": "processador",
    "cpu_generation": "geração do processador",
    "cpu_model": "modelo do processador",
    "gpu": "placa de vídeo",
    "screen_in": "tamanho da tela",
    "brand": "marca",
}

MISSING_MSG = {
    "ram_gb": "RAM não informada no título",
    "storage_gb": "Armazenamento não informado no título",
    "cpu_line": "Processador não informado no título",
    "cpu_generation": "Geração do processador não informada no título",
    "cpu_model": "Modelo exato do processador não informado",
    "gpu": "Placa de vídeo não informada no título",
    "screen_in": "Tamanho da tela não informado",
    "brand": "Marca não informada no título",
}

CATEGORY_LABELS = {
    "notebook": "notebook", "desktop": "PC", "tablet": "tablet", "monitor": "monitor",
    "placa_video": "placa de vídeo", "placa_mae": "placa-mãe", "processador": "processador",
    "memoria": "memória", "armazenamento": "SSD/HD", "fonte": "fonte", "gabinete": "gabinete",
    "acessorio": "acessório",
}


@dataclass
class MatchResult:
    accepted: bool
    score: int  # 0-100
    level: str  # "exato" | "provavel" | "duvidoso" | "excluido"
    reasons: list[str] = field(default_factory=list)  # avisos para o usuário
    rejected_because: str | None = None
    specs: Specs | None = None


def _gen_label(specs: Specs) -> str:
    line = specs.cpu_line or ""
    if line.startswith("ryzen"):
        return f"série {specs.cpu_generation}000"
    if line.startswith(("ultra", "core")):
        return f"série {specs.cpu_generation}"
    return f"{specs.cpu_generation}ª geração"


def cpu_line_label(line: str) -> str:
    """"ultra7" -> "Core Ultra 7", "ryzen7" -> "Ryzen 7", "i7" -> "i7"."""
    for prefix, label in (("ryzen_ai", "Ryzen AI "), ("ryzen", "Ryzen "), ("ultra", "Core Ultra "), ("core", "Core ")):
        if line.startswith(prefix):
            return label + line[len(prefix):]
    return line


def _fmt(field_name: str, specs: Specs) -> str:
    v = getattr(specs, field_name)
    if field_name in ("ram_gb", "storage_gb"):
        return f"{v // 1024}TB" if v >= 1024 and v % 1024 == 0 else f"{v}GB"
    if field_name == "cpu_line":
        return cpu_line_label(v)
    if field_name == "cpu_generation":
        return _gen_label(specs)
    if field_name == "category":
        return CATEGORY_LABELS.get(v, v)
    if field_name == "screen_in":
        return f'{v:g}"'
    return str(v).upper() if field_name in ("gpu", "cpu_model") else str(v)


def match(query: Specs, title: str, offer_specs: Specs | None = None) -> MatchResult:
    """Avalia se um anúncio atende a busca."""
    norm = normalize(title)
    offer = offer_specs or extract_specs(title)

    if is_accessory(norm, offer.category) and query.category != "acessorio":
        return MatchResult(False, 0, "excluido", rejected_because="acessório/peça", specs=offer)

    requested = [f for f in WEIGHTS if getattr(query, f) not in (None, "")]
    # Geração sem linha (ex.: só "13ª geração") ainda vale; modelo implica linha e geração.
    if not requested:
        # Busca sem specs reconhecíveis: aceita tudo que não é acessório, score neutro.
        return MatchResult(True, 50, "duvidoso", ["Busca sem especificações reconhecidas"], specs=offer)

    total = sum(WEIGHTS[f] for f in requested)
    got = 0.0
    reasons: list[str] = []

    for f in requested:
        want = getattr(query, f)
        have = getattr(offer, f)

        if have in (None, ""):
            # Categoria ausente é comum em títulos curtos; os outros campos geram aviso.
            got += WEIGHTS[f] * 0.5
            if f != "category":
                reasons.append(MISSING_MSG[f])
            continue

        if f in ("ram_gb", "storage_gb"):
            if have == want:
                got += WEIGHTS[f]
            elif have > want:
                got += WEIGHTS[f] * 0.8
                reasons.append(f"Tem mais {LABELS[f]} que o pedido ({_fmt(f, offer)})")
            else:
                return _reject(offer, f"{LABELS[f]}: {_fmt(f, offer)} (pedido {_fmt(f, query)})")
            continue

        if f == "screen_in":
            if abs(have - want) <= 0.5:
                got += WEIGHTS[f]
            else:
                return _reject(offer, f"tela {_fmt(f, offer)} (pedido {_fmt(f, query)})")
            continue

        if f == "category":
            if have == want:
                got += WEIGHTS[f]
            else:
                return _reject(offer, f"é {CATEGORY_LABELS.get(have, have)}, não {CATEGORY_LABELS.get(want, want)}")
            continue

        if f == "gpu":
            # "rtx 4060" pedido aceita "rtx 4060" mas não "rtx 4060 ti"
            if have == want:
                got += WEIGHTS[f]
            else:
                return _reject(offer, f"placa de vídeo {_fmt(f, offer)} (pedido {_fmt(f, query)})")
            continue

        if f == "cpu_generation":
            # Só compara geração dentro da mesma família de processador
            if offer.cpu_line and query.cpu_line and _family(offer.cpu_line) != _family(query.cpu_line):
                return _reject(offer, f"processador {cpu_line_label(offer.cpu_line)} (pedido {cpu_line_label(query.cpu_line)})")
            if have == want:
                got += WEIGHTS[f]
            else:
                return _reject(offer, f"processador {_gen_label(offer)} (pedido {_gen_label(query)})")
            continue

        # cpu_line, cpu_model, brand: igualdade simples
        if str(have).lower() == str(want).lower():
            got += WEIGHTS[f]
        else:
            return _reject(offer, f"{LABELS[f]} {_fmt(f, offer)} (pedido {_fmt(f, query)})")

    # Palavras extras da busca ("gamer", "oled") viram bônus/aviso leve
    missing_kw = [k for k in query.keywords if k not in norm]
    score = round(100 * got / total)
    if query.keywords:
        score = max(0, score - 5 * len(missing_kw))
        if missing_kw:
            reasons.append("Não menciona: " + ", ".join(missing_kw))

    if score >= 95 and not reasons:
        level = "exato"
    elif score >= 70:
        level = "provavel"
    else:
        level = "duvidoso"
    return MatchResult(True, min(score, 100), level, reasons, specs=offer)


def _family(line: str) -> str:
    for p in ("ryzen_ai", "ryzen", "ultra", "core", "athlon", "snapdragon"):
        if line.startswith(p):
            return p
    if line.startswith("i") and len(line) == 2:
        return "intel_i"
    if line.startswith("m") and line[1:2].isdigit():
        return "apple"
    return line


def _reject(offer: Specs, why: str) -> MatchResult:
    return MatchResult(False, 0, "excluido", rejected_because=why, specs=offer)
