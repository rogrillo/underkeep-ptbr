"""Testes do auditor de publicação (histórico Git sintético, nada do jogo real)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import zlib

import pytest

from ukloc.textdb import TextTable, build_text_table_bytes, text_file_name

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("audit_publication", ROOT / "scripts" / "audit_publication.py")
ap = importlib.util.module_from_spec(_spec)
sys.modules["audit_publication"] = ap
_spec.loader.exec_module(ap)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git ausente")

NOREPLY = "12345+fulano@users.noreply.github.com"
FAKE_TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
LONG_EN = "The ancient lantern flickers as the cold wind sweeps across the hall."
# Dados pessoais sintéticos montados em tempo de execução, para o próprio arquivo de teste não acionar o auditor.
FAKE_EMAIL = "fulano.real" + "@" + "gmail.com"
FAKE_USER = "Joao" + "zinho"


class Repo:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str, email: str = NOREPLY) -> str:
        cmd = ["git", "-C", str(self.path), "-c", "user.name=Fulano", "-c", f"user.email={email}",
               "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args]
        return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

    def commit(self, files: dict[str, bytes | str | None], message: str = "commit", email: str = NOREPLY) -> None:
        for rel, content in files.items():
            target = self.path / rel
            if content is None:
                self.git("rm", "-q", rel)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
            self.git("add", rel)
        self.git("commit", "-q", "-m", message, email=email)


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    r = Repo(tmp_path / "repo")
    r.commit({"README.md": "# Projeto\nInstale em C:\\Users\\steamuser\\Documents ou /home/deck.\n"}, "inicio")
    return r


def kinds(report: ap.Report) -> set[tuple[str, str]]:
    return {(f.kind, f.severity) for f in report.findings}


def test_clean_repo_has_no_findings(repo: Repo) -> None:
    report = ap.audit(repo.path)
    assert report.commits == 1
    assert report.blobs_scanned == 1
    assert report.findings == []
    assert not report.blockers()


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return len(data).to_bytes(4, "big") + kind + data + zlib.crc32(kind + data).to_bytes(4, "big")


def make_png(*extra: tuple[bytes, bytes]) -> bytes:
    """PNG válido de 1x1 (RGB); ``extra`` insere chunks auxiliares antes do IDAT."""
    ihdr = png_chunk(b"IHDR", (1).to_bytes(4, "big") * 2 + bytes([8, 2, 0, 0, 0]))
    idat = png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
    return (ap.PNG_SIGNATURE + ihdr + b"".join(png_chunk(k, d) for k, d in extra) + idat
            + png_chunk(b"IEND", b""))


PNG = make_png()


def test_readme_screenshots_are_the_only_allowed_images(repo: Repo) -> None:
    repo.commit({"assets/screenshots/menu-principal.png": PNG})
    assert ap.audit(repo.path).findings == []
    repo.commit({"assets/outra-pasta/menu.png": PNG, "assets/screenshots/Captura de Tela.png": PNG})
    blocked = {f.path for f in ap.audit(repo.path).blockers()}
    assert blocked == {"assets/outra-pasta/menu.png", "assets/screenshots/Captura de Tela.png"}


def test_large_screenshot_is_reported() -> None:
    found = ap.path_problems("assets/screenshots/grande.png", 3 * 2**20, PNG)
    assert [(k, s) for k, s, _ in found] == [("grande", "medio")]


@pytest.mark.parametrize("chunk", [
    (b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00<x:xmpmeta/>"),
    (b"tEXt", b"Author\x00" + FAKE_USER.encode()),
    (b"eXIf", b"MM\x00*"),
    (b"pHYs", b"\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01"),
])
def test_screenshot_metadata_blocks(chunk: tuple[bytes, bytes]) -> None:
    data = make_png(chunk)
    found = ap.path_problems("assets/screenshots/menu.png", len(data), data)
    assert [(k, s) for k, s, _ in found] == [("metadado", "bloqueador")]
    assert chunk[0].decode() in found[0][2]


@pytest.mark.parametrize("name, data", [
    ("quebrada.png", PNG[:-6]),
    ("falsa.png", b"GIF89a" + b"\x00" * 20),
    ("foto.jpg", b"\xff\xd8\xff\xe1\x00\x08Exif\x00\x00\xff\xda\x00\x02"),
    ("foto.jpeg", b"\xff\xd8\xff\xfe\x00\x06nome\xff\xda\x00\x02"),
    ("foto.webp", b"RIFF\x1a\x00\x00\x00WEBPEXIF\x04\x00\x00\x00MM\x00*"),
])
def test_invalid_or_tagged_images_are_blocked(name: str, data: bytes) -> None:
    found = ap.path_problems(f"assets/screenshots/{name}", len(data), data)
    assert ("metadado", "bloqueador") in [(k, s) for k, s, _ in found]


def test_clean_jpeg_and_webp_pass() -> None:
    jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xda\x00\x02"
    webp = b"RIFF\x12\x00\x00\x00WEBPVP8L\x05\x00\x00\x00\x2f\x00\x00\x00\x00\x00"
    for name, data in (("ok.jpg", jpeg), ("ok.webp", webp)):
        assert ap.path_problems(f"assets/screenshots/{name}", len(data), data) == []


@pytest.mark.parametrize("path", [
    "CLAUDE.md", "docs/FASE_3A_INSTRUCOES.md", "docs/FASES.md", "docs/PUBLICACAO.md", "outra/claude.md",
    "docs/CONTATO_RAKE_IN_GRASS.md", ".local/notas.txt", "publico/CHANGELOG.md",
])
def test_internal_material_is_blocked_anywhere(path: str) -> None:
    found = ap.path_problems(path, 10, b"interno\n")
    assert any(s == "bloqueador" for _, s, _ in found), found


def test_internal_file_new_in_working_tree_is_blocked(repo: Repo) -> None:
    (repo.path / "docs").mkdir()
    (repo.path / "docs" / "FASE_9Z_RELATORIO.md").write_text("relatório interno\n", encoding="utf-8")
    report = ap.audit(repo.path, tree=True)
    assert {f.path for f in report.blockers()} == {"docs/FASE_9Z_RELATORIO.md"}


def test_staged_content_is_audited_with_its_real_path(repo: Repo) -> None:
    """Pré-commit: o que está no índice é auditado pelo caminho real, não como objeto sem caminho."""
    shots = repo.path / "assets" / "screenshots"
    shots.mkdir(parents=True)
    (shots / "menu.png").write_bytes(PNG)
    repo.git("add", "assets/screenshots/menu.png")
    assert ap.audit(repo.path, loose=True).blockers() == []  # captura limpa preparada: aceita
    (shots / "menu.png").write_bytes(make_png((b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00<x/>")))
    (repo.path / "CLAUDE.md").write_text("instruções locais\n", encoding="utf-8")
    repo.git("add", "assets/screenshots/menu.png")
    repo.git("add", "-f", "CLAUDE.md")  # adição forçada: o .gitignore não protegeria
    blocked = {(f.path, f.kind) for f in ap.audit(repo.path, loose=True).blockers()}
    assert ("assets/screenshots/menu.png", "metadado") in blocked
    assert ("CLAUDE.md", "interno") in blocked


def test_deleted_game_file_is_found_in_history(repo: Repo) -> None:
    repo.commit({"base/text_text_game_en.txt.rfile": b"\x00\x01DfT"}, "oops")
    repo.commit({"base/text_text_game_en.txt.rfile": None}, "remove")
    report = ap.audit(repo.path)
    hits = [f for f in report.findings if f.kind == "proprietario"]
    assert hits and hits[0].severity == "bloqueador"
    assert not hits[0].in_head  # só no histórico: limpar a árvore não basta
    assert hits[0].commits
    assert ("binario", "bloqueador") in kinds(report)


def test_secret_is_blocker_and_masked(repo: Repo) -> None:
    repo.commit({"cfg.txt": f"token: {FAKE_TOKEN}\n"})
    report = ap.audit(repo.path)
    assert ("segredo", "bloqueador") in kinds(report)
    assert FAKE_TOKEN not in ap.summarize(report)


def test_placeholders_are_not_secrets(repo: Repo) -> None:
    repo.commit({"t.py": 'SECRET = "COPYRIGHTED-PLACEHOLDER"\npassword = "<sua senha aqui>"\n'})
    assert ap.audit(repo.path).findings == []


def test_personal_paths_and_terms(repo: Repo) -> None:
    text = (f"C:\\Users\\{FAKE_USER}\\Documents\\Underkeep e /home/" + "maria/x e C:/Users/usuario-teste"
            " e caminhos `C:\\Users\\…`\n")  # reticência não é nome de usuário
    repo.commit({"docs/log.md": text})
    report = ap.audit(repo.path, terms=[FAKE_USER])
    details = " ".join(f.detail for f in report.findings if f.kind == "pessoal")
    assert details.count("caminho com nome de usuário") == 2  # Joaozinho e maria; usuario-teste é genérico
    assert "termo pessoal" in details
    assert FAKE_USER not in ap.summarize(report)


def test_commit_email_metadata(repo: Repo) -> None:
    repo.commit({"a.txt": "x"}, "pessoal", email=FAKE_EMAIL)
    report = ap.audit(repo.path)
    meta = [f for f in report.findings if f.kind == "metadado"]
    assert len(meta) == 1 and meta[0].severity == "alto"
    assert FAKE_EMAIL not in ap.summarize(report)
    assert any("noreply" in ident for ident in report.identities)


def test_email_in_file(repo: Repo) -> None:
    repo.commit({"a.txt": f"contato: {FAKE_EMAIL}; ok: noreply@anthropic.com"})
    hits = [f for f in ap.audit(repo.path).findings if f.kind == "pessoal"]
    assert len(hits) == 1


def make_game(tmp_path: Path, texts: dict[str, str]) -> Path:
    game = tmp_path / "Underkeep"
    (game / "base").mkdir(parents=True)
    table = TextTable("game", "en", entries=list(texts.items()))
    (game / "base" / text_file_name("game", "en")).write_bytes(build_text_table_bytes(table))
    return game


def test_original_text_detected_without_printing_it(repo: Repo, tmp_path: Path) -> None:
    game = make_game(tmp_path, {"lamp_01": LONG_EN, "short": "Yes."})
    repo.commit({"docs/nota.md": f'Original: "{LONG_EN}" -> tradução própria.\n'})
    report = ap.audit(repo.path, game=game)
    assert report.original_strings == 1
    hits = [f for f in report.findings if f.kind == "original"]
    assert len(hits) == 1 and hits[0].severity == "baixo"
    assert "game:lamp_01" in hits[0].detail
    assert LONG_EN[:32] not in ap.summarize(report)


def test_mass_original_text_is_blocker(repo: Repo, tmp_path: Path) -> None:
    texts = {f"line_{i:02d}": f"Sentence number {i:02d} of the dungeon chronicle, long enough to count." for i in range(25)}
    game = make_game(tmp_path, texts)
    repo.commit({"dump.txt": "\n".join(texts.values())})
    report = ap.audit(repo.path, game=game)
    assert ("original", "bloqueador") in kinds(report)


def test_tree_mode_scans_uncommitted_files(repo: Repo) -> None:
    (repo.path / "novo.txt").write_text(f"token: {FAKE_TOKEN}\n", encoding="utf-8")
    (repo.path / ".gitignore").write_text("ignorado.txt\n", encoding="utf-8")
    (repo.path / "ignorado.txt").write_text(f"token: {FAKE_TOKEN}\n", encoding="utf-8")
    assert not ap.audit(repo.path).blockers()  # só histórico: ainda não commitado
    report = ap.audit(repo.path, tree=True)
    hits = [f for f in report.blockers() if f.blob == "árvore"]
    assert [f.path for f in hits] == ["novo.txt"]  # arquivos ignorados pelo Git ficam de fora
    assert report.tree_files == 3


def test_directory_mode_without_git(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "copia publica"
    (folder / "docs").mkdir(parents=True)
    (folder / "docs" / "ok.md").write_text("Instale em C:\\Users\\<usuário>\\Documents.\n", encoding="utf-8")
    report = ap.audit_directory(folder)
    assert report.tree_files == 1 and report.findings == []
    (folder / "base.rfile").write_bytes(b"\x00DfT")
    (folder / ".git").mkdir()
    (folder / ".git" / "segredo.txt").write_text(f"token: {FAKE_TOKEN}\n", encoding="utf-8")  # .git é ignorado
    assert ap.main(["--diretorio", str(folder)]) == 1
    out = capsys.readouterr().out
    assert "pasta sem Git: 2 arquivos" in out and "base.rfile" in out and "segredo" not in out


def test_main_exit_codes(repo: Repo, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert ap.main(["--repo", str(repo.path)]) == 0
    repo.commit({"x.dll": b"MZ\x00\x00"})
    out = tmp_path / "r.json"
    assert ap.main(["--repo", str(repo.path), "--json", str(out)]) == 1
    assert out.is_file()
    assert "bloqueador" in capsys.readouterr().out
    assert ap.main(["--repo", str(tmp_path / "nao-existe")]) == 2


def test_project_history_has_no_blockers() -> None:
    """O próprio repositório não pode ter arquivos do jogo, binários ou segredos em nenhum commit."""
    if not (ROOT / ".git").exists():
        pytest.skip("cópia sem .git")
    report = ap.audit(ROOT)
    assert [f"{f.path}: {f.detail}" for f in report.blockers()] == []
