# ABOUTME: Tests for Phase 2 config extensions
# ABOUTME: Verifies loading of upload_temp_path, fts_enabled, items_per_page fields

import pytest
import yaml
from pathlib import Path
from src.audio_manager.config import get_config


def test_config_loads_phase2_fields_from_yaml(tmp_path):
    """Test that Phase 2 config fields load properly from YAML file."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "monitored_directory": "/custom/monitored",
        "storage_path": "/custom/storage", 
        "whisper_model": "small.en",
        "sample_rate": 22050,
        "max_concurrent_transcriptions": 4,
        "upload_temp_path": "/custom/uploads",
        "fts_enabled": True,
        "items_per_page": 25
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    
    # Verify Phase 1 fields still work
    assert config.monitored_directory == "/custom/monitored"
    assert config.storage_path == "/custom/storage"
    assert config.whisper_model == "small.en"
    assert config.sample_rate == 22050
    assert config.max_concurrent_transcriptions == 4
    
    # Verify Phase 2 fields
    assert config.upload_temp_path == "/custom/uploads"
    assert config.fts_enabled == True
    assert config.items_per_page == 25


def test_config_uses_defaults_for_missing_phase2_keys(tmp_path):
    """Test that missing Phase 2 keys use default values."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "monitored_directory": "/custom/monitored"
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    
    # Verify Phase 1 field
    assert config.monitored_directory == "/custom/monitored"
    
    # Verify Phase 2 defaults
    assert config.upload_temp_path == "./data/uploads"
    assert config.fts_enabled == True
    assert config.items_per_page == 20


def test_config_handles_bad_types_for_phase2_fields(tmp_path):
    """Test that bad types for Phase 2 fields are handled gracefully with defaults."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "monitored_directory": "/custom/monitored",
        "upload_temp_path": 123,  # bad type - should be string
        "fts_enabled": "not_a_bool",  # bad type - should be bool
        "items_per_page": "not_a_number"  # bad type - should be int
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    
    assert config.monitored_directory == "/custom/monitored"
    # Should use defaults due to bad types
    assert config.upload_temp_path == "./data/uploads"
    assert config.fts_enabled == True
    assert config.items_per_page == 20


def test_config_missing_file_uses_all_phase2_defaults():
    """Test that missing config file uses all Phase 2 defaults."""
    config = get_config("nonexistent_file.yaml")
    
    # Phase 1 defaults
    assert config.monitored_directory == "./incoming"
    assert config.storage_path == "./data/audio"
    assert config.whisper_model == "base.en"
    assert config.sample_rate == 16000
    assert config.max_concurrent_transcriptions == 2
    
    # Phase 2 defaults
    assert config.upload_temp_path == "./data/uploads"
    assert config.fts_enabled == True
    assert config.items_per_page == 20


def test_config_partial_phase2_overrides(tmp_path):
    """Test that partial Phase 2 overrides work correctly."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "fts_enabled": False,
        "items_per_page": 50
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    
    # Overridden Phase 2 values
    assert config.fts_enabled == False
    assert config.items_per_page == 50
    
    # Default Phase 2 value for missing key
    assert config.upload_temp_path == "./data/uploads"
    
    # Default Phase 1 values for missing keys
    assert config.monitored_directory == "./incoming"
    assert config.storage_path == "./data/audio"
    assert config.whisper_model == "base.en"
    assert config.sample_rate == 16000
    assert config.max_concurrent_transcriptions == 2