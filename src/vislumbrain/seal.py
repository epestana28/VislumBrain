"""O Selo: prova de integridade e proveniência de cada execução.

Cada etapa acrescenta uma entrada a data/<tag>/seal.json com o modelo, o corpus, os parâmetros e
os hashes dos artefactos. O hash da entrada cobre o corpo todo e a entrada anterior, por isso
alterar qualquer coisa a meio parte a cadeia. Sem chave de assinatura: prova que o resultado
não foi mexido, não prova quem o fez.
Nada pessoal entra aqui: caminhos relativos ao projecto, sem utilizador nem nome de máquina.
"""
import json
import platform
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from urllib.request import urlopen

from . import config
from .util import canonical, hash_path, relpath, sha256_text

EXCLUDE = ("sessoes",)  # sessões ao vivo escrevem-se depois e não fazem parte do que é selado


def _path(tag):
    return config.DATA_DIR / tag / "seal.json"


def _chain(tag):
    p = _path(tag)
    return json.loads(p.read_text(encoding="utf-8"))["chain"] if p.exists() else []


def corpus_paths(tag):
    """Os ficheiros de corpus lidos na última etapa que os registou, ou None se o Selo não existe."""
    for entry in reversed(_chain(tag)):
        if entry["body"]["corpus"]:
            return sorted(c["path"] for c in entry["body"]["corpus"])
    return None


def last(tag, stage=None):
    for entry in reversed(_chain(tag)):
        if stage is None or entry["body"]["stage"] == stage:
            return entry["seal"]
    return None


def _versions():
    out = {"python": platform.python_version()}
    for pkg in ("torch", "transformers", "qdrant-client", "scikit-learn", "numpy"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def _qdrant(names):
    try:
        with urlopen(config.QDRANT_URL + "/", timeout=3) as r:
            version = json.load(r).get("version")
        counts = {}
        for name in names:
            with urlopen(f"{config.QDRANT_URL}/collections/{name}", timeout=3) as r:
                counts[name] = json.load(r)["result"]["points_count"]
        return {"version": version, "collections": counts}
    except Exception:
        return None


def stamp(tag, stage, *, params, artifacts, corpus_files=(), model=None, qdrant_collections=()):
    chain = _chain(tag)
    arts = []
    for a in artifacts:
        digest, size = hash_path(a, exclude=EXCLUDE)
        arts.append({"path": relpath(a), "sha256": digest, "bytes": size})
    body = {
        "vislumbrain": config.VERSION,
        "credits": config.CREDITS,
        "stage": stage,
        "tag": tag,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prev": chain[-1]["seal"] if chain else None,
        "model": model,
        "embedder": {"id": config.EMBED_ID, "revision": config.EMBED_REVISION},
        "params": params,
        "corpus": [{"path": relpath(f), "sha256": hash_path(f)[0]} for f in corpus_files],
        "artifacts": arts,
        "env": _versions(),
        "qdrant": _qdrant(qdrant_collections) if qdrant_collections else None,
    }
    seal = sha256_text(canonical(body))
    chain.append({"body": body, "seal": seal})
    out = _path(tag)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"chain": chain}, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return seal


def verify(tag, say=print):
    """Confere a cadeia, cada artefacto pela entrada mais recente que o cobre, e o corpus da última entrada.
    Não reconfere o Qdrant nem os pesos do modelo. True se tudo bate."""
    chain = _chain(tag)
    if not chain:
        say(f"sem selo para a tag {tag!r}")
        return False
    ok, prev = True, None
    for i, e in enumerate(chain):
        good = sha256_text(canonical(e["body"])) == e["seal"] and e["body"]["prev"] == prev
        say(f"{'OK    ' if good else 'FALHA '} [{i}] {e['body']['stage']:<8} {e['seal'][:16]}")
        ok, prev = ok and good, e["seal"]
    body = chain[-1]["body"]
    seen = set()
    for e in reversed(chain):
        for a in e["body"]["artifacts"]:
            if a["path"] in seen:
                continue
            seen.add(a["path"])
            p = config.ROOT / a["path"]
            now = hash_path(p, exclude=EXCLUDE)[0] if p.exists() else None
            good = now == a["sha256"]
            say(f"{'OK    ' if good else 'FALHA '} artefacto {a['path']}" + ("" if p.exists() else " (não existe)"))
            ok = ok and good
    unchecked = 0
    for c in body["corpus"]:
        p = config.ROOT / c["path"]
        if not p.exists():
            if c["path"].startswith("corpus/"):
                say(f"FALHA  corpus {c['path']} (já não existe)")
                ok = False
            else:
                say(f"--     corpus {c['path']} (fora do repositório, não verificável)")
                unchecked += 1
            continue
        good = hash_path(p)[0] == c["sha256"]
        say(f"{'OK    ' if good else 'FALHA '} corpus {c['path']}")
        ok = ok and good
    if unchecked:
        say(f"aviso: {unchecked} ficheiro(s) de corpus externo não puderam ser verificados")
    return ok
