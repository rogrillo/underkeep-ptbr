"""Atualização do jogo com uma tradução anterior instalada (Fase 2A), em instalações sintéticas.

Simula: Beta anterior instalada → o jogo é atualizado (executável e tabelas mudam) → o instalador antigo
recusa a build nova → o instalador novo encontra a versão antiga, remove-a com o manifesto dela e instala a
nova. Nada do jogo real nem da pasta Documentos real é usado.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ukloc import installer, l10n, shadow
from ukloc.textdb import TextTable, build_text_table_bytes, load_text_table, text_file_name

OLD_PATCH = "underkeep-ptbr-0.1.0-beta.2"


def never_running() -> bool:
    return False


def always_running() -> bool:
    return True


def _project(game: Path, root: Path, text: str) -> Path:
    """Catálogo sintético com os hashes ATUAIS do jogo falso."""
    root.mkdir(parents=True, exist_ok=True)
    base = game / "base"
    files = {text_file_name(c, lang): shadow.file_sha256(base / text_file_name(c, lang))
             for c in ("common", "game") for lang in ("en", "es")}
    project = {"schema": l10n.PROJECT_SCHEMA, "locale": "pt-BR", "reference_language": "en", "target_slot": "es",
               "pack": "base", "expected": {"exe_sha256": shadow.file_sha256(game / "underkeep.exe"),
                                            "files": files, "game_build": None}}
    (root / "project.json").write_text(json.dumps(project), encoding="utf-8")
    en = load_text_table((base / text_file_name("common", "en")).read_bytes(), "common", "en").as_dict()
    catalog = l10n.Catalog("common", entries={"menu_ok": l10n.Entry(
        source_sha256=l10n.text_sha256(en["menu_ok"]), text=text, translation_status="translated", origin="teste")})
    l10n.save_catalog(root / "common.json", catalog)
    return root


def _update_game(game: Path) -> None:
    """Simula a atualização do jogo: executável novo e referência en alterada."""
    (game / "underkeep.exe").write_bytes(b"MZ\x00build nova\x00")
    path = game / "base" / text_file_name("common", "en")
    table = load_text_table(path.read_bytes(), "common", "en")
    entries = [(k, v + " (1.0.6)" if k == "tooltip_x" else v) for k, v in table.entries]
    path.write_bytes(build_text_table_bytes(TextTable("common", "en", table.version, entries)))
    (game / "base" / "novo_recurso.png").write_bytes(b"recurso novo da build")


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    documents = tmp_path / "Documents"
    (documents / "Underkeep").mkdir(parents=True)
    (documents / "Underkeep" / "save_1").write_bytes(b"save sintetico")
    return documents


@pytest.fixture
def old_install(fake_game: Path, docs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Beta anterior instalada sobre a build antiga; devolve o catálogo antigo."""
    old_root = _project(fake_game, tmp_path / "beta2" / "pt-BR", "Velho {color_text}%1\\nfim")
    monkeypatch.setattr(installer, "PATCH_NAME", OLD_PATCH)
    work = tmp_path / "tmp"
    work.mkdir()
    assert installer.install(fake_game, docs, old_root, execute=True, running=never_running, workdir=work).executed
    monkeypatch.setattr(installer, "PATCH_NAME", "underkeep-ptbr-0.1.0-beta.3")
    return old_root


def test_game_update_makes_old_pack_stale(fake_game: Path, docs: Path, old_install: Path) -> None:
    _update_game(fake_game)
    manifest = shadow.read_manifest(docs / "Underkeep" / "mods" / "base")
    stale = shadow.stale_against_game(manifest, fake_game)
    assert any("executável" in p for p in stale) and any("mudou" in p for p in stale)
    # O pack antigo é uma cópia INTEGRAL da build anterior: não tem o recurso novo (por isso deve ser removido).
    assert not (docs / "Underkeep" / "mods" / "base" / "base" / "novo_recurso.png").exists()


def test_old_installer_refuses_new_build_and_points_to_uninstall(fake_game: Path, docs: Path,
                                                                 old_install: Path) -> None:
    _update_game(fake_game)
    lines: list[str] = []
    code = installer.main(["--jogo", str(fake_game), "--documentos", str(docs), "--traducao", str(old_install),
                           "--sim"], out=lines.append, running=never_running, pause=False)
    assert code == installer.EXIT_BLOCKED
    assert any("não suportada" in line for line in lines)
    assert any("desinstale a tradução" in line for line in lines)


def test_old_pack_can_be_uninstalled_after_game_update(fake_game: Path, docs: Path, old_install: Path) -> None:
    _update_game(fake_game)
    before = (docs / "Underkeep" / "save_1").read_bytes()
    assert installer.uninstall(docs, execute=True, running=never_running).executed
    assert not (docs / "Underkeep" / "mods").exists()
    assert (docs / "Underkeep" / "save_1").read_bytes() == before


def test_new_installer_replaces_old_version_after_update(fake_game: Path, docs: Path, old_install: Path,
                                                         tmp_path: Path) -> None:
    _update_game(fake_game)
    new_root = _project(fake_game, tmp_path / "beta3" / "pt-BR", "Novo {color_text}%1\\nfim")
    lines: list[str] = []
    code = installer.main(["--jogo", str(fake_game), "--documentos", str(docs), "--traducao", str(new_root), "--sim"],
                          out=lines.append, running=never_running, pause=False)
    assert code == installer.EXIT_OK, lines
    assert any("Versão anterior removida" in line for line in lines)
    target = docs / "Underkeep" / "mods" / "base"
    manifest = shadow.read_manifest(target)
    assert manifest["patch"] == "underkeep-ptbr-0.1.0-beta.3"
    assert shadow.stale_against_game(manifest, fake_game) == []
    assert (target / "base" / "novo_recurso.png").exists()
    es = load_text_table((target / "base" / text_file_name("common", "es")).read_bytes(), "common", "es").as_dict()
    assert es["menu_ok"] == "Novo {color_text}%1\\nfim"


def test_new_installer_only_checks_when_verifying(fake_game: Path, docs: Path, old_install: Path,
                                                  tmp_path: Path) -> None:
    _update_game(fake_game)
    new_root = _project(fake_game, tmp_path / "beta3" / "pt-BR", "Novo {color_text}%1\\nfim")
    before = shadow.hash_tree(docs)
    lines: list[str] = []
    code = installer.main(["--jogo", str(fake_game), "--documentos", str(docs), "--traducao", str(new_root),
                           "--verificar"], out=lines.append, running=never_running, pause=False)
    assert code == installer.EXIT_BLOCKED  # versão antiga ainda instalada; nada foi removido
    assert shadow.hash_tree(docs) == before


def test_update_blocked_while_game_is_running(fake_game: Path, docs: Path, old_install: Path,
                                              tmp_path: Path) -> None:
    _update_game(fake_game)
    new_root = _project(fake_game, tmp_path / "beta3" / "pt-BR", "Novo {color_text}%1\\nfim")
    before = shadow.hash_tree(docs)
    code = installer.main(["--jogo", str(fake_game), "--documentos", str(docs), "--traducao", str(new_root), "--sim"],
                          out=lambda _l: None, running=always_running, pause=False)
    assert code == installer.EXIT_BLOCKED
    assert not installer.uninstall(docs, execute=True, running=always_running).executed
    assert shadow.hash_tree(docs) == before


def test_third_party_mods_survive_the_update(fake_game: Path, docs: Path, old_install: Path,
                                             tmp_path: Path) -> None:
    other = docs / "Underkeep" / "mods" / "outro_mod"
    other.mkdir()
    (other / "arquivo.txt").write_text("mod de terceiro", encoding="utf-8")
    _update_game(fake_game)
    new_root = _project(fake_game, tmp_path / "beta3" / "pt-BR", "Novo {color_text}%1\\nfim")
    lines: list[str] = []
    assert installer.main(["--jogo", str(fake_game), "--documentos", str(docs), "--traducao", str(new_root), "--sim"],
                          out=lines.append, running=never_running, pause=False) == installer.EXIT_OK
    assert (other / "arquivo.txt").read_text(encoding="utf-8") == "mod de terceiro"
    assert any("outro mod detectado" in line for line in lines)


def test_foreign_mods_base_is_never_replaced(fake_game: Path, docs: Path, tmp_path: Path) -> None:
    foreign = docs / "Underkeep" / "mods" / "base"
    foreign.mkdir(parents=True)
    (foreign / "do_outro_mod.txt").write_text("x", encoding="utf-8")
    new_root = _project(fake_game, tmp_path / "beta3" / "pt-BR", "Novo {color_text}%1\\nfim")
    code = installer.main(["--jogo", str(fake_game), "--documentos", str(docs), "--traducao", str(new_root), "--sim"],
                          out=lambda _l: None, running=never_running, pause=False)
    assert code == installer.EXIT_BLOCKED
    assert sorted(p.name for p in foreign.iterdir()) == ["do_outro_mod.txt"]
    assert not installer.uninstall(docs, execute=True, running=never_running).executed
