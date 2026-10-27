"""Leitura do corpus. Barreira: só entra texto que esteja dentro de corpus/."""
from pathlib import Path

from . import config
from .util import relpath

SUFFIXES = {".txt", ".md"}
SKIP_DIRS = {"private"}
SKIP_FILES = {"ATTRIBUTION.txt"}
MIN_BLOCK = 16


class CorpusRefused(Exception):
    pass


def _below(base, p):
    """As pastas de p dentro de corpus/. Vazio se p estiver fora (corpus externo)."""
    try:
        return p.relative_to(base).parts
    except ValueError:
        return ()


def resolve_inputs(paths=None, allow_external=False):
    """Lista os ficheiros a ler. Sem argumentos lê corpus/ inteiro, menos corpus/private/.

    Um caminho fora de corpus/ é recusado, a menos que se passe allow_external de propósito.
    O mesmo vale para uma ligação simbólica que aponte para fora. A pasta private/ só entra se
    for pedida pelo nome, nunca por --corpus corpus nem por omissão.
    """
    base = config.CORPUS_DIR.resolve()
    roots = [Path(p).resolve() for p in paths] if paths else [base]
    files = []
    for root in roots:
        if not allow_external and not root.is_relative_to(base):
            raise CorpusRefused(
                f"{root.name!r} está fora de corpus/. Mete o texto lá dentro "
                "ou usa --allow-external se é mesmo isso que queres."
            )
        candidates = [root] if root.is_file() else sorted(root.rglob("*"))
        for f in candidates:
            if not f.is_file() or f.suffix not in SUFFIXES or f.name in SKIP_FILES:
                continue
            if not allow_external and not f.resolve().is_relative_to(base):
                raise CorpusRefused(
                    f"{f.name!r} aponta para fora de corpus/ (ligação simbólica?). "
                    "Copia o texto para lá ou usa --allow-external se é mesmo isso que queres."
                )
            if SKIP_DIRS & set(_below(base, f)) and not SKIP_DIRS & set(_below(base, root)):
                continue
            if f not in files:
                files.append(f)
    if not files:
        raise CorpusRefused("nenhum ficheiro .txt ou .md encontrado")
    return files


def blocks(files, tok, size=config.BLOCK_TOKENS):
    """Parte cada ficheiro em blocos de tokens. Cada bloco começa com o token de fim de texto,
    que fica na posição 0 e nunca é contado: as activações aí são anormais e sujavam o top-k."""
    eos = tok.eos_token_id
    step = size - 1
    for f in files:
        ids = tok.encode(f.read_text(encoding="utf-8", errors="replace"))
        for i in range(0, len(ids), step):
            part = ids[i:i + step]
            if len(part) >= MIN_BLOCK:
                yield relpath(f), [eos] + part
