"""Sentidos: os contextos de um neurónio agrupados por proximidade semântica."""


def cluster_senses(vecs, threshold):
    """Uma etiqueta por contexto, numerada pela ordem de aparição.

    Os contextos chegam do mais forte para o mais fraco, por isso o sentido 0 é o do contexto mais forte.
    Mais de um sentido sugere polissemia. O limiar é distância de cosseno entre grupos.
    """
    n = len(vecs)
    if n < 2:
        return [0] * n
    from sklearn.cluster import AgglomerativeClustering

    raw = AgglomerativeClustering(
        n_clusters=None, distance_threshold=threshold, metric="cosine", linkage="average"
    ).fit_predict(vecs)
    order = {}
    return [order.setdefault(int(r), len(order)) for r in raw]
