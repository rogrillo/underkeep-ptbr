"""Tabelas de texto, catálogo, builder (gates 1 e 2) e pseudo-localização."""
from __future__ import annotations

import pytest

from conftest import SECRET
from ukloc import markup
from ukloc.catalog import (
    catalog_from_json, catalog_from_table, catalog_to_json, ensure_untracked_output, table_from_catalog,
    text_hash,
)
from ukloc.formats import FormatError
from ukloc.formats.dft import DfTFile, Int32, Table, serialize_dft
from ukloc.pseudo import pseudolocalize
from ukloc.textdb import TextTable, build_text_table_bytes, find_text_tables, load_text_table
from ukloc.validate import validate_catalog

ENTRIES = [("a_01", "Olá {color_text}%1{color_white}\\nfim"), ("a_02", "Linha\r\nDois"),
           ("dup_value", "Olá {color_text}%1{color_white}\\nfim"), ("vazio", "")]


def test_text_table_roundtrip_and_shape():
    data = build_text_table_bytes(TextTable("common", "xx", 1, ENTRIES))
    table = load_text_table(data, "common", "xx")
    assert table.entries == ENTRIES
    assert build_text_table_bytes(table) == data
    with pytest.raises(FormatError):
        load_text_table(data, "common", "yy")  # raiz não confere


def test_text_table_rejects_non_string_values():
    doc = DfTFile(1, Table([("text_common_xx", Table([("a", Int32(1))]))]))
    with pytest.raises(FormatError):
        load_text_table(serialize_dft(doc), "common", "xx")


def test_gate1_unchanged_catalog_is_byte_identical():
    original = build_text_table_bytes(TextTable("game", "xx", 1, ENTRIES))
    catalog = catalog_from_table(load_text_table(original, "game", "xx"), source_bytes=original)
    text = catalog_to_json(catalog)
    assert catalog_to_json(catalog_from_json(text)) == text  # JSON determinístico
    rebuilt = build_text_table_bytes(table_from_catalog(catalog_from_json(text)))
    assert rebuilt == original
    assert catalog.entries[0].source_sha256 == text_hash(ENTRIES[0][1])


def test_gate2_modified_catalog_preserves_invariants():
    original = build_text_table_bytes(TextTable("game", "en", 1, ENTRIES))
    catalog = catalog_from_table(load_text_table(original, "game", "en"))
    for entry in catalog.entries:
        entry.text = pseudolocalize(entry.text)
    data = build_text_table_bytes(table_from_catalog(catalog, language="es"))
    back = load_text_table(data, "game", "es")
    assert back.ids() == [i for i, _ in ENTRIES]
    for (_, new), (_, old) in zip(back.entries, ENTRIES):
        assert markup.tokens(new) == markup.tokens(old)
    assert build_text_table_bytes(back) == data
    assert data != original


def test_catalog_index_must_be_contiguous():
    catalog = catalog_from_table(TextTable("game", "en", 1, ENTRIES))
    catalog.entries[1].index = 7
    with pytest.raises(ValueError):
        table_from_catalog(catalog)


def test_find_text_tables(fake_game):
    found = find_text_tables(fake_game / "base")
    assert set(found) == {("common", "en"), ("common", "es"), ("game", "en"), ("game", "es")}


def test_output_guard(tmp_path):
    project = tmp_path / "proj"
    game = tmp_path / "game"
    (project / "work").mkdir(parents=True)
    game.mkdir()
    assert ensure_untracked_output(project / "work" / "x.json", project, game)
    for bad in (project / "docs" / "x.json", game / "x.json", project / "workx" / "a"):
        with pytest.raises(ValueError):
            ensure_untracked_output(bad, project, game)


# ----------------------------------------------------------------- pseudo
@pytest.mark.parametrize("text", [
    "{a:center}{color:#feffb8}Thanks for playing %1!\\nBye\r\nEnd{sprite:ui_mouse_lmb}",
    "%2 de %1", "{hero_name}", "plain", "",
])
def test_pseudolocalize_never_touches_tokens(text):
    out = pseudolocalize(text)
    assert markup.tokens(out) == markup.tokens(text)
    assert "…" not in out
    if text:
        assert "[!!" in out and out.endswith("!!]")
        result = validate_catalog([("k", out)], {"k": text},
                                  glyphs=frozenset(map(ord, out + text)) | {32})
        assert not [i for i in result.errors if i.code != "UNSUPPORTED_GLYPH"]


def test_pseudo_keeps_leading_tags_first():
    assert pseudolocalize("{a:left}Abc").startswith("{a:left}[!!")
    assert pseudolocalize("Cão") == "[!!Çãõ!!]"
