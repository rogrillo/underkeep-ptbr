"""Validador: casos sintéticos positivos e negativos."""
from __future__ import annotations

import json

import pytest

from ukloc import markup
from ukloc.validate import KNOWN_UNSUPPORTED, load_exceptions, parse_exceptions, validate_catalog

GLYPHS = frozenset(range(32, 127)) | frozenset(map(ord, "áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇü"))
REF = {
    "menu_ok": "{color_text}OK %1{color_white}\\nnext",
    "two": "%1 of %2",
    "crlf": "Line\r\nTwo",
    "credits_no_localize": "Studio Name",
    "plain": "Hello",
}


def codes(result):
    return set(result.codes())


def test_valid_translation_passes():
    entries = [("menu_ok", "{color_text}Certo %1{color_white}\\npróximo"), ("two", "%2 de %1"),
               ("crlf", "Linha\r\nDuas"), ("credits_no_localize", "Studio Name"), ("plain", "Olá")]
    result = validate_catalog(entries, REF, glyphs=GLYPHS)
    assert result.ok, result.issues
    assert not result.issues


@pytest.mark.parametrize("text,code", [
    ("{color_text}OK %1\\nnext", "MARKUP_MISMATCH"),
    ("{color_text OK %1{color_white}\\nnext", "MARKUP_MALFORMED"),
    ("{color_text}OK %2{color_white}\\nnext", "PLACEHOLDER_MISMATCH"),
    ("{color_text}OK %1{color_white}\nnext", "LINEBREAK_BARE"),
    ("{color_text}OK %1{color_white}next", "LINEBREAK_MISMATCH"),
    ("{color_text}OK… %1{color_white}\\nnext", "UNSUPPORTED_GLYPH"),
    ("{color_text}OK Ж %1{color_white}\\nnext", "UNSUPPORTED_GLYPH"),
    ("   ", "EMPTY_VALUE"),
    ("{color_white}OK %1{color_text}\\nnext", "MARKUP_ORDER"),
    ("{color_text}OK %1{color_white}\\nnext", "UNTRANSLATED"),
    ("{color_text}OK %1{color_white}\\nnext\x07", "UNSUPPORTED_GLYPH"),
])
def test_negative_cases(text, code):
    result = validate_catalog([("menu_ok", text)] + [(k, v + "x") for k, v in REF.items() if k != "menu_ok"
                                                     and not k.endswith("_no_localize")]
                              + [("credits_no_localize", REF["credits_no_localize"])], REF, glyphs=GLYPHS)
    assert code in {i.code for i in result.issues if i.id == "menu_ok"}


def test_known_unsupported_blocked_without_glyph_set():
    for char in KNOWN_UNSUPPORTED:
        result = validate_catalog([("plain", f"Olá{char}")], {"plain": "Hello"})
        assert "UNSUPPORTED_GLYPH" in codes(result)


def test_ids_duplicate_missing_extra_cross_category_and_replaced():
    entries = [("plain", "Olá"), ("plain", "Olá 2"), ("novo", "x"), ("menu_ok", REF["menu_ok"] + " ")]
    result = validate_catalog(entries, {"plain": "Hello", "menu_ok": REF["menu_ok"], "two": "%1 of %2"},
                              replaced={"plain": "Hola", "cut_01": "Cortado"},
                              other_category_ids={"menu_ok"})
    found = codes(result)
    assert {"DUPLICATE_ID", "MISSING_ID", "EXTRA_ID", "DUPLICATE_ID_CROSS_CATEGORY",
            "MISSING_VS_REPLACED"} <= found


def test_no_localize_must_not_change():
    result = validate_catalog([("credits_no_localize", "Nome do Estúdio")], REF)
    assert "NO_LOCALIZE_CHANGED" in codes(result)


def test_exceptions_require_justification(tmp_path):
    with pytest.raises(ValueError):
        parse_exceptions([{"id": "menu_ok", "code": "MARKUP_MISMATCH", "justification": ""}])
    with pytest.raises(ValueError):
        parse_exceptions({"id": "x"})
    path = tmp_path / "exc.json"
    path.write_text(json.dumps([{"id": "menu_ok", "code": "MARKUP_MISMATCH",
                                 "justification": "Tag de cor removida por decisão editorial revisada."}]),
                    encoding="utf-8")
    rules = load_exceptions(path)
    result = validate_catalog([("menu_ok", "{color_text}Certo %1\\npróximo")], {"menu_ok": REF["menu_ok"]},
                              exceptions=rules)
    assert "MARKUP_MISMATCH" not in codes(result)
    assert [i.code for i in result.suppressed] == ["MARKUP_MISMATCH"]


def test_markup_helpers():
    text = "{a:left}Hi %1\\n{font:}x\r\ny"
    assert markup.tokens(text) == ["{a:left}", "%1", "\\n", "{font:}", "\r\n"]
    assert "".join(p for _, p in markup.split_tokens(text)) == text
    assert markup.brace_problems("{:regular}") == ["tag malformada '{:regular}'"]
    assert markup.brace_problems("a}") and markup.brace_problems("{a{b}}")
    assert markup.line_breaks("a\nb\r\nc\rd") == {"escaped": 0, "crlf": 1, "bare_lf": 1, "bare_cr": 1}


def test_empty_id_is_blocking_and_not_suppressible():
    rules = parse_exceptions([{"id": "#0", "code": "EMPTY_ID", "justification": "tentativa de suprimir bloqueio"}])
    result = validate_catalog([("", "x"), ("ok", "y")], {"ok": "y"}, exceptions=rules)
    assert not result.ok
    assert "EMPTY_ID" in codes(result)
    assert result.suppressed == []


def test_non_string_value_is_blocking():
    result = validate_catalog([("ok", 3)], {"ok": "y"})  # type: ignore[list-item]
    assert not result.ok
    assert "NON_STRING_VALUE" in codes(result)
