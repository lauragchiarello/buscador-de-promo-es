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
