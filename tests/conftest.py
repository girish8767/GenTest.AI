import os
import sys
import pytest

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.utils.test_generator import TestGenerator
from src.utils.test_executor import TestExecutor
from src.utils.test_reporter import TestReporter
from src.utils.html_reporter import HTMLReporter

@pytest.fixture
def test_generator():
    return TestGenerator()

@pytest.fixture
def test_executor():
    return TestExecutor(base_url="https://rtss-sit.jioconnect.com")

@pytest.fixture
def test_reporter():
    return TestReporter()

@pytest.fixture
def html_reporter():
    return HTMLReporter()