# ABOUTME: Tests for configuration saving
import pytest
from src.audio_manager.config import get_config, save_config
import os
import yaml
import tempfile


def test_save_config_updates_values():
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        tmp_file.write("monitored_directory: /test/dir\n")
        tmp_file.write("whisper_model: base.en\n")
        tmp_file.write("default_language: auto\n")
        tmp_path = tmp_file.name

    # Load initial config
    config = get_config(tmp_path)
    assert config.monitored_directory == "/test/dir"
    assert config.whisper_model == "base.en"
    assert config.default_language == "auto"

    # Save changes
    changes = {"whisper_model": "large-v3-turbo", "default_language": "fr-CA"}
    updated_config = save_config(changes, tmp_path)

    # Verify in-memory config updated
    assert updated_config.whisper_model == "large-v3-turbo"
    assert updated_config.default_language == "fr-CA"

    # Verify file contents
    with open(tmp_path, "r") as f:
        data = yaml.safe_load(f)
        assert data["whisper_model"] == "large-v3-turbo"
        assert data["default_language"] == "fr-CA"
        assert data["monitored_directory"] == "/test/dir"  # unchanged

    # Clean up
    os.unlink(tmp_path)


def test_save_config_creates_new_file():
    # Use a temp file that doesn't exist
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
    os.unlink(tmp_path)

    # Should create new file
    changes = {"whisper_model": "small", "default_language": "en"}
    config = save_config(changes, tmp_path)

    # Verify file exists and has changes
    assert os.path.exists(tmp_path)
    with open(tmp_path, "r") as f:
        data = yaml.safe_load(f)
        assert data["whisper_model"] == "small"
        assert data["default_language"] == "en"

    # Clean up
    os.unlink(tmp_path)


def test_save_config_invalid_key():
    with tempfile.NamedTemporaryFile(mode="w") as tmp_file:
        # Try to save invalid key
        with pytest.raises(ValueError, match="Invalid config key: invalid_key"):
            save_config({"invalid_key": "value"}, tmp_file.name)


def test_save_config_atomic_write():
    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        tmp_file.write("whisper_model: base.en\n")
        tmp_path = tmp_file.name

    # Save changes - should preserve existing values
    changes = {"default_language": "es"}
    save_config(changes, tmp_path)

    # Verify file has both values
    with open(tmp_path, "r") as f:
        data = yaml.safe_load(f)
        assert data["whisper_model"] == "base.en"
        assert data["default_language"] == "es"

    # Clean up
    os.unlink(tmp_path)


def test_save_config_handles_invalid_yaml():
    # Create invalid YAML file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        tmp_file.write("invalid: yaml: :\n")
        tmp_path = tmp_file.name

    # Should raise error when trying to save
    with pytest.raises(yaml.YAMLError, match=r"(?i)invalid|error"):
        save_config({"whisper_model": "small"}, tmp_path)

    # Clean up
    os.unlink(tmp_path)
