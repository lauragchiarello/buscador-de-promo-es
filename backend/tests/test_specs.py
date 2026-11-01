"""Testes do parser de especificações com títulos reais de anúncios e buscas digitadas."""

import pytest

from app.parsing.normalize import normalize
from app.parsing.specs import extract_specs

from .conftest import fixture_json

# (texto, specs esperadas — só os campos listados são verificados)
QUERY_CASES = [
    ("notebook 32gb de ram i7 13th", dict(category="notebook", ram_gb=32, cpu_brand="intel", cpu_line="i7", cpu_generation=13)),
    ("notebook 32gb ram i713th", dict(category="notebook", ram_gb=32, cpu_line="i7", cpu_generation=13)),
    ("notebook 32gb ram i7 13th", dict(category="notebook", ram_gb=32, cpu_line="i7", cpu_generation=13)),
    ("Notebook i7 13ª geração 32 GB", dict(category="notebook", ram_gb=32, cpu_line="i7", cpu_generation=13)),
    ("notebook i7 13 gen 32gb", dict(ram_gb=32, cpu_line="i7", cpu_generation=13)),
    ("notebook i7-13700H 32GB", dict(cpu_line="i7", cpu_generation=13, cpu_model="13700h", ram_gb=32)),
    ("notebook i7 décima terceira geração 32gb", dict(cpu_line="i7", cpu_generation=13, ram_gb=32)),
    ("notebook ryzen 7 7735hs 16gb", dict(cpu_brand="amd", cpu_line="ryzen7", cpu_model="7735hs", cpu_generation=7, ram_gb=16)),
    ("notebook ryzen7 16 gb", dict(cpu_line="ryzen7", ram_gb=16)),
    ("notebook core ultra 7 155h 32gb", dict(cpu_line="ultra7", cpu_model="155h", cpu_generation=1, ram_gb=32)),
    ("notebook gamer rtx 4060 16gb", dict(category="notebook", gpu="rtx 4060", ram_gb=16, keywords=["gamer"])),
    ("placa de video rtx 4060 ti", dict(category="placa_video", gpu="rtx 4060 ti")),
    ("rtx 4060", dict(gpu="rtx 4060", category=None)),
    ("tablet samsung 128gb", dict(category="tablet", brand="samsung", storage_gb=128, ram_gb=None)),
    ("pc gamer i5 12400f 16gb rtx 3060", dict(category="desktop", cpu_line="i5", cpu_generation=12, ram_gb=16, gpu="rtx 3060")),
    ("macbook air m2 8gb", dict(category="notebook", cpu_brand="apple", cpu_line="m2", ram_gb=8)),
    ("notebook lenovo i5 16gb ssd 512", dict(brand="lenovo", cpu_line="i5", ram_gb=16)),
    ("notebook dell 15.6 polegadas i5", dict(brand="dell", screen_in=15.6, cpu_line="i5")),
]

# Títulos reais (KaBuM!, Mercado Livre, Amazon, Pichau...) com o que esperamos extrair
TITLE_CASES = [
    ('Notebook Gamer Acer Nitro V15, Intel Core i9-13900H 13ª Geração, 16GB RAM, SSD 512GB, RTX 4060, Tela 15.6" Full HD, Windows 11 Home - ANV15-52-96AQ',
     dict(category="notebook", brand="acer", cpu_line="i9", cpu_generation=13, cpu_model="13900h", ram_gb=16, storage_gb=512, storage_type="ssd", gpu="rtx 4060", screen_in=15.6)),
    ('Notebook Asus Vivobook Tela 16" Ips Intel Core i7 13ª Geração 12gb Ram 1TB Nvme M.2 - Prata',
     dict(brand="asus", cpu_line="i7", cpu_generation=13, ram_gb=12, storage_gb=1024, screen_in=16.0)),
    ("Notebook Asus Vivobook 16 X1605va Intel Core I7 1355u 16gb Ram 512gb SSD WINDOWS 11 Home Tela",
     dict(cpu_line="i7", cpu_model="1355u", cpu_generation=13, ram_gb=16, storage_gb=512)),
    ('Notebook Dell 15 I Dc15-i71355u-m90 15.6" Full Hd 13ª Gen Intel Core i7 16gb 512gb SSD Win 11 Pro',
     dict(brand="dell", cpu_line="i7", cpu_generation=13, ram_gb=16, storage_gb=512, screen_in=15.6)),
    ("Notebook Gamer Asus Rog Strix G16, Core Ultra 9, Nvidia RTX™ 5060, 32 Gb Ram, 1.0 Tb, WINDOWS 11",
     dict(brand="asus", cpu_line="ultra9", gpu="rtx 5060", ram_gb=32, storage_gb=1024)),
    ("Notebook Acer Aspire Go 15 Ag15-71p-747n Intel® Core™ i7 De 13ªg 16gb Ram 512gb SSD  15.6” Fhd",
     dict(cpu_line="i7", cpu_generation=13, ram_gb=16, storage_gb=512, screen_in=15.6)),
    ('Notebook Gamer MSI Cyborg 15 Intel Core i7-13, 16GB RAM, SSD 512GB, 15.6" FHD 144Hz',
     dict(brand="msi", cpu_line="i7", cpu_generation=13, ram_gb=16, storage_gb=512)),
    ('Notebook Acer Aspire 5 15" Fhd i7 12ª Gen Nvme 1TB 64gb Ram',
     dict(cpu_line="i7", cpu_generation=12, ram_gb=64, storage_gb=1024, screen_in=15.0)),
    ("Notebook Gamer Nave Estelar Intel® Core™ i7-14700hx | Nvidia® Geforce®  RTX 4060, 8GB Gd | 32 GB",
     dict(cpu_line="i7", cpu_generation=14, cpu_model="14700hx", gpu="rtx 4060", ram_gb=32)),
    ("Notebook Alienware Aurora Ac16250 Core 7 240h Ram 32gb SSD 512gb RTX 3050 6gb Tela 16'' Qhd",
     dict(brand="dell", cpu_line="core7", cpu_model="240h", ram_gb=32, storage_gb=512, gpu="rtx 3050", screen_in=16.0)),
    ('Notebook Asus Zenbook A14 Ux3407qa, Snapdragon X1 26 100, 32GB RAM, SSD 1TB, Tela 14" OLED',
     dict(cpu_brand="qualcomm", cpu_line="snapdragon", ram_gb=32, storage_gb=1024, screen_in=14.0)),
    ("Notebook Asus Vivobook S 14 Copilot+ PC S5406sa Intel Core Ultra 7 258 V 32gb Ram  1TB SSD",
     dict(category="notebook", cpu_line="ultra7", cpu_generation=2, ram_gb=32, storage_gb=1024)),
    ("Notebook Lenovo Thinkpad E14 Gen 7 Intel Ultra 7 258v 32gb 1TB SSD WINDOWS 11 Pro",
     dict(brand="lenovo", cpu_line="ultra7", cpu_model="258v", ram_gb=32, storage_gb=1024)),
    ('Notebook Lenovo IdeaPad Slim 3 Ryzen 7 7735HS 16GB 512GB SSD 15.6"',
     dict(brand="lenovo", cpu_line="ryzen7", cpu_model="7735hs", ram_gb=16, storage_gb=512, screen_in=15.6)),
    ("Notebook Gamer Gigabyte Gaming A18, 18\" QHD+ 165Hz, AMD Ryzen 7 260, 32GB, 1TB SSD, NVIDIA RTX 5050",
     dict(cpu_line="ryzen7", ram_gb=32, storage_gb=1024, screen_in=18.0, gpu="rtx 5050")),
    ("Recondicionado - Notebook Gamer Acer Helios Neo PHN16-71-72W6 i7 RTX 4060 16GB 512GB 16\" 165Hz",
     dict(category="notebook", cpu_line="i7", gpu="rtx 4060", ram_gb=16, storage_gb=512)),
    ("Computador Intel Core i7 Setima Geracao  32gb Ddr4 SSD 1TB",
     dict(category="desktop", cpu_line="i7", cpu_generation=7, ram_gb=32, storage_gb=1024)),
    ("Computador  Intel  i7 Geracao 8 32 Gb Nvme 1TB", dict(category="desktop", cpu_generation=8, ram_gb=32)),
    ("PC Gamer Intel i7 Sexta Geração  32 Gb M2 512 500w", dict(category="desktop", cpu_generation=6, ram_gb=32)),
    ("Memoria Notebook Ddr5 32gb 5600mhz Adata Ad5s560032g-s", dict(category="memoria", ram_gb=32)),
    ("Carregador Fonte Para Notebook Dell 19.5v 65w", dict(category="acessorio")),
    ("Capa Case Notebook 15.6 Polegadas Impermeável", dict(category="acessorio")),
    ("Tela 15.6 Led Para Notebook Slim 30 Pinos", dict(category="acessorio")),
    ("Notebook Samsung Galaxy Book4 Intel Core i5-1335U 8GB 256GB SSD 15.6", dict(brand="samsung", cpu_line="i5", cpu_generation=13, ram_gb=8, storage_gb=256)),
    ("Notebook HP Victus 15 Intel Core i5-12450H 8GB RAM 512GB SSD RTX 3050 4GB", dict(brand="hp", cpu_line="i5", cpu_generation=12, ram_gb=8, gpu="rtx 3050")),
    ("Apple MacBook Air 13 M3 8GB 256GB SSD - Meia-noite", dict(category="notebook", cpu_line="m3", ram_gb=8, storage_gb=256)),
    ("Notebook Lenovo Ideapad 1 15iau7, WINDOWS 11 Home, 15.6\" Hd, Intel Core I7-1255u, 12gb, SSD 512",
     dict(cpu_line="i7", cpu_generation=12, cpu_model="1255u", ram_gb=12)),
    ("Tablet Samsung Galaxy Tab S9 FE 128GB 6GB RAM Wi-Fi 10.9\"", dict(category="tablet", ram_gb=6, storage_gb=128, screen_in=10.9)),
    ("Placa de Vídeo RTX 4060 Ti 8GB GDDR6 Gigabyte", dict(category="placa_video", gpu="rtx 4060 ti")),
    ("Processador Intel Core i7-13700K 13ª Geração LGA1700", dict(category="processador", cpu_line="i7", cpu_generation=13, cpu_model="13700k")),
    ("Notebook Positivo Vision i15 Intel Celeron N4020 4GB 128GB eMMC", dict(cpu_line="celeron", ram_gb=4, storage_gb=128, storage_type="emmc")),
    ("Notebook Dell Latitude 3440 i5-1335U 16GB DDR4 SSD 256GB", dict(brand="dell", cpu_generation=13, ram_gb=16, storage_gb=256)),
    ("Notebook Lenovo Legion 5i i7-14650HX 32GB 1TB RTX 4060", dict(brand="lenovo", cpu_generation=14, ram_gb=32, storage_gb=1024, gpu="rtx 4060")),
    ("Notebook Asus TUF Gaming F15 Core i7 11800H 16GB 512GB SSD RTX 3050 Ti", dict(brand="asus", cpu_generation=11, gpu="rtx 3050 ti", ram_gb=16)),
    ("Notebook Gamer Acer Nitro 5 AMD Ryzen 5 7535HS 8GB RAM 512GB SSD RTX 2050", dict(cpu_line="ryzen5", cpu_model="7535hs", ram_gb=8, gpu="rtx 2050")),
    ("Notebook Ultra Fino Intel i3 10ª geração 8gb", dict(cpu_line="i3", cpu_generation=10, ram_gb=8)),
]


@pytest.mark.parametrize("text,expected", QUERY_CASES + TITLE_CASES, ids=lambda v: v[:50] if isinstance(v, str) else "")
def test_extract_specs(text, expected):
    specs = extract_specs(text, is_query=(text, expected) in QUERY_CASES)
    for key, value in expected.items():
        assert getattr(specs, key) == value, f"{key}: {getattr(specs, key)!r} != {value!r}  | normalizado: {normalize(text)}"


@pytest.mark.parametrize(
    "raw,normalized",
    [
        ("i713th", "i7 13 gen"),
        ("i7-13700H", "i7 13700h"),
        ("13ª Geração", "13 gen"),
        ("32GB", "32 gb"),
        ("32 Gb RAM", "32 gb ram"),
        ("Intel® Core™ i7", "intel core i7"),
        ('Tela 15.6"', "tela 15.6 pol"),
        ("RTX4060", "rtx 4060"),
    ],
)
def test_normalize(raw, normalized):
    assert normalize(raw) == normalized


def test_real_titles_never_crash_and_most_have_ram():
    titles = fixture_json("kabum_titles.json")
    assert len(titles) > 50
    with_ram = 0
    for t in titles:
        s = extract_specs(t)
        assert s.category is not None, t
        with_ram += s.ram_gb is not None
    # Em títulos reais do KaBuM! a RAM quase sempre está presente
    assert with_ram / len(titles) > 0.9


def test_category_from_store_category_hint():
    # Título sem a palavra "tablet"; a categoria da loja (anexada ao texto) resolve.
    assert extract_specs("Lenovo Idea Tab Pro Octa-Core 12GB RAM 256GB").category == "tablet"
    assert extract_specs("Samsung Galaxy Book4 Intel Core i5 8GB Notebooks").category == "notebook"


@pytest.mark.parametrize("text,expected", [
    ("Notebook Asus VivoBook S 14, Core Ultra7, 32GB, 1TB GB SSD, Tela de 14\" OLED", dict(cpu_line="ultra7", ram_gb=32)),
    ("Notebook ASUS Zenbook DUO Intel Core Ultra X9 378H, 32 GB, 1.0 TB W11 Home", dict(cpu_line="ultra9", cpu_model="378h", cpu_generation=3, ram_gb=32)),
    ("Notebook Lenovo Ideapad Slim 3 Tela 15,3\" Windows 11 AMD Ryzen7 7735HS 512GB SSD 8GB", dict(cpu_line="ryzen7", cpu_model="7735hs", ram_gb=8, storage_gb=512)),
    ("Notebook Acer Travel Mate TMX214-51-50WH Intel Core 5 120U 16GB RAM 512GB SSD", dict(cpu_line="core5", cpu_model="120u", ram_gb=16)),
    ("Notebook Lenovo IdeaPad Slim 3, Intel Core i7 13620H, 24GB, 512GB, Tela de 15,3\" FHD", dict(cpu_line="i7", cpu_generation=13, ram_gb=24, storage_gb=512, screen_in=15.3)),
])
def test_fastshop_titles(text, expected):
    s = extract_specs(text)
    for k, v in expected.items():
        assert getattr(s, k) == v, (k, getattr(s, k), normalize(text))
