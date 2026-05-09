"""Shared pytest configuration and marker registration."""
import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "implementation_mirror: marks tests as implementation-mirror (not part of hard gate)",
    )
