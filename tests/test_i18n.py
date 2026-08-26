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


def test_messages_pick_message_respects_language():
    set_language('es')
    from src.app.messages import pick_message, _MESSAGES_ORANGE
    from src.app.math_engine import Zone
    msg_es = pick_message(Zone.ORANGE, nickname='TestUser')
    # Spanish message must come from ES_STRINGS
    assert any(ES_STRINGS[k].replace('{nickname}', 'TestUser') in msg_es or msg_es.startswith('TestUser,') for k in _MESSAGES_ORANGE)

    set_language('en')
    msg_en = pick_message(Zone.ORANGE, nickname='TestUser')
    assert any(EN_STRINGS[k].replace('{nickname}', 'TestUser') in msg_en or msg_en.startswith('TestUser,') for k in _MESSAGES_ORANGE)


def test_monitor_dispatches_in_configured_language(monkeypatch, tmp_path):
    import json
    import app.config
    import app.i18n
    from unittest.mock import patch, MagicMock
    import monitor

    config_dir = tmp_path / '.local' / 'share' / 'fokiz'
    config_dir.mkdir(parents=True, exist_ok=True)
    fake_config = config_dir / 'config.json'
    monkeypatch.setattr(app.config, '_CONFIG_FILE', fake_config)
    monkeypatch.setattr(app.config, 'FOKIZ_DATA_DIR', config_dir)

    for lang in ['es', 'en']:
        with open(fake_config, 'w') as f:
            json.dump({'language': lang, 'timezone': 'America/Mexico_City'}, f)
        app.config._loaded = None

        with patch('monitor.DB_PATH') as mock_db, \
             patch('monitor.SECRET_PATH') as mock_sec, \
             patch('app.db.get_active_tasks') as mock_tasks, \
             patch('app.db.get_phases') as mock_phases, \
             patch('app.db.get_user_config', return_value={'nickname': 'TestUser', 'timezone': 'America/Mexico_City'}), \
             patch('app.db.get_last_notification', return_value=None), \
             patch('app.db.insert_notification') as mock_insert, \
             patch('monitor.check_contract_integrity') as mock_integrity, \
             patch('monitor.get_presence') as mock_presence, \
             patch('monitor.dispatch') as mock_dispatch:

            mock_db.exists.return_value = True
            mock_sec.exists.return_value = True
            mock_tasks.return_value = [{'id': 1, 'title': 'Test Project', 'created_at': '2026-08-20 00:00:00', 'deadline': '2026-08-30 00:00:00', 'total_phases': 2}]
            mock_phases.return_value = [{'phase_number': 1, 'title': 'Phase 1', 'status': 'PENDING', 'target_deadline': '2026-08-25 00:00:00'}]
            mock_integrity.return_value = app.integrity.IntegrityStatus.OK
            
            presence_obj = MagicMock()
            presence_obj.detected = True
            presence_obj.is_active = True
            presence_obj.idle_seconds = 0.0
            mock_presence.return_value = presence_obj
            mock_dispatch.return_value = {'notification_sent': True, 'audio_played': False}

            monitor.run()

            assert app.i18n.CURRENT_LANG == lang
            assert mock_dispatch.called
            call_kwargs = mock_dispatch.call_args.kwargs
            assert 'title' in call_kwargs
            assert 'body' in call_kwargs

