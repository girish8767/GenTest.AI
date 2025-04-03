from .base import AIProvider
import requests
from typing import List, Dict, Any
import re

class LocalAIProvider(AIProvider):
    def __init__(self, host: str = "http://localhost:8080"):
        self.host = host

    def generate_completion(self, prompt: str) -> str:
        response = requests.post(
            f"{self.host}/v1/completions",
            json={
                "prompt": prompt,
                "max_tokens": 1000
            }
        )
        return response.json()["choices"][0]["text"]


class LocalAIProvider:
    def parse_curl_command(self, curl_command: str) -> Dict[str, Any]:
        """Parse curl command to extract API details"""
        method_match = re.search(r'-X\s+(\w+)', curl_command) or re.search(r'--request\s+(\w+)', curl_command)
        url_match = re.search(r'https?://[^\s]+', curl_command)
        headers = dict(re.findall(r'-H\s*[\'"]([^:]+):\s*([^\'"]+)[\'"]', curl_command))
        data_match = re.search(r'--data\s*[\'"](.+?)[\'"]', curl_command)
        
        endpoint = url_match.group(0).split('jioconnect.com')[-1] if url_match else ''
        
        return {
            'method': method_match.group(1) if method_match else 'GET',
            'endpoint': endpoint,
            'headers': headers,
            'data': data_match.group(1) if data_match else None
        }

    def generate_test_scenarios(self, curl_command: str) -> List[Dict[str, Any]]:
        api_details = self.parse_curl_command(curl_command)
        
        # Base test scenario from curl
        base_scenario = {
            'description': f'Valid {api_details["method"]} Request',
            'test_type': 'positive',
            'method': api_details['method'],
            'endpoint': api_details['endpoint'],
            'headers': api_details['headers'],
            'expected_status_code': 200,
            'expected_schema': {
                'status': bool,
                'code': int,
                'message': str,
                'data': list
            }
        }
        
        # Generate variations
        scenarios = [
            base_scenario,
            self._generate_missing_headers_scenario(base_scenario),
            self._generate_invalid_signature_scenario(base_scenario),
            self._generate_invalid_params_scenario(base_scenario)
        ]
        
        return scenarios

    def _generate_missing_headers_scenario(self, base_scenario: Dict) -> Dict:
        return {
            **base_scenario,
            'description': 'Missing Required Headers Test',
            'test_type': 'negative',
            'headers': {'x-merchant-id': base_scenario['headers'].get('x-merchant-id', '')},
            'expected_status_code': 400
        }

    def _generate_invalid_signature_scenario(self, base_scenario: Dict) -> Dict:
        headers = base_scenario['headers'].copy()
        headers['x-signature'] = 'INVALID_SIGNATURE'
        return {
            **base_scenario,
            'description': 'Invalid Signature Test',
            'test_type': 'security',
            'headers': headers,
            'expected_status_code': 401
        }

    def _generate_invalid_params_scenario(self, base_scenario: Dict) -> Dict:
        return {
            **base_scenario,
            'description': 'Invalid Parameters Test',
            'test_type': 'negative',
            'params': {'paymentMethod': 'INVALID_METHOD'},
            'expected_status_code': 400
        }