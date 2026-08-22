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

import importlib
import json
import src.app.i18n

def test_i18n_persistence(monkeypatch, tmp_path):
    """
    Verify that reloading the i18n module correctly picks up the persisted language
    from config.json, and uses English as a safe default if invalid or missing.
    """
    monkeypatch.setattr("os.path.expanduser", lambda path: str(tmp_path) if path == "~" else path)
    
    config_dir = tmp_path / ".local" / "share" / "fokiz"
    config_dir.mkdir(parents=True, exist_ok=True)
    fake_config = config_dir / "config.json"
    
    # Save "es"
    with open(fake_config, "w") as f:
        json.dump({"language": "es"}, f)
    
    importlib.reload(src.app.i18n)
    assert src.app.i18n.CURRENT_LANG == "es"
    assert src.app.i18n._("cli.usage") == src.app.i18n.ES_STRINGS["cli.usage"]
    
    # Save "en"
    with open(fake_config, "w") as f:
        json.dump({"language": "en"}, f)
        
    importlib.reload(src.app.i18n)
    assert src.app.i18n.CURRENT_LANG == "en"
    assert src.app.i18n._("cli.usage") == src.app.i18n.EN_STRINGS["cli.usage"]
    
    # Save invalid
    with open(fake_config, "w") as f:
        json.dump({"language": "fr"}, f)
        
    importlib.reload(src.app.i18n)
    assert src.app.i18n.CURRENT_LANG == "en"
    
    # Delete file
    fake_config.unlink()
    importlib.reload(src.app.i18n)
    assert src.app.i18n.CURRENT_LANG == "en"

