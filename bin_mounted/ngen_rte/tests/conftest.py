"""Pytest fixtures"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["NGEN_LOG_TO_RTE"] = "true"
