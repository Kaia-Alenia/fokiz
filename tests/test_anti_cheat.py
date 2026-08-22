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
from app.i18n import set_language

set_language("en")

VALID_INSTRUCTIONS = "Implement the authentication module with JWT and unit tests"


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
            "I completed the implementation of the authentication module. "
            "The unit tests pass with 85% coverage. "
            "I documented the JWT endpoints."
        )
        # Should not raise
        validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.5)


class TestLexicalOverlap(unittest.TestCase):
    def test_unrelated_text_rejected(self):
        unrelated = (
            "Cats sleep all day. They eat fish from a small bowl. "
            "Sometimes birds fly outside."
        )
        with self.assertRaises(AntiCheatError):
            validate_completion_log(unrelated, VALID_INSTRUCTIONS, tau=0.5)

    def test_related_text_passes(self):
        related = (
            "I implemented authentication using JWT. "
            "I wrote unit tests for the module. "
            "The code works correctly."
        )
        validate_completion_log(related, VALID_INSTRUCTIONS, tau=0.5)


class TestEarlyCompletion(unittest.TestCase):
    def test_early_without_phrase_rejected(self):
        good_log = (
            "I implemented the authentication module with JWT and unit tests "
            "in record time. Everything works."
        )
        with self.assertRaises(EarlyCompletionError):
            validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.05)

    def test_early_with_phrase_passes(self):
        good_log = (
            "i confirm i finished early. "
            "I implemented the authentication module with JWT and unit tests. "
            "Everything is documented."
        )
        validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.05)

    def test_normal_tau_no_phrase_required(self):
        good_log = (
            "I implemented the authentication module with JWT. "
            "The unit tests pass correctly."
        )
        # tau=0.5 → no early check required
        validate_completion_log(good_log, VALID_INSTRUCTIONS, tau=0.5)


class TestEarlyConfirmPhrase(unittest.TestCase):
    def test_exact_phrase(self):
        self.assertTrue(
            validate_early_confirm_phrase("i confirm i finished early")
        )

    def test_phrase_in_larger_text(self):
        self.assertTrue(
            validate_early_confirm_phrase(
                "i confirm i finished early, everything is complete"
            )
        )

    def test_wrong_phrase(self):
        self.assertFalse(
            validate_early_confirm_phrase("i think i am done")
        )

    def test_spanish_phrase(self):
        set_language("es")
        self.assertTrue(
            validate_early_confirm_phrase("confirmo que termine antes de tiempo")
        )
        set_language("en")  # restore



if __name__ == "__main__":
    unittest.main(verbosity=2)
