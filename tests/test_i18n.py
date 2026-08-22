import pytest
from src.app.i18n import _, set_language, ES_STRINGS, EN_STRINGS

def test_i18n_translation_key_resolution():
    """
    Ensure that _("cli.usage") returns the translated string and not the key itself.
    """
    set_language("es")
    es_usage = _("cli.usage")
    assert es_usage != "cli.usage"
    assert es_usage == ES_STRINGS["cli.usage"]
    
    set_language("en")
    en_usage = _("cli.usage")
    assert en_usage != "cli.usage"
    assert en_usage == EN_STRINGS["cli.usage"]

def test_i18n_placeholder_interpolation():
    """
    Verify that placeholders are interpolated correctly.
    """
    set_language("es")
    # ES: "Fase {i} de {total_phases}"
    es_text = _("contract.phase_section", i=2, total_phases=5)
    assert es_text == "Fase 2 de 5"
    
    set_language("en")
    # EN: "Phase {i} of {total_phases}"
    en_text = _("contract.phase_section", i=2, total_phases=5)
    assert en_text == "Phase 2 of 5"

def test_i18n_fallback_to_key():
    """
    Verify that a missing key returns the key itself.
    """
    set_language("es")
    assert _("nonexistent.key") == "nonexistent.key"
