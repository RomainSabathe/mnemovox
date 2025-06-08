# ABOUTME: Configuration loader module
# ABOUTME: Loads YAML configuration with sensible defaults

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass
class Config:
    """Configuration data class with default values."""
    monitored_directory: str = "./incoming"
    storage_path: str = "./data/audio"
    whisper_model: str = "base.en"
    sample_rate: int = 16000
    max_concurrent_transcriptions: int = 2


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
        with open(config_path, 'r') as f:
            yaml_data = yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        # Use all defaults if file missing or invalid
        return config
    
    # Update config with values from YAML, using defaults for missing/invalid types
    if isinstance(yaml_data.get('monitored_directory'), str):
        config.monitored_directory = yaml_data['monitored_directory']
    
    if isinstance(yaml_data.get('storage_path'), str):
        config.storage_path = yaml_data['storage_path']
    
    if isinstance(yaml_data.get('whisper_model'), str):
        config.whisper_model = yaml_data['whisper_model']
    
    if isinstance(yaml_data.get('sample_rate'), int):
        config.sample_rate = yaml_data['sample_rate']
    
    if isinstance(yaml_data.get('max_concurrent_transcriptions'), int):
        config.max_concurrent_transcriptions = yaml_data['max_concurrent_transcriptions']
    
    return config