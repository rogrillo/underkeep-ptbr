"""Pasta local externa (UKLOC_LOCAL_DIR): material do jogo fisicamente fora do repositório."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ukloc.catalog import LOCAL_DIR_ENV, ensure_untracked_output, external_local_dir, local_roots

ROOT = Path(__file__).resolve().parents[1]


def test_without_variable_uses_ignored_project_folders(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    assert external_local_dir(project, {}) is None
    assert local_roots(project, {}) == (project / "work", project / "audit" / "local")


def test_external_folder_outside_repo(tmp_path: Path) -> None:
    project, local = tmp_path / "repo", tmp_path / "underkeep-ptbr-local"
    env = {LOCAL_DIR_ENV: str(local)}
    work, audit = local_roots(project, env)
    assert (work, audit) == (local.resolve() / "work", local.resolve() / "audit")
    assert ensure_untracked_output(work / "extract" / "x.json", project, environ=env)
    assert ensure_untracked_output(project / "work" / "x.json", project, environ=env)  # padrão continua aceito


@pytest.mark.parametrize("inside", [".", "docs", "work"])
def test_external_folder_inside_repo_is_refused(tmp_path: Path, inside: str) -> None:
    project = tmp_path / "repo"
    with pytest.raises(ValueError, match="fora do repositório"):
        local_roots(project, {LOCAL_DIR_ENV: str(project / inside)})


def test_output_elsewhere_or_in_game_is_refused(tmp_path: Path) -> None:
    project, local, game = tmp_path / "repo", tmp_path / "local", tmp_path / "game"
    env = {LOCAL_DIR_ENV: str(local)}
    with pytest.raises(ValueError, match="saída deve ficar"):
        ensure_untracked_output(tmp_path / "outro" / "x.json", project, environ=env)
    with pytest.raises(ValueError, match="instalação do jogo"):
        ensure_untracked_output(game / "x.json", project, game, environ={LOCAL_DIR_ENV: str(game)})


def _inventory_module():
    spec = importlib.util.spec_from_file_location("audit_inventory", ROOT / "scripts" / "audit_inventory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_default_output_goes_to_external_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    game, local = tmp_path / "game", tmp_path / "local"
    game.mkdir()
    (game / "underkeep.exe").write_bytes(b"MZ")
    monkeypatch.setenv(LOCAL_DIR_ENV, str(local))
    assert _inventory_module().main(["--game-root", str(game)]) == 0
    data = json.loads((local / "audit" / "inventory.json").read_text(encoding="utf-8"))
    assert data["file_count"] == 1
