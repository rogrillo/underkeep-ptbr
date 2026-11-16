"""Auditoria de publicação: varre **todo o histórico Git** antes de tornar o repositório público.

Uso:
    python scripts/audit_publication.py [--jogo PASTA_DO_JOGO] [--arvore] [--objetos-soltos]
                                        [--termo TEXTO ...] [--json RELATORIO.json]

O que é verificado em cada blob alcançável (todas as branches, tags, stash e reflog) e, com
``--objetos-soltos``, também nos objetos inalcançáveis:

* arquivos do jogo e extensões proibidas (``.rfile``, ``.db``, ``.exe``, ``.dll``, imagens, áudio, fontes...);
* conteúdo binário e blobs grandes;
* credenciais (chaves privadas, tokens do GitHub/AWS/Slack/Google/Anthropic/OpenAI, senhas, URLs com usuário:senha);
* dados pessoais: e-mails fora da lista permitida, caminhos ``C:\\Users\\<nome>`` / ``/home/<nome>`` /
  ``/Users/<nome>``, o nome de usuário e o nome desta máquina e os termos passados em ``--termo``;
* com ``--jogo``: trechos do **texto original** do jogo (todas as tabelas ``text_text_*`` de ``base``),
  comparados localmente por janelas de 32 caracteres. Nada é enviado para fora e o relatório não imprime
  o texto original, só o arquivo, o id e o idioma.

Também confere autores e committers e procura os mesmos padrões nas mensagens de commit. Com ``--arvore``,
analisa ainda os arquivos da árvore de trabalho que seriam commitados (não ignorados), antes do commit.

Valores sensíveis são mascarados na saída. Código de saída: 0 sem bloqueadores, 1 com bloqueadores,
2 em erro de uso.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass, field
import getpass
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_SUFFIXES = (
    ".rfile", ".db", ".exe", ".dll", ".so", ".dylib", ".pdb", ".level", ".clip", ".gzf", ".sav",
    ".dds", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp", ".ico", ".psd",
    ".wav", ".ogg", ".mp3", ".flac", ".bank", ".fsb",
    ".ttf", ".otf", ".fnt", ".woff", ".woff2",
    ".zip", ".7z", ".rar", ".gz", ".tar", ".bin", ".dat", ".pak", ".dmp", ".bak",
    ".pyc", ".pyo", ".env", ".pem", ".key", ".p12", ".pfx",
)
FORBIDDEN_NAMES = (
    "underkeep.exe", "game_config.txt", "game_log.txt", "player_profile", "save_auto", "save_quick",
    "save_1", "save_2", "save_3", "steam_appid.txt", "localconfig.vdf", "loginusers.vdf", "config.vdf",
    ".env", "id_rsa", "id_ed25519", "credentials", ".netrc", ".pypirc",
)
FORBIDDEN_DIRS = ("work/", "audit/local/", "dist/", "build/", "mods/", "__pycache__/", ".venv/")
LARGE_BLOB = 2 * 2**20
ALLOWED_EMAILS = re.compile(
    r"(?i)^(noreply@anthropic\.com|[^@]+@users\.noreply\.github\.com|noreply@github\.com|"
    r"[^@]+@example\.(com|org|net)|[^@]+@localhost)$"
)
GENERIC_USERS = {
    "steamuser", "public", "default", "deck", "user", "usuario", "usuário", "nome", "name", "runner",
    "<usuario>", "<usuário>", "<user>", "<nome>", "voce", "você", "seu_usuario", "seunome",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("chave privada", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("token GitHub", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("chave AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("token Slack", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    ("chave Google", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("chave Anthropic/OpenAI", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}\b")),
    ("chave Stripe", re.compile(r"\b[rs]k_live_[0-9A-Za-z]{20,}\b")),
    ("token npm/PyPI", re.compile(r"\b(?:npm_[A-Za-z0-9]{36}|pypi-[A-Za-z0-9_\-]{50,})\b")),
    ("URL com credencial", re.compile(r"\b[a-z][a-z0-9+.\-]*://[^/\s:@\"'<>]+:[^/\s@\"'<>]+@[^\s\"'<>]+", re.I)),
    ("senha/token atribuído", re.compile(
        r"(?i)\b(?:password|passwd|senha|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)"
        r"\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']")),
]
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
USER_PATH_RES = [
    re.compile(r"(?i)\b[A-Z]:[\\/]+(?:Users|Documents and Settings)[\\/]+([^\\/\s\"'`<>|*?:]+)"),
    re.compile(r"(?<![\w.])/home/([A-Za-z0-9._\-]+)"),
    re.compile(r"(?<![\w.])/Users/([A-Za-z0-9._\-]+)"),
]
PLACEHOLDER_RE = re.compile(r"(?i)placeholder|example|exemplo|dummy|fake|falso|changeme|x{4,}|\*{3,}|<[^>]+>")
GENERIC_PREFIXES = ("usuario", "usuário", "user", "exemplo", "example", "fulano", "nome")
WINDOW = 32
MIN_ORIGINAL = 40
TEXT_WINDOW_OK = re.compile(r"^[^\\\"\n\r\t{}<>\[\]]+$")


@dataclass
class Finding:
    kind: str           # proprietario | binario | grande | segredo | pessoal | original | metadado
    severity: str       # bloqueador | alto | medio | baixo
    path: str
    detail: str
    blob: str = ""
    commits: list[str] = field(default_factory=list)
    in_head: bool = False


@dataclass
class Report:
    commits: int = 0
    refs: list[str] = field(default_factory=list)
    objects: dict[str, int] = field(default_factory=dict)
    blobs_scanned: int = 0
    paths_ever: int = 0
    unreachable: int = 0
    tree_files: int = 0
    identities: dict[str, int] = field(default_factory=dict)
    original_strings: int = 0
    findings: list[Finding] = field(default_factory=list)

    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "bloqueador"]


# --------------------------------------------------------------------------- git
def git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], input=input_bytes, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falhou: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def reachable_blobs(repo: Path) -> dict[str, set[str]]:
    """blob -> caminhos, para tudo alcançável por refs, stash e reflog."""
    out = git(repo, "rev-list", "--objects", "--all", "--reflog")
    blobs: dict[str, set[str]] = defaultdict(set)
    lines = [line.split(" ", 1) for line in out.decode("utf-8", "replace").splitlines()]
    shas = "\n".join(parts[0] for parts in lines).encode()
    kinds = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)", input_bytes=shas).decode().splitlines()
    kind_of = dict(line.split(" ", 1) for line in kinds if " " in line)
    for parts in lines:
        if kind_of.get(parts[0]) == "blob":
            blobs[parts[0]].add(parts[1] if len(parts) > 1 else "")
    return blobs


def all_objects(repo: Path) -> dict[str, str]:
    out = git(repo, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)")
    return dict(line.split(" ", 1) for line in out.decode().splitlines() if " " in line)


def read_blobs(repo: Path, shas: Iterable[str]) -> Iterator[tuple[str, bytes]]:
    shas = list(shas)
    if not shas:
        return
    data = git(repo, "cat-file", "--batch", input_bytes=("\n".join(shas) + "\n").encode())
    pos = 0
    for _ in shas:
        nl = data.index(b"\n", pos)
        header = data[pos:nl].decode().split()
        size = int(header[2])
        yield header[0], data[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1


def commits_touching(repo: Path) -> dict[str, list[str]]:
    """blob -> commits (abreviados) que o introduziram."""
    out = git(repo, "log", "--all", "--reflog", "--format=@%h", "--raw", "--no-renames", "--no-abbrev")
    result: dict[str, list[str]] = defaultdict(list)
    current = ""
    for line in out.decode("utf-8", "replace").splitlines():
        if line.startswith("@"):
            current = line[1:]
        elif line.startswith(":"):
            fields = line.split()
            if len(fields) >= 4 and set(fields[3]) != {"0"}:
                result[fields[3]].append(current[:10])
    return result


# --------------------------------------------------------------------------- padrões
def mask(value: str) -> str:
    if len(value) <= 6:
        return value[0] + "***" if value else "***"
    return f"{value[:3]}***{value[-2:]} ({len(value)} caracteres)"


def personal_terms(extra: Iterable[str]) -> list[str]:
    terms = {t for t in extra if t and len(t) >= 3}
    for candidate in (getpass.getuser(), platform.node(), os.environ.get("USERNAME", ""), os.environ.get("USER", "")):
        if candidate and len(candidate) >= 3 and candidate.lower() not in GENERIC_USERS:
            terms.add(candidate)
    for key in ("user.email",):
        try:
            value = git(ROOT, "config", key).decode().strip()
        except (RuntimeError, OSError):
            value = ""
        if value and not ALLOWED_EMAILS.match(value):
            terms.add(value)
    return sorted(terms, key=str.lower)


def scan_text(text: str, terms: list[str]) -> list[tuple[str, str, str]]:
    """Devolve (tipo, severidade, detalhe mascarado)."""
    hits: list[tuple[str, str, str]] = []
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.groups() else match.group(0)
            if PLACEHOLDER_RE.search(value) or (
                    label == "URL com credencial" and re.search(r"(?i)usuario|user:pass|<|\{", match.group(0))):
                continue
            hits.append(("segredo", "bloqueador", f"{label}: {mask(value)}"))
    for match in EMAIL_RE.finditer(text):
        if not ALLOWED_EMAILS.match(match.group(0)):
            hits.append(("pessoal", "alto", f"e-mail: {mask(match.group(0))}"))
    for pattern in USER_PATH_RES:
        for match in pattern.finditer(text):
            name = match.group(1).rstrip(".,;:)!?")
            low = name.lower()
            if low not in GENERIC_USERS and not low.startswith(GENERIC_PREFIXES) and not name.startswith(
                    ("<", "$", "%", "{", "…", ".")):  # "C:\\Users\\…" é reticência, não nome
                hits.append(("pessoal", "medio", f"caminho com nome de usuário: …{mask(name)}"))
    lowered = text.lower()
    for term in terms:
        count = lowered.count(term.lower())
        if count:
            hits.append(("pessoal", "medio", f"termo pessoal {mask(term)}: {count} ocorrência(s)"))
    return hits


def path_problems(path: str, size: int, data: bytes) -> list[tuple[str, str, str]]:
    low = path.lower().replace("\\", "/")
    name = low.rsplit("/", 1)[-1]
    found: list[tuple[str, str, str]] = []
    if name.endswith(FORBIDDEN_SUFFIXES) or name in FORBIDDEN_NAMES:
        found.append(("proprietario", "bloqueador", f"arquivo de tipo proibido: {name}"))
    if any(low.startswith(d) or f"/{d}" in low for d in FORBIDDEN_DIRS):
        found.append(("proprietario", "bloqueador", "arquivo em diretório que deveria ser ignorado"))
    if b"\x00" in data[:8192]:
        found.append(("binario", "bloqueador", f"conteúdo binário ({size} bytes)"))
    elif size > LARGE_BLOB:
        found.append(("grande", "medio", f"blob grande: {size / 2**20:.1f} MB"))
    return found


# --------------------------------------------------------------------------- texto original
def original_windows(game: Path) -> tuple[dict[str, tuple[str, str]], int]:
    """janela de 32 caracteres -> (idioma, id). Considera textos >= 40 caracteres de todas as tabelas."""
    sys.path.insert(0, str(ROOT))
    from ukloc.textdb import find_text_tables, load_text_table  # noqa: PLC0415

    windows: dict[str, tuple[str, str]] = {}
    count = 0
    tables = find_text_tables(game / "base")
    if not tables:
        raise SystemExit(f"nenhuma tabela de texto em {game / 'base'}")
    for (category, lang), path in tables.items():
        for entry_id, text in load_text_table(path.read_bytes(), category, lang).entries:
            if len(text) < MIN_ORIGINAL:
                continue
            count += 1
            for start in range(0, len(text) - WINDOW + 1, WINDOW // 2):
                chunk = text[start:start + WINDOW]
                if TEXT_WINDOW_OK.match(chunk) and len(set(chunk)) > 8:
                    windows.setdefault(chunk, (lang, f"{category}:{entry_id}"))
                    break
    return windows, count


def find_original(text: str, windows: dict[str, tuple[str, str]]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    seen: set[str] = set()
    for i in range(len(text) - WINDOW + 1):
        chunk = text[i:i + WINDOW]
        ref = windows.get(chunk)
        if ref and ref[1] not in seen:
            seen.add(ref[1])
            hits.append(ref)
    return hits


# --------------------------------------------------------------------------- auditoria
def scan_content(paths: list[str], data: bytes, base: dict, terms: list[str],
                 windows: dict[str, tuple[str, str]]) -> list[Finding]:
    found: list[Finding] = []
    for p in paths:
        for kind, severity, detail in path_problems(p, len(data), data):
            found.append(Finding(kind, severity, p, detail, **base))
    if b"\x00" in data[:8192]:
        return found
    text = data.decode("utf-8", "replace")
    path = paths[0]
    for kind, severity, detail in scan_text(text, terms):
        found.append(Finding(kind, severity, path, detail, **base))
    if windows:
        hits = find_original(text, windows)
        if hits:
            langs = sorted({lang for lang, _ in hits})
            sample = ", ".join(ref for _, ref in hits[:5])
            severity = "bloqueador" if len(hits) >= 20 else "medio" if len(hits) >= 5 else "baixo"
            found.append(Finding(
                "original", severity, path,
                f"{len(hits)} trecho(s) idêntico(s) ao texto original ({'/'.join(langs)}); ex.: {sample}", **base))
    return found


def audit(repo: Path, *, game: Path | None = None, terms: Iterable[str] = (), loose: bool = False,
          tree: bool = False) -> Report:
    """Audita o histórico; com ``tree=True`` também os arquivos da árvore de trabalho ainda não commitados."""
    report = Report()
    report.refs = git(repo, "for-each-ref", "--format=%(refname)").decode().split()
    report.commits = int(git(repo, "rev-list", "--all", "--reflog", "--count").decode().strip() or 0)
    objects = all_objects(repo)
    report.objects = {kind: sum(1 for v in objects.values() if v == kind) for kind in sorted(set(objects.values()))}
    blobs = reachable_blobs(repo)
    loose_blobs = {sha for sha, kind in objects.items() if kind == "blob"} - set(blobs)
    report.unreachable = len(loose_blobs)
    if loose:
        for sha in loose_blobs:
            blobs[sha].add("<objeto inalcançável>")
    report.paths_ever = len({p for paths in blobs.values() for p in paths})
    head_blobs = set()
    try:
        for line in git(repo, "ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines():
            head_blobs.add(line.split()[2])
    except RuntimeError:
        pass
    introduced = commits_touching(repo)
    term_list = personal_terms(terms)
    windows: dict[str, tuple[str, str]] = {}
    if game is not None:
        windows, report.original_strings = original_windows(game)

    for sha, data in read_blobs(repo, blobs):
        report.blobs_scanned += 1
        base = dict(blob=sha[:10], commits=introduced.get(sha, [])[:5], in_head=sha in head_blobs)
        report.findings += scan_content(sorted(blobs[sha]), data, base, term_list, windows)
    if tree:
        listing = git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        for rel in sorted(set(listing.decode("utf-8", "replace").split("\0")) - {""}):
            path = repo / rel
            if not path.is_file():
                continue
            report.tree_files += 1
            base = dict(blob="árvore", commits=[], in_head=True)
            report.findings += scan_content([rel], path.read_bytes(), base, term_list, windows)

    identities: dict[str, int] = defaultdict(int)
    log = git(repo, "log", "--all", "--reflog", "--format=%h%x1f%an <%ae>%x1f%cn <%ce>%x1f%B%x1e")
    for record in log.decode("utf-8", "replace").split("\x1e"):
        parts = record.strip("\n").split("\x1f")
        if len(parts) < 4:
            continue
        short, author, committer, message = parts
        for ident in {author, committer}:
            identities[ident] += 1
        for ident in {author, committer}:
            email = ident.rsplit("<", 1)[-1].rstrip(">")
            if email and not ALLOWED_EMAILS.match(email):
                report.findings.append(Finding(
                    "metadado", "alto", f"commit {short}", f"e-mail de autor/committer: {mask(email)}", commits=[short]))
        for kind, severity, detail in scan_text(message, term_list):
            report.findings.append(Finding(kind, severity, f"mensagem do commit {short}", detail, commits=[short]))
    report.identities = {mask_identity(k): v for k, v in identities.items()}
    return report


def audit_directory(directory: Path, *, game: Path | None = None, terms: Iterable[str] = ()) -> Report:
    """Audita uma pasta comum, sem Git (ex.: a cópia pública exportada). Ignora ``.git`` se existir."""
    if not directory.is_dir():
        raise RuntimeError(f"pasta inexistente: {directory}")
    report = Report()
    term_list = personal_terms(terms)
    windows: dict[str, tuple[str, str]] = {}
    if game is not None:
        windows, report.original_strings = original_windows(game)
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and ".git" not in p.relative_to(directory).parts):
        rel = path.relative_to(directory).as_posix()
        report.tree_files += 1
        base = dict(blob="árvore", commits=[], in_head=True)
        report.findings += scan_content([rel], path.read_bytes(), base, term_list, windows)
    report.paths_ever = report.tree_files
    return report


def mask_identity(ident: str) -> str:
    name, _, email = ident.partition(" <")
    email = email.rstrip(">")
    return f"{name} <{email if ALLOWED_EMAILS.match(email) else mask(email)}>"


# --------------------------------------------------------------------------- saída
def summarize(report: Report) -> str:
    if not report.refs and not report.commits:
        lines = [f"pasta sem Git: {report.tree_files} arquivos analisados"]
    else:
        lines = [
        f"refs: {len(report.refs)} ({', '.join(report.refs)})",
        f"commits (todas as refs + reflog): {report.commits}",
        f"objetos no repositório: {report.objects} | blobs analisados: {report.blobs_scanned} "
        f"| caminhos já versionados: {report.paths_ever} | blobs inalcançáveis: {report.unreachable}"
        + (f" | arquivos da árvore de trabalho: {report.tree_files}" if report.tree_files else ""),
        "identidades: " + "; ".join(f"{k} x{v}" for k, v in report.identities.items()),
    ]
    if report.original_strings:
        lines.append(f"textos originais comparados (>= {MIN_ORIGINAL} caracteres, todas as línguas): "
                     f"{report.original_strings}")
    grouped: dict[tuple[str, str, str], list[Finding]] = defaultdict(list)
    for f in report.findings:
        grouped[(f.severity, f.kind, f.detail if f.kind == "metadado" else f.path)].append(f)
    order = {"bloqueador": 0, "alto": 1, "medio": 2, "baixo": 3}
    lines.append(f"achados: {len(report.findings)} ({len(report.blockers())} bloqueadores)")
    for (severity, kind, key), items in sorted(grouped.items(), key=lambda kv: (order[kv[0][0]], kv[0][1], kv[0][2])):
        head = ("árvore de trabalho" if all(i.blob == "árvore" for i in items)
                else "HEAD" if any(i.in_head for i in items) else "só histórico")
        details = sorted({i.detail for i in items})
        if kind == "metadado":
            lines.append(f"  [{severity}] {kind}: {key} em {len(items)} commit(s)")
        else:
            lines.append(f"  [{severity}] {kind}: {key} ({len(items)} versão(ões), {head})")
            for d in details[:4]:
                lines.append(f"      - {d}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=ROOT, help="repositório Git (padrão: este projeto)")
    parser.add_argument("--jogo", type=Path, help="pasta do Underkeep para comparar com o texto original (só leitura)")
    parser.add_argument("--termo", action="append", default=[], help="termo pessoal extra a procurar (repetível)")
    parser.add_argument("--objetos-soltos", action="store_true", help="também analisar objetos inalcançáveis")
    parser.add_argument("--arvore", action="store_true",
                        help="também analisar a árvore de trabalho (arquivos não commitados e não ignorados)")
    parser.add_argument("--diretorio", type=Path,
                        help="auditar uma pasta sem Git (ex.: a cópia pública exportada) em vez de um repositório")
    parser.add_argument("--json", type=Path, help="gravar o relatório completo em JSON (fora do repositório)")
    args = parser.parse_args(argv)
    try:
        if args.diretorio:
            report = audit_directory(args.diretorio, game=args.jogo, terms=args.termo)
        else:
            report = audit(args.repo, game=args.jogo, terms=args.termo, loose=args.objetos_soltos, tree=args.arvore)
    except RuntimeError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    print(summarize(report))
    if args.json:
        args.json.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if report.blockers() else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
