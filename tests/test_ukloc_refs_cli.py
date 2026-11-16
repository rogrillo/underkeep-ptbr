"""Análise de referências e CLI ponta a ponta sobre um jogo sintético."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from conftest import SECRET
from ukloc.fonts import game_supported_codepoints
from ukloc.refs import analyze, collect_def_references, dialogue_context, exe_identifiers, script_identifiers
from ukloc.textdb import find_text_tables, load_text_table

spec = importlib.util.spec_from_file_location(
    "ukloc_cli", Path(__file__).resolve().parents[1] / "scripts" / "ukloc_cli.py")
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
sys.modules["ukloc_cli"] = cli
spec.loader.exec_module(cli)


def load_all(game: Path):
    return {k: load_text_table(p.read_bytes(), *k) for k, p in find_text_tables(game / "base").items()}


def test_script_identifiers_ignore_comments():
    ids = script_identifiers("say npc_a_01\n// say [[npc_b_01 texto]]\nsay npc_a_02")
    assert {"npc_a_01", "npc_a_02"} <= ids and "npc_b_01" not in ids


def test_reference_analysis(fake_game):
    tables = load_all(fake_game)
    refs = collect_def_references(fake_game / "base")
    report = analyze(tables, refs, exe_identifiers((fake_game / "underkeep.exe").read_bytes()))
    game = report["categories"]["game"]
    assert {x["id"]: x["ref"] for x in game["only_in_other_languages"]} == {
        "npc_talk_03": "none", "npc_cut_01": "none"}
    common = report["categories"]["common"]
    assert {x["id"]: x["ref"] for x in common["only_in_reference"]} == {"credits_no_localize": "exe"}
    assert report["text_fields"]["text"]["kind"] == "text_field"
    assert "enter_text" not in report["text_fields"]  # menos de 5 valores
    context = dialogue_context(tables[("game", "en")], refs, extra_ids=tables[("game", "es")].ids())
    talk = next(g for g in context if g["group"] == "npc_talk")
    assert talk["ids"] == ["npc_talk_01", "npc_talk_02", "npc_talk_03"]
    assert talk["referenced_by"] == ["def_def.txt.rfile"]


def test_glyph_intersection(fake_game):
    glyphs = game_supported_codepoints(fake_game)
    assert ord("ã") in glyphs and 0x2026 not in glyphs


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    (root / "work").mkdir(parents=True)
    (root / "audit" / "local").mkdir(parents=True)
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    return root


def test_cli_end_to_end(fake_game, project, capsys):
    g = ["--game-root", str(fake_game)]
    assert cli.main(g + ["roundtrip"]) == 0
    assert cli.main(g + ["gate-unchanged"]) == 0
    assert cli.main(g + ["extract", "--out", str(project / "work" / "ex"),
                         "--analysis", str(project / "audit" / "local" / "a.json")]) == 0
    catalog = project / "work" / "ex" / "catalog" / "common_en.json"
    assert json.loads(catalog.read_text(encoding="utf-8"))["entries"][0]["id"] == "menu_ok"
    analysis = (project / "audit" / "local" / "a.json").read_text(encoding="utf-8")
    assert SECRET not in analysis  # análise só com IDs e contagens
    assert cli.main(g + ["pseudo", "--out-dir", str(project / "work" / "pseudo"),
                         "--exceptions", str(Path(__file__).resolve().parents[1] / "data" /
                                             "validation_exceptions.json")]) == 0
    built = project / "work" / "pseudo" / "text_text_common_es.txt.rfile"
    pseudo_table = load_text_table(built.read_bytes(), "common", "es")
    assert pseudo_table.as_dict()["credits_no_localize"].startswith(SECRET)  # _no_localize intacto
    assert "[!!" in pseudo_table.as_dict()["menu_ok"]
    assert cli.main(g + ["build", "--catalog", str(catalog), "--language", "es",
                         "--out-dir", str(project / "work" / "b")]) == 0
    assert cli.main(g + ["validate", "--catalog", str(catalog)]) == 0  # en x en: só avisos UNTRANSLATED
    es_catalog = project / "work" / "ex" / "catalog" / "common_es.json"
    assert cli.main(g + ["validate", "--catalog", str(es_catalog)]) == 2  # MISSING_ID credits_no_localize
    assert cli.main(g + ["inspect-db", "--report", str(project / "audit" / "local" / "db.json")]) == 0
    db = json.loads((project / "audit" / "local" / "db.json").read_text(encoding="utf-8"))
    assert db["rfile_name_rule"]["file_equals_name_slash_to_underscore_plus_rfile"] is True


def test_cli_refuses_outputs_outside_work_or_in_game(fake_game, project):
    g = ["--game-root", str(fake_game)]
    assert cli.main(g + ["extract", "--out", str(project / "docs"),
                         "--analysis", str(project / "audit" / "local" / "a.json")]) == 1
    assert cli.main(g + ["pseudo", "--out-dir", str(fake_game / "base")]) == 1
    assert not (project / "docs").exists()
    assert not list((fake_game / "base").glob("*.json"))


def test_cli_never_modifies_game(fake_game, project):
    before = {p: p.read_bytes() for p in fake_game.rglob("*") if p.is_file()}
    g = ["--game-root", str(fake_game)]
    cli.main(g + ["extract", "--out", str(project / "work" / "ex"),
                  "--analysis", str(project / "audit" / "local" / "a.json")])
    cli.main(g + ["pseudo", "--out-dir", str(project / "work" / "p")])
    after = {p: p.read_bytes() for p in fake_game.rglob("*") if p.is_file()}
    assert before == after
