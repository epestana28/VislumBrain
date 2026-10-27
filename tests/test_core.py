import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from vislumbrain import config, corpus, seal
from vislumbrain.scan import merge_topk
from vislumbrain.senses import cluster_senses


class TopK(unittest.TestCase):
    def test_merge_keeps_best_k_across_chunks(self):
        n, k = 2, 3
        vals = torch.full((n, k), float("-inf"))
        pos = torch.zeros((n, k), dtype=torch.long)
        chk = torch.full((n, k), -1, dtype=torch.long)
        a = torch.tensor([[1.0, 5.0], [3.0, 2.0]])      # (k_novo, N)
        vals, pos, chk = merge_topk(vals, pos, chk, a, torch.tensor([[7, 8], [9, 10]]), 0, k)
        b = torch.tensor([[4.0, 1.0], [0.5, 9.0]])
        vals, pos, chk = merge_topk(vals, pos, chk, b, torch.tensor([[1, 2], [3, 4]]), 1, k)
        self.assertEqual(vals[0].tolist(), [4.0, 3.0, 1.0])
        self.assertEqual(chk[0].tolist(), [1, 0, 0])
        self.assertEqual(pos[1].tolist(), [4, 8, 10])


class Senses(unittest.TestCase):
    def test_two_orthogonal_groups_are_two_senses(self):
        x = np.array([[1, 0, 0], [0.99, 0.1, 0], [0, 1, 0], [0.1, 0.99, 0]], dtype=float)
        self.assertEqual(cluster_senses(x, 0.7), [0, 0, 1, 1])

    def test_identical_vectors_are_one_sense(self):
        self.assertEqual(cluster_senses(np.ones((4, 3)), 0.7), [0, 0, 0, 0])

    def test_single_context(self):
        self.assertEqual(cluster_senses(np.ones((1, 3)), 0.7), [0])


class Barrier(unittest.TestCase):
    def test_outside_corpus_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.txt").write_text("texto privado")
            with self.assertRaises(corpus.CorpusRefused):
                corpus.resolve_inputs([d])

    def test_outside_corpus_needs_explicit_flag(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.txt").write_text("texto")
            self.assertEqual(len(corpus.resolve_inputs([d], allow_external=True)), 1)

    def test_default_reads_sample_and_skips_private(self):
        files = corpus.resolve_inputs()
        self.assertTrue(files)
        self.assertFalse(any("private" in f.parts for f in files))


class Seal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = config.DATA_DIR, config.ROOT
        config.ROOT = Path(self.tmp.name)
        config.DATA_DIR = config.ROOT / "data"
        (config.ROOT / "data" / "t").mkdir(parents=True)
        self.art = config.ROOT / "data" / "t" / "a.txt"
        self.art.write_text("resultado")

    def tearDown(self):
        config.DATA_DIR, config.ROOT = self.old
        self.tmp.cleanup()

    def test_verify_ok_then_tamper_fails(self):
        seal.stamp("t", "scan", params={}, artifacts=[self.art])
        quiet = lambda *_: None
        self.assertTrue(seal.verify("t", say=quiet))
        self.art.write_text("alterado")
        self.assertFalse(seal.verify("t", say=quiet))

    def test_chain_breaks_if_body_is_edited(self):
        seal.stamp("t", "scan", params={"a": 1}, artifacts=[self.art])
        p = config.DATA_DIR / "t" / "seal.json"
        d = json.loads(p.read_text())
        d["chain"][0]["body"]["params"]["a"] = 2
        p.write_text(json.dumps(d))
        self.assertFalse(seal.verify("t", say=lambda *_: None))

    def test_seal_holds_no_absolute_path_or_user(self):
        seal.stamp("t", "scan", params={}, artifacts=[self.art])
        text = (config.DATA_DIR / "t" / "seal.json").read_text()
        self.assertNotIn(self.tmp.name, text)
        self.assertNotIn("/home/", text)


class CorpusBarrierReal(unittest.TestCase):
    """Corpus temporário com private/ e uma ligação simbólica, sem depender das pastas do repositório."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = config.CORPUS_DIR
        config.CORPUS_DIR = Path(self.tmp.name) / "corpus"
        (config.CORPUS_DIR / "sample").mkdir(parents=True)
        (config.CORPUS_DIR / "private").mkdir()
        (config.CORPUS_DIR / "sample" / "a.txt").write_text("texto publico")
        (config.CORPUS_DIR / "private" / "p.txt").write_text("texto privado")
        self.outside = Path(self.tmp.name) / "fora.txt"
        self.outside.write_text("segredo")

    def tearDown(self):
        config.CORPUS_DIR = self.old
        self.tmp.cleanup()

    def names(self, files):
        return sorted(f.name for f in files)

    def test_default_skips_private(self):
        self.assertEqual(self.names(corpus.resolve_inputs()), ["a.txt"])

    def test_explicit_corpus_root_still_skips_private(self):
        self.assertEqual(self.names(corpus.resolve_inputs([config.CORPUS_DIR])), ["a.txt"])

    def test_private_only_when_asked_by_name(self):
        self.assertEqual(self.names(corpus.resolve_inputs([config.CORPUS_DIR / "private"])), ["p.txt"])

    def test_symlink_pointing_outside_is_refused(self):
        (config.CORPUS_DIR / "sample" / "link.txt").symlink_to(self.outside)
        with self.assertRaises(corpus.CorpusRefused):
            corpus.resolve_inputs()


class SealStrict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = config.DATA_DIR, config.ROOT
        config.ROOT = Path(self.tmp.name)
        config.DATA_DIR = config.ROOT / "data"
        (config.ROOT / "data" / "t").mkdir(parents=True)
        (config.ROOT / "corpus").mkdir()
        self.corpus = config.ROOT / "corpus" / "c.txt"
        self.corpus.write_text("texto")
        self.a1 = config.ROOT / "data" / "t" / "a1.txt"
        self.a2 = config.ROOT / "data" / "t" / "a2.txt"
        self.a1.write_text("um")
        self.a2.write_text("dois")
        self.quiet = lambda *_: None

    def tearDown(self):
        config.DATA_DIR, config.ROOT = self.old
        self.tmp.cleanup()

    def test_missing_corpus_inside_repo_fails(self):
        seal.stamp("t", "scan", params={}, artifacts=[self.a1], corpus_files=[self.corpus])
        self.assertTrue(seal.verify("t", say=self.quiet))
        self.corpus.unlink()
        self.assertFalse(seal.verify("t", say=self.quiet))

    def test_artifact_of_an_older_stage_is_still_checked(self):
        seal.stamp("t", "scan", params={}, artifacts=[self.a1])
        seal.stamp("t", "index", params={}, artifacts=[self.a2])
        self.assertTrue(seal.verify("t", say=self.quiet))
        self.a1.write_text("adulterado")
        self.assertFalse(seal.verify("t", say=self.quiet))


class StoreMatchesIndex(unittest.TestCase):
    """O leitor tem de recusar um modo ou umas colecções diferentes das do último index."""
    DEAD = "http://127.0.0.1:1"  # nada a ouvir: força o modo local

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = config.DATA_DIR
        config.DATA_DIR = Path(self.tmp.name) / "data"
        (config.DATA_DIR / "t").mkdir(parents=True)

    def tearDown(self):
        config.DATA_DIR = self.old
        self.tmp.cleanup()

    def build_local_index(self):
        from vislumbrain.store import Store, point
        st = Store("t", url=self.DEAD)
        st.reset()
        pts = [point(i, np.eye(config.EMBED_DIM)[i], {"layer": 0, "neuron": i}) for i in range(3)]
        st.upsert(st.sen, pts)
        st.upsert(st.ctx, pts[:2])
        st.write_meta()
        st.c.close()

    def test_local_index_read_back_in_local_mode_is_accepted(self):
        from vislumbrain.store import Store
        self.build_local_index()
        st = Store("t", url=self.DEAD, reader=True)
        self.assertEqual(st.mode, "local")
        st.c.close()

    def test_index_made_on_server_but_server_down_is_refused(self):
        from vislumbrain.store import Store
        (config.DATA_DIR / "t" / "index_meta.json").write_text(
            json.dumps({"backend": "server", "points": {}}))
        with self.assertRaises(SystemExit) as cm:
            Store("t", url=self.DEAD, reader=True)
        self.assertIn("up", str(cm.exception))

    def test_changed_point_count_is_refused(self):
        from vislumbrain.store import Store
        self.build_local_index()
        meta = config.DATA_DIR / "t" / "index_meta.json"
        d = json.loads(meta.read_text())
        d["points"] = {k: v + 1 for k, v in d["points"].items()}
        meta.write_text(json.dumps(d))
        with self.assertRaises(SystemExit):
            Store("t", url=self.DEAD, reader=True)

    def test_old_index_without_meta_still_works(self):
        from vislumbrain.store import Store
        st = Store("t", url=self.DEAD, reader=True)
        st.c.close()


class ModelPath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = config.ROOT
        config.ROOT = Path(self.tmp.name)
        (config.ROOT / "data" / "ft" / "model").mkdir(parents=True)

    def tearDown(self):
        config.ROOT = self.old
        self.tmp.cleanup()

    def test_relative_path_counts_from_project_root(self):
        from vislumbrain.model import resolve_model
        self.assertEqual(resolve_model("data/ft/model"), str((config.ROOT / "data/ft/model").resolve()))

    def test_none_stays_none(self):
        from vislumbrain.model import resolve_model
        self.assertIsNone(resolve_model(None))

    def test_outside_project_is_refused(self):
        from vislumbrain.model import resolve_model
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(ValueError):
                resolve_model(other)

    def test_missing_folder_and_hub_ids_are_refused(self):
        from vislumbrain.model import resolve_model
        for ref in ("data/nao-existe", "gpt2-medium"):
            with self.assertRaises(ValueError):
                resolve_model(ref)


if __name__ == "__main__":
    unittest.main()
