# ABOUTME: Tests for config.py module
# ABOUTME: Verifies YAML config loading with defaults and validation

import yaml
from mnemovox.config import get_config


def test_config_loads_from_yaml(tmp_path):
    """Test that config loads properly from YAML file."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "monitored_directory": "/custom/monitored",
        "storage_path": "/custom/storage",
        "whisper_model": "small.en",
        "sample_rate": 22050,
        "max_concurrent_transcriptions": 4,
        "upload_temp_path": "/custom/uploads",
        "fts_enabled": True,
        "items_per_page": 25,
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = get_config(str(config_file))

    assert config.monitored_directory == "/custom/monitored"
    assert config.storage_path == "/custom/storage"
    assert config.whisper_model == "small.en"
    assert config.sample_rate == 22050
    assert config.max_concurrent_transcriptions == 4
    assert config.upload_temp_path == "/custom/uploads"
    assert config.fts_enabled is True
    assert config.items_per_page == 25


def test_config_uses_defaults_for_missing_keys(tmp_path):
    """Test that missing keys use default values."""
    config_file = tmp_path / "config.yaml"
    config_data = {"monitored_directory": "/custom/monitored"}

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = get_config(str(config_file))

    assert config.monitored_directory == "/custom/monitored"
    assert config.storage_path == "./data/audio"  # default
    assert config.whisper_model == "base.en"  # default
    assert config.sample_rate == 16000  # default
    assert config.max_concurrent_transcriptions == 2  # default
    assert config.upload_temp_path == "./data/uploads"  # default
    assert config.fts_enabled is True  # default
    assert config.items_per_page == 20  # default


def test_config_handles_bad_types(tmp_path):
    """Test that bad types are handled gracefully with defaults."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "monitored_directory": "/custom/monitored",
        "sample_rate": "not_a_number",  # bad type
        "max_concurrent_transcriptions": "also_not_a_number",  # bad type
        "upload_temp_path": 123,  # bad type - should be string
        "fts_enabled": "not_a_bool",  # bad type - should be bool
        "items_per_page": "not_a_number",  # bad type - should be int
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = get_config(str(config_file))

    assert config.monitored_directory == "/custom/monitored"
    assert config.sample_rate == 16000  # default due to bad type
    assert config.max_concurrent_transcriptions == 2  # default due to bad type
    assert config.upload_temp_path == "./data/uploads"  # default due to bad type
    assert config.fts_enabled is True  # default due to bad type
    assert config.items_per_page == 20  # default due to bad type


def test_config_handles_missing_file():
    """Test that missing config file uses all defaults."""
    config = get_config("nonexistent_file.yaml")

    assert config.monitored_directory == "./incoming"
    assert config.storage_path == "./data/audio"
    assert config.whisper_model == "base.en"
    assert config.sample_rate == 16000
    assert config.max_concurrent_transcriptions == 2
    assert config.upload_temp_path == "./data/uploads"
    assert config.fts_enabled is True
    assert config.items_per_page == 20


def test_config_overrides_correctly(tmp_path):
    """Test that partial overrides work correctly."""
    config_file = tmp_path / "config.yaml"
    config_data = {"whisper_model": "large-v2", "max_concurrent_transcriptions": 1}

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = get_config(str(config_file))

    # Overridden values
    assert config.whisper_model == "large-v2"
    assert config.max_concurrent_transcriptions == 1

    # Default values for missing keys
    assert config.monitored_directory == "./incoming"
    assert config.storage_path == "./data/audio"
    assert config.sample_rate == 16000
    assert config.upload_temp_path == "./data/uploads"
    assert config.fts_enabled is True
    assert config.items_per_page == 20


def test_config_partial_new_field_overrides(tmp_path):
    """Test that partial overrides work correctly for new fields."""
    config_file = tmp_path / "config.yaml"
    config_data = {"fts_enabled": False, "items_per_page": 50}

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = get_config(str(config_file))

    # Overridden values
    assert config.fts_enabled is False
    assert config.items_per_page == 50

    # Default value for missing new field
    assert config.upload_temp_path == "./data/uploads"

    # Default values for missing original fields
    assert config.monitored_directory == "./incoming"
    assert config.storage_path == "./data/audio"
    assert config.whisper_model == "base.en"
    assert config.sample_rate == 16000
    assert config.max_concurrent_transcriptions == 2
