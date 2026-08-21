"""
tests/test_anti_cheat.py — Anti-cheat heuristic tests.
Copyright (C) Alenia Studios — GNU GPL v3
"""

import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from app.anti_cheat import validate_completion_log, validate_early_confirm_phrase
from app.errors import AntiCheatError, EarlyCompletionError


VALID_INSTRUCTIONS = "Implementar el módulo de autenticación con JWT y pruebas unitarias"


class TestGarbageRejection(unittest.TestCase):
    GARBAGE = [
        "asdfasdfasdf",
        "qwerty",
        "123456",
        "aaaaaaa",
        "aaaaaaaaaaaaaaaaaaaa",
        "   ",
        "",
        "asdf asdf asdf asdf",
        "qwertyuiop qwertyuiop",
    ]

    def test_garbage_rejected(self):
        for text in self.GARBAGE:
            with self.subTest(text=repr(text)):
                with self.assertRaises((AntiCheatError, EarlyCompletionError),
                                       msg=f"Should have been rejected: {text!r}"):
                    validate_completion_log(text, VALID_INSTRUCTIONS, tau=0.5)


class TestEntropyCheck(unittest.TestCase):
    def test_low_entropy_rejected(self):
        # Very repetitive text
        with self.assertRaises(AntiCheatError):
            validate_completion_log("aaabbb" * 5, VALID_INSTRUCTIONS, tau=0.5)

    def test_normal_text_passes(self):
        good_log = (
            "Completé la implementación del módulo de autenticación. "
            "Las pruebas unitarias pasan con cobertura del 85%. "
            "Documenté los endpoints de JWT."
        )
        # Should not raise
        validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.5)


class TestLexicalOverlap(unittest.TestCase):
    def test_unrelated_text_rejected(self):
        unrelated = (
            "Fui al supermercado y compré pan. Después vi la televisión "
            "y luego dormí una siesta larga. La película estuvo buena."
        )
        with self.assertRaises(AntiCheatError):
            validate_completion_log(unrelated, VALID_INSTRUCTIONS, tau=0.5)

    def test_related_text_passes(self):
        related = (
            "Implementé la autenticación usando JWT. "
            "Escribí pruebas unitarias para el módulo. "
            "El código funciona correctamente."
        )
        validate_completion_log(related, VALID_INSTRUCTIONS, tau=0.5)


class TestEarlyCompletion(unittest.TestCase):
    def test_early_without_phrase_rejected(self):
        good_log = (
            "Implementé el módulo de autenticación con JWT y pruebas unitarias "
            "en tiempo récord. Todo funciona."
        )
        with self.assertRaises(EarlyCompletionError):
            validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.05)

    def test_early_with_phrase_passes(self):
        good_log = (
            "confirmo que termine antes de tiempo. "
            "Implementé el módulo de autenticación con JWT y pruebas unitarias. "
            "Todo está documentado."
        )
        validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.05)

    def test_normal_tau_no_phrase_required(self):
        good_log = (
            "Implementé el módulo de autenticación con JWT. "
            "Las pruebas unitarias pasan correctamente."
        )
        # tau=0.5 → no early check required
        validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.5)


class TestEarlyConfirmPhrase(unittest.TestCase):
    def test_exact_phrase(self):
        self.assertTrue(
            validate_early_confirm_phrase("confirmo que termine antes de tiempo")
        )

    def test_phrase_in_larger_text(self):
        self.assertTrue(
            validate_early_confirm_phrase(
                "confirmo que termine antes de tiempo, todo está completo"
            )
        )

    def test_wrong_phrase(self):
        self.assertFalse(
            validate_early_confirm_phrase("creo que ya terminé")
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
