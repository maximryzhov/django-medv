import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from . import load_env


class LoadEnvTests(TestCase):
    def test_parses_quoted_and_unquoted_values(self):
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "PLAIN=value\n"
                'DOUBLE_QUOTED="first\\nsecond"\n'
                "SINGLE_QUOTED='quoted value'\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                load_env(env_path)

                self.assertEqual(os.environ["PLAIN"], "value")
                self.assertEqual(os.environ["DOUBLE_QUOTED"], "first\nsecond")
                self.assertEqual(os.environ["SINGLE_QUOTED"], "quoted value")

    def test_ignores_comment(self):
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("# COMMENT=ignored\nSETTING=value\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                load_env(env_path)

                self.assertNotIn("COMMENT", os.environ)
                self.assertEqual(os.environ["SETTING"], "value")

    def test_parses_value_with_inline_comment(self):
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("SETTING=value # comment\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                load_env(env_path)

                self.assertEqual(os.environ["SETTING"], "value")

    def test_does_not_overwrite_existing_value(self):
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("SETTING=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"SETTING": "existing"}, clear=True):
                load_env(env_path)

                self.assertEqual(os.environ["SETTING"], "existing")
