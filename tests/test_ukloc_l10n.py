"""Catálogo PT-BR: modelo, determinismo, não sobrescrita, validação e integração com o builder."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ukloc import l10n, shadow
from ukloc.fonts import game_supported_codepoints
from ukloc.textdb import load_text_table, text_file_name

REPO = Path(__file__).resolve().parents[1]


def _tables(game: Path, lang: str) -> dict[str, dict[str, str]]:
    out = {}
    for cat in ("common", "game"):
        path = game / "base" / text_file_name(cat, lang)
        out[cat] = load_text_table(path.read_bytes(), cat, lang).as_dict()
    return out


def _project(game: Path) -> l10n.Project:
    files = {text_file_name(c, lang): shadow.file_sha256(game / "base" / text_file_name(c, lang))
             for c in ("common", "game") for lang in ("en", "es")}
    return l10n.Project("pt-BR", "en", "es", "base", None, shadow.file_sha256(game / "underkeep.exe"), files)


def _entry(ref: str, text: str | None = None, tr: str = "pending", rv: str = "pending", **kw) -> l10n.Entry:
    return l10n.Entry(l10n.text_sha256(ref), text, tr, rv, **kw)


# ------------------------------------------------------------------ modelo e serialização
def test_serialization_is_deterministic_and_sorted() -> None:
    cat = l10n.Catalog("common", entries={"b": _entry("B"), "a": _entry("A", "Á", "translated", "approved",
                                                                           context="ctx", terminology=["x"])})
    text = l10n.catalog_to_json(cat)
    again = l10n.catalog_to_json(l10n.catalog_from_dict(json.loads(text)))
    assert text == again
    assert text.index('"a"') < text.index('"b"') and text.endswith("\n") and "Á" in text


@pytest.mark.parametrize("mutate", [
    lambda e: e.update(text="x"),                                     # pending com texto
    lambda e: e.update(review_status="approved"),                     # aprovado sem tradução
    lambda e: e.update(translation_status="done"),                    # estado inválido
    lambda e: e.update(extra="?"),                                    # campo desconhecido
    lambda e: e.update(source_sha256="abc"),                          # hash inválido
    lambda e: e.update(text="ok", translation_status="translated",
                       exceptions=[{"code": "X", "justification": "curta"}]),
    lambda e: e.update(translation_status="translated", text=""),      # traduzido vazio
])
def test_catalog_rejects_invalid_entries(mutate) -> None:
    raw = {"source_sha256": "0" * 64, "text": None, "translation_status": "pending", "review_status": "pending"}
    mutate(raw)
    data = {"schema": l10n.CATALOG_SCHEMA, "category": "common", "entries": {"id": raw}}
    with pytest.raises(l10n.CatalogError):
        l10n.catalog_from_dict(data)


def test_catalog_rejects_empty_id_and_bad_category() -> None:
    entry = {"source_sha256": "0" * 64, "text": None, "translation_status": "pending", "review_status": "pending"}
    with pytest.raises(l10n.CatalogError):
        l10n.catalog_from_dict({"schema": l10n.CATALOG_SCHEMA, "category": "common", "entries": {" ": entry}})
    with pytest.raises(l10n.CatalogError):
        l10n.catalog_from_dict({"schema": l10n.CATALOG_SCHEMA, "category": "menus", "entries": {}})


@pytest.mark.parametrize("tr,rv,expected", [
    ("pending", "pending", (False, False, False)),
    ("translated", "pending", (False, False, True)),
    ("translated", "reviewed", (False, True, True)),
    ("translated", "approved", (True, True, True)),
    ("translated", "needs_review", (False, False, False)),
    ("needs_review", "pending", (False, False, False)),
])
def test_policy_matrix(tr: str, rv: str, expected: tuple[bool, bool, bool]) -> None:
    entry = _entry("A", None if tr == "pending" else "Á", tr, rv)
    assert tuple(entry.is_applicable(p) for p in ("approved", "reviewed", "translated")) == expected


# ------------------------------------------------------------------ geração sem sobrescrever
def test_add_pending_never_overwrites_existing_translation() -> None:
    ref = {"a": "A", "b": "B"}
    cat = l10n.Catalog("common", entries={"a": _entry("A", "Minha tradução", "translated", "approved")})
    added, kept = l10n.add_pending(cat, ["a", "b"], ref)
    assert added == ["b"] and kept == ["a"]
    assert cat.entries["a"].text == "Minha tradução" and cat.entries["a"].review_status == "approved"
    assert cat.entries["b"].text is None and cat.entries["b"].translation_status == "pending"
    with pytest.raises(l10n.CatalogError):
        l10n.add_pending(cat, ["inexistente"], ref)


def test_stale_detection_preserves_text() -> None:
    cat = l10n.Catalog("common", entries={"a": _entry("Old", "Velho", "translated", "approved"),
                                          "b": _entry("B", "Bê", "translated", "pending")})
    ref = {"a": "New", "b": "B"}
    assert l10n.stale_entries(cat, ref) == ["a"]
    assert l10n.mark_stale(cat, ref) == ["a"]
    a = cat.entries["a"]
    assert a.text == "Velho" and a.translation_status == "needs_review" and a.review_status == "needs_review"
    assert not a.is_applicable("translated")


# ------------------------------------------------------------------ validação
def test_validate_l10n_reports_errors_and_warnings() -> None:
    ref = {"ph": "Has %1 item", "tag": "{color_text}Hello", "long": "Ok", "stale": "Now", "slotless": "X",
           "exc": "{color_text}Hi"}
    slot = {"ph": "Tiene %1", "tag": "{color_text}Hola", "long": "Vale", "stale": "Ahora", "exc": "{color_text}Ho"}
    cat = l10n.Catalog("common", entries={
        "ph": _entry(ref["ph"], "Tem item", "translated"),                        # placeholder perdido
        "tag": _entry(ref["tag"], "Olá…", "translated"),                          # tag perdida + glifo
        "long": _entry(ref["long"], "Um texto bem mais comprido", "translated"),  # aviso de comprimento
        "stale": _entry("Then", "Agora", "translated"),                           # referência mudou
        "slotless": _entry(ref["slotless"], "X", "translated"),                   # sem slot
        "ghost": _entry("?", "Fantasma", "translated"),                           # ID inexistente
        "exc": _entry(ref["exc"], "Oi", "translated", exceptions=[
            {"code": "MARKUP_MISMATCH", "justification": "Tag removida por decisão editorial documentada."}]),
    })
    report = l10n.validate_l10n(cat, ref, slot, glyphs=frozenset(range(32, 127)) | {ord("á")})
    got = {(i.code, i.id, i.severity) for i in report.issues}
    assert ("PLACEHOLDER_MISMATCH", "ph", "error") in got
    assert ("MARKUP_MISMATCH", "tag", "error") in got and ("UNSUPPORTED_GLYPH", "tag", "error") in got
    assert ("LENGTH_OVER_SLOT", "long", "warning") in got
    assert ("STALE_SOURCE", "stale", "error") in got
    assert ("MISSING_IN_SLOT", "slotless", "error") in got
    assert ("UNKNOWN_ID", "ghost", "error") in got
    assert not any(i.id == "exc" for i in report.issues)  # exceção justificada suprime
    assert not report.ok


# ------------------------------------------------------------------ integração com o builder
def _catalogs(game: Path) -> dict[str, l10n.Catalog]:
    en = _tables(game, "en")
    return {
        "common": l10n.Catalog("common", entries={
            "menu_ok": _entry(en["common"]["menu_ok"], "PT {color_text}%1\\nfim", "translated", "approved"),
            "tooltip_x": _entry(en["common"]["tooltip_x"], "{a:left}Abc PT{color_white}def", "translated"),
        }),
        "game": l10n.Catalog("game", entries={
            "npc_talk_01": _entry(en["game"]["npc_talk_01"], "Fala um", "translated", "reviewed"),
            "npc_talk_02": _entry(en["game"]["npc_talk_02"]),  # pending
        }),
    }


def test_select_changes_respects_policy_and_hashes_slot(fake_game: Path) -> None:
    en, es = _tables(fake_game, "en"), _tables(fake_game, "es")
    project, cats = _project(fake_game), _catalogs(fake_game)
    approved = l10n.select_changes(project, cats, en, es, "approved")
    assert [(c.category, c.id) for c in approved.changes] == [("common", "menu_ok")]
    assert approved.changes[0].source_text_sha256 == l10n.text_sha256(es["common"]["menu_ok"])
    translated = l10n.select_changes(project, cats, en, es, "translated")
    assert {c.id for c in translated.changes} == {"menu_ok", "tooltip_x", "npc_talk_01"}
    assert "game/npc_talk_02" in translated.skipped["pending/pending"]


def test_select_changes_blocks_when_reference_changed(fake_game: Path) -> None:
    en, es = _tables(fake_game, "en"), _tables(fake_game, "es")
    cats = _catalogs(fake_game)
    en["common"]["menu_ok"] = "texto inglês atualizado"
    with pytest.raises(shadow.ShadowError, match="mudou"):
        l10n.select_changes(_project(fake_game), cats, en, es, "approved")


def test_end_to_end_build_changes_only_selected_entries(fake_game: Path, tmp_path: Path) -> None:
    en, es = _tables(fake_game, "en"), _tables(fake_game, "es")
    project = _project(fake_game)
    selection = l10n.select_changes(project, _catalogs(fake_game), en, es, "translated")
    patch = l10n.make_patch(project, "amostra", selection.changes)
    result = shadow.build_shadow(fake_game, patch, tmp_path / "work" / "shadow", reference=en,
                                 glyphs=game_supported_codepoints(fake_game), exceptions=selection.exceptions)
    for cat in ("common", "game"):
        name = text_file_name(cat, "es")
        old = load_text_table((fake_game / "base" / name).read_bytes(), cat, "es")
        new = load_text_table((result.pack_dir / name).read_bytes(), cat, "es")
        assert new.ids() == old.ids()  # todas as chaves do slot preservadas, na ordem
        changed = {k for (k, a), (_, b) in zip(old.entries, new.entries) if a != b}
        assert changed == {c.id for c in selection.changes if c.category == cat}
    es_game = load_text_table((result.pack_dir / text_file_name("game", "es")).read_bytes(), "game", "es")
    assert es_game.as_dict()["npc_cut_01"] == es["game"]["npc_cut_01"]  # chave extra do slot intocada
    assert shadow.verify_shadow(result.root, result.manifest) == []


def test_build_detects_game_update_via_project_hashes(fake_game: Path, tmp_path: Path) -> None:
    en, es = _tables(fake_game, "en"), _tables(fake_game, "es")
    project = _project(fake_game)
    selection = l10n.select_changes(project, _catalogs(fake_game), en, es, "approved")
    patch = l10n.make_patch(project, "amostra", selection.changes)
    en_file = fake_game / "base" / text_file_name("game", "en")
    en_file.write_bytes(en_file.read_bytes() + b"\x00")  # "atualização" de outra tabela
    with pytest.raises(shadow.ShadowError, match="diferente do esperado"):
        shadow.build_shadow(fake_game, patch, tmp_path / "work" / "shadow")


def test_make_patch_requires_changes_and_hashes(fake_game: Path) -> None:
    project = _project(fake_game)
    with pytest.raises(shadow.ShadowError):
        l10n.make_patch(project, "x", [])
    project.expected_files.pop(text_file_name("common", "es"))
    with pytest.raises(shadow.ShadowError):
        l10n.make_patch(project, "x", [shadow.Change("common", "menu_ok", "0" * 64, "a")])


# ------------------------------------------------------------------ catálogo real do repositório
def test_repository_catalog_is_canonical_and_scoped() -> None:
    root = REPO / "l10n" / "pt-BR"
    project = l10n.load_project(root / "project.json")
    assert (project.reference_language, project.target_slot, project.pack) == ("en", "es", "base")
    catalogs = l10n.load_catalogs(root)
    total = 0
    for category, catalog in catalogs.items():
        path = root / f"{category}.json"
        assert path.read_text(encoding="utf-8") == l10n.catalog_to_json(catalog)  # forma canônica
        for entry_id, entry in catalog.entries.items():
            # 98 chaves extras sem uso (só no slot es): torren_pushed_portal_* e torren_killed_regular_04+.
            # As demais falas do Torren (torren_second_meet_*, torren_killed_regular_01..03) existem em en.
            assert not re.fullmatch(r"torren_(pushed_portal_.*|killed_regular_(0[4-9]|[1-9]\d+))", entry_id)
            assert not entry_id.endswith("_no_localize")  # nunca traduzidas
            assert entry.translation_status in l10n.TRANSLATION_STATES
        total += len(catalog.entries)
    assert total > 0
    new_game = catalogs["common"].entries["menu_new_game"]
    # Revisão editorial 1F (caixa de frase) autorizada; aprovação preservada e registrada.
    assert (new_game.text, new_game.review_status) == ("Novo jogo", "approved")
    assert "1F" in new_game.review_note


def test_promote_batch_is_traceable_and_conservative() -> None:
    cat = l10n.Catalog("common", entries={
        "a": _entry("A", "Á", "translated", origin="ia:lote-01"),
        "b": _entry("B", "Bê", "translated", "approved", origin="ia:lote-01", review_note="humano"),
        "c": _entry("C", "Cê", "translated", origin="ia:lote-02"),
        "d": _entry("D", "Dê", "needs_review", origin="ia:lote-01"),
        "e": _entry("E", "Ê", "translated", origin="ia:lote-01"),
    })
    promoted = l10n.promote(cat, origin="ia:lote-01", to="approved", note="qa-lote:ia:lote-01", passing=["a", "b"])
    assert promoted == ["a"]
    assert cat.entries["a"].review_status == "approved" and cat.entries["a"].review_note == "qa-lote:ia:lote-01"
    assert cat.entries["b"].review_note == "humano"          # aprovada antes: intocada
    assert cat.entries["c"].review_status == "pending"       # outro lote
    assert cat.entries["e"].review_status == "pending"       # não passou no QA
    with pytest.raises(l10n.CatalogError):
        l10n.promote(cat, origin="ia:lote-01", to="approved", note=" ")
    again = l10n.catalog_from_dict(json.loads(l10n.catalog_to_json(cat)))
    assert again.entries["a"].origin == "ia:lote-01"


def test_length_warning_respects_justified_exception() -> None:
    ref, slot = {"a": "Stun"}, {"a": "Aturdido"}
    plain = l10n.Catalog("common", entries={"a": _entry("Stun", "Atordoamento prolongado", "translated")})
    assert any(i.code == "LENGTH_OVER_SLOT" for i in l10n.validate_l10n(plain, ref, slot).issues)
    waived = l10n.Catalog("common", entries={"a": _entry("Stun", "Atordoamento prolongado", "translated", exceptions=[
        {"code": "LENGTH_OVER_SLOT", "justification": "Painel comporta nomes maiores (verificado)."}])})
    assert not l10n.validate_l10n(waived, ref, slot).issues
