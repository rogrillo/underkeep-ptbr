"""Auditoria e ZIP determinístico do script de release (sem PyInstaller e sem arquivos do jogo)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_release", ROOT / "scripts" / "build_release.py")
br = importlib.util.module_from_spec(spec)
sys.modules["build_release"] = br  # necessário para @dataclass em módulo carregado por caminho
assert spec.loader is not None
spec.loader.exec_module(br)


def _zip(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in files.items():
            zf.writestr(f"{br.PACKAGE_NAME}/{name}", data)
    return path


def test_audit_flags_game_files_private_data_and_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(br, "private_markers", lambda: [b"usuario-secreto"])
    path = _zip(tmp_path / "a.zip", {"base/text_text_game_es.txt.rfile": b"x",
                                     "LEIA-ME.txt": b"caminho C:/Users/usuario-secreto/x"})
    problems = br.audit_zip(path)
    assert any("arquivo proibido" in p for p in problems)
    assert any("dado privado" in p for p in problems)
    assert any("faltando no pacote" in p for p in problems)


def test_audit_flags_unexpected_catalog_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(br, "private_markers", lambda: [])
    catalog = b'{"entries": {"x": {"source_sha256": "0", "source_text": "ORIGINAL"}}}'
    path = _zip(tmp_path / "b.zip", {"dados/pt-BR/game.json": catalog})
    assert any("campo inesperado" in p for p in br.audit_zip(path))


def test_make_zip_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage = tmp_path / "stage"
    (stage / "dados").mkdir(parents=True)
    (stage / "LEIA-ME.txt").write_text("oi", encoding="utf-8")
    (stage / "dados" / "a.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(br, "DIST_DIR", tmp_path / "d1")
    first = br.file_sha256(br.make_zip(stage))
    monkeypatch.setattr(br, "DIST_DIR", tmp_path / "d2")
    second = br.make_zip(stage)
    assert br.file_sha256(second) == first
    assert second.with_name(second.name + ".sha256").read_text(encoding="ascii").startswith(first)
