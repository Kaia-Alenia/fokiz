import pytest
from src.app.i18n import _, set_language, ES_STRINGS, EN_STRINGS

def test_i18n_translation_key_resolution():
    set_language('es')
    es_usage = _('cli.usage')
    assert es_usage != 'cli.usage'
    assert es_usage == ES_STRINGS['cli.usage']
    set_language('en')
    en_usage = _('cli.usage')
    assert en_usage != 'cli.usage'
    assert en_usage == EN_STRINGS['cli.usage']

def test_i18n_placeholder_interpolation():
    set_language('es')
    es_text = _('contract.phase_section', i=2, total_phases=5)
    assert es_text == ES_STRINGS['contract.phase_section'].format(i=2, total_phases=5)
    set_language('en')
    en_text = _('contract.phase_section', i=2, total_phases=5)
    assert en_text == 'Phase 2 of 5'

def test_i18n_fallback_to_key():
    set_language('es')
    assert _('nonexistent.key') == 'nonexistent.key'
import json
import src.app.config
import src.app.constants

def test_i18n_persistence(monkeypatch, tmp_path):
    config_dir = tmp_path / '.local' / 'share' / 'fokiz'
    config_dir.mkdir(parents=True, exist_ok=True)
    fake_config = config_dir / 'config.json'
    monkeypatch.setattr(src.app.config, '_CONFIG_FILE', fake_config)
    monkeypatch.setattr(src.app.config, 'FOKIZ_DATA_DIR', config_dir)
    with open(fake_config, 'w') as f:
        json.dump({'language': 'es', 'timezone': 'America/Mexico_City'}, f)
    src.app.config._loaded = None
    conf = src.app.config.load_config()
    lang = conf.get('language', 'en')
    src.app.i18n.set_language(lang)
    assert src.app.i18n.CURRENT_LANG == 'es'
    assert src.app.i18n._('cli.usage') == src.app.i18n.ES_STRINGS['cli.usage']
    with open(fake_config, 'w') as f:
        json.dump({'language': 'en', 'timezone': 'America/Mexico_City'}, f)
    src.app.config._loaded = None
    conf = src.app.config.load_config()
    lang = conf.get('language', 'en')
    src.app.i18n.set_language(lang)
    assert src.app.i18n.CURRENT_LANG == 'en'
    assert src.app.i18n._('cli.usage') == src.app.i18n.EN_STRINGS['cli.usage']
    with open(fake_config, 'w') as f:
        json.dump({'language': 'fr', 'timezone': 'America/Mexico_City'}, f)
    src.app.config._loaded = None
    conf = src.app.config.load_config()
    lang = conf.get('language', 'en')
    src.app.i18n.set_language(lang)
    assert src.app.i18n.CURRENT_LANG == 'en'
    fake_config.unlink()
    # Mock defaults for when file is missing
    monkeypatch.setitem(src.app.config._DEFAULTS, 'timezone', 'America/Mexico_City')
    src.app.config._loaded = None
    conf = src.app.config.load_config()
    lang = conf.get('language', 'en')
    src.app.i18n.set_language(lang)
    assert src.app.i18n.CURRENT_LANG == 'en'
