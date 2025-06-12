# ABOUTME: Configuration loader module
# ABOUTME: Loads and saves YAML configuration with sensible defaults

import yaml
from dataclasses import dataclass
import os
import tempfile
import shutil


@dataclass
class Config:
    """Configuration data class with default values."""

    monitored_directory: str = "./incoming"
    storage_path: str = "./data/audio"
    whisper_model: str = "base.en"
    sample_rate: int = 16000
    max_concurrent_transcriptions: int = 2
    upload_temp_path: str = "./data/uploads"
    fts_enabled: bool = True
    items_per_page: int = 20
    default_language: str = "auto"


def get_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration from YAML file with defaults for missing keys.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Config object with loaded or default values
    """
    config = Config()

    try:
        with open(config_path, "r") as f:
            yaml_data = yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        # Use all defaults if file missing or invalid
        return config

    # Update config with values from YAML, using defaults for missing/invalid types
    if isinstance(yaml_data.get("monitored_directory"), str):
        config.monitored_directory = yaml_data["monitored_directory"]

    if isinstance(yaml_data.get("storage_path"), str):
        config.storage_path = yaml_data["storage_path"]

    if isinstance(yaml_data.get("whisper_model"), str):
        config.whisper_model = yaml_data["whisper_model"]

    if isinstance(yaml_data.get("sample_rate"), int):
        config.sample_rate = yaml_data["sample_rate"]

    if isinstance(yaml_data.get("max_concurrent_transcriptions"), int):
        config.max_concurrent_transcriptions = yaml_data[
            "max_concurrent_transcriptions"
        ]

    if isinstance(yaml_data.get("upload_temp_path"), str):
        config.upload_temp_path = yaml_data["upload_temp_path"]

    if isinstance(yaml_data.get("fts_enabled"), bool):
        config.fts_enabled = yaml_data["fts_enabled"]

    if isinstance(yaml_data.get("items_per_page"), int):
        config.items_per_page = yaml_data["items_per_page"]

    if isinstance(yaml_data.get("default_language"), str):
        config.default_language = yaml_data["default_language"]

    return config


def save_config(changes: dict, config_path: str = "config.yaml") -> Config:
    """
    Save configuration changes to YAML file.

    Args:
        changes: Dictionary of configuration changes
        config_path: Path to the YAML configuration file

    Returns:
        Updated Config object

    Raises:
        Exception: If saving fails
    """
    # Load existing config or start with defaults
    try:
        with open(config_path, "r") as f:
            existing_data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        existing_data = {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}")

    # Merge changes
    updated_data = {**existing_data, **changes}

    # Validate changes
    for key in changes:
        if key not in Config.__annotations__:
            raise ValueError(f"Invalid config key: {key}")

    # Write updated config atomically
    try:
        # Write to temp file first
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            yaml.dump(updated_data, tmp_file, sort_keys=False)
            tmp_path = tmp_file.name

        # Replace original file
        shutil.move(tmp_path, config_path)
    except Exception as e:
        # Clean up temp file if error occurs
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise Exception(f"Failed to save config: {str(e)}")

    # Return updated config
    return get_config(config_path)
