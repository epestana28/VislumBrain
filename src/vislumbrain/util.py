"""Utilitários de caminhos e hashes. Os caminhos que saem daqui são sempre relativos ao projecto."""
import hashlib
import json
from pathlib import Path

from . import config


def relpath(p):
    """Caminho relativo à raiz do projecto. Fora dela, só o nome do ficheiro, para não expor a máquina."""
    p = Path(p).resolve()
    try:
        return p.relative_to(config.ROOT).as_posix()
    except ValueError:
        return p.name


def show_piece(s):
    """Um token legível. O espaço inicial vira ▁ e a quebra de linha vira ⏎, para se ver onde o BPE corta."""
    s = s.replace("\n", "⏎").replace("`", "'")
    return "▁" + s[1:] if s.startswith(" ") else s


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_path(p, exclude=()):
    """Hash de um ficheiro, ou de uma árvore (caminhos relativos e hashes, por ordem). Devolve (sha256, bytes)."""
    p = Path(p)
    if p.is_file():
        return sha256_file(p), p.stat().st_size
    h = hashlib.sha256()
    total = 0
    for f in sorted(x for x in p.rglob("*") if x.is_file()):
        rel = f.relative_to(p)
        if set(exclude) & set(rel.parts):
            continue
        h.update(f"{rel.as_posix()}\0{sha256_file(f)}\n".encode("utf-8"))
        total += f.stat().st_size
    return h.hexdigest(), total
