"""Interface gráfica para Linux/Steam Deck (modo Desktop), usando ``kdialog`` (KDE) ou ``zenity``.

Esta camada só troca a forma de perguntar e de mostrar mensagens: instalação, verificação, status e
desinstalação são os mesmos fluxos de :mod:`ukloc.installer` (``dispatch``/``run_install``/...), com as
mesmas verificações de segurança. Os diálogos são chamados com ``subprocess`` e argumentos em lista,
sem shell. Nada aqui manipula o pack.

Sem ambiente gráfico (nem ``kdialog`` nem ``zenity``), cai para o modo terminal do instalador.
"""
from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Mapping

from . import installer

TITLE = f"Underkeep PT-BR {installer.VERSION}"
PROG = "Instalador-Underkeep-PTBR.sh"
ACTIONS = [("instalar", "Instalar a tradução"),
           ("verificar", "Verificar se dá para instalar (não altera nada)"),
           ("status", "Ver o estado da instalação"),
           ("desinstalar", "Desinstalar a tradução")]
INTRO = ("Tradução comunitária e não oficial do Underkeep para português do Brasil.\n"
         "Feche o jogo antes de instalar ou desinstalar.\n"
         "Depois de instalar, escolha \"Español\" no menu de idiomas do jogo.\n\n"
         "O que deseja fazer?")

Runner = Callable[[list[str]], tuple[int, str]]


def _run(argv: list[str]) -> tuple[int, str]:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout.strip()


def find_dialog_tool(which: Callable[[str], str | None] = shutil.which,
                     env: Mapping[str, str] = os.environ) -> str | None:
    """``kdialog`` (preferido no KDE/SteamOS) ou ``zenity``; ``None`` sem tela gráfica."""
    if not (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY")):
        return None
    for tool in ("kdialog", "zenity"):
        if which(tool):
            return tool
    return None


class Dialogs:
    """Diálogos básicos; ``run``/``spawn`` são injetáveis para testes."""

    def __init__(self, tool: str, run: Runner = _run,
                 spawn: Callable[..., subprocess.Popen] = subprocess.Popen) -> None:
        if tool not in {"kdialog", "zenity"}:
            raise ValueError(f"ferramenta de diálogo desconhecida: {tool}")
        self.tool = tool
        self.run = run
        self.spawn = spawn
        self._busy: list[subprocess.Popen] = []

    def _z(self, text: str) -> str:  # zenity interpreta marcação Pango; caminhos com & ou < precisam de escape
        return html.escape(text, quote=False)

    def _message(self, kind: str, text: str) -> None:
        if self.tool == "kdialog":
            flag = {"info": "--msgbox", "warning": "--sorry", "error": "--error"}[kind]
            self.run(["kdialog", "--title", TITLE, flag, text])
        else:
            self.run(["zenity", f"--{kind}", "--title", TITLE, "--width", "560", "--text", self._z(text)])

    def info(self, text: str) -> None:
        self._message("info", text)

    def warning(self, text: str) -> None:
        self._message("warning", text)

    def error(self, text: str) -> None:
        self._message("error", text)

    def yesno(self, text: str, yes: str = "Sim", no: str = "Não") -> bool:
        if self.tool == "kdialog":
            argv = ["kdialog", "--title", TITLE, "--yes-label", yes, "--no-label", no, "--yesno", text]
        else:
            argv = ["zenity", "--question", "--title", TITLE, "--width", "560", "--ok-label", yes,
                    "--cancel-label", no, "--text", self._z(text)]
        return self.run(argv)[0] == 0

    def menu(self, text: str, items: list[tuple[str, str]]) -> str | None:
        """Tag escolhida, ou ``None`` se o jogador cancelar."""
        pairs = [value for item in items for value in item]
        if self.tool == "kdialog":
            code, out = self.run(["kdialog", "--title", TITLE, "--menu", text, *pairs])
        else:
            code, out = self.run(["zenity", "--list", "--title", TITLE, "--text", self._z(text), "--width", "640",
                                  "--height", "380", "--hide-header", "--column", "id", "--column", "Opção",
                                  "--hide-column", "1", "--print-column", "1", *pairs])
        tags = {tag for tag, _label in items}
        choice = out.strip().split("|")[0]
        return choice if code == 0 and choice in tags else None

    def directory(self, start: Path | None = None) -> Path | None:
        start_dir = str(start if start is not None else Path.home())
        if self.tool == "kdialog":
            code, out = self.run(["kdialog", "--title", TITLE, "--getexistingdirectory", start_dir])
        else:
            code, out = self.run(["zenity", "--file-selection", "--directory", "--title", TITLE,
                                  "--filename", start_dir.rstrip("/") + "/"])
        return Path(out) if code == 0 and out.strip() else None

    def notify(self, text: str) -> None:
        """Aviso sem bloquear (a geração do pack leva alguns minutos)."""
        try:
            if self.tool == "kdialog":
                self.spawn(["kdialog", "--title", TITLE, "--passivepopup", text, "20"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif not self._busy:
                self._busy.append(self.spawn(["zenity", "--progress", "--pulsate", "--no-cancel", "--auto-close",
                                              "--title", TITLE, "--width", "560", "--text", self._z(text)],
                                             stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL))
        except OSError:
            pass  # o aviso é opcional; o resultado final sempre é mostrado

    def close_notifications(self) -> None:
        for proc in self._busy:
            try:
                if proc.stdin is not None:
                    proc.stdin.close()  # com --auto-close o zenity fecha ao terminar a entrada
                proc.wait(timeout=10)
            except (OSError, subprocess.SubprocessError):
                proc.kill()
        self._busy.clear()


class DialogConsole(installer.Console):
    """Adapta o ``Console`` do instalador a diálogos: as mensagens se acumulam e aparecem na próxima
    pergunta ou no resultado final."""

    def __init__(self, dialogs: Dialogs) -> None:
        super().__init__(assume_yes=False, input_fn=lambda _prompt: "", out=self._collect)
        self.dialogs = dialogs
        self.lines: list[str] = []

    def _collect(self, message: str) -> None:
        self.lines.append(message.strip())

    def take(self) -> str:
        text = "\n".join(line for line in self.lines if not line.startswith("Procurando "))
        self.lines.clear()
        return text.strip()

    def confirm(self, prompt: str) -> bool:
        context = self.take()
        return self.dialogs.yesno(f"{context}\n\n{prompt}" if context else prompt)

    def progress(self, message: str) -> None:
        self.dialogs.notify(message)

    def choose_path(self, found: list[Path], *, missing: str, manual: str) -> Path | None:
        self.take()
        if len(found) == 1:
            if self.dialogs.yesno(f"Encontrado:\n{found[0]}\n\nUsar esta pasta?", yes="Usar esta pasta",
                                  no="Escolher outra..."):
                return found[0]
            return self.dialogs.directory(found[0])
        if found:
            items = [(str(n), str(path)) for n, path in enumerate(found, 1)] + [("outra", "Escolher outra pasta...")]
            choice = self.dialogs.menu("Encontrei mais de uma pasta. Qual delas usar?", items)
            if choice is None:
                return None
            if choice != "outra":
                return found[int(choice) - 1]
            return self.dialogs.directory()
        self.dialogs.info(f"{missing}\n\nNa próxima janela, escolha a pasta manualmente.\n{manual}.")
        return self.dialogs.directory()


def run_gui(dialogs: Dialogs, l10n_root: Path, *, documents: Path | None = None, game: Path | None = None,
            running: Callable[[], bool] | None = None) -> int:
    """Menu principal. Repete até o jogador sair; devolve o código da última ação."""
    code = installer.EXIT_OK
    while True:
        choice = dialogs.menu(INTRO, ACTIONS)
        if choice is None:
            return code
        console = DialogConsole(dialogs)
        args = argparse.Namespace(jogo=game, documentos=documents, traducao=l10n_root, sim=False,
                                  verificar=choice == "verificar", desinstalar=choice == "desinstalar",
                                  status=choice == "status")
        try:
            code = installer.guarded(console.out, lambda: installer.dispatch(args, console, running))
        finally:
            dialogs.close_notifications()
        text = console.take() or "Nada foi alterado."
        if code == installer.EXIT_OK:
            dialogs.info(text)
        elif code == installer.EXIT_BLOCKED:
            dialogs.warning(text)
        else:
            dialogs.error(text)


def _with_catalog(argv: list[str], l10n_root: Path) -> list[str]:
    return argv if "--traducao" in argv else [*argv, "--traducao", str(l10n_root)]


def main(argv: list[str] | None = None, *, l10n_root: Path, entry_script: Path | None = None) -> int:
    """Sem argumentos: interface gráfica. ``--terminal``: instalador interativo no terminal.
    Outros argumentos (``--verificar``, ``--status``, ``--desinstalar``...): repassados ao instalador."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--terminal":
        return installer.main(_with_catalog(args[1:], l10n_root), prog=PROG)
    if args:
        return installer.main(_with_catalog(args, l10n_root), prog=PROG)
    tool = find_dialog_tool()
    if tool is not None:
        return run_gui(Dialogs(tool), l10n_root)
    if sys.stdin is not None and sys.stdin.isatty():
        return installer.main(_with_catalog([], l10n_root), prog=PROG)
    terminal = shutil.which("konsole")
    if terminal and entry_script is not None:  # aberto por duplo clique, sem kdialog/zenity: abre um terminal
        return subprocess.call([terminal, "-e", sys.executable, "-I", "-B", str(entry_script), "--terminal"])
    print("ERRO: nenhuma interface disponível (kdialog, zenity ou terminal). "
          f"Abra o Konsole e rode: ./{PROG} --terminal", file=sys.stderr)
    return installer.EXIT_ERROR
