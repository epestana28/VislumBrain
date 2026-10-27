"""Qdrant: duas colecções por tag. Só toca em colecções com o prefixo vislumbrain_."""
import json
import time
import urllib.request
import warnings

from qdrant_client import QdrantClient, models

from . import config


def point(pid, vec, payload):
    return models.PointStruct(id=pid, vector=[float(x) for x in vec], payload=payload)


def pid(layer, neuron, k):
    """Id estável: camada, neurónio e (sentido ou rank). Cabe com folga em 3072 neurónios e k < 100."""
    return layer * 10_000_000 + neuron * 100 + k


def _server_up(url):
    try:
        with urllib.request.urlopen(url + "/", timeout=2):
            return True
    except Exception:
        return False


class Store:
    """Usa o servidor Qdrant se houver um a responder. Senão, o modo local embebido, que não precisa de Docker."""

    def __init__(self, tag, url=None, reader=False):
        """reader=True confere, antes de pesquisar, que este modo e estas colecções são as do último index."""
        url = url or config.QDRANT_URL
        self.tag, self.url = tag, url
        self.local = not _server_up(url)
        if self.local:
            path = config.DATA_DIR / "qdrant_local"
            path.mkdir(parents=True, exist_ok=True)
            with warnings.catch_warnings():  # o aviso do Qdrant sobre "mais de 20 000 pontos" é em inglês e já está dito na linha abaixo
                warnings.filterwarnings("ignore", message="Local mode is not recommended")
                self.c = QdrantClient(path=str(path))
            print("  qdrant: sem servidor, a usar o modo local (força bruta, sem HNSW)")
        else:
            self.c = QdrantClient(url=url, timeout=120, check_compatibility=False)
        self.ctx = f"{config.COLLECTION_PREFIX}{tag}_contexts"
        self.sen = f"{config.COLLECTION_PREFIX}{tag}_senses"
        if reader:
            self._check_matches_index()

    @property
    def mode(self):
        return "local" if self.local else "server"

    def _count(self, name):
        try:
            return self.c.count(name, exact=True).count
        except Exception:
            return None

    def write_meta(self):
        """Regista onde e com quantos pontos o índice ficou, para os leitores detectarem um modo ou colecções trocados."""
        meta = {"backend": self.mode, "points": {n: self._count(n) for n in (self.sen, self.ctx)}}
        (config.DATA_DIR / self.tag / "index_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    def _check_matches_index(self):
        path = config.DATA_DIR / self.tag / "index_meta.json"
        if not path.exists():  # índice antigo, feito antes deste registo
            return
        meta = json.loads(path.read_text(encoding="utf-8"))
        if meta["backend"] != self.mode:
            if meta["backend"] == "server":
                raise SystemExit(f"O índice {self.tag!r} foi feito num servidor Qdrant e ele não responde em {self.url}. "
                                 "Arranca-o com: ./vislumbrain up")
            raise SystemExit(f"O índice {self.tag!r} foi feito em modo local, mas agora há um servidor Qdrant em {self.url}, "
                             "que pode ter colecções de outra altura. Refaz o índice com: "
                             f"./vislumbrain index --tag {self.tag}")
        for name, expected in meta["points"].items():
            found = self._count(name)
            if found != expected:
                raise SystemExit(f"A colecção {name} tem {found} pontos e o último index gravou {expected}. "
                                 f"Refaz o índice com: ./vislumbrain index --tag {self.tag}")

    def reset(self):
        for name in (self.ctx, self.sen):
            assert name.startswith(config.COLLECTION_PREFIX)
            if self.c.collection_exists(name):
                self.c.delete_collection(name)
            self.c.create_collection(
                name, vectors_config=models.VectorParams(size=config.EMBED_DIM, distance=models.Distance.COSINE),
                # índice HNSW cedo, para o benchmark comparar de facto aproximada contra exacta
                optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1000))
            if self.local:  # no modo local estes índices não fazem nada e só geram um aviso em inglês
                continue
            for field in ("layer", "neuron"):
                self.c.create_payload_index(name, field_name=field, field_schema=models.PayloadSchemaType.INTEGER)

    def upsert(self, name, points, batch=512):
        for i in range(0, len(points), batch):
            self.c.upsert(name, points=points[i:i + batch], wait=True)

    def query(self, name, vec, limit=10, exact=False, layer=None, neuron=None):
        must = []
        if layer is not None:
            must.append(models.FieldCondition(key="layer", match=models.MatchValue(value=layer)))
        if neuron is not None:
            must.append(models.FieldCondition(key="neuron", match=models.MatchValue(value=neuron)))
        return self.c.query_points(
            name, query=[float(x) for x in vec], limit=limit, with_payload=True,
            query_filter=models.Filter(must=must) if must else None,
            search_params=models.SearchParams(exact=exact)).points

    def wait_indexed(self, name, timeout=120):
        """O índice HNSW é construído em segundo plano. Espera até a colecção ficar verde."""
        t0 = time.time()
        info = self.c.get_collection(name)
        if self.local:
            return info
        while time.time() - t0 < timeout:
            done = info.status == models.CollectionStatus.GREEN and \
                (info.indexed_vectors_count or 0) >= 0.9 * (info.points_count or 0)
            if done:
                break
            time.sleep(1)
            info = self.c.get_collection(name)
        return info
