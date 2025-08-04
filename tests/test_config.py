"""
Tests for the configuration module.
"""
import importlib.metadata
import pytest
from stoppls.config import get_version


def test_get_version():
    """
    Test that get_version returns the expected version.
    """
    # Since the package is installed in development mode,
    # we expect the actual version from setup.py
    expected_version = "0.1.0"
    assert get_version() == expected_version


def test_pytest_setup():
    """
    Simple test to verify pytest is working correctly.
    """
    assert True