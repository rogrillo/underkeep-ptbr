"""Steam Deck/Linux: descoberta de prefixos Proton, detecção do jogo, interface gráfica, launcher e pacote.

Tudo em diretórios temporários com jogo e catálogo sintéticos; nada real é tocado. Partes que dependem do
Linux (links simbólicos, permissões após ``unzip``) são puladas onde não houver suporte.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

import pytest

from conftest import make_fake_game
from ukloc import gui, installer, l10n, shadow, steam
from ukloc.textdb import load_text_table, text_file_name

ROOT = Path(__file__).resolve().parents[1]
DOCS_PARTS = ("pfx", "drive_c", "users", "steamuser", "Documents")


def never_running() -> bool:
    return False


# ------------------------------------------------------------------ cenários sintéticos
def _escape(path: Path) -> str:
    return str(path).replace("\\", "\\\\")


def make_steam(tmp_path: Path, *, game_in: str = "ssd", prefixes: tuple[str, ...] = ("ssd",),
               game_dir_in_prefix: bool = True) -> dict[str, Path]:
    """Steam com biblioteca interna ("ssd") e um cartão microSD ("sd", com espaço no nome)."""
    libs = {"ssd": tmp_path / "home" / ".local" / "share" / "Steam",
            "sd": tmp_path / "run" / "media" / "deck" / "Cartão SD & Jogos",
            "hdd": tmp_path / "mnt" / "outro disco"}
    for lib in libs.values():
        (lib / "steamapps").mkdir(parents=True, exist_ok=True)
    vdf = "".join(f' "{n}"\n {{\n  "path" "{_escape(lib)}"\n }}\n' for n, lib in enumerate(libs.values()))
    (libs["ssd"] / "steamapps" / "libraryfolders.vdf").write_text(f'"libraryfolders"\n{{\n{vdf}}}\n',
                                                                  encoding="utf-8")
    game = make_fake_game(libs[game_in] / "steamapps" / "common" / "Underkeep")
    (libs[game_in] / "steamapps" / "appmanifest_2411200.acf").write_text(
        '"AppState"\n{\n "appid" "2411200"\n "installdir" "Underkeep"\n}\n', encoding="utf-8")
    out = {"root": libs["ssd"], "game": game, **libs}
    for name in prefixes:
        docs = libs[name] / "steamapps" / "compatdata" / "2411200"
        docs = docs.joinpath(*DOCS_PARTS)
        docs.mkdir(parents=True)
        if game_dir_in_prefix:
            (docs / "Underkeep").mkdir()
            (docs / "Underkeep" / "game_config.txt").write_text("config sintética", encoding="utf-8")
        out[f"docs_{name}"] = docs
    return out


@pytest.fixture
def l10n_root(tmp_path: Path) -> Path:
    """Catálogo compatível com o jogo sintético (os arquivos do jogo falso são determinísticos)."""
    ref = make_fake_game(tmp_path / "ref_game")
    root = tmp_path / "dados" / "pt-BR"
    root.mkdir(parents=True)
    base = ref / "base"
    files = {text_file_name(c, "es"): shadow.file_sha256(base / text_file_name(c, "es")) for c in ("common", "game")}
    project = {"schema": l10n.PROJECT_SCHEMA, "locale": "pt-BR", "reference_language": "en", "target_slot": "es",
               "pack": "base", "expected": {"exe_sha256": shadow.file_sha256(ref / "underkeep.exe"),
                                            "files": files, "game_build": None}}
    (root / "project.json").write_text(json.dumps(project), encoding="utf-8")
    en = load_text_table((base / text_file_name("common", "en")).read_bytes(), "common", "en").as_dict()
    catalog = l10n.Catalog("common", entries={"menu_ok": l10n.Entry(
        source_sha256=l10n.text_sha256(en["menu_ok"]), text="Novo Jogo {color_text}%1\\nfim",
        translation_status="translated", origin="teste")})
    l10n.save_catalog(root / "common.json", catalog)
    return root


@pytest.fixture
def linux(monkeypatch: pytest.MonkeyPatch):
    """Simula o Linux para a resolução de pastas (o resto do código já é multiplataforma)."""
    monkeypatch.setattr(installer, "is_windows", lambda: False)

    def use(roots: list[Path]) -> None:
        monkeypatch.setattr(steam, "registry_steam_roots", lambda: [])
        monkeypatch.setattr(steam, "default_steam_roots", lambda: roots)
    return use


# ------------------------------------------------------------------ descoberta
def test_internal_ssd_game_and_prefix(tmp_path: Path) -> None:
    s = make_steam(tmp_path)
    assert steam.find_game_dirs([s["root"]]) == [s["game"]]
    found = steam.find_proton_documents(s["game"], [s["root"]])
    assert found.matched == s["docs_ssd"] and found.candidates == [s["docs_ssd"]]


def test_microsd_game_prefers_prefix_in_same_library(tmp_path: Path) -> None:
    s = make_steam(tmp_path, game_in="sd", prefixes=("sd", "ssd"))  # prefixo antigo no SSD
    assert steam.find_game_dirs([s["root"]]) == [s["game"]]
    found = steam.find_proton_documents(s["game"], [s["root"]])
    assert found.matched == s["docs_sd"]
    assert set(found.candidates) == {s["docs_sd"], s["docs_ssd"]}


def test_prefix_only_in_other_libraries_is_ambiguous(tmp_path: Path) -> None:
    s = make_steam(tmp_path, game_in="ssd", prefixes=("sd", "hdd"))
    found = steam.find_proton_documents(s["game"], [s["root"]])
    assert found.matched is None and len(found.candidates) == 2


def test_no_prefix_found(tmp_path: Path) -> None:
    s = make_steam(tmp_path, prefixes=())
    found = steam.find_proton_documents(s["game"], [s["root"]])
    assert found.matched is None and found.candidates == []


def test_old_my_documents_layout_prefers_folder_with_game(tmp_path: Path) -> None:
    s = make_steam(tmp_path)
    old = s["docs_ssd"].parent / "My Documents"
    old.mkdir()
    found = steam.find_proton_documents(s["game"], [s["root"]])
    assert found.matched == s["docs_ssd"] and old in found.candidates


def test_game_outside_steam_layout_has_no_matched_prefix(tmp_path: Path) -> None:
    s = make_steam(tmp_path)
    loose = make_fake_game(tmp_path / "copia solta")
    assert steam.library_of_game(loose) is None
    assert steam.find_proton_documents(loose, [s["root"]]).matched is None


def test_symlinked_steam_roots_are_not_duplicated(tmp_path: Path) -> None:
    s = make_steam(tmp_path)
    link = tmp_path / "home" / ".steam" / "steam"
    link.parent.mkdir(parents=True)
    try:
        os.symlink(s["root"], link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("sem suporte a links simbólicos neste sistema")
    assert steam.find_game_dirs([link, s["root"]]) == [link / "steamapps" / "common" / "Underkeep"]
    assert len(steam.find_proton_documents(s["game"], [link, s["root"]]).candidates) == 1


# ------------------------------------------------------------------ jogo aberto (Linux/Proton)
def _proc(tmp_path: Path, processes: dict[int, list[str]]) -> Path:
    proc = tmp_path / "proc"
    (proc / "self").mkdir(parents=True)
    for pid, args in processes.items():
        (proc / str(pid)).mkdir()
        (proc / str(pid) / "cmdline").write_bytes(b"\x00".join(a.encode() for a in args) + b"\x00")
    return proc


def test_linux_game_running_detects_proton_process(tmp_path: Path) -> None:
    proc = _proc(tmp_path, {10: ["/usr/bin/bash"],
                            42: ["Z:\\home\\deck\\.local\\share\\Steam\\steamapps\\common\\Underkeep\\underkeep.exe"]})
    assert shadow.linux_game_running(proc)


def test_linux_game_running_ignores_installer_and_others(tmp_path: Path) -> None:
    proc = _proc(tmp_path, {10: ["python3", "x.py", "--jogo", "/jogos/Underkeep/underkeep.exe"],
                            11: ["/usr/bin/kdialog", "underkeep.exe.txt"]})
    assert shadow.linux_game_running(proc, ignore=[10]) is False
    assert shadow.linux_game_running(proc) is True  # sem ignorar, o argumento conta (falha segura)


def test_linux_game_running_fails_safe_without_proc(tmp_path: Path) -> None:
    assert shadow.linux_game_running(tmp_path / "sem_proc") is True


# ------------------------------------------------------------------ fluxo completo no "Linux"
def test_linux_flow_autodetects_prefix_install_status_uninstall(tmp_path: Path, l10n_root: Path, linux) -> None:
    s = make_steam(tmp_path, game_in="sd", prefixes=("sd",))
    linux([s["root"]])
    game_before = shadow.hash_tree(s["game"])
    lines: list[str] = []
    common = ["--traducao", str(l10n_root), "--sim"]
    assert installer.main(common, out=lines.append, running=never_running, pause=False) == 0
    target = s["docs_sd"] / "Underkeep" / "mods" / "base"
    assert (target / shadow.MANIFEST_NAME).is_file()
    assert any("prefixo do jogo" in line for line in lines)
    assert installer.main(["--status"], out=lines.append, running=never_running, pause=False) == 0
    assert installer.main(["--desinstalar", "--sim"], out=lines.append, running=never_running, pause=False) == 0
    assert not target.exists()
    assert (s["docs_sd"] / "Underkeep" / "game_config.txt").read_text(encoding="utf-8") == "config sintética"
    assert shadow.hash_tree(s["game"]) == game_before


def test_linux_ambiguous_prefix_refused_noninteractive(tmp_path: Path, l10n_root: Path, linux) -> None:
    s = make_steam(tmp_path, game_in="ssd", prefixes=("sd", "hdd"))
    linux([s["root"]])
    lines: list[str] = []
    code = installer.main(["--traducao", str(l10n_root), "--sim"], out=lines.append, running=never_running,
                          pause=False)
    assert code == installer.EXIT_ERROR and any("--documentos" in line for line in lines)
    assert not list(tmp_path.rglob("mods"))


def test_linux_ambiguous_prefix_interactive_choice(tmp_path: Path, l10n_root: Path, linux) -> None:
    s = make_steam(tmp_path, game_in="ssd", prefixes=("sd", "hdd"))
    linux([s["root"]])
    candidates = steam.find_proton_documents(s["game"], [s["root"]]).candidates
    answers = iter(["", "2", "s"])  # Enter = jogo encontrado; 2 = segundo prefixo; confirma
    code = installer.main(["--traducao", str(l10n_root)], input_fn=lambda _p: next(answers), out=lambda _m: None,
                          running=never_running, pause=False)
    assert code == 0
    assert (candidates[1] / "Underkeep" / "mods" / "base").is_dir()
    assert not (candidates[0] / "Underkeep" / "mods").exists()


def test_linux_missing_prefix_asks_manual_path(tmp_path: Path, l10n_root: Path, linux) -> None:
    s = make_steam(tmp_path, prefixes=())
    linux([s["root"]])
    lines: list[str] = []
    answers = iter(["", ""])  # jogo encontrado; nenhuma pasta Documentos digitada
    code = installer.main(["--traducao", str(l10n_root)], input_fn=lambda _p: next(answers), out=lines.append,
                          running=never_running, pause=False)
    assert code == installer.EXIT_BLOCKED and any("prefixo Proton" in line for line in lines)


def test_reinstall_after_uninstall_and_incompatible_blocked(tmp_path: Path, l10n_root: Path, linux) -> None:
    s = make_steam(tmp_path)
    linux([s["root"]])
    run = lambda *a: installer.main([*a], out=lambda _m: None, running=never_running, pause=False)  # noqa: E731
    assert run("--traducao", str(l10n_root), "--sim") == 0
    assert run("--traducao", str(l10n_root), "--sim") == installer.EXIT_BLOCKED  # já instalada
    assert run("--desinstalar", "--sim") == 0
    assert run("--traducao", str(l10n_root), "--sim") == 0  # reinstala
    assert run("--desinstalar", "--sim") == 0
    (s["game"] / "underkeep.exe").write_bytes(b"MZ outra build")
    assert run("--traducao", str(l10n_root), "--sim") == installer.EXIT_BLOCKED
    assert not (s["docs_ssd"] / "Underkeep" / "mods").exists()


def test_write_permission_problem_blocks(tmp_path: Path, l10n_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_steam(tmp_path)
    real_access = os.access
    monkeypatch.setattr(installer.os, "access",
                        lambda p, mode: False if Path(p).name == "Underkeep" and mode == os.W_OK else real_access(p, mode))
    project = installer.load_project(l10n_root)
    plan = installer.plan_install(s["game"], s["docs_ssd"], project, running=never_running, workdir=tmp_path)
    assert any("sem permissão de escrita" in p for p in plan.problems)


def test_symlinked_target_is_never_followed_or_removed(tmp_path: Path) -> None:
    docs = tmp_path / "Documents"
    elsewhere = tmp_path / "dados_importantes"
    elsewhere.mkdir()
    (elsewhere / "x.txt").write_text("não apagar")
    (docs / "Underkeep" / "mods").mkdir(parents=True)
    try:
        os.symlink(elsewhere, docs / "Underkeep" / "mods" / "base", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("sem suporte a links simbólicos neste sistema")
    assert installer.target_state(docs, "base").kind == "foreign"
    plan = installer.uninstall(docs, execute=True, running=never_running)
    assert not plan.executed and any("link simbólico" in p for p in plan.problems)
    assert (elsewhere / "x.txt").read_text() == "não apagar"


# ------------------------------------------------------------------ interface gráfica (diálogos simulados)
class FakeDialogs:
    """Responde aos diálogos em ordem; registra as linhas de comando."""

    def __init__(self, answers: list[tuple[int, str]]) -> None:
        self.answers = list(answers)
        self.calls: list[list[str]] = []
        self.spawned: list[list[str]] = []

    def run(self, argv: list[str]) -> tuple[int, str]:
        assert all(isinstance(a, str) for a in argv)
        self.calls.append(argv)
        if argv[0] == "kdialog" and any(f in argv for f in ("--msgbox", "--sorry", "--error")):
            return 0, ""
        if argv[0] == "zenity" and any(f in argv for f in ("--info", "--warning", "--error")):
            return 0, ""
        return self.answers.pop(0)

    def spawn(self, argv: list[str], **_kwargs) -> object:
        self.spawned.append(argv)

        class Done:
            stdin = None

            def wait(self, timeout: float | None = None) -> int:
                return 0
        return Done()

    def texts(self, flag: str) -> list[str]:
        return [c[c.index(flag) + 1] for c in self.calls if flag in c]


def _gui(tmp_path: Path, l10n_root: Path, answers: list[tuple[int, str]], tool: str = "kdialog",
         **kwargs) -> tuple[int, FakeDialogs, dict[str, Path]]:
    s = make_steam(tmp_path)
    fake = FakeDialogs(answers)
    dialogs = gui.Dialogs(tool, run=fake.run, spawn=fake.spawn)
    code = gui.run_gui(dialogs, l10n_root, documents=s["docs_ssd"], running=never_running,
                       **({"game": s["game"]} | kwargs))
    return code, fake, s


def test_gui_install_then_uninstall_with_kdialog(tmp_path: Path, l10n_root: Path) -> None:
    answers = [(0, "instalar"), (0, ""),          # menu; confirma instalação
               (0, "desinstalar"), (0, ""),       # menu; confirma remoção
               (1, "")]                           # sair
    code, fake, s = _gui(tmp_path, l10n_root, answers)
    assert code == 0
    confirms = fake.texts("--yesno")
    assert "Instalar a tradução agora?" in confirms[0] and "Jogo compatível" in confirms[0]
    assert str(s["docs_ssd"] / "Underkeep" / "mods" / "base") in confirms[0]
    assert any("Español" in t for t in fake.texts("--msgbox"))
    assert any("Tradução removida" in t for t in fake.texts("--msgbox"))
    assert fake.spawned and fake.spawned[0][:3] == ["kdialog", "--title", gui.TITLE]  # aviso de progresso
    assert not (s["docs_ssd"] / "Underkeep" / "mods").exists()


def test_gui_cancel_and_verify_change_nothing(tmp_path: Path, l10n_root: Path) -> None:
    answers = [(0, "verificar"), (0, "instalar"), (1, ""), (0, "status"), (1, "")]
    code, fake, s = _gui(tmp_path, l10n_root, answers)
    assert not (s["docs_ssd"] / "Underkeep" / "mods").exists()
    assert any("Modo verificação" in t for t in fake.texts("--msgbox"))
    assert any("Cancelado" in t for t in fake.texts("--sorry"))
    assert any("não instalada" in t for t in fake.texts("--msgbox"))


def test_gui_detects_game_and_lets_player_pick_another(tmp_path: Path, l10n_root: Path, linux) -> None:
    s = make_steam(tmp_path, game_in="sd", prefixes=("sd",))
    linux([s["root"]])
    other = make_fake_game(tmp_path / "outra pasta" / "Underkeep")
    # "Escolher outra..." -> pasta; com o jogo fora da biblioteca, o prefixo deixa de ser certo e é perguntado
    fake = FakeDialogs([(0, "verificar"), (1, ""), (0, str(other)), (0, ""), (1, "")])
    code = gui.run_gui(gui.Dialogs("kdialog", run=fake.run, spawn=fake.spawn), l10n_root, running=never_running)
    assert code == 0
    questions = fake.texts("--yesno")
    assert str(s["game"]) in questions[0] and str(s["docs_sd"]) in questions[1]
    assert any("getexistingdirectory" in " ".join(c) for c in fake.calls)
    assert any(str(other) in t and "Modo verificação" in t for t in fake.texts("--msgbox"))


def test_gui_blocked_install_shows_warning(tmp_path: Path, l10n_root: Path) -> None:
    s = make_steam(tmp_path)
    (s["game"] / "underkeep.exe").write_bytes(b"MZ outra build")
    fake = FakeDialogs([(0, "instalar"), (1, "")])
    gui.run_gui(gui.Dialogs("kdialog", run=fake.run, spawn=fake.spawn), l10n_root, documents=s["docs_ssd"],
                game=s["game"], running=never_running)
    assert any("não suportada" in t for t in fake.texts("--sorry"))
    assert not (s["docs_ssd"] / "Underkeep" / "mods").exists()


def test_zenity_escapes_markup_and_parses_menu(tmp_path: Path) -> None:
    fake = FakeDialogs([(0, "status|"), (0, "")])
    dialogs = gui.Dialogs("zenity", run=fake.run, spawn=fake.spawn)
    assert dialogs.menu("Escolha", gui.ACTIONS) == "status"
    assert dialogs.yesno("Pasta /run/media/Cartão & <SD>") is True
    assert "Cartão &amp; &lt;SD&gt;" in fake.texts("--text")[-1]
    dialogs.info("a & b")
    assert fake.calls[-1][fake.calls[-1].index("--text") + 1] == "a &amp; b"


def test_menu_cancel_or_unknown_tag_returns_none() -> None:
    fake = FakeDialogs([(1, ""), (0, "rm -rf /")])
    dialogs = gui.Dialogs("kdialog", run=fake.run)
    assert dialogs.menu("x", gui.ACTIONS) is None
    assert dialogs.menu("x", gui.ACTIONS) is None


def test_find_dialog_tool() -> None:
    which = {"kdialog": "/usr/bin/kdialog", "zenity": "/usr/bin/zenity"}.get
    assert gui.find_dialog_tool(which, {}) is None  # sem tela gráfica
    assert gui.find_dialog_tool(which, {"DISPLAY": ":0"}) == "kdialog"
    assert gui.find_dialog_tool(lambda t: "/usr/bin/zenity" if t == "zenity" else None,
                                {"WAYLAND_DISPLAY": "wayland-0"}) == "zenity"
    assert gui.find_dialog_tool(lambda _t: None, {"DISPLAY": ":0"}) is None


def test_gui_main_passes_arguments_to_installer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(installer, "main", lambda argv, prog: seen.append(argv) or 0)
    assert gui.main(["--status"], l10n_root=tmp_path) == 0
    assert gui.main(["--terminal"], l10n_root=tmp_path) == 0
    assert gui.main(["--verificar", "--traducao", "x"], l10n_root=tmp_path) == 0
    assert seen == [["--status", "--traducao", str(tmp_path)], ["--traducao", str(tmp_path)],
                    ["--verificar", "--traducao", "x"]]


# ------------------------------------------------------------------ pacote Steam Deck
def _load_build_release():
    spec = importlib.util.spec_from_file_location("build_release_deck", ROOT / "scripts" / "build_release.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_release_deck"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def deck_zip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    br = _load_build_release()
    out = tmp_path_factory.mktemp("deck_build")
    br.BUILD_DIR, br.DIST_DIR = out / "build", out / "dist"
    path, spec = br.build_deck()
    assert br.audit_zip(path, spec) == []
    return path


def test_deck_zip_structure_permissions_and_contents(deck_zip: Path) -> None:
    br = _load_build_release()
    name = br.DECK_PACKAGE_NAME
    with zipfile.ZipFile(deck_zip) as zf:
        infos = {i.filename: i for i in zf.infolist()}
        names = [n for n, i in infos.items() if not i.is_dir()]
        assert all("\\" not in n and n.startswith(f"{name}/") for n in infos)
        assert all(i.create_system == 3 for i in infos.values())
        launcher = infos[f"{name}/Instalador-Underkeep-PTBR.sh"]
        assert stat.S_IMODE(launcher.external_attr >> 16) == 0o755
        assert stat.S_IMODE(infos[f"{name}/app/ukloc/installer.py"].external_attr >> 16) == 0o644
        assert zf.read(launcher.filename).startswith(b"#!/usr/bin/env bash\n")
        assert all(b"\r" not in zf.read(n) for n in names if n.endswith((".sh", ".py")))
        assert not any("__pycache__" in n or n.endswith((".pyc", ".rfile", ".db", ".exe")) for n in names)
        assert f"{name}/app/ukloc/catalog.py" not in names  # só o que o instalador importa
        assert {f"{name}/dados/pt-BR/{c}" for c in br.CATALOG_FILES} <= set(names)
        assert {f"{name}/{rel}" for rel in br.PROJECT_LICENSES} <= set(names)
        assert b"MIT License" in zf.read(f"{name}/licencas/LICENCA-CODIGO-MIT.txt")
        assert b"CC BY-NC-SA 4.0" in zf.read(f"{name}/licencas/LICENCA-TRADUCAO-CC-BY-NC-SA-4.0.txt")
        assert b"Rake in Grass" in zf.read(f"{name}/licencas/AVISO-LEGAL.txt")
        version = br.VERSION.encode()
        assert f'VERSION = "{br.VERSION}"'.encode() in zf.read(f"{name}/app/ukloc/installer.py")
        assert version in zf.read(f"{name}/VERSAO.txt") and version in zf.read(f"{name}/LEIA-ME.txt")


def test_audit_rejects_version_mismatch_and_missing_licenses(deck_zip: Path, tmp_path: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    br = _load_build_release()
    monkeypatch.setattr(br, "private_markers", lambda: [])
    spec = br.deck_spec()
    bad = tmp_path / "versao.zip"
    with zipfile.ZipFile(deck_zip) as src, zipfile.ZipFile(bad, "w") as dst:
        for info in src.infolist():
            if "/licencas/" in info.filename:
                continue  # licenças removidas
            data = src.read(info)
            if info.filename.endswith("app/ukloc/installer.py"):
                data = data.replace(f'VERSION = "{br.VERSION}"'.encode(), b'VERSION = "9.9.9"')
            dst.writestr(info, data)
    problems = "\n".join(br.audit_zip(bad, spec))
    assert "installer.VERSION (9.9.9) difere" in problems
    assert "licencas/LICENCA-CODIGO-MIT.txt" in problems


def test_deck_zip_is_deterministic(deck_zip: Path, tmp_path: Path) -> None:
    br = _load_build_release()
    br.BUILD_DIR, br.DIST_DIR = tmp_path / "build", tmp_path / "dist"
    again, _spec = br.build_deck()
    assert br.file_sha256(again) == br.file_sha256(deck_zip)


def test_audit_rejects_windows_style_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """O defeito do ``Compress-Archive``: barras invertidas, sem permissões Unix, CRLF e caches."""
    br = _load_build_release()
    monkeypatch.setattr(br, "private_markers", lambda: [])
    spec = br.deck_spec()
    bad = tmp_path / "ruim.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        info = zipfile.ZipInfo("placeholder")
        info.filename = f"{spec.name}\\app\\ukloc\\installer.py"  # contorna a normalização do zipfile no Windows
        info.create_system = 0
        zf.writestr(info, b"x = 1\r\n")
        zf.writestr(zipfile.ZipInfo(f"{spec.name}/Instalador-Underkeep-PTBR.sh"), b"#!/bin/bash\r\n")
        zf.writestr(f"{spec.name}/app/ukloc/__pycache__/x.cpython-313.pyc", b"")
    problems = "\n".join(br.audit_zip(bad, spec))
    for expected in ("não POSIX", "create_system=0", "CRLF", "cache Python", "permissão", "faltando"):
        assert expected in problems


def _extract(deck_zip: Path, dest: Path) -> Path:
    with zipfile.ZipFile(deck_zip) as zf:
        zf.extractall(dest)
    return next(dest.iterdir())


def test_extracted_package_runs_full_cycle(deck_zip: Path, tmp_path: Path, l10n_root: Path) -> None:
    """O pacote extraído funciona sozinho (só a biblioteca padrão) e não grava caches na própria pasta."""
    # O pacote roda num subprocesso com a detecção real de processos: com o Underkeep aberto nesta máquina, o
    # instalador recusa a instalação (comportamento correto), e o teste não teria como validar o ciclo.
    if shadow.is_game_running():
        pytest.skip("o Underkeep está aberto nesta máquina; feche o jogo para rodar este teste")
    package = _extract(deck_zip, tmp_path / "extraido com espaço")
    game = make_fake_game(tmp_path / "jogo")
    docs = tmp_path / "Documents"
    (docs / "Underkeep").mkdir(parents=True)
    entry = package / "app" / "underkeep_ptbr.py"
    env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "HOME"}}

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", "-B", str(entry), "--jogo", str(game), "--documentos", str(docs),
                               "--traducao", str(l10n_root), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env, cwd=tmp_path, timeout=300,
                              stdin=subprocess.DEVNULL, check=False)
    before_game = shadow.hash_tree(game)
    verify = run("--verificar")
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert not (docs / "Underkeep" / "mods").exists()
    assert run("--sim").returncode == 0
    assert (docs / "Underkeep" / "mods" / "base" / shadow.MANIFEST_NAME).is_file()
    assert run("--status").returncode == 0
    assert run("--desinstalar", "--sim").returncode == 0
    assert not (docs / "Underkeep" / "mods").exists()
    assert shadow.hash_tree(game) == before_game
    assert not list(package.rglob("__pycache__"))


@pytest.mark.skipif(sys.platform == "win32" or shutil.which("unzip") is None, reason="precisa de Linux com unzip")
def test_unzip_on_linux_keeps_executable_bit(deck_zip: Path, tmp_path: Path) -> None:
    subprocess.run(["unzip", "-q", str(deck_zip), "-d", str(tmp_path)], check=True)
    launcher = next(tmp_path.iterdir()) / "Instalador-Underkeep-PTBR.sh"
    assert os.access(launcher, os.X_OK)
    assert (launcher.parent / "app" / "ukloc" / "installer.py").is_file()


# ------------------------------------------------------------------ launcher .sh
def _bash() -> str | None:
    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if sys.platform == "win32":
        return str(git_bash) if git_bash.is_file() else None
    return shutil.which("bash")


@pytest.mark.skipif(_bash() is None, reason="bash indisponível")
def test_launcher_finds_python_and_forwards_arguments(deck_zip: Path, tmp_path: Path) -> None:
    package = _extract(deck_zip, tmp_path / "pkg")
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    (fakebin / "python3").write_bytes(b'#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\necho "PY $*"\n')
    os.chmod(fakebin / "python3", 0o755)
    script = 'PATH="$PWD/fakebin:/usr/bin:/bin"; export PATH; unset DISPLAY WAYLAND_DISPLAY; exec bash "$1" --status'
    result = subprocess.run([_bash(), "-c", script, "_", f"pkg/{package.name}/Instalador-Underkeep-PTBR.sh"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("PY -I -B ") and result.stdout.rstrip().endswith("app/underkeep_ptbr.py --status")


@pytest.mark.skipif(_bash() is None, reason="bash indisponível")
def test_launcher_reports_missing_files_and_python(deck_zip: Path, tmp_path: Path) -> None:
    package = _extract(deck_zip, tmp_path / "pkg")
    launcher = f"pkg/{package.name}/Instalador-Underkeep-PTBR.sh"
    (tmp_path / "vazio").mkdir()
    no_python = 'PATH="$PWD/vazio:/usr/bin:/bin"; export PATH; unset DISPLAY WAYLAND_DISPLAY; '
    # sem Python 3.11+ (um "python3" que recusa a versão)
    (tmp_path / "vazio" / "python3").write_bytes(b"#!/bin/sh\nexit 1\n")
    os.chmod(tmp_path / "vazio" / "python3", 0o755)
    (tmp_path / "vazio" / "python").write_bytes(b"#!/bin/sh\nexit 1\n")
    os.chmod(tmp_path / "vazio" / "python", 0o755)
    result = subprocess.run([_bash(), "-c", no_python + 'exec bash "$1"', "_", launcher], cwd=tmp_path,
                            capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 1 and "Python 3.11" in result.stderr
    # pacote incompleto (copiado sem a pasta app/)
    shutil.rmtree(package / "app")
    result = subprocess.run([_bash(), "-c", no_python + 'exec bash "$1"', "_", launcher], cwd=tmp_path,
                            capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 1 and "Extraia o ZIP inteiro" in result.stderr
