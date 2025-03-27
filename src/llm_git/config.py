import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def load_yaml_config(file_path):
    """Load a YAML config file if it exists, otherwise return empty dict."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


# Repo config will be loaded on demand
def _get_repo_config_file() -> Optional[str]:
    """Find the repo config file by traversing up from current directory."""
    current_path = Path.cwd()
    while current_path != current_path.parent:
        git_dir = current_path / ".git"
        if git_dir.exists() and git_dir.is_dir():
            config_path = current_path / ".llm-git.yaml"
            return str(config_path)
        current_path = current_path.parent
    return None


def _get_repo_config():
    """Get repository-specific configuration."""
    repo_config_file = _get_repo_config_file()
    if repo_config_file:
        return load_yaml_config(repo_config_file)
    return {}


# Get the directory of the current file for global config
_current_dir = os.path.dirname(os.path.abspath(__file__))
_global_config_file = os.path.join(_current_dir, "config.yaml")

# User config in home directory
_user_config_file = os.path.expanduser("~/.config/llm-git/config.yaml")

# Load individual config files
global_config = load_yaml_config(_global_config_file)
user_config = load_yaml_config(_user_config_file)
repo_config = _get_repo_config()


def merged_config() -> Dict[str, Any]:
    """
    Get a merged configuration from global, user, and repo configs.

    The merge is performed with the following precedence (highest to lowest):
    1. Repository config
    2. User config
    3. Global config

    Returns:
        Dict[str, Any]: Merged configuration dictionary
    """
    # Start with global config
    result = global_config.copy()

    # Update with user config
    result.update(user_config)

    # Update with repo config
    result.update(repo_config)

    return result
