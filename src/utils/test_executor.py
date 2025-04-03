import requests
import json
from urllib.parse import urlparse, parse_qs
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TestExecutor:
    def execute_test(self, method: str, url: str, headers: dict, body: dict, expected_status: int) -> Dict[str, Any]:
        """Execute a single test case"""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body
            )
            
            return {
                'status': 'success' if response.status_code == expected_status else 'failed',
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'response': response.json() if response.text else None,
                'request': {
                    'method': method,
                    'url': url,
                    'headers': headers,
                    'body': body
                }
            }
        except Exception as e:
            logger.error(f"Test execution error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'request': {
                    'method': method,
                    'url': url,
                    'headers': headers,
                    'body': body
                }
            }
    def execute_test(self, curl_command, test_type='positive', modifications=None):
        parsed = self.parse_curl_command(curl_command)
        
        # Start with original request data
        request_data = {
            'method': parsed['method'],
            'url': parsed['url'],
            'headers': parsed['headers'].copy(),
            'params': parsed['params'].copy()
        }
        
        # Add body if present in parsed data
        if 'body' in parsed:
            request_data['json'] = parsed['body']
        
        try:
            response = requests.request(
                method=request_data['method'],
                url=request_data['url'],
                headers=request_data['headers'],
                params=request_data['params'],
                json=request_data.get('json'),
                verify=False  # Allow self-signed certificates
            )
            
            # Update status check logic
            status = 'PASS'
            if test_type == 'positive' and response.status_code not in [200, 201]:
                status = 'FAIL'
            elif test_type == 'negative' and response.status_code in [200, 201]:
                status = 'FAIL'
            
            return {
                'expected_status_code': 200 if test_type == 'positive' else 400,
                'actual_status_code': response.status_code,
                'request': request_data,
                'response': response.json() if response.text else None,
                'status': status,
                'test_type': test_type
            }
        except Exception as e:
            logger.error(f"Test execution error: {str(e)}")
            return {
                'expected_status_code': 200 if test_type == 'positive' else 400,
                'actual_status_code': 500,
                'error': str(e),
                'request': request_data,
                'response': {'error': str(e)},
                'status': 'FAIL',
                'test_type': test_type
            }

    def parse_curl_command(self, curl_command):
        try:
            curl_command = curl_command.replace('\\\n', ' ').strip()
            
            # Parse headers
            headers = {}
            header_parts = curl_command.split('--header')
            for part in header_parts[1:]:
                try:
                    # Clean and parse header content
                    header_content = part.split('--')[0]  # Get content until next -- flag
                    header_content = header_content.strip().strip("'").strip('"')
                    if ':' in header_content:
                        key, value = header_content.split(':', 1)
                        # Clean header value properly
                        value = value.strip().rstrip('\\').strip()
                        headers[key.strip()] = value
                except:
                    continue
                
            # Method detection
            method = 'GET'  # default
            if '-X' in curl_command:
                method = curl_command.split('-X')[1].split()[0]  # explicit method
            elif '--data' in curl_command or '-d' in curl_command:
                method = 'POST'  # implicit POST when data present
                
            # Parse URL
            url_part = curl_command.split("'")[1] if "'" in curl_command else curl_command.split('"')[1]
            parsed_url = urlparse(url_part)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
            
            # Parse request body
            body = None
            if '--data' in curl_command or '-d' in curl_command:
                try:
                    data_part = curl_command.split('--data')[1] if '--data' in curl_command else curl_command.split('-d')[1]
                    body_content = data_part.strip().strip("'").strip('"')
                    body = json.loads(body_content)
                except:
                    pass
            
            request_data = {
                'method': method,
                'url': base_url,
                'headers': headers,
                'params': params
            }
            
            if body:
                request_data['body'] = body
                
            return request_data
        except Exception as e:
            logging.error(f"Failed to parse curl command: {str(e)}")
            raise ValueError(f"Failed to parse curl command: {str(e)}")

    def generate_test_cases(self, curl_command):
        parsed = self.parse_curl_command(curl_command)
        required_headers = {
            'x-merchant-id': parsed['headers'].get('x-merchant-id', ''),
            'x-business-flow': parsed['headers'].get('x-business-flow', ''),
            'x-transaction-time': parsed['headers'].get('x-transaction-time', ''),
            'x-signature': parsed['headers'].get('x-signature', '')
        }
        
        prompt = {
            "model": "mistral",
            "prompt": f"""Generate test cases for this API:
            Method: {parsed['method']}
            URL: {parsed['url']}
            Required Headers: {json.dumps(required_headers, indent=2)}
            Parameters: {json.dumps(parsed['params'], indent=2)}
    
            Return a JSON array of test cases in this exact format:
            [
                {{
                    "name": "Valid Request Test",
                    "type": "positive",
                    "modifications": null
                }},
                {{
                    "name": "Missing x-merchant-id Test",
                    "type": "negative",
                    "modifications": {{"remove_header": "x-merchant-id"}}
                }}
            ]"""
        }
        
        try:
            response = requests.post(
                self.local_ai_url,
                json=prompt,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                test_cases = json.loads(ai_response['response'])
                if isinstance(test_cases, list) and len(test_cases) > 0:
                    return test_cases
                
            return self._generate_basic_test_cases(parsed)
        except Exception as e:
            logging.error(f"AI test generation failed: {e}")
            return self._generate_basic_test_cases(parsed)

    def apply_modifications(self, request_data, modifications):
        modified = request_data.copy()
        
        if 'remove_header' in modifications:
            modified['headers'].pop(modifications['remove_header'], None)
            
        if 'modify_header' in modifications:
            header, value = modifications['modify_header']
            modified['headers'][header] = value
            
        if 'modify_param' in modifications:
            param, value = modifications['modify_param']
            modified['params'][param] = value
            
        return modified

    def __init__(self):
        self.local_ai_url = "http://localhost:11434/api/generate"
        self._check_ollama_health()

    def _check_ollama_health(self):
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code != 200:
                logging.warning("Ollama service is not responding properly")
        except Exception as e:
            logging.error(f"Failed to connect to Ollama: {str(e)}")
            logging.warning("Make sure Ollama is installed and running")
        self.model_name = "llama2"  # or your specific local model name

    def generate_test_cases(self, curl_command):
        parsed = self.parse_curl_command(curl_command)
        
        # Create AI prompt with actual headers
        prompt = {
            "model": "mistral",
            "prompt": f"""Create API test cases for this endpoint:
            Method: {parsed['method']}
            URL: {parsed['url']}
            Current Headers: {json.dumps(parsed['headers'], indent=2)}
            Parameters: {json.dumps(parsed['params'], indent=2)}
    
            Create test cases that:
            1. Use these exact headers for positive test
            2. Remove each header one by one for negative tests
            3. Test invalid values for each parameter
    
            Return only a JSON array in this format:
            [
                {{
                    "name": "Test Name",
                    "type": "positive/negative",
                    "modifications": {{
                        "remove_header": "header-name" or
                        "modify_header": ["header-name", "new-value"] or
                        "modify_param": ["param-name", "new-value"]
                    }}
                }}
            ]"""
        }
        
        try:
            response = requests.post(
                self.local_ai_url,
                json=prompt,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                # Extract JSON array from response
                response_text = ai_response['response']
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    test_cases = json.loads(response_text[start_idx:end_idx])
                    if isinstance(test_cases, list) and len(test_cases) > 0:
                        # Add original headers to each test case
                        for test in test_cases:
                            test['original_headers'] = parsed['headers']
                        return test_cases
        
            # Fallback to basic test cases if AI fails
            return self._generate_basic_test_cases(parsed)
            
        except Exception as e:
            logging.error(f"AI test generation failed: {e}")
            return self._generate_basic_test_cases(parsed)

    def _generate_basic_test_cases(self, parsed):
        """Generate basic test cases when AI fails"""
        test_cases = []
        
        # Base positive test
        test_cases.append({
            'name': 'Valid Request with All Headers',
            'type': 'positive',
            'modifications': None
        })
        
        # Required headers tests
        required_headers = ['x-merchant-id', 'x-business-flow', 'x-transaction-time', 'x-signature']
        for header in required_headers:
            test_cases.append({
                'name': f'Missing {header} Test',
                'type': 'negative',
                'modifications': {'remove_header': header}
            })
        
        # Parameter tests
        for param in parsed['params']:
            test_cases.append({
                'name': f'Invalid {param} Test',
                'type': 'negative',
                'modifications': {'modify_param': (param, 'INVALID_VALUE')}
            })
        
        return test_cases

    def run_all_tests(self, curl_command):
        test_cases = self.generate_test_cases(curl_command)
        results = []
        
        for test_case in test_cases:
            # Execute each test case
            result = self.execute_test(
                curl_command,
                test_case['type'],
                test_case.get('modifications')
            )
            
            # Include test case details in result
            results.append({
                'test_name': test_case['name'],
                'test_type': test_case['type'],
                'modifications': test_case.get('modifications'),
                'expected_status_code': result['expected_status_code'],
                'actual_status_code': result['actual_status_code'],
                'request': {
                    'method': result['request']['method'],
                    'url': result['request']['url'],
                    'headers': result['request']['headers'],
                    'params': result['request']['params']
                },
                'response': result.get('response', {}),
                'status': 'PASS' if result['actual_status_code'] == result['expected_status_code'] else 'FAIL',
                'error': result.get('error')
            })
            
            # Log each test execution
            logging.info(f"Test: {test_case['name']} - Status: {results[-1]['status']}")
        
        return results

    def _generate_basic_test_cases(self, parsed):
        test_cases = []
        
        # Ensure we have the original headers
        original_headers = parsed['headers'].copy()
        
        # Base positive test with all original headers
        test_cases.append({
            'name': 'Valid Request Test',
            'type': 'positive',
            'modifications': None,
            'original_headers': original_headers  # Store original headers
        })
        
        # Header validation tests
        for header in original_headers:
            test_cases.append({
                'name': f'Missing {header} Test',
                'type': 'negative',
                'modifications': {
                    'remove_header': header
                },
                'original_headers': original_headers
            })
            
            # Invalid header value test
            test_cases.append({
                'name': f'Invalid {header} Value Test',
                'type': 'negative',
                'modifications': {
                    'modify_header': [header, 'invalid_value']
                },
                'original_headers': original_headers
            })
        
        # Parameter validation
        for param, value in parsed['params'].items():
            test_cases.append({
                'name': f'Invalid {param} Test',
                'type': 'negative',
                'modifications': {
                    'modify_param': [param, 'INVALID_VALUE']
                },
                'original_headers': original_headers
            })
        
        return test_cases