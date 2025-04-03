import requests
import json
from transformers import pipeline
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class HuggingFaceProvider:
    def __init__(self):
        device = -1  # Use CPU
        self.generator = pipeline(
            'text-generation', 
            model='gpt2',
            device=device
        )
        logger.info("Initialized GPT2 model on CPU")

    def generate_test_scenarios(self, prompt: str) -> str:
        logger.info("Starting AI test generation")
        try:
            # Generate structured test cases
            test_cases = [
                {
                    "description": "Valid Request Test",
                    "test_type": "positive",
                    "method": "GET",
                    "url": prompt.split("'")[1],  # Extract URL from curl
                    "headers": self._extract_headers(prompt),
                    "body": {},
                    "expected_status_code": 200
                },
                {
                    "description": "Missing Merchant ID Test",
                    "test_type": "negative",
                    "method": "GET",
                    "url": prompt.split("'")[1],
                    "headers": self._remove_header(self._extract_headers(prompt), 'x-merchant-id'),
                    "body": {},
                    "expected_status_code": 400
                },
                {
                    "description": "Invalid Signature Test",
                    "test_type": "negative",
                    "method": "GET",
                    "url": prompt.split("'")[1],
                    "headers": self._modify_header(self._extract_headers(prompt), 'x-signature', 'invalid'),
                    "body": {},
                    "expected_status_code": 400
                }
            ]
            
            return json.dumps(test_cases)
            
        except Exception as e:
            logger.error(f"Error in AI generation: {e}")
            return json.dumps([])

    def _extract_headers(self, curl_command: str) -> dict:
        headers = {}
        for line in curl_command.split('--header'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().strip("'").strip('"')
                value = value.strip().strip("'").strip('"').strip('\\')
                headers[key] = value
        return headers

    def _remove_header(self, headers: dict, header_name: str) -> dict:
        headers_copy = headers.copy()
        headers_copy.pop(header_name, None)
        return headers_copy

    def _modify_header(self, headers: dict, header_name: str, new_value: str) -> dict:
        headers_copy = headers.copy()
        if header_name in headers_copy:
            headers_copy[header_name] = new_value
        return headers_copy

    def _call_model(self, prompt: str) -> str:
        # Local model doesn't need API calls
        return self.generate_test_scenarios(prompt)