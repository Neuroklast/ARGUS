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

from main import load_config


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------
class TestLoadConfig:
    """Unit tests for the YAML config loader."""

    def test_load_existing_config(self, tmp_path):
        """A valid YAML file should be parsed into a dict."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("ascom:\n  telescope_prog_id: TestScope\n")
        result = load_config(str(cfg_file))
        assert result == {"ascom": {"telescope_prog_id": "TestScope"}}

    def test_missing_config_returns_empty_dict(self, tmp_path):
        """A non-existent path should return an empty dict."""
        result = load_config(str(tmp_path / "does_not_exist.yaml"))
        assert result == {}

    def test_invalid_yaml_returns_empty_dict(self, tmp_path):
        """Malformed YAML should return an empty dict."""
        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text(":::\n  - ][")
        result = load_config(str(cfg_file))
        assert result == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        """An empty YAML file should return an empty dict."""
        cfg_file = tmp_path / "empty.yaml"
        cfg_file.write_text("")
        result = load_config(str(cfg_file))
        assert result == {}

    def test_default_config_loads(self):
        """The repo config.yaml should load without error."""
        result = load_config()
        assert isinstance(result, dict)
        assert "ascom" in result
