"""Extração de especificações estruturadas a partir de texto livre.

A MESMA função `extract_specs` é usada para a busca digitada e para os títulos
dos anúncios, assim os dois lados ficam comparáveis.

Exemplo:
    extract_specs("notebook 32gb de ram i713th")
    -> Specs(category="notebook", ram_gb=32, cpu_brand="intel",
             cpu_line="i7", cpu_generation=13, ...)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .normalize import normalize

# ---------------------------------------------------------------------------
# Vocabulário
# ---------------------------------------------------------------------------

# Ordem importa só dentro de cada entrada (frases antes de palavras soltas).
CATEGORY_WORDS: list[tuple[str, str]] = [
    # acessórios / peças que aparecem misturados nas buscas
    (r"capa|capinha|case|bolsa|mochila|maleta|sleeve|pasta", "acessorio"),
    (r"carregador|fonte para|fonte notebook|fonte carregador|adaptador|cabo|hub|dock|dockstation", "acessorio"),
    (r"bateria|pelicula|skin|adesivo|dobradica|carcaca|tampa|moldura|flat|conector|jack", "acessorio"),
    (r"tela|display|lcd|touch screen", "acessorio"),
    (r"teclado|mouse|mousepad|suporte|base refrigeradora|cooler para|cooler notebook|webcam|headset|fone", "acessorio"),
    (r"kit upgrade|kit memoria|kit", "acessorio"),
    # produtos
    (r"notebooks?|laptops?|macbook|chromebook|ultrabook|netbook|notebok|note gamer", "notebook"),
    (r"all in one|all-in-one|aio|mini pc|pc gamer|pc|computador|desktop|workstation|imac|mac mini", "desktop"),
    (r"tablets?|ipad|galaxy tab|idea tab|redmi pad|xiaomi pad", "tablet"),
    (r"monitor|monitores", "monitor"),
    (r"placa de video|placa video|placa grafica|gpu", "placa_video"),
    (r"placa mae|placa-mae|motherboard", "placa_mae"),
    (r"processador|cpu", "processador"),
    (r"memoria ram|memoria|pente de memoria|modulo de memoria", "memoria"),
    (r"ssd|hd externo|hd interno|hdd|disco rigido|nvme|m 2", "armazenamento"),
    (r"fonte", "fonte"),
    (r"gabinete", "gabinete"),
]

_CATEGORY_RES = [(re.compile(rf"\b(?:{pat})\b"), cat) for pat, cat in CATEGORY_WORDS]

BRANDS = [
    "acer", "asus", "dell", "lenovo", "hp", "samsung", "apple", "msi", "gigabyte",
    "avell", "positivo", "vaio", "lg", "multilaser", "concordia", "alienware",
    "razer", "huawei", "xiaomi", "microsoft", "compaq", "philco", "galaxy book",
    "legion", "ideapad", "thinkpad", "vivobook", "zenbook", "rog", "tuf", "nitro",
    "predator", "aspire", "inspiron", "vostro", "latitude", "pavilion", "victus", "omen",
]
# Marca "mãe" de algumas linhas
_LINE_TO_BRAND = {
    "legion": "lenovo", "ideapad": "lenovo", "thinkpad": "lenovo",
    "vivobook": "asus", "zenbook": "asus", "rog": "asus", "tuf": "asus",
    "nitro": "acer", "predator": "acer", "aspire": "acer",
    "inspiron": "dell", "vostro": "dell", "latitude": "dell", "alienware": "dell",
    "pavilion": "hp", "victus": "hp", "omen": "hp", "galaxy book": "samsung",
}
_BRAND_RE = re.compile(r"\b(" + "|".join(re.escape(b) for b in BRANDS) + r")\b")

COMMON_RAM_SIZES = {4, 6, 8, 12, 16, 20, 24, 32, 36, 40, 48, 64, 96, 128}

# ---------------------------------------------------------------------------
# Regex de specs (rodam sobre texto JÁ normalizado)
# ---------------------------------------------------------------------------

_SIZE = r"(\d{1,4}(?:[.,]\d{1,2})?)\s(gb|tb)"
_RAM_EXPLICIT = [
    re.compile(r"(\d{1,3})\sgb\s(?:de\s)?(?:memoria\s)?(?:ram|ddr\d|lpddr\d\w?)\b"),
    re.compile(r"\b(?:ram|memoria|memoria ram)\s(?:de\s)?(?:ddr\d\s|lpddr\d\w?\s)?(\d{1,3})\sgb\b"),
    re.compile(r"(\d{1,3})\sgb\s(?:\d{3,4}\smhz\s)?(?:ddr\d|lpddr\d\w?)\b"),
]
_STORAGE_KW = r"(?:ssd|nvme|m 2|m\.2|hd|hdd|emmc|ufs|armazenamento|pcie)"
_STORAGE_EXPLICIT = [
    re.compile(rf"\b{_STORAGE_KW}\s(?:de\s)?(?:nvme\s|m 2\s|pcie\s)?{_SIZE}"),
    re.compile(rf"{_SIZE}\s(?:de\s)?(?:armazenamento\s)?{_STORAGE_KW}\b"),
]
_ANY_SIZE = re.compile(rf"\b{_SIZE}\b")
_GPU_VRAM_CONTEXT = re.compile(r"(?:rtx|gtx|rx|arc|radeon|geforce)\s\w*\s?\d{3,4}\w*\s(?:ti\s|super\s|xt\s)?$")

_INTEL_I = re.compile(r"\b(?:core\s)?i([3579])\s(\d{4,5})([a-z]{0,3}\d?)\b")
_INTEL_I_GEN_AFTER = re.compile(r"\b(?:core\s)?i([3579])\s(?:de\s)?(\d{1,2})\s?gen\b")
_INTEL_I_GEN_BEFORE_NUM = re.compile(r"\b(?:core\s)?i([3579])\s(?:de\s)?gen\s(\d{1,2})\b")
_INTEL_I_BARE_GEN = re.compile(r"\b(?:core\s)?i([3579])\s(1[0-4]|[4-9])\b(?!\s(?:gb|tb|pol|hz)\b)")
_INTEL_I_LINE = re.compile(r"\b(?:core\s)?i([3579])\b")
_GEN_ANYWHERE = re.compile(r"\b(\d{1,2})\s?gen\b")
# "core ultra 7 155h", "intel ultra 7 258v", "core ultra x9 378h" (série 3, nomenclatura nova)
_INTEL_ULTRA = re.compile(r"\b(?:core\s|intel\s)ultra\s(?:x\s?)?([3579])(?:\s(\d{3})\s?([a-z]{0,2}))?\b")
_INTEL_CORE_N = re.compile(r"\b(?:intel\s)?core\s([3579])\s(\d{3})\s?([a-z]{0,2})\b")
_INTEL_LOW = re.compile(r"\b(celeron|pentium|atom)\b|\bintel\s(n\d{2,3})\b|\b(n100|n200|n305|n4020|n4500|n5100)\b")
_RYZEN_AI = re.compile(r"\bryzen\sai\s(?:max\s?\+?\s)?([3579])\s(?:pro\s)?(?:hx\s)?(\d{3})?")
_RYZEN = re.compile(r"\bryzen\s([3579])\s?(?:pro\s)?(\d{4})?\s?([a-z]{0,3})\b")
_ATHLON = re.compile(r"\bathlon\b")
_APPLE_M = re.compile(r"\b(?:apple\s|chip\s)?m([1-5])(?:\s(pro|max|ultra))?\b")
_SNAPDRAGON = re.compile(r"\bsnapdragon\s(x\d?|x\s?elite|x\s?plus|\d{3,4})")
_MEDIATEK = re.compile(r"\b(mediatek|helio|dimensity|kompanio)\b")

_GPU_NVIDIA = re.compile(r"\b(rtx|gtx|mx)\s?(\d{3,4})\s?(ti\b|super\b)?")
_GPU_AMD = re.compile(r"\brx\s?(\d{3,4})\s?(xtx|xt|m|s)?\b")
_GPU_ARC = re.compile(r"\barc\s([ab]\d{3})\b")

_SCREEN = [
    re.compile(r"\b(\d{1,2}(?:[.,]\d{1,2})?)\spol\b"),
    re.compile(r"\btela\s(?:de\s)?(?:\w+\s)?(\d{2}(?:[.,]\d{1,2})?)\b(?!\s?(?:gb|tb|gen|hz))"),
]


@dataclass
class Specs:
    """Especificações estruturadas extraídas de um texto."""

    category: str | None = None
    brand: str | None = None
    ram_gb: int | None = None
    storage_gb: int | None = None
    storage_type: str | None = None  # "ssd" | "hd" | "emmc"
    cpu_brand: str | None = None  # intel | amd | apple | qualcomm | mediatek
    cpu_line: str | None = None  # i7, ultra7, core7, ryzen7, ryzen_ai9, m3, celeron...
    cpu_generation: int | None = None  # Intel: 13; Ryzen: 7 (série 7000); Ultra: 1/2; Apple: 3
    cpu_model: str | None = None  # 13700h, 7735hs, 155h
    gpu: str | None = None  # "rtx 4060", "rx 7600"
    screen_in: float | None = None
    keywords: list[str] = field(default_factory=list)  # palavras não reconhecidas (só na busca)
    ram_inferred: bool = False  # RAM deduzida sem a palavra "ram"

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, [], False)}

    def is_empty(self) -> bool:
        return not any(
            [self.ram_gb, self.storage_gb, self.cpu_line, self.cpu_model, self.gpu, self.screen_in]
        )


# ---------------------------------------------------------------------------
# Extratores
# ---------------------------------------------------------------------------


def _to_gb(value: str, unit: str) -> int:
    num = float(value.replace(",", "."))
    return int(round(num * 1024)) if unit == "tb" else int(round(num))


def detect_category(text: str) -> str | None:
    """Categoria = a PRIMEIRA palavra de categoria que aparece no texto.

    Títulos quase sempre começam pelo tipo do produto ("Notebook Gamer Acer...",
    "Carregador para notebook Dell..."), então a primeira ocorrência decide.
    """
    best: tuple[int, str] | None = None
    for rx, cat in _CATEGORY_RES:
        m = rx.search(text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), cat)
    return best[1] if best else None


def _extract_ram(t: str, category: str | None) -> tuple[int | None, bool, list[tuple[int, int]]]:
    """Retorna (ram_gb, inferida?, spans usados)."""
    for rx in _RAM_EXPLICIT:
        m = rx.search(t)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 256:
                return val, False, [m.span()]
    return None, False, []


def _extract_storage(t: str) -> tuple[int | None, str | None, list[tuple[int, int]]]:
    for rx in _STORAGE_EXPLICIT:
        m = rx.search(t)
        if m:
            gb = _to_gb(m.group(1), m.group(2))
            kind = "ssd"
            ctx = m.group(0)
            if re.search(r"\b(?:hd|hdd)\b", ctx):
                kind = "hd"
            elif "emmc" in ctx or "ufs" in ctx:
                kind = "emmc"
            if gb >= 32:
                return gb, kind, [m.span()]
    # Sem palavra-chave: qualquer valor em TB é armazenamento.
    for m in _ANY_SIZE.finditer(t):
        if m.group(2) == "tb":
            return _to_gb(m.group(1), "tb"), ("ssd" if re.search(r"\b(ssd|nvme)\b", t) else None), [m.span()]
    return None, None, []


def _infer_ram_and_storage(
    t: str, used: list[tuple[int, int]], ram: int | None, storage: int | None
) -> tuple[int | None, int | None, bool]:
    """Para tamanhos "soltos" (ex.: "i7 16gb 512gb ssd"): pequenos = RAM, grandes = armazenamento."""
    inferred = False
    for m in _ANY_SIZE.finditer(t):
        if any(s <= m.start() < e for s, e in used):
            continue
        if m.group(2) != "gb":
            continue
        val = int(float(m.group(1).replace(",", ".")))
        before = t[: m.start()]
        after = t[m.end() : m.end() + 12]
        # VRAM de placa de vídeo ("rtx 4060 8gb", "8gb gddr6", "6gb dedicada").
        # Logo depois da GPU, até 8GB é VRAM; 16GB+ quase sempre é a RAM do notebook.
        if re.match(r"\s?(?:gddr\d|gd\b|vram|dedicad|de video)", after):
            continue
        if _GPU_VRAM_CONTEXT.search(before) and val <= 8:
            continue
        if ram is None and val in COMMON_RAM_SIZES:
            ram, inferred = val, True
        elif storage is None and val >= 128:
            storage = val
    return ram, storage, inferred


def _intel_gen_from_model(model_digits: str) -> int:
    # 13700 -> 13 ; 1355 -> 13 ; 1165 -> 11 ; 1005 -> 10 ; 8550 -> 8
    if model_digits.startswith("1") and len(model_digits) >= 4:
        return int(model_digits[:2])
    return int(model_digits[0])


def _extract_cpu(t: str) -> dict:
    out: dict = {}

    m = _INTEL_ULTRA.search(t)
    if m:
        out.update(cpu_brand="intel", cpu_line=f"ultra{m.group(1)}")
        if m.group(2):
            out["cpu_model"] = (m.group(2) + (m.group(3) or "")).strip()
            out["cpu_generation"] = int(m.group(2)[0])
        return out

    m = _INTEL_I.search(t)
    if m:
        digits = m.group(2)
        out.update(
            cpu_brand="intel",
            cpu_line=f"i{m.group(1)}",
            cpu_model=digits + (m.group(3) or ""),
            cpu_generation=_intel_gen_from_model(digits),
        )
        return out

    m = _INTEL_I_GEN_AFTER.search(t) or _INTEL_I_GEN_BEFORE_NUM.search(t) or _INTEL_I_BARE_GEN.search(t)
    if m:
        out.update(cpu_brand="intel", cpu_line=f"i{m.group(1)}", cpu_generation=int(m.group(2)))
        return out

    m = _INTEL_I_LINE.search(t)
    if m:
        out.update(cpu_brand="intel", cpu_line=f"i{m.group(1)}")
        g = _GEN_ANYWHERE.search(t)
        if g and 4 <= int(g.group(1)) <= 15:
            out["cpu_generation"] = int(g.group(1))
        return out

    m = _INTEL_CORE_N.search(t)
    if m:
        out.update(
            cpu_brand="intel",
            cpu_line=f"core{m.group(1)}",
            cpu_model=(m.group(2) + (m.group(3) or "")).strip(),
            cpu_generation=int(m.group(2)[0]),
        )
        return out

    m = _RYZEN_AI.search(t)
    if m:
        out.update(cpu_brand="amd", cpu_line=f"ryzen_ai{m.group(1)}")
        if m.group(2):
            out["cpu_model"] = m.group(2)
        return out

    m = _RYZEN.search(t)
    if m:
        out.update(cpu_brand="amd", cpu_line=f"ryzen{m.group(1)}")
        if m.group(2):
            out["cpu_model"] = m.group(2) + (m.group(3) or "")
            out["cpu_generation"] = int(m.group(2)[0])
        else:
            # "ryzen 7 serie 7000" / "ryzen 7 7000"
            s = re.search(r"\b([1-9])000\b", t)
            if s:
                out["cpu_generation"] = int(s.group(1))
        return out

    if _ATHLON.search(t):
        return {"cpu_brand": "amd", "cpu_line": "athlon"}

    m = _INTEL_LOW.search(t)
    if m:
        line = m.group(1) or m.group(2) or m.group(3)
        return {"cpu_brand": "intel", "cpu_line": line}

    m = _SNAPDRAGON.search(t)
    if m:
        return {"cpu_brand": "qualcomm", "cpu_line": "snapdragon", "cpu_model": m.group(1).replace(" ", "")}

    m = _APPLE_M.search(t)
    if m and re.search(r"\b(apple|macbook|mac|imac|ipad|chip)\b", t):
        line = f"m{m.group(1)}" + (f" {m.group(2)}" if m.group(2) else "")
        return {"cpu_brand": "apple", "cpu_line": line, "cpu_generation": int(m.group(1))}

    if _MEDIATEK.search(t):
        return {"cpu_brand": "mediatek", "cpu_line": "mediatek"}

    # Só a marca
    if re.search(r"\bintel\b", t):
        return {"cpu_brand": "intel"}
    if re.search(r"\bamd\b", t) and not _GPU_AMD.search(t):
        return {"cpu_brand": "amd"}
    return out


def _extract_gpu(t: str) -> str | None:
    m = _GPU_NVIDIA.search(t)
    if m:
        name = f"{m.group(1)} {m.group(2)}"
        if m.group(3):
            name += f" {m.group(3)}"
        return name
    m = _GPU_AMD.search(t)
    if m:
        return f"rx {m.group(1)}" + (f" {m.group(2)}" if m.group(2) in ("xt", "xtx") else "")
    m = _GPU_ARC.search(t)
    if m:
        return f"arc {m.group(1)}"
    return None


def _extract_screen(t: str) -> float | None:
    for rx in _SCREEN:
        m = rx.search(t)
        if m:
            val = float(m.group(1).replace(",", "."))
            if 7 <= val <= 49:
                return val
    return None


def _extract_brand(t: str) -> str | None:
    m = _BRAND_RE.search(t)
    if not m:
        return None
    b = m.group(1)
    return _LINE_TO_BRAND.get(b, b)


_STOPWORDS = {
    "de", "da", "do", "com", "e", "para", "o", "a", "em", "gb", "tb", "ram", "gen", "intel",
    "amd", "core", "ssd", "memoria", "processador", "geracao", "pol", "tela", "polegadas",
    "nvme", "hd", "placa", "video", "mae", "barato", "promocao", "oferta", "melhor", "preco", "novo",
}


def extract_specs(text: str, *, is_query: bool = False) -> Specs:
    """Extrai specs de um texto livre (busca ou título de anúncio)."""
    t = normalize(text)
    specs = Specs()
    specs.category = detect_category(t)
    specs.brand = _extract_brand(t)

    ram, _, ram_spans = _extract_ram(t, specs.category)
    storage, storage_type, st_spans = _extract_storage(t)
    ram, storage, inferred = _infer_ram_and_storage(t, ram_spans + st_spans, ram, storage)
    specs.ram_gb, specs.ram_inferred = ram, inferred
    specs.storage_gb, specs.storage_type = storage, storage_type

    for k, v in _extract_cpu(t).items():
        setattr(specs, k, v)
    specs.gpu = _extract_gpu(t)
    specs.screen_in = _extract_screen(t)

    # Tablets/celulares: um "128gb" solto é armazenamento, não RAM.
    if specs.category == "tablet" and specs.ram_inferred and specs.ram_gb and specs.ram_gb >= 32:
        specs.storage_gb = specs.storage_gb or specs.ram_gb
        specs.ram_gb, specs.ram_inferred = None, False

    if is_query:
        specs.keywords = _residual_keywords(t, specs)
    return specs


def _residual_keywords(t: str, specs: Specs) -> list[str]:
    """Palavras da busca que não viraram spec (ex.: "gamer", "oled") — contam só como bônus."""
    words = []
    for w in t.split():
        if w in _STOPWORDS or len(w) < 3 or any(ch.isdigit() for ch in w):
            continue
        if specs.category and re.fullmatch(r"notebook|laptop|tablet|pc|computador|desktop|monitor", w):
            continue
        if re.fullmatch(r"i[3579]|ryzen|ultra|rtx|gtx|rx", w):
            continue
        if specs.brand and w == specs.brand:
            continue
        words.append(w)
    return words
