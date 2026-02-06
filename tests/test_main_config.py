"""Tests for config loading and ArgusController mode management.

These tests do NOT require a display – they exercise pure-logic
functions from ``src/main.py``.
"""

import os
import sys
from pathlib import Path

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import load_config, DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------
class TestLoadConfig:
    """Unit tests for the YAML config loader."""

    def test_load_existing_config(self, tmp_path):
        """A valid YAML file should be parsed and merged with defaults."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("ascom:\n  telescope_prog_id: TestScope\n")
        result = load_config(str(cfg_file))
        assert result["ascom"]["telescope_prog_id"] == "TestScope"
        # Missing keys should be filled from defaults
        assert "hardware" in result

    def test_missing_config_returns_defaults(self, tmp_path):
        """A non-existent path should return DEFAULT_CONFIG."""
        result = load_config(str(tmp_path / "does_not_exist.yaml"))
        assert result == DEFAULT_CONFIG

    def test_invalid_yaml_returns_defaults(self, tmp_path):
        """Malformed YAML should return DEFAULT_CONFIG."""
        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text(":::\n  - ][")
        result = load_config(str(cfg_file))
        assert result == DEFAULT_CONFIG

    def test_empty_file_returns_defaults(self, tmp_path):
        """An empty YAML file should return DEFAULT_CONFIG."""
        cfg_file = tmp_path / "empty.yaml"
        cfg_file.write_text("")
        result = load_config(str(cfg_file))
        assert result == DEFAULT_CONFIG

    def test_default_config_loads(self):
        """The repo config.yaml should load without error."""
        result = load_config()
        assert isinstance(result, dict)
        assert "ascom" in result
