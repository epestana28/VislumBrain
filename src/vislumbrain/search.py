"""Pesquisa polissemântica: de um texto para o par (neurónio, sentido) mais próximo, e o seu benchmark."""
import time

from . import config
from .embed import Embedder
from .store import Store

BENCH_QUERIES = [
    "the capital city of a country on the Atlantic coast",
    "money deposited in a bank account",
    "the bank of a river with trees",
    "a programming language used for data science",
    "the king and the royal family",
    "the result of a football match",
    "how to cook rice with olive oil",
    "population and economy statistics",
    "the history of the empire and its colonies",
    "the weather is rainy and cold",
    "a musician playing the guitar",
    "medical treatment for a disease",
]


def search(tag, query, limit=10, exact=False, contexts=False, say=print):
    store = Store(tag, reader=True)
    vec = Embedder().encode([query])[0]
    name = store.ctx if contexts else store.sen
    t0 = time.perf_counter()
    hits = store.query(name, vec, limit=limit, exact=exact)
    ms = (time.perf_counter() - t0) * 1000
    say(f"{len(hits)} resultados em {ms:.1f} ms ({'exacta' if exact else 'aproximada'}, "
        f"{'contextos' if contexts else 'sentidos'})")
    for h in hits:
        p = h.payload
        what = f"sentido {p['sense'] + 1}" if "size" in p else f"rank {p['rank']}"
        txt = (p.get("example") or p["text"]).replace("\n", " ")[:80]
        say(f"  {h.score:.3f}  L{p['layer']}.N{p['neuron']}  {what}  act {p.get('max_act', p.get('act'))}  «{txt}»")
    return hits


def bench(tag, limit=10, repeats=5, say=print):
    """Compara pesquisa aproximada (HNSW) com exacta (força bruta): latência e recall@limit."""
    store = Store(tag, reader=True)
    if store.local:
        say("modo local: aproximada e exacta são ambas força bruta, o benchmark não diz nada. "
            "Arranca o Qdrant (vislumbrain up) para comparar HNSW com exacta.")
        return
    vecs = Embedder().encode(BENCH_QUERIES)
    for label, name in (("sentidos", store.sen), ("contextos", store.ctx)):
        info = store.wait_indexed(name)
        t_ap = t_ex = rec = 0.0
        for v in vecs:
            store.query(name, v, limit=limit)  # aquece
            t0 = time.perf_counter()
            for _ in range(repeats):
                ap = store.query(name, v, limit=limit)
            t_ap += (time.perf_counter() - t0) / repeats
            t0 = time.perf_counter()
            for _ in range(repeats):
                ex = store.query(name, v, limit=limit, exact=True)
            t_ex += (time.perf_counter() - t0) / repeats
            rec += len({h.id for h in ap} & {h.id for h in ex}) / max(1, len(ex))
        n = len(vecs)
        say(f"{label:<10} pontos={info.points_count} indexados={info.indexed_vectors_count}  "
            f"aproximada={t_ap / n * 1000:.1f} ms  exacta={t_ex / n * 1000:.1f} ms  recall@{limit}={rec / n:.3f}")
