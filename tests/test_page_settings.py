from fastapi.testclient import TestClient
import yaml
from audio_manager.config import get_config
from audio_manager.db import init_db
from audio_manager.app import create_app

def test_settings_page_selects_defaults(tmp_path):
    # Prepare a temp config with default_language
    cfg_path = tmp_path / "config.yaml"
    cfg_data = {
        "monitored_directory": "./incoming",
        "storage_path": "./data/audio",
        "whisper_model": "small",
        "sample_rate": 16000,
        "max_concurrent_transcriptions": 2,
        "default_language": "fr-CA",
    }
    cfg_path.write_text(yaml.safe_dump(cfg_data))
    config = get_config(str(cfg_path))

    # Initialize an empty database
    db_path = str(tmp_path / "metadata.db")
    init_db(db_path)

    app = create_app(config, db_path)
    client = TestClient(app)

    response = client.get("/settings")
    assert response.status_code == 200
    html = response.text

    assert '<form id="settings-form">' in html
    assert '<select id="default-model"' in html
    assert '<option value="small" selected="selected">' in html
    assert '<select id="default-language"' in html
    assert '<option value="fr-CA" selected="selected">' in html
