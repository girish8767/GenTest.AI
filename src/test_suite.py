from typing import List, Dict, Any
import json
import os
from datetime import datetime
from .test_generator import TestGenerator
from .test_executor import TestExecutor
from .api_parser import APIParser
from config.config import settings

class TestSuite:
    def __init__(self, name: str):
        self.name = name
        self.generator = TestGenerator()
        self.executor = TestExecutor(base_url=settings.BASE_URL)
        self.api_specs = {}

    def load_api_spec(self, spec_path: str):
        parser = APIParser()
        self.api_specs = parser.parse_openapi(spec_path)

    def run_tests(self):
        all_results = []
        for spec_key, spec in self.api_specs.items():
            test_cases = self.generator.generate_test_cases(spec)
            results = self.executor.execute_parallel(test_cases)
            all_results.extend(results)
        return all_results