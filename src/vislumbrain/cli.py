"""Linha de comandos do VislumBrain."""
import argparse
import os
import re
import subprocess
import sys

from . import config, corpus, seal
from .util import relpath


def _tag(s):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", s):
        raise argparse.ArgumentTypeError("a tag só pode ter letras, números, - e _")
    return s


def _topk(s):
    n = int(s)
    if not 1 <= n < 100:
        raise argparse.ArgumentTypeError("--topk tem de estar entre 1 e 99")
    return n


def _model(s):
    from .model import resolve_model
    try:
        return resolve_model(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def _layers(s):
    return tuple(int(x) for x in s.split(","))


def _corpus_args(p):
    p.add_argument("--corpus", nargs="*", help="ficheiros ou pastas dentro de corpus/ (por omissão, corpus/ inteiro)")
    p.add_argument("--allow-external", action="store_true", help="aceita corpus fora de corpus/ (cuidado: o texto fica em data/)")


def _scan_args(p):
    p.add_argument("--model", type=_model, help="pesos locais (ex. data/ft/model). Por omissão, o GPT-2 small oficial")
    p.add_argument("--layers", type=_layers, default=config.DEFAULT_LAYERS)
    p.add_argument("--topk", type=_topk, default=config.DEFAULT_TOPK)
    p.add_argument("--min-act", type=float, default=config.DEFAULT_MIN_ACT)
    _corpus_args(p)


def _files(a):
    return corpus.resolve_inputs(a.corpus, a.allow_external)


def cmd_up(a):
    (config.ROOT / "qdrant_storage").mkdir(exist_ok=True)  # senão o Docker cria-a como root e o Qdrant não consegue escrever
    env = dict(os.environ)
    if hasattr(os, "getuid"):  # no Windows não existe, e o Docker Desktop não precisa disto
        env.update(VB_UID=str(os.getuid()), VB_GID=str(os.getgid()))
    subprocess.run(["docker", "compose", "-f", str(config.ROOT / "docker-compose.yml"),
                    "down" if a.cmd == "down" else "up", *([] if a.cmd == "down" else ["-d"])], check=True, env=env)


def cmd_scan(a):
    from . import scan
    scan.scan(a.tag, _files(a), a.model, a.layers, a.topk, a.min_act)


def cmd_index(a):
    from . import indexer
    indexer.build(a.tag, a.threshold)


def cmd_notes(a):
    from . import notes
    notes.write(a.tag, a.max_notes)


def cmd_run(a):
    """scan, index, notes e, no fim, o Selo que cobre tudo."""
    from . import indexer, notes, scan
    from .model import identity
    files = _files(a)
    scan.scan(a.tag, files, a.model, a.layers, a.topk, a.min_act)
    indexer.build(a.tag, a.threshold)
    notes.write(a.tag, a.max_notes)
    base = config.DATA_DIR / a.tag
    s = seal.stamp(a.tag, "run", params={"layers": list(a.layers), "topk": a.topk, "min_act": a.min_act,
                                          "threshold": a.threshold, "max_notes": a.max_notes},
                   model=identity(a.model), corpus_files=files,
                   artifacts=[base / "contexts.jsonl", base / "stats.npz", base / "scan_meta.json",
                              base / "senses.jsonl", config.VAULT_DIR / a.tag / "neurons",
                              config.VAULT_DIR / a.tag / "Indice.md"],
                   qdrant_collections=[f"{config.COLLECTION_PREFIX}{a.tag}_senses",
                                       f"{config.COLLECTION_PREFIX}{a.tag}_contexts"])
    print(f"SELO FINAL ({a.tag}): {s}")


def cmd_search(a):
    from . import search
    search.search(a.tag, a.query, a.limit, a.exact, a.contexts)


def cmd_bench(a):
    from . import search
    search.bench(a.tag, a.limit)


def cmd_live(a):
    from . import live
    texts = [a.text] if a.text else (line.strip() for line in sys.stdin if line.strip())
    live.run(a.tag, texts, a.top, a.note)


def cmd_serve(a):
    from . import serve
    if not 4 <= a.per_layer <= 24:
        sys.exit("erro: --per-layer tem de estar entre 4 e 24")
    serve.run(a.tag, a.port, a.per_layer)


def cmd_ablate(a):
    from . import ablate
    ablate.run(a.tag, a.layer, a.neuron)


def cmd_finetune(a):
    from . import finetune
    files = corpus.resolve_inputs(a.corpus, a.allow_external)
    finetune.run(files, a.epochs, a.lr, a.batch)


def cmd_diff(a):
    from . import diff
    diff.run(a.layers, a.top)


def cmd_verify(a):
    sys.exit(0 if seal.verify(a.tag) else 1)


def _utf8_console():
    """A consola do Windows pode usar cp850 ou cp1252 e rebentar com acentos e símbolos. Força UTF-8 na saída."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _utf8_console()
    ap = argparse.ArgumentParser(prog="vislumbrain", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        return p

    def tag(p):
        p.add_argument("--tag", type=_tag, default="base", help="nome do conjunto de resultados (base, ft, ...)")

    for n in ("up", "down"):
        add(n, cmd_up, "arranca ou pára o Qdrant do projecto")

    p = add("scan", cmd_scan, "passo 1: contextos de topo por neurónio")
    tag(p); _scan_args(p)
    p = add("index", cmd_index, "passo 2: embeddings, sentidos e Qdrant")
    tag(p); p.add_argument("--threshold", type=float, default=config.DEFAULT_SENSE_THRESHOLD)
    p = add("notes", cmd_notes, "passo 3: notas para o Obsidian")
    tag(p); p.add_argument("--max-notes", type=int, default=config.DEFAULT_MAX_NOTES)
    p = add("run", cmd_run, "scan + index + notes + Selo final")
    tag(p); _scan_args(p)
    p.add_argument("--threshold", type=float, default=config.DEFAULT_SENSE_THRESHOLD)
    p.add_argument("--max-notes", type=int, default=config.DEFAULT_MAX_NOTES)

    p = add("search", cmd_search, "pesquisa polissemântica por texto")
    tag(p); p.add_argument("query"); p.add_argument("--limit", type=int, default=10)
    p.add_argument("--exact", action="store_true", help="força bruta em vez de HNSW")
    p.add_argument("--contexts", action="store_true", help="pesquisar contextos em vez de sentidos")
    p = add("bench", cmd_bench, "aproximada contra exacta: latência e recall")
    tag(p); p.add_argument("--limit", type=int, default=10)
    p = add("live", cmd_live, "neurónios e sentidos a cada token, em tempo real")
    tag(p); p.add_argument("--text"); p.add_argument("--top", type=int, default=5)
    p.add_argument("--note", action="store_true", help="grava a sessão em vault/<tag>/sessoes/")
    p = add("serve", cmd_serve, "painel no browser: neurónios a acender e os contextos onde disparam")
    tag(p); p.add_argument("--port", type=int, default=8765)
    p.add_argument("--per-layer", type=int, default=config.DEFAULT_PANEL_PER_LAYER, help="neurónios mostrados por camada (4 a 24)")
    p = add("ablate", cmd_ablate, "desliga um neurónio e mede o efeito")
    tag(p); p.add_argument("layer", type=int); p.add_argument("neuron", type=int)

    p = add("finetune", cmd_finetune, "fine-tuning do GPT-2 small (prova de conceito)")
    _corpus_args(p)
    p.add_argument("--epochs", type=int, default=3); p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--batch", type=int, default=4)
    p = add("diff", cmd_diff, "o que mudou entre base e ft")
    p.add_argument("--layers", type=_layers, default=config.DEFAULT_LAYERS); p.add_argument("--top", type=int, default=20)
    p = add("verify", cmd_verify, "confere o Selo")
    tag(p)

    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except corpus.CorpusRefused as e:
        sys.exit(f"corpus recusado: {e}")


if __name__ == "__main__":
    main()
