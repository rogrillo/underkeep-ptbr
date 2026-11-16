"""Instalador do jogador e descoberta da Steam, em instalações sintéticas (nada real é tocado)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ukloc import installer, l10n, shadow, steam
from ukloc.textdb import load_text_table, text_file_name

NEW_TEXT = "Novo Jogo {color_text}%1\\nfim"


def never_running() -> bool:
    return False


def always_running() -> bool:
    return True


def _hashes(root: Path) -> dict[str, str]:
    return shadow.hash_tree(root)


@pytest.fixture
def l10n_root(fake_game: Path, tmp_path: Path) -> Path:
    """Catálogo PT-BR sintético compatível com o jogo falso (sem texto original, só hashes)."""
    root = tmp_path / "dados" / "pt-BR"
    root.mkdir(parents=True)
    base = fake_game / "base"
    files = {text_file_name(c, "es"): shadow.file_sha256(base / text_file_name(c, "es")) for c in ("common", "game")}
    project = {"schema": l10n.PROJECT_SCHEMA, "locale": "pt-BR", "reference_language": "en", "target_slot": "es",
               "pack": "base", "expected": {"exe_sha256": shadow.file_sha256(fake_game / "underkeep.exe"),
                                            "files": files, "game_build": None}}
    (root / "project.json").write_text(json.dumps(project), encoding="utf-8")
    en = load_text_table((base / text_file_name("common", "en")).read_bytes(), "common", "en").as_dict()
    catalog = l10n.Catalog("common", entries={"menu_ok": l10n.Entry(
        source_sha256=l10n.text_sha256(en["menu_ok"]), text=NEW_TEXT, translation_status="translated",
        origin="teste")})
    l10n.save_catalog(root / "common.json", catalog)
    return root


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    documents = tmp_path / "Documents"
    (documents / "Underkeep").mkdir(parents=True)
    (documents / "Underkeep" / "save_1").write_bytes(b"save sintetico")
    return documents


def _install(fake_game: Path, docs: Path, l10n_root: Path, tmp_path: Path, **kwargs) -> installer.Outcome:
    work = tmp_path / "tmp"
    work.mkdir(exist_ok=True)
    return installer.install(fake_game, docs, l10n_root, running=kwargs.pop("running", never_running),
                             workdir=work, **kwargs)


# ------------------------------------------------------------------ Steam
def test_vdf_pairs_unescape_windows_paths() -> None:
    text = '"libraryfolders"\n{\n "0"\n {\n  "path"  "D:\\\\Jogos\\\\Steam"\n  "label" ""\n }\n}\n'
    assert ("path", r"D:\Jogos\Steam") in steam.vdf_pairs(text)


def test_find_game_in_secondary_library(tmp_path: Path) -> None:
    root, lib = tmp_path / "Steam", tmp_path / "Biblioteca 2"
    (root / "steamapps").mkdir(parents=True)
    escaped = str(lib).replace("\\", "\\\\")
    (root / "steamapps" / "libraryfolders.vdf").write_text(
        f'"libraryfolders"\n{{\n "1"\n {{\n  "path" "{escaped}"\n }}\n}}\n', encoding="utf-8")
    game = lib / "steamapps" / "common" / "UnderkeepDir"
    game.mkdir(parents=True)
    (game / "underkeep.exe").write_bytes(b"MZ")
    (lib / "steamapps" / "appmanifest_2411200.acf").write_text(
        '"AppState"\n{\n "appid" "2411200"\n "installdir" "UnderkeepDir"\n "buildid" "123"\n}\n', encoding="utf-8")
    assert steam.find_game_dirs([root, root]) == [game]
    assert steam.game_build(game) == "123"


def test_find_game_none_and_missing_roots(tmp_path: Path) -> None:
    assert steam.find_game_dirs([tmp_path / "nao_existe"]) == []


def test_normalize_game_path_accepts_exe_and_quotes(tmp_path: Path) -> None:
    exe = tmp_path / "Underkeep" / "underkeep.exe"
    assert installer.normalize_game_path(f'"{exe}"') == exe.parent


# ------------------------------------------------------------------ verificação
def test_check_game_ok_and_incompatible(fake_game: Path, l10n_root: Path) -> None:
    project = installer.load_project(l10n_root)
    assert installer.check_game(fake_game, project).ok
    (fake_game / "underkeep.exe").write_bytes(b"MZ outra build")
    problems = installer.check_game(fake_game, project).problems
    assert any("versão do jogo não suportada" in p for p in problems)


def test_check_game_detects_changed_text_file(fake_game: Path, l10n_root: Path) -> None:
    project = installer.load_project(l10n_root)
    target = fake_game / "base" / text_file_name("game", "es")
    target.write_bytes(target.read_bytes() + b"\x00")
    assert any("diferente(s) do esperado" in p for p in installer.check_game(fake_game, project).problems)


def test_missing_catalog_is_clear_error(tmp_path: Path) -> None:
    with pytest.raises(installer.InstallerError, match="extraia o ZIP"):
        installer.load_project(tmp_path / "vazio")


# ------------------------------------------------------------------ instalação
def test_dry_run_changes_nothing(fake_game: Path, docs: Path, l10n_root: Path, tmp_path: Path) -> None:
    before_game, before_docs = _hashes(fake_game), _hashes(docs)
    outcome = _install(fake_game, docs, l10n_root, tmp_path)
    assert outcome.plan.ok and not outcome.executed
    assert _hashes(fake_game) == before_game and _hashes(docs) == before_docs


def test_full_cycle_install_duplicate_uninstall(fake_game: Path, docs: Path, l10n_root: Path, tmp_path: Path) -> None:
    before_game = _hashes(fake_game)
    outcome = _install(fake_game, docs, l10n_root, tmp_path, execute=True)
    assert outcome.executed and outcome.changes == 1
    target = docs / "Underkeep" / "mods" / "base"
    table = load_text_table((target / "base" / text_file_name("common", "es")).read_bytes(), "common", "es")
    assert table.as_dict()["menu_ok"] == NEW_TEXT
    assert installer.target_state(docs, "base").kind == "current"
    assert list((tmp_path / "tmp").iterdir()) == []  # temporários apagados
    # duplicada: bloqueada sem alterar nada
    snapshot = _hashes(docs)
    again = _install(fake_game, docs, l10n_root, tmp_path, execute=True)
    assert not again.executed and any("já está instalada" in p for p in again.plan.problems)
    assert _hashes(docs) == snapshot
    # desinstalação
    plan = installer.uninstall(docs, execute=True, running=never_running)
    assert plan.executed and not target.exists() and not (docs / "Underkeep" / "mods").exists()
    assert (docs / "Underkeep" / "save_1").read_bytes() == b"save sintetico"
    assert _hashes(fake_game) == before_game


def test_incompatible_game_blocks_before_writing(fake_game: Path, docs: Path, l10n_root: Path,
                                                tmp_path: Path) -> None:
    (fake_game / "underkeep.exe").write_bytes(b"MZ outra build")
    snapshot = _hashes(docs)
    outcome = _install(fake_game, docs, l10n_root, tmp_path, execute=True)
    assert not outcome.executed and _hashes(docs) == snapshot


@pytest.mark.parametrize("setup, expected", [
    ("foreign", "outro mod"),
    ("running", "está aberto"),
    ("no_user_dir", "abra o Underkeep uma vez"),
])
def test_unsafe_conditions_block(fake_game: Path, docs: Path, l10n_root: Path, tmp_path: Path,
                                 setup: str, expected: str) -> None:
    running = never_running
    if setup == "foreign":
        (docs / "Underkeep" / "mods" / "base").mkdir(parents=True)
        (docs / "Underkeep" / "mods" / "base" / "arquivo_de_outro_mod.txt").write_text("x")
    elif setup == "running":
        running = always_running
    else:
        docs = tmp_path / "SemJogo"
        docs.mkdir()
    snapshot = _hashes(docs)
    outcome = _install(fake_game, docs, l10n_root, tmp_path, execute=True, running=running)
    assert not outcome.executed and any(expected in p for p in outcome.plan.problems)
    assert _hashes(docs) == snapshot


def test_other_mods_are_warned_and_preserved(fake_game: Path, docs: Path, l10n_root: Path, tmp_path: Path) -> None:
    other = docs / "Underkeep" / "mods" / "meu_mod"
    other.mkdir(parents=True)
    (other / "x.txt").write_text("mod de terceiro")
    outcome = _install(fake_game, docs, l10n_root, tmp_path, execute=True)
    assert outcome.executed and any("meu_mod" in w for w in outcome.plan.warnings)
    installer.uninstall(docs, execute=True, running=never_running)
    assert (other / "x.txt").read_text() == "mod de terceiro"
    assert (docs / "Underkeep" / "mods").is_dir()  # não remove pasta que tem conteúdo de terceiros


def test_other_version_and_damaged_install(fake_game: Path, docs: Path, l10n_root: Path, tmp_path: Path,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installer, "PATCH_NAME", "underkeep-ptbr-0.0.1")
    assert _install(fake_game, docs, l10n_root, tmp_path, execute=True).executed
    monkeypatch.setattr(installer, "PATCH_NAME", "underkeep-ptbr-0.1.0-beta.1")
    assert installer.target_state(docs, "base").kind == "other"
    target = docs / "Underkeep" / "mods" / "base" / "base" / text_file_name("common", "es")
    target.write_bytes(target.read_bytes() + b"\x00")
    assert installer.target_state(docs, "base").kind == "damaged"
    assert not installer.uninstall(docs, execute=True, running=never_running).executed  # recusa: alterada


# ------------------------------------------------------------------ interface
def test_main_noninteractive_install_status_uninstall(fake_game: Path, docs: Path, l10n_root: Path) -> None:
    lines: list[str] = []
    common = ["--jogo", str(fake_game / "underkeep.exe"), "--documentos", str(docs), "--traducao", str(l10n_root)]
    assert installer.main(common + ["--verificar"], out=lines.append, running=never_running, pause=False) == 0
    assert not (docs / "Underkeep" / "mods").exists()
    assert installer.main(common + ["--sim"], out=lines.append, running=never_running, pause=False) == 0
    assert any("Español" in line for line in lines)
    assert installer.main(common + ["--status"], out=lines.append, running=never_running, pause=False) == 0
    assert installer.main(common + ["--sim"], out=lines.append, running=never_running, pause=False) == 2
    assert installer.main(["--documentos", str(docs), "--desinstalar", "--sim"], out=lines.append,
                          running=never_running, pause=False) == 0
    assert not (docs / "Underkeep" / "mods").exists()


def test_main_interactive_manual_folder_and_cancel(fake_game: Path, docs: Path, l10n_root: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(steam, "find_game_dirs", lambda roots=None: [])
    answers = iter([str(fake_game), "n"])
    lines: list[str] = []
    code = installer.main(["--documentos", str(docs), "--traducao", str(l10n_root)],
                          input_fn=lambda _p: next(answers), out=lines.append, running=never_running, pause=False)
    assert code == 2 and any("Cancelado" in line for line in lines)
    assert not (docs / "Underkeep" / "mods").exists()


def test_main_reports_incompatible_version(fake_game: Path, docs: Path, l10n_root: Path) -> None:
    (fake_game / "underkeep.exe").write_bytes(b"MZ outra build")
    lines: list[str] = []
    code = installer.main(["--jogo", str(fake_game), "--documentos", str(docs), "--traducao", str(l10n_root), "--sim"],
                          out=lines.append, running=never_running, pause=False)
    assert code == 2 and any("não suportada" in line for line in lines)
