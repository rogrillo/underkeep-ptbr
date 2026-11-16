"""Pack-sombra: build, verificação, instalação e desinstalação em diretórios temporários.

Nada aqui toca a instalação real nem a pasta Documentos real.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import SECRET
from ukloc import shadow
from ukloc.fonts import game_supported_codepoints
from ukloc.textdb import load_text_table, text_file_name


# Preserva os tokens da referência sintética ({color_text}, %1 e \\n literal).
NEW_TEXT = "Novo Jogo {color_text}%1\\nfim"


def _patch_dict(game: Path, *, new_text: str = NEW_TEXT, entry_id: str = "menu_ok") -> dict:
    base = game / "base"
    es = load_text_table((base / text_file_name("common", "es")).read_bytes(), "common", "es").as_dict()
    return {
        "schema": shadow.PATCH_SCHEMA,
        "name": "teste_novo_jogo",
        "pack": "base",
        "slot": "es",
        "expected": {
            "game_build": None,
            "exe_sha256": shadow.file_sha256(game / "underkeep.exe"),
            "files": {text_file_name("common", "es"): shadow.file_sha256(base / text_file_name("common", "es"))},
        },
        "changes": [{"category": "common", "id": entry_id,
                     "source_text_sha256": shadow.text_sha256(es.get(entry_id, "")), "text": new_text}],
    }


def _reference(game: Path) -> dict[str, dict[str, str]]:
    data = (game / "base" / text_file_name("common", "en")).read_bytes()
    return {"common": load_text_table(data, "common", "en").as_dict()}


def _build(game: Path, out: Path, **kwargs) -> shadow.BuildResult:
    patch = shadow.parse_patch(_patch_dict(game, **kwargs))
    return shadow.build_shadow(game, patch, out, reference=_reference(game),
                               glyphs=game_supported_codepoints(game))


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    documents = tmp_path / "Documents"
    (documents / "Underkeep").mkdir(parents=True)  # o jogo já rodou ao menos uma vez
    return documents


def never_running() -> bool:
    return False


# ------------------------------------------------------------------ patch
def test_patch_rejects_invalid(fake_game: Path) -> None:
    good = _patch_dict(fake_game)
    shadow.parse_patch(good)
    for mutate in (lambda d: d.update(schema="x"),
                   lambda d: d["changes"][0].update(text=""),
                   lambda d: d["changes"][0].update(id=" "),
                   lambda d: d.update(pack="../base"),
                   lambda d: d["expected"].update(files={}),
                   lambda d: d["changes"].append(dict(d["changes"][0]))):
        bad = json.loads(json.dumps(good))
        mutate(bad)
        with pytest.raises(shadow.ShadowError):
            shadow.parse_patch(bad)


def test_real_patch_file_is_valid_and_has_no_original_text() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "patches" / "fase1c_a_novo_jogo.json"
    patch = shadow.load_patch(path)
    assert [(c.category, c.id, c.text) for c in patch.changes] == [("common", "menu_new_game", "Novo Jogo")]
    assert patch.changed_files() == ["text_text_common_es.txt.rfile"]
    assert "Nueva" not in path.read_text(encoding="utf-8")


# ------------------------------------------------------------------ build
def test_build_changes_only_target_entry(fake_game: Path, tmp_path: Path) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")
    m = result.manifest
    changed = text_file_name("common", "es")
    assert m["patched_files"] == [changed]
    assert set(m["shadow_files"]) == set(m["source"]["files"])
    for rel, digest in m["shadow_files"].items():
        same = digest == m["source"]["files"][rel]
        assert same is (rel != changed)
    old = load_text_table((fake_game / "base" / changed).read_bytes(), "common", "es")
    new = load_text_table((result.pack_dir / changed).read_bytes(), "common", "es")
    assert new.ids() == old.ids()
    diff = [k for (k, a), (_, b) in zip(old.entries, new.entries) if a != b]
    assert diff == ["menu_ok"] and new.as_dict()["menu_ok"] == NEW_TEXT
    assert result.manifest_path.parent.name == "base" and result.pack_dir.parent.name == "base"
    assert SECRET not in result.manifest_path.read_text(encoding="utf-8")  # sem texto original
    assert shadow.verify_shadow(result.root, m) == []
    assert shadow.stale_against_game(m, fake_game) == []


def test_build_is_deterministic_and_rebuild_replaces(fake_game: Path, tmp_path: Path) -> None:
    out = tmp_path / "work" / "shadow"
    first = _build(fake_game, out).manifest["shadow_files"]
    second = _build(fake_game, out).manifest["shadow_files"]
    assert first == second
    assert not out.with_name(out.name + ".tmp").exists()


def test_build_refuses_foreign_output_and_game_dir(fake_game: Path, tmp_path: Path) -> None:
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "user_file.txt").write_text("x")
    with pytest.raises(shadow.ShadowError):
        _build(fake_game, foreign)
    assert (foreign / "user_file.txt").exists()
    with pytest.raises(shadow.ShadowError):
        _build(fake_game, fake_game / "out")


@pytest.mark.parametrize("breaker", ["exe", "file", "source_text", "unknown_id"])
def test_preflight_failures_abort_before_writing(fake_game: Path, tmp_path: Path, breaker: str) -> None:
    data = _patch_dict(fake_game)
    if breaker == "exe":
        data["expected"]["exe_sha256"] = "0" * 64
    elif breaker == "file":
        data["expected"]["files"][text_file_name("common", "es")] = "0" * 64
    elif breaker == "source_text":
        data["changes"][0]["source_text_sha256"] = "0" * 64
    else:
        data["changes"][0]["id"] = "nao_existe"
    out = tmp_path / "work" / "shadow"
    with pytest.raises(shadow.ShadowError):
        shadow.build_shadow(fake_game, shadow.parse_patch(data), out)
    assert not out.exists()


@pytest.mark.parametrize("text", ["Novo…", "Novo %2", "Novo {color_text"])
def test_build_blocks_invalid_text(fake_game: Path, tmp_path: Path, text: str) -> None:
    out = tmp_path / "work" / "shadow"
    with pytest.raises(shadow.ShadowError, match="validação"):
        _build(fake_game, out, new_text=text)
    assert not out.exists()


def test_verify_detects_tampering(fake_game: Path, tmp_path: Path) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")
    victim = next(p for p in result.pack_dir.iterdir() if p.name.startswith("level_"))
    victim.write_bytes(victim.read_bytes() + b"x")
    (result.pack_dir / "extra.bin").write_bytes(b"1")
    problems = shadow.verify_shadow(result.root, result.manifest)
    assert any("hash divergente" in p for p in problems)
    assert any("conjunto de arquivos" in p for p in problems)


# ------------------------------------------------------------------ install / uninstall
def test_install_dry_run_changes_nothing(fake_game: Path, tmp_path: Path, docs: Path) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")
    before = sorted(p.relative_to(docs) for p in docs.rglob("*"))
    plan = shadow.install(result.root, docs, fake_game, running=never_running)
    assert plan.ok and not plan.executed
    assert plan.target == docs / "Underkeep" / "mods" / "base"
    assert sorted(p.relative_to(docs) for p in docs.rglob("*")) == before


def test_install_blocked_conditions(fake_game: Path, tmp_path: Path) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")
    no_app = tmp_path / "EmptyDocs"
    no_app.mkdir()
    plan = shadow.install(result.root, no_app, fake_game, execute=True, running=lambda: True)
    assert not plan.executed
    joined = " ".join(plan.problems)
    assert "nunca rodou" in joined and "em execução" in joined
    assert not (no_app / "Underkeep").exists()


def test_install_verify_uninstall_cycle(fake_game: Path, tmp_path: Path, docs: Path) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")
    plan = shadow.install(result.root, docs, fake_game, execute=True, running=never_running)
    assert plan.executed
    target = plan.target
    assert (target / "base" / text_file_name("common", "es")).is_file()
    assert json.loads((target / shadow.INSTALL_RECORD_NAME).read_text())["created_mods_dir"] is True
    assert not any(p.name.startswith(shadow.STAGING_PREFIX) for p in target.parent.iterdir())
    info = shadow.status(docs, "base", fake_game)
    assert info["installed"] and info["managed"] and info["problems"] == [] and info["stale"] == []
    again = shadow.install(result.root, docs, fake_game, execute=True, running=never_running)
    assert not again.executed and any("já existe" in p for p in again.problems)
    dry = shadow.uninstall(docs, "base", running=never_running)
    assert dry.ok and not dry.executed and target.exists()
    done = shadow.uninstall(docs, "base", execute=True, running=never_running)
    assert done.executed and not target.exists()
    assert not (docs / "Underkeep" / "mods").exists()  # criado por nós, removido vazio
    assert (docs / "Underkeep").is_dir()  # pasta do jogo preservada


def test_uninstall_keeps_preexisting_mods_dir(fake_game: Path, tmp_path: Path, docs: Path) -> None:
    mods = docs / "Underkeep" / "mods"
    (mods / "outro_mod").mkdir(parents=True)
    result = _build(fake_game, tmp_path / "work" / "shadow")
    assert shadow.install(result.root, docs, fake_game, execute=True, running=never_running).executed
    assert shadow.uninstall(docs, "base", execute=True, running=never_running).executed
    assert (mods / "outro_mod").is_dir()


def test_uninstall_refuses_tampered_or_unmanaged(fake_game: Path, tmp_path: Path, docs: Path) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")
    target = shadow.install(result.root, docs, fake_game, execute=True, running=never_running).target
    (target / "base" / "user_added.txt").write_text("arquivo do usuário")
    plan = shadow.uninstall(docs, "base", execute=True, running=never_running)
    assert not plan.executed and (target / "base" / "user_added.txt").exists()
    (target / "base" / "user_added.txt").unlink()
    (target / shadow.MANIFEST_NAME).unlink()
    plan = shadow.uninstall(docs, "base", execute=True, running=never_running)
    assert not plan.executed and any("não gerenciado" in p for p in plan.problems)
    assert target.exists()


def test_install_rolls_back_on_failure(fake_game: Path, tmp_path: Path, docs: Path,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")

    def boom(src, dst):
        raise OSError("falha simulada no rename")

    monkeypatch.setattr(shadow.os, "replace", boom)
    with pytest.raises(OSError):
        shadow.install(result.root, docs, fake_game, execute=True, running=never_running)
    assert not (docs / "Underkeep" / "mods").exists()


def test_install_blocked_when_game_changed(fake_game: Path, tmp_path: Path, docs: Path) -> None:
    result = _build(fake_game, tmp_path / "work" / "shadow")
    exe = fake_game / "underkeep.exe"
    exe.write_bytes(exe.read_bytes() + b"update")
    plan = shadow.install(result.root, docs, fake_game, execute=True, running=never_running)
    assert not plan.executed and any("executável" in p for p in plan.problems)
    assert not (docs / "Underkeep" / "mods").exists()


def test_cli_install_is_dry_run_by_default(fake_game: Path, tmp_path: Path, docs: Path,
                                           monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import importlib.util
    cli_path = Path(__file__).resolve().parents[1] / "scripts" / "ukloc_cli.py"
    spec = importlib.util.spec_from_file_location("ukloc_cli_test", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)  # type: ignore[union-attr]
    result = _build(fake_game, tmp_path / "work" / "shadow")
    monkeypatch.setattr(shadow, "is_game_running", never_running)  # mesmo módulo usado pela CLI
    code = cli.main(["--game-root", str(fake_game), "shadow-install", "--shadow", str(result.root),
                     "--documents", str(docs)])
    assert code == 0
    assert "DRY-RUN" in capsys.readouterr().out
    assert not (docs / "Underkeep" / "mods").exists()
