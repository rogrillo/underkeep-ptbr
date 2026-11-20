"""Acréscimo controlado de IDs ausentes no slot (Fase 2A) e comparação entre builds (dados sintéticos)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from ukloc import l10n, shadow
from ukloc.textdb import TextTable, build_text_table_bytes, load_text_table, text_file_name

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compare_builds  # noqa: E402

ADD_EXC = [{"code": "MISSING_IN_SLOT", "justification": "entrada nova só no en; acrescentar ao slot"}]


def _table(entries: list[tuple[str, str]], category: str = "common", lang: str = "es") -> bytes:
    return build_text_table_bytes(TextTable(category, lang, 1, entries))


# ------------------------------------------------------------------ apply_changes
def test_addition_is_appended_and_preserves_original_order() -> None:
    original = _table([("a", "A es"), ("b", "B es")])
    changes = [shadow.Change("common", "novo", shadow.ABSENT_SHA256, "Novo {color_text}", add=True),
               shadow.Change("common", "a", shadow.text_sha256("A es"), "A pt")]
    result = shadow.apply_changes(original, "common", "es", changes,
                                  reference={"a": "A en", "b": "B en", "novo": "New {color_text}"})
    table = load_text_table(result.data, "common", "es")
    assert table.entries == [("a", "A pt"), ("b", "B es"), ("novo", "Novo {color_text}")]
    assert result.changed_ids == ["a", "novo"]


@pytest.mark.parametrize("change, reference, message", [
    (shadow.Change("common", "a", shadow.ABSENT_SHA256, "x", add=True), {"a": "A"}, "já existe"),
    (shadow.Change("common", "z", shadow.ABSENT_SHA256, "x", add=True), {"a": "A"}, "não existe na referência"),
    (shadow.Change("common", "z", "0" * 64, "x", add=True), {"z": "Z"}, "hash de ausência"),
])
def test_invalid_additions_are_refused(change: shadow.Change, reference: dict[str, str], message: str) -> None:
    with pytest.raises(shadow.ShadowError, match=message):
        shadow.apply_changes(_table([("a", "A es")]), "common", "es", [change], reference=reference)


def test_addition_is_validated_like_any_translation() -> None:
    change = shadow.Change("common", "z", shadow.ABSENT_SHA256, "sem placeholder", add=True)
    with pytest.raises(shadow.ShadowError, match="PLACEHOLDER_MISMATCH"):
        shadow.apply_changes(_table([("a", "A es")]), "common", "es", [change], reference={"z": "valor %1"})


# ------------------------------------------------------------------ patch
def _patch_dict(**change: object) -> dict:
    return {"schema": shadow.PATCH_SCHEMA, "name": "p", "pack": "base", "slot": "es",
            "expected": {"exe_sha256": "0" * 64, "files": {text_file_name("common", "es"): "1" * 64}},
            "changes": [{"category": "common", "id": "z", "text": "t", **change}]}


def test_patch_add_flag_requires_bool_and_absent_hash() -> None:
    patch = shadow.parse_patch(_patch_dict(source_text_sha256=shadow.ABSENT_SHA256, add=True))
    assert patch.changes[0].add
    with pytest.raises(shadow.ShadowError, match="booleano"):
        shadow.parse_patch(_patch_dict(source_text_sha256=shadow.ABSENT_SHA256, add="sim"))
    with pytest.raises(shadow.ShadowError, match="texto vazio"):
        shadow.parse_patch(_patch_dict(source_text_sha256="2" * 64, add=True))
    assert not shadow.parse_patch(_patch_dict(source_text_sha256="2" * 64)).changes[0].add


# ------------------------------------------------------------------ catálogo
def _catalog(exceptions: list[dict[str, str]]) -> l10n.Catalog:
    return l10n.Catalog("common", entries={"z": l10n.Entry(
        source_sha256=l10n.text_sha256("Z en"), text="Z pt", translation_status="translated",
        exceptions=list(exceptions))})


def test_missing_in_slot_needs_explicit_exception() -> None:
    blocked = l10n.validate_l10n(_catalog([]), {"z": "Z en"}, {"a": "A es"})
    assert [i.code for i in blocked.errors] == ["MISSING_IN_SLOT"]
    allowed = l10n.validate_l10n(_catalog(ADD_EXC), {"z": "Z en"}, {"a": "A es"})
    assert allowed.ok and [i.code for i in allowed.issues] == ["SLOT_ADDITION"]


def test_select_changes_marks_additions() -> None:
    project = l10n.Project("pt-BR", "en", "es", "base", None, "0" * 64, {text_file_name("common", "es"): "1" * 64})
    ref, slot = {"common": {"z": "Z en"}}, {"common": {"a": "A es"}}
    with pytest.raises(shadow.ShadowError, match="ausente no slot"):
        l10n.select_changes(project, {"common": _catalog([])}, ref, slot, "translated")
    selection = l10n.select_changes(project, {"common": _catalog(ADD_EXC)}, ref, slot, "translated")
    assert selection.changes == [shadow.Change("common", "z", shadow.ABSENT_SHA256, "Z pt", add=True)]


# ------------------------------------------------------------------ build completo
def _patch_for(game: Path, changes: list[shadow.Change]) -> shadow.Patch:
    base = game / "base"
    files = {p.name: shadow.file_sha256(p) for p in base.glob("text_text_*")}
    return shadow.Patch("teste-add", "base", "es", None, shadow.file_sha256(game / "underkeep.exe"), files,
                        tuple(changes))


def test_build_shadow_with_addition_verifies(fake_game: Path, tmp_path: Path) -> None:
    en = load_text_table((fake_game / "base" / text_file_name("common", "en")).read_bytes(), "common", "en")
    # "credits_no_localize" existe no en e não no es do jogo falso: candidato a acréscimo.
    change = shadow.Change("common", "credits_no_localize", shadow.ABSENT_SHA256,
                           en.as_dict()["credits_no_localize"], add=True)
    result = shadow.build_shadow(fake_game, _patch_for(fake_game, [change]), tmp_path / "out",
                                 reference={"common": en.as_dict()})
    assert shadow.verify_shadow(result.root, result.manifest) == []
    assert result.manifest["changes"][0]["add"] is True
    table = load_text_table((result.pack_dir / text_file_name("common", "es")).read_bytes(), "common", "es")
    assert table.ids()[-1] == "credits_no_localize"


def test_build_shadow_refuses_cross_category_duplicate(fake_game: Path, tmp_path: Path) -> None:
    # "npc_talk_01" existe no es de game; acrescentá-lo em common repetiria o ID na fusão do jogo.
    change = shadow.Change("common", "npc_talk_01", shadow.ABSENT_SHA256, "x", add=True)
    with pytest.raises(shadow.ShadowError, match="repetiria o ID"):
        shadow.build_shadow(fake_game, _patch_for(fake_game, [change]), tmp_path / "out")
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------ compare_builds
def _write_extract(root: Path, build: str, tables: dict[tuple[str, str], list[tuple[str, str]]]) -> Path:
    (root / "catalog").mkdir(parents=True)
    for (category, lang), entries in tables.items():
        data = {"schema": "ukloc.catalog/1", "category": category, "language": lang, "dft_version": 1,
                "game_build": build, "source_sha256": "0" * 64,
                "entries": [{"id": i, "index": n, "source_sha256": "", "text": t} for n, (i, t) in enumerate(entries)]}
        (root / "catalog" / f"{category}_{lang}.json").write_text(json.dumps(data), encoding="utf-8")
    return root


def test_compare_builds_classifies_entries(tmp_path: Path) -> None:
    old = _write_extract(tmp_path / "old", "1", {
        ("common", "en"): [("same", "S"), ("edit", "E {color_text}"), ("slot", "L"), ("gone", "G")],
        ("common", "es"): [("same", "S es"), ("edit", "E es"), ("slot", "L es"), ("gone", "G es")],
        ("skills", "en"): [("moved", "M")], ("skills", "es"): [("moved", "M es")]})
    new = _write_extract(tmp_path / "new", "2", {
        ("common", "en"): [("same", "S"), ("edit", "E2"), ("slot", "L"), ("fresh", "G"), ("moved", "M")],
        ("common", "es"): [("same", "S es"), ("edit", "E es"), ("slot", "L es 2"), ("moved", "M es")],
        ("skills", "en"): [], ("skills", "es"): []})
    cat = tmp_path / "l10n"
    cat.mkdir()
    for category, ids in (("common", {"same": "S", "edit": "E {color_text}"}), ("skills", {"moved": "M"})):
        entries = {i: {"source_sha256": compare_builds.text_sha256(t)} for i, t in ids.items()}
        (cat / f"{category}.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")
    report = compare_builds.compare(old, new, cat, ("common", "skills"))
    common = report["categories"]["common"]
    assert common["added"] == ["fresh", "moved"] and common["removed"] == ["gone"]
    assert common["changed"] == ["edit"] and common["token_changes"] == ["edit"] and common["slot_only"] == ["slot"]
    assert common["catalog"]["needs_review"] == ["edit"]
    assert any("sem correspondente no slot es" in s for s in common["structural"])
    assert report["moved"] == [{"id": "moved", "from": "skills", "to": "common"}]
    assert report["renamed"] == [{"from": "common/gone", "to": "common/fresh"}]
    assert report["categories"]["skills"]["catalog"]["orphaned"] == ["moved"]
    assert "S es" not in json.dumps(report)  # nenhum texto original no relatório


def test_compare_builds_cli_reports_missing_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert compare_builds.main(["--old", str(tmp_path / "x"), "--new", str(tmp_path / "y"),
                                "--l10n", str(tmp_path)]) == 1
    assert "ERRO" in capsys.readouterr().err
