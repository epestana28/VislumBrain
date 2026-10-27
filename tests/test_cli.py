import io
import os
import sys
import unittest
from unittest import mock

from vislumbrain import cli


def _correr_up(**ambiente_os):
    """Corre cmd_up sem tocar no Docker nem no disco e devolve o ambiente passado ao subprocesso."""
    with mock.patch.object(cli.subprocess, "run") as run, mock.patch.object(type(cli.config.ROOT), "mkdir"):
        cli.cmd_up(mock.Mock(cmd="up"))
    return run.call_args.kwargs["env"]


class Portabilidade(unittest.TestCase):
    def test_up_sem_getuid_como_no_windows(self):
        """No Windows os.getuid não existe: o up tem de arrancar na mesma, sem passar o utilizador."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VB_UID", None)
            guardado = {n: getattr(os, n) for n in ("getuid", "getgid") if hasattr(os, n)}
            for n in guardado:
                delattr(os, n)
            try:
                env = _correr_up()
            finally:
                for n, f in guardado.items():
                    setattr(os, n, f)
        self.assertNotIn("VB_UID", env)

    def test_up_com_getuid_passa_o_utilizador(self):
        """Em Linux e macOS o contentor corre como o utilizador, para a pasta de dados não ficar do root."""
        with mock.patch.object(os, "getuid", create=True, return_value=1234), \
                mock.patch.object(os, "getgid", create=True, return_value=5678):
            env = _correr_up()
        self.assertEqual((env["VB_UID"], env["VB_GID"]), ("1234", "5678"))

    def test_consola_cp1252_passa_a_utf8(self):
        """A consola antiga do Windows usa cp1252 e rebentava com acentos e com o ▁ dos tokens."""
        antigo = sys.stdout, sys.stderr
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        try:
            cli._utf8_console()
            sys.stdout.write("neurónio ▁the ↵\n")
            sys.stdout.flush()
            self.assertEqual(sys.stdout.encoding.lower().replace("-", ""), "utf8")
        finally:
            sys.stdout, sys.stderr = antigo


if __name__ == "__main__":
    unittest.main()
