"""Testes do filtro de compatibilidade (o que aparece e o que é descartado)."""

import pytest

from app.parsing.matcher import match
from app.parsing.specs import extract_specs

Q = "notebook 32gb ram i7 13th"

ACCEPT = [
    ("Notebook Dell Inspiron i7-13620H 32GB SSD 1TB", "exato"),
    ("Notebook Lenovo Ideapad Slim 3 Core i7 13ª Geração 32GB DDR5 512GB", "exato"),
    ("Notebook Asus Vivobook 16 Intel Core I7 1355u 32gb Ram 512gb SSD", "exato"),
]

REJECT = [
    ("Notebook Gamer MSI Cyborg 15 Intel Core i7-13, 16GB RAM, SSD 512GB", "RAM"),
    ("Notebook Acer Aspire 5 Intel Core i7-12650H, 32GB RAM, SSD 1TB", "geração"),
    ("Notebook Gamer Acer Nitro V15, Intel Core i9-13900H 13ª Geração, 32GB RAM", "i9"),
    ("Notebook Gamer Avell Storm 305 I5 13420h 32gb Ram 1tb Nvme", "i5"),
    ("Notebook Asus Vivobook S14 Intel Core Ultra 7 258v 32gb Ram 1TB SSD", "Core Ultra"),
    ("Notebook Lenovo Thinkpad E14 Amd Ryzen 7 250 32gb 1TB SSD", "Ryzen"),
    ("Computador Bluepc Pro - Intel Core i7 13700f, 32gb Ddr4, SSD 1TB", "PC"),
    ("Memoria Notebook Ddr5 32gb 5600mhz Adata", "memória"),
    ("Carregador Fonte Para Notebook Dell i7 65w", "acessório"),
    ("Capa Notebook 15.6 Neoprene", "acessório"),
    ("Tela 15.6 Led Para Notebook i7 Slim 30 Pinos", "acessório"),
    ("Teclado Para Notebook Dell Inspiron 15 3000 Abnt2", "acessório"),
    ("Placa Mãe Notebook Dell i7-1355u 13ª geração", "placa-mãe"),
    ("Notebook Dell i7 13ª geração 32gb Com Defeito Para Retirada De Peças", "acessório"),
]


@pytest.mark.parametrize("title,level", ACCEPT)
def test_accepts_matching_offers(title, level):
    r = match(extract_specs(Q, is_query=True), title)
    assert r.accepted, r.rejected_because
    assert r.level == level
    assert r.score == 100


@pytest.mark.parametrize("title,why", REJECT)
def test_rejects_non_matching(title, why):
    r = match(extract_specs(Q, is_query=True), title)
    assert not r.accepted
    assert why.lower() in (r.rejected_because or "").lower()


def test_missing_ram_is_accepted_with_reason():
    r = match(extract_specs(Q, is_query=True), "Notebook Lenovo i7 13ª geração SSD 512GB")
    assert r.accepted
    assert "RAM não informada no título" in r.reasons
    assert r.level == "provavel"
    assert r.score < 100


def test_more_ram_is_accepted_with_warning():
    r = match(extract_specs(Q, is_query=True), "Notebook Asus Vivobook Intel Core i7 13ª Geração 40gb Ram 512gb")
    assert r.accepted
    assert any("mais RAM" in x for x in r.reasons)


def test_exact_model_required_when_asked():
    q = extract_specs("notebook i7-13700H 32gb", is_query=True)
    assert match(q, "Notebook Dell i7-13700H 32GB 1TB").accepted
    r = match(q, "Notebook Dell i7-13620H 32GB 1TB")
    assert not r.accepted and "modelo" in r.rejected_because


def test_ryzen_series():
    q = extract_specs("notebook ryzen 7 7735hs 16gb", is_query=True)
    assert match(q, "Notebook Lenovo IdeaPad Slim 3 Ryzen 7 7735HS 16GB 512GB SSD").accepted
    assert not match(q, "Notebook Lenovo IdeaPad Slim 3 Ryzen 7 5700U 16GB 512GB SSD").accepted
    assert not match(q, "Notebook Lenovo IdeaPad Ryzen 5 7535HS 16GB").accepted


def test_gpu_query():
    q = extract_specs("notebook rtx 4060", is_query=True)
    assert match(q, "Notebook Gamer Acer Nitro V15 i7-13620H 16GB RTX 4060").accepted
    assert not match(q, "Notebook Gamer Acer Nitro V15 i7-13620H 16GB RTX 4050").accepted


def test_accessory_search_still_works():
    q = extract_specs("memoria ram 32gb ddr5", is_query=True)
    assert q.category == "memoria"
    assert match(q, "Memoria Notebook Ddr5 32gb 5600mhz Adata").accepted
    assert not match(q, "Notebook Dell i7 32GB").accepted


def test_query_without_specs_accepts_everything_but_accessories():
    q = extract_specs("notebook", is_query=True)
    assert match(q, "Notebook Dell Inspiron 15").accepted
    assert not match(q, "Capa para notebook 15.6").accepted


# --- Buscas "vagas" (só marca/categoria) precisam ser rigorosas -------------

SAMSUNG_TAB_ACCEPT = [
    "Tablet Samsung Galaxy Tab S10 Fe Wifi, 128GB, 8GB, Tela 10.9 90hz",
    "Tablet Samsung Tab A11 Wifi 64gb 4gb Ram Tela 8.7",
    "Tablet Samsung Galaxy Tab S12+ 512gb Wifi - Cinza, Com Caneta S Pen E Capa Teclado",
]
SAMSUNG_TAB_REJECT = [
    ("PC GAMER CAPTAIN Intel Core i5 12400F / NVIDIA GeForce RTX 5060 / 16GB DDR4", "pc"),
    ("PC Gamer NOIR Intel Core Ultra 5 245KF / Radeon RX 9060 XT 16GB", "pc"),
    ("Caneta Dinamic para Samsung Galaxy Tab S9 FE - Touch e esferográfica", "acessório"),
    ("Capa Para Samsung Galaxy Tab S9 Fe 10.9 Polegadas", "acessório"),
    ("Pelicula de Vidro para Galaxy Tab S10 Fe", "acessório"),
    ("Tablet Lenovo Idea Tab Pro 12GB RAM 256GB", "marca"),
    ("Notebook Samsung Galaxy Book4 Intel Core i5 8GB 256GB", "notebook"),
]


def test_samsung_tab_query_is_understood():
    q = extract_specs("samsung tab", is_query=True)
    assert q.category == "tablet" and q.brand == "samsung" and q.keywords == []


@pytest.mark.parametrize("title", SAMSUNG_TAB_ACCEPT)
def test_samsung_tab_accepts_tablets(title):
    assert match(extract_specs("samsung tab", is_query=True), title).accepted


@pytest.mark.parametrize("title,why", SAMSUNG_TAB_REJECT)
def test_samsung_tab_rejects_others(title, why):
    r = match(extract_specs("samsung tab", is_query=True), title)
    assert not r.accepted
    assert why.lower() in r.rejected_because.lower()


def test_brand_missing_from_title_is_rejected():
    r = match(extract_specs("notebook dell", is_query=True), "Notebook Gamer i7 16GB RTX 4060")
    assert not r.accepted and "dell" in r.rejected_because.lower()


def test_brand_from_product_line_counts():
    # "IdeaPad" é linha da Lenovo: a marca conta mesmo sem a palavra "Lenovo"
    assert match(extract_specs("notebook lenovo", is_query=True), "Notebook IdeaPad Slim 3 i5 8GB").accepted


def test_vague_query_requires_typed_words():
    r = match(extract_specs("notebook gamer", is_query=True), "Notebook Dell Inspiron 15 i5 8GB")
    assert not r.accepted and "gamer" in r.rejected_because


def test_specific_query_keeps_keywords_soft():
    # Com specs fortes, palavra extra só tira pontos (não exclui)
    r = match(extract_specs("notebook gamer rtx 4060", is_query=True), "Notebook Acer Nitro V15 i7-13620H 16GB RTX 4060")
    assert r.accepted and any("gamer" in x for x in r.reasons)


# --- Celulares e filtro de tipo de produto -----------------------------------

from app.services.orchestrator import parse_query  # noqa: E402


@pytest.mark.parametrize("text,category,model", [
    ("Apple iPhone 15 Pro Max 256GB Titânio Natural", "celular", "iphone 15 pro max"),
    ("Smartphone Samsung Galaxy S24 Ultra 512GB 12GB RAM", "celular", "galaxy s24 ultra"),
    ("Celular Motorola Moto G85 5G 256GB 8GB RAM", "celular", "moto g85"),
    ("Smartphone Xiaomi Redmi Note 14 Pro 5G 256GB", "celular", "redmi note 14 pro"),
    ("Smartphone Samsung Galaxy A55 5G 128GB", "celular", "galaxy a55"),
    ("Tablet Samsung Galaxy Tab S9 FE 128GB", "tablet", None),
    ("Capa Para iPhone 15 Pro Silicone Preta", "acessorio", None),
    ("Película de Vidro Galaxy S24 Ultra", "acessorio", None),
])
def test_phone_titles(text, category, model):
    s = extract_specs(text)
    assert s.category == category
    if category == "celular":
        assert s.phone_model == model


def test_iphone_model_is_required():
    q = extract_specs("iphone 15", is_query=True)
    assert q.brand == "apple" and q.phone_model == "iphone 15"
    assert match(q, "Apple iPhone 15 128GB Preto").accepted
    variant = match(q, "Apple iPhone 15 Pro 256GB")
    assert variant.accepted and any("Variação" in r for r in variant.reasons)
    assert not match(q, "iPhone 13 128GB Meia-noite").accepted
    assert not match(q, "Apple iPhone 16 128GB").accepted
    assert not match(extract_specs("iphone 15 pro", is_query=True), "Apple iPhone 15 128GB").accepted


def test_product_type_filter_overrides_query():
    specs, q = parse_query("samsung", "celular")
    assert specs.category == "celular" and q.store_terms[0] == "celular samsung"
    assert q.raw == "samsung [celular]"  # cache separado por tipo
    assert match(specs, "Smartphone Samsung Galaxy A55 5G 128GB").accepted
    assert not match(specs, "Tablet Samsung Galaxy Tab S9 FE").accepted
    assert not match(specs, "Notebook Samsung Galaxy Book4 i5 8GB").accepted
    assert not match(specs, "Capa Para Samsung Galaxy A55").accepted
    # tipo inválido é ignorado
    s2, q2 = parse_query("samsung", "geladeira")
    assert s2.category is None and q2.raw == "samsung"


def test_iphone_new_names_and_missing_model():
    assert extract_specs("iPhone Apple 16e 128GB Preto").phone_model == "iphone 16e"
    assert extract_specs("Apple iPhone Air 256GB Dourado").phone_model == "iphone air"
    q = extract_specs("iphone 15", is_query=True)
    assert not match(q, "iPhone Apple 16e 128GB Preto").accepted
    r = match(q, "Smartphone Apple 128GB Preto")  # sem modelo no título
    assert not r.accepted and "modelo não identificado" in r.rejected_because


def test_color_variants_are_collapsed():
    from app.schemas import Offer
    from app.services.orchestrator import collapse_color_variants

    def mk(i, title, price):
        return Offer(store="fastshop", store_name="Fast Shop", external_id=str(i), title=title, url="u", price_cash=price)

    out = collapse_color_variants([
        mk(1, "Celular Samsung Galaxy A07 128GB Preto", 1010.88),
        mk(2, "Celular Samsung Galaxy A07 128GB Verde Claro", 1010.88),
        mk(3, "Celular Samsung Galaxy A07 128GB Lilás", 1010.88),
        mk(4, "Celular Samsung Galaxy A07 128GB Preto", 999.0),  # preço diferente: fica separado
    ])
    assert [o.external_id for o in out] == ["1", "4"]
    assert "3 opções" in out[0].match_reasons[-1]
