from utils.ai_providers.base import AIProvider
from utils.ai_providers.huggingface_provider import HuggingFaceProvider
from pydantic import BaseModel, Field
import logging
from typing import  List, Dict, Any, Union, Tuple
import re
import json
import subprocess
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

class TestGenerator(BaseModel):
    ai: HuggingFaceProvider = Field(default_factory=HuggingFaceProvider)
    
    class Config:
        arbitrary_types_allowed = True

    def parse_curl_command(self, curl_command: str) -> Dict[str, Any]:
        """Parse curl command into components"""
        logger.info("Parsing curl command")
        try:
            # Clean up curl command
            curl_command = curl_command.replace('\\\n', ' ').strip()
            
            # Log the curl command for debugging
            logger.info(f"Parsing curl command: {curl_command}")
            
            # Extract URL - try multiple patterns to be more robust
            url = None
            
            # Pattern 1: With --location flag
            url_match = re.search(r"--location\s+'(https?://[^']+)'", curl_command)
            
            # Pattern 2: Standard curl URL pattern with quotes
            if not url_match:
                url_match = re.search(r"curl\s+['\"]?(https?://[^'\"]+)['\"]?", curl_command)
            
            # Pattern 3: URL without quotes
            if not url_match:
                url_match = re.search(r"curl\s+(https?://\S+)(\s|$)", curl_command)
            
            # Pattern 4: URL with --url or -L flag
            if not url_match:
                url_match = re.search(r"(?:--url|-L)\s+['\"]?(https?://[^'\"]+)['\"]?", curl_command)
                
            # Pattern 5: Last resort - find any URL in the command
            if not url_match:
                url_match = re.search(r"(https?://[^\s'\"]+)", curl_command)
                
            if url_match:
                url = url_match.group(1)
                # Clean up URL if it has trailing quotes or special chars
                url = url.rstrip("'\"")
                logger.info(f"Found URL: {url}")
            else:
                logger.error(f"URL not found in curl command: {curl_command}")
                raise ValueError("URL not found in curl command")
            
            # Parse URL for endpoint and params
            parsed_url = urlparse(url)
            endpoint = parsed_url.path
            
            # Extract query parameters
            params = parse_qs(parsed_url.query)
            
            # Extract method
            method_match = re.search(r'-X\s+([A-Z]+)', curl_command)
            method = method_match.group(1) if method_match else 'GET'
            self.generate_test_cases(curl_command, return_raw=True)
            # Extract headers - try multiple patterns
            headers = {}
            # With --header
            header_matches = re.findall(r"--header\s+'([^:]+):\s*([^']+)'", curl_command)
            
            # With -H and quotes
            if not header_matches:
                header_matches = re.findall(r"-H\s+['\"]([^:]+):\s*([^'\"]+)['\"]", curl_command)
            
            # Without quotes
            if not header_matches:
                header_matches = re.findall(r"-H\s+([^:]+):\s*([^\s]+)", curl_command)
                
            for key, value in header_matches:
                headers[key.strip()] = value.strip()
            
            # Extract body - try multiple patterns
            body = None
            # JSON body with quotes
            body_match = re.search(r"-d\s+['\"]({.+?})['\"]", curl_command, re.DOTALL)
            
            # JSON body without quotes
            if not body_match:
                body_match = re.search(r"-d\s+({.+?})\s", curl_command, re.DOTALL)
                
            # With --data instead of -d
            if not body_match:
                body_match = re.search(r"--data\s+['\"]({.+?})['\"]", curl_command, re.DOTALL)
            
            if body_match:
                try:
                    body_str = body_match.group(1)
                    logger.info(f"Found body: {body_str}")
                    body = json.loads(body_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Could not parse body as JSON: {e}")
                    body = body_match.group(1)
            
            return {
                'method': method,
                'url': url,
                'endpoint': endpoint,
                'headers': headers,
                'body': body,
                'params': {k: v[0] for k, v in params.items()} if params else {}
            }
            
        except Exception as e:
            logger.error(f"Error parsing curl command: {e}")
            raise ValueError(f"Failed to parse curl command: {e}")

    def generate_test_cases(self, curl_command: str, return_raw: bool = False, parsed_curl=None) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], str]]:
        """Generate test cases for a curl command"""
        try:
            logger.info(f"Generating test cases for curl command: {curl_command[:50]}...")
            
            # Generate the prompt for the AI, using parsed_curl for optimization if available
            prompt = self._generate_optimized_prompt(curl_command, parsed_curl) if parsed_curl else self._generate_prompt(curl_command)
            
            # Get the AI response
            ai_response = self._generate_ai_test_scenarios(prompt)
            
            # Parse the AI response to extract test cases
            test_cases = self._parse_ai_response(ai_response, curl_command)
            logger.info(f"Generated {len(test_cases)} test cases")
            
            if return_raw:
                return test_cases, ai_response
            return test_cases
        except Exception as e:
            logger.error(f"Error generating test cases: {str(e)}", exc_info=True)
            if return_raw:
                return [], str(e)
            return []

    def _generate_optimized_prompt(self, curl_command: str, parsed_curl: dict) -> str:
        """
        Generate an optimized prompt that systematically creates test cases for:
        1. Each header (missing and invalid)
        2. Each request parameter (missing and invalid)
        3. Each query parameter (missing and invalid)
        """
        # Extract key information from parsed_curl
        url = parsed_curl.get('url', '')
        method = parsed_curl.get('method', 'GET')
        headers = parsed_curl.get('headers', {})
        body = parsed_curl.get('body', {})
        
        # Extract query parameters from URL
        query_params = {}
        if '?' in url:
            base_url, query_string = url.split('?', 1)
            for param_pair in query_string.split('&'):
                if '=' in param_pair:
                    key, value = param_pair.split('=', 1)
                    query_params[key] = value
        
        # Create a structured test plan
        test_plan = []
        
        # 1. Add a baseline positive test
        test_plan.append({
            "description": "Baseline positive test with all valid parameters",
            "test_type": "positive",
            "expected_status_code": 200,
            "curl_command": curl_command
        })
        
        # 2. Generate test cases for each header
        for header_name in headers.keys():
            # Missing header test
            test_plan.append({
                "description": f"Missing required header: {header_name}",
                "test_type": "negative",
                "expected_status_code": 400,
                "curl_command": f"Remove the {header_name} header"
            })
            
            # Invalid header test
            test_plan.append({
                "description": f"Invalid value for header: {header_name}",
                "test_type": "negative",
                "expected_status_code": 400,
                "curl_command": f"Set {header_name} to an invalid value"
            })
        
        # 3. Generate test cases for each body parameter (if body is present and is a dict)
        if isinstance(body, dict):
            for param_name in body.keys():
                # Missing parameter test
                test_plan.append({
                    "description": f"Missing required body parameter: {param_name}",
                    "test_type": "negative",
                    "expected_status_code": 400,
                    "curl_command": f"Remove the {param_name} parameter from the request body"
                })
                
                # Invalid parameter test
                test_plan.append({
                    "description": f"Invalid value for body parameter: {param_name}",
                    "test_type": "negative",
                    "expected_status_code": 400,
                    "curl_command": f"Set {param_name} to an invalid value"
                })
        
        # 4. Generate test cases for each query parameter
        for param_name in query_params.keys():
            # Missing parameter test
            test_plan.append({
                "description": f"Missing required query parameter: {param_name}",
                "test_type": "negative",
                "expected_status_code": 400,
                "curl_command": f"Remove the {param_name} query parameter"
            })
            
            # Invalid parameter test
            test_plan.append({
                "description": f"Invalid value for query parameter: {param_name}",
                "test_type": "negative",
                "expected_status_code": 400,
                "curl_command": f"Set {param_name} to an invalid value"
            })
        
        # Create the optimized prompt
        prompt = f"""
        You are an API testing expert. I will provide you with a curl command and a structured test plan.
        Your task is to implement the test plan by modifying the curl command for each test case.
        
        Original curl command:
        ```
        {curl_command}
        ```
        
        API Details:
        - Method: {method}
        - URL: {url}
        - Headers: {json.dumps(headers, indent=2)}
        - Body Parameters: {json.dumps(body, indent=2) if body else "None"}
        - Query Parameters: {json.dumps(query_params, indent=2) if query_params else "None"}
        
        Test Plan:
        {json.dumps(test_plan, indent=2)}
        
        For each test case in the test plan:
        1. Keep the description, test_type, and expected_status_code as they are
        2. Replace the curl_command with an actual modified curl command that implements the test case
        
        For example, if the test case says "Remove the Authorization header", modify the original curl command to remove that specific header.
        
        Return the completed test plan as a JSON array with the same structure, but with actual curl commands.
        Do not include any explanatory text, just return the JSON array.
        """
        return prompt

    def _generate_prompt(self, curl_command: str) -> str:
        """Generate a prompt for the AI to generate test cases"""
        prompt = f"""
        You are an API testing expert. I will provide you with a curl command, and I want you to generate comprehensive test cases for this API.
        
        Here is the curl command:
        ```
        {curl_command}
        ```
        
        # Please generate as many relevant test cases as possible to thoroughly test the API. Include:
        Please generate only 5 relevant test cases as possible to thoroughly test the API. Include:
        1. Positive test cases (valid inputs that should succeed)
        2. Negative test cases (invalid inputs that should fail)
        
        For each test case, provide:
        - Description of the test case
        - Test type (positive or negative)
        - Expected status code
        - Modified curl command for the test case
        
        Format your response as a JSON array of test case objects with the following structure:
        [
            {{
            "description": "Test case description",
            "test_type": "positive or negative",
            "expected_status_code": 200 or 400 or other appropriate code,
            "curl_command": "modified curl command in JSON format"
            }},
            ...
        ]
        
        Focus on testing:
        - Required parameters
        - Parameter validation
        - Edge cases
        - Authentication/authorization if applicable
        - Different HTTP methods if applicable

        Specifically include test cases for:
        1. Each header in the request:
           - Removing each required header one by one
           - Using invalid values for each header
           - Using malformed header formats
        
        2. If the request has a body:
           - Removing each required parameter one by one
           - Using invalid data types for parameters
           - Using boundary values (too long strings, negative numbers, etc.)
           - Using malformed JSON structure
           - Using empty body if body is required
        
        Return only the JSON array without any additional text.
        """
        return prompt

    def _generate_ai_test_scenarios(self, curl_command: str) -> str:
        """Generate test scenarios using Llama model"""
        try:
            logger.info("Preparing prompt for AI model")
            
            # Create a comprehensive prompt to generate test cases
            prompt = f"""
            You are an API testing expert. Given the following curl command, generate comprehensive test cases 
            including positive and negative scenarios. Generate as many relevant test cases as possible to thoroughly test the API.
            For each test case, provide:
            1. Description
            2. Test type (positive/negative)
            3. Expected status code
            4. Modified curl command for the test case
             
            Include test cases for:
            - Valid inputs
            - Invalid inputs
            - Missing required parameters 
            - Boundary values
            - Security testing (e.g., SQL injection, XSS)

            Specifically test:
            1. Headers:
               - Remove each header one by one to test if they are required
               - Use invalid values for authentication headers
               - Use malformed header formats
            
            2. Request body (if present):
               - Remove required fields one by one
               - Use invalid data types (strings instead of numbers, etc.)
               - Use boundary values (empty strings, very long strings, negative numbers)
               - Use malformed JSON
               - Test with empty body if body is required
            
            Curl command:
            {curl_command}
            
            Format your response as JSON with an array of test cases.
            """
            
            logger.info("Executing AI model with prompt")
            
            # First, let's check which models are available
            check_models_cmd = ["curl", "http://localhost:11434/api/tags"]
            logger.info("Checking available models")
            
            try:
                models_process = subprocess.Popen(
                    check_models_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                models_stdout, models_stderr = models_process.communicate(timeout=10)
                
                if models_process.returncode == 0:
                    models_data = json.loads(models_stdout.decode('utf-8'))
                    available_models = [model['name'] for model in models_data.get('models', [])]
                    logger.info(f"Available models: {available_models}")
                    
                    # Choose the first available model
                    model_to_use = available_models[0] if available_models else "mistral"
                else:
                    logger.warning(f"Failed to get available models: {models_stderr.decode('utf-8')}")
                    model_to_use = "mistral"  # Default to mistral as it's commonly available
            except Exception as e:
                logger.error(f"Error checking available models: {str(e)}")
                model_to_use = "mistral"  # Default to mistral as it's commonly available
            
            logger.info(f"Using model: {model_to_use}")
            
            # Increased timeout and added retry logic
            max_retries = 3
            timeout_seconds = 180  # Increased from 60 to 180 seconds
            
            for retry in range(max_retries):
                try:
                    logger.info(f"Attempt {retry + 1}/{max_retries} to call Ollama API")
                    
                    # Call AI model using Ollama
                    cmd = [
                        "curl", "-X", "POST", "http://localhost:11434/api/generate",
                        "-d", json.dumps({
                            "model": model_to_use,
                            "prompt": prompt,
                            "stream": False,
                            # Add parameters to control generation
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "max_tokens": 4000  # Request more tokens for comprehensive output
                        })
                    ]
                    
                    logger.info(f"Executing Ollama API call with model {model_to_use}")
                    print(f"Calling Ollama API with model {model_to_use} (attempt {retry + 1}/{max_retries})")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    print(f"Waiting for Ollama response (timeout: {timeout_seconds}s)...")
                    stdout, stderr = process.communicate(timeout=timeout_seconds)
                    
                    if stderr:
                        logger.warning(f"Stderr from Ollama model: {stderr.decode('utf-8')}")
                        print(f"Error from Ollama: {stderr.decode('utf-8')}")
                    
                    if stdout:
                        print(f"Received response from Ollama (first 100 chars): {stdout.decode('utf-8')[:100]}")
                        
                        try:
                            response_json = json.loads(stdout.decode('utf-8'))
                            ai_response = response_json.get('response', '')
                            logger.info(f"Received {len(ai_response)} characters from Ollama model")
                            
                            # Check if the response seems valid (contains test cases)
                            if '[' in ai_response and ']' in ai_response and len(ai_response) > 100:
                                return ai_response
                            else:
                                logger.warning("Response doesn't appear to contain valid test cases, retrying...")
                                if retry == max_retries - 1:
                                    # On last retry, return what we have
                                    return ai_response
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON from Ollama response: {e}")
                            if retry == max_retries - 1:
                                # On last retry, create a default test case
                                return json.dumps([{
                                    "description": "Default test case",
                                    "test_type": "positive",
                                    "expected_status_code": 200,
                                    "curl_command": curl_command
                                }])
                    else:
                        logger.error("No response received from Ollama API")
                        print("No response received from Ollama API")
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"Ollama API call timed out after {timeout_seconds} seconds on attempt {retry + 1}/{max_retries}")
                    print(f"Ollama API call timed out after {timeout_seconds} seconds")
                    
                    if retry == max_retries - 1:
                        # On last retry, create a default test case
                        return json.dumps([{
                            "description": "Default test case (timeout occurred)",
                            "test_type": "positive",
                            "expected_status_code": 200,
                            "curl_command": curl_command
                        }])
                
                # Wait before retrying
                if retry < max_retries - 1:
                    retry_wait = 5  # seconds
                    logger.info(f"Waiting {retry_wait} seconds before retry...")
                    print(f"Waiting {retry_wait} seconds before retry...")
                    import time
                    time.sleep(retry_wait)
            
            # If we get here, all retries failed
            return json.dumps([{
                "description": "Default test case (all retries failed)",
                "test_type": "positive",
                "expected_status_code": 200,
                "curl_command": curl_command
            }])
                
        except Exception as e:
            logger.error(f"Error calling Ollama model: {str(e)}", exc_info=True)
            print(f"Error calling Ollama model: {str(e)}")
            # Create a default test case as fallback
            return json.dumps([{
                "description": "Default test case (error occurred)",
                "test_type": "positive",
                "expected_status_code": 200,
                "curl_command": curl_command
            }])
    
    def _parse_ai_response(self, ai_response: str, curl_command: str) -> List[Dict[str, Any]]:
        """Parse the AI response to extract test cases"""
        try:
            logger.info("Parsing AI response")
            
            # Save the raw AI response to a file for debugging
            with open('/tmp/raw_ai_response.txt', 'w') as f:
                f.write(ai_response)
            logger.info("Saved raw AI response to /tmp/raw_ai_response.txt")
            
            # First, try to parse as JSON
            try:
                # Check if the response is a JSON array
                if ai_response.strip().startswith('[') and ai_response.strip().endswith(']'):
                    # Fix control characters before parsing
                    fixed_json = re.sub(r'[\x00-\x1F\x7F]', '', ai_response)
                    # Fix invalid escape sequences
                    fixed_json = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', fixed_json)
                    test_cases = json.loads(fixed_json)
                    logger.info(f"Successfully parsed JSON response with {len(test_cases)} test cases")
                    return test_cases
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse response as JSON: {e}")
            
            # Check if the response is from Ollama and contains a JSON wrapper
            if ai_response.startswith('{"model":'):
                try:
                    # Parse the Ollama response wrapper
                    ollama_response = json.loads(ai_response)
                    # Extract the actual response content
                    ai_response = ollama_response.get('response', '')
                    logger.info(f"Extracted response from Ollama wrapper: {ai_response[:100]}...")
                    
                    # Save the extracted response for debugging
                    with open('/tmp/extracted_ai_response.txt', 'w') as f:
                        f.write(ai_response)
                    
                    # Try to parse the extracted response as JSON
                    try:
                        if ai_response.strip().startswith('[') and ai_response.strip().endswith(']'):
                            test_cases = json.loads(ai_response)
                            logger.info(f"Successfully parsed JSON from Ollama response with {len(test_cases)} test cases")
                            
                            # Process each test case to ensure it has all required fields
                            for test_case in test_cases:
                                # Rename modified_curl_command to curl_command if needed
                                if 'modified_curl_command' in test_case and 'curl_command' not in test_case:
                                    test_case['curl_command'] = test_case.pop('modified_curl_command')
                            
                            return test_cases
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse extracted response as JSON: {e}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Ollama response wrapper: {e}")
            
            # If we couldn't parse as JSON, fall back to text parsing
            # Manual parsing approach - look for test case patterns
            test_cases = []
            
            # Try to find test case sections
            # First, try to split by test case markers
            test_case_markers = [
                r'Test Case \d+[:.]\s*',
                r'Test \d+[:.]\s*',
                r'\d+\.\s+Test Case[:.]\s*',
                r'\d+\.\s+'
            ]
            
            for marker in test_case_markers:
                sections = re.split(marker, ai_response)
                if len(sections) > 1:
                    # Remove the first section if it's just introductory text
                    if not re.search(r'description|test type|status code|curl', sections[0], re.IGNORECASE):
                        sections = sections[1:]
                    
                    logger.info(f"Split response into {len(sections)} sections using marker: {marker}")
                    
                    for i, section in enumerate(sections):
                        if not section.strip():
                            continue
                        
                        # Create a test case
                        test_case = {}
                        
                        # Extract description
                        desc_match = re.search(r'(?:Description|Title)[:.]\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
                        if desc_match:
                            test_case['description'] = desc_match.group(1).strip()
                        else:
                            # Use the first line as description
                            first_line = section.strip().split('\n')[0]
                            test_case['description'] = first_line[:100]  # Limit length
                        
                        # Extract test type
                        type_match = re.search(r'Test Type[:.]\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
                        if type_match:
                            test_type = type_match.group(1).strip().lower()
                            if 'positive' in test_type:
                                test_case['test_type'] = 'positive'
                            elif 'negative' in test_type:
                                test_case['test_type'] = 'negative'
                            else:
                                test_case['test_type'] = 'positive'  # Default to positive
                        else:
                            # Infer from description
                            if any(word in test_case.get('description', '').lower() for word in ['invalid', 'error', 'fail', 'negative']):
                                test_case['test_type'] = 'negative'
                            else:
                                test_case['test_type'] = 'positive'
                        
                        # Extract expected status code
                        status_match = re.search(r'(?:Expected )?Status Code[:.]\s*(\d+)', section, re.IGNORECASE)
                        if status_match:
                            test_case['expected_status_code'] = int(status_match.group(1))
                        else:
                            # Default based on test type
                            test_case['expected_status_code'] = 200 if test_case.get('test_type') == 'positive' else 400
                        
                        # Extract curl command
                        curl_match = re.search(r'(curl\s+.*?)(?:\n\n|\n(?:[A-Z]|$)|$)', section, re.DOTALL | re.IGNORECASE)
                        if curl_match:
                            curl_cmd = curl_match.group(1).strip()
                            # Clean up multi-line curl commands
                            curl_cmd = re.sub(r'\s*\\\s*\n\s*', ' ', curl_cmd)
                            curl_cmd = re.sub(r'\s+', ' ', curl_cmd)
                            test_case['curl_command'] = curl_cmd
                        else:
                            # Use original curl command
                            test_case['curl_command'] = curl_command
                        
                        # Add the test case if it has the required fields
                        if test_case.get('description') and test_case.get('curl_command'):
                            test_cases.append(test_case)
                    
                    # If we found test cases, break out of the marker loop
                    if test_cases:
                        break
            
            # If we didn't find any test cases using markers, try to find curl commands directly
            if not test_cases:
                logger.info("No test cases found using markers, trying to find curl commands directly")
                
                # Find all curl commands in the response
                curl_matches = re.finditer(r'(curl\s+.*?)(?:\n\n|\n(?:[A-Z]|$)|$)', ai_response, re.DOTALL | re.IGNORECASE)
                
                for i, match in enumerate(curl_matches):
                    curl_cmd = match.group(1).strip()
                    # Clean up multi-line curl commands
                    curl_cmd = re.sub(r'\s*\\\s*\n\s*', ' ', curl_cmd)
                    curl_cmd = re.sub(r'\s+', ' ', curl_cmd)
                    
                    # Find the context around this curl command
                    start_pos = max(0, match.start() - 200)  # Look back up to 200 chars
                    end_pos = min(len(ai_response), match.end() + 200)  # Look ahead up to 200 chars
                    context = ai_response[start_pos:end_pos]
                    
                    test_case = {
                        'curl_command': curl_cmd,
                        'description': f"Test Case {i+1}"
                    }
                    
                    # Try to extract description from context
                    desc_match = re.search(r'(?:Description|Title)[:.]\s*(.*?)(?:\n|$)', context, re.IGNORECASE)
                    if desc_match:
                        test_case['description'] = desc_match.group(1).strip()
                    
                    # Try to extract test type from context
                    type_match = re.search(r'Test Type[:.]\s*(.*?)(?:\n|$)', context, re.IGNORECASE)
                    if type_match:
                        test_type = type_match.group(1).strip().lower()
                        if 'positive' in test_type:
                            test_case['test_type'] = 'positive'
                        elif 'negative' in test_type:
                            test_case['test_type'] = 'negative'
                        else:
                            test_case['test_type'] = 'positive'
                    else:
                        # Infer from context
                        if any(word in context.lower() for word in ['invalid', 'error', 'fail', 'negative']):
                            test_case['test_type'] = 'negative'
                        else:
                            test_case['test_type'] = 'positive'
                    
                    # Try to extract status code from context
                    status_match = re.search(r'(?:Expected )?Status Code[:.]\s*(\d+)', context, re.IGNORECASE)
                    if status_match:
                        test_case['expected_status_code'] = str(int(status_match.group(1)))
                    else:
                        # Default based on test type
                        test_case['expected_status_code'] = str(200 if test_case.get('test_type') == 'positive' else 400)
                    
                    test_cases.append(test_case)
            
            logger.info(f"Extracted {len(test_cases)} test cases")
            return test_cases
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}", exc_info=True)
            # Return an empty list
            return []
    
    def _fix_json(self, json_str: str) -> str:
        """Fix common JSON formatting issues"""
        logger.info(f"Attempting to fix JSON: {json_str[:100]}...")
        
        # First, let's try to normalize the JSON structure
        # Remove any leading/trailing whitespace
        fixed = json_str.strip()
        
        # Replace single quotes with double quotes for property names and string values
        fixed = re.sub(r"'([^']*?)'", r'"\1"', fixed)
        
        # Fix unquoted property names (common in AI-generated JSON)
        fixed = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', fixed)
        
        # Fix trailing commas in arrays and objects
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # Fix missing commas between objects
        fixed = re.sub(r'}(\s*){', r'},\1{', fixed)
        
        # Fix newlines and spaces in string values
        fixed = re.sub(r'"\s*\n\s*([^"]*)"', r'" \1"', fixed)
        
        # Fix escaped quotes
        fixed = re.sub(r'\\+"', '"', fixed)
        fixed = re.sub(r'(?<!\\)"(?=\w)', r'\\"', fixed)
        
        # Fix tabs and special characters in strings
        fixed = re.sub(r'\t', ' ', fixed)
        
        # Try a more direct approach - manually rebuild the JSON
        try:
            # Extract all test cases using regex
            test_cases = []
            
            # Look for patterns that indicate the start of a test case
            test_case_pattern = r'{\s*"Description":\s*"([^"]+)".*?}'
            matches = re.finditer(test_case_pattern, fixed, re.DOTALL)
            
            for match in matches:
                test_case_str = match.group(0)
                
                # Clean up the test case JSON
                test_case_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', test_case_str)
                test_case_str = re.sub(r':\s*"([^"]*?)"([^,}])', r':"\1"\2', test_case_str)
                
                try:
                    # Try to parse the individual test case
                    test_case = json.loads(test_case_str)
                    test_cases.append(test_case)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse individual test case: {test_case_str[:50]}...")
            
            if test_cases:
                # Convert the list of test cases to a JSON string
                return json.dumps(test_cases)
            
            # If the above approach didn't work, try a line-by-line approach
            lines = fixed.split('\n')
            clean_lines = []
            
            in_test_case = False
            current_test_case = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('{'):
                    in_test_case = True
                    current_test_case = line
                elif line.startswith('}'):
                    current_test_case += line
                    in_test_case = False
                    
                    # Clean up the test case
                    clean_test_case = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', current_test_case)
                    clean_test_case = re.sub(r':\s*"([^"]*?)"([^,}])', r':"\1"\2', clean_test_case)
                    
                    clean_lines.append(clean_test_case)
                    current_test_case = ""
                elif in_test_case:
                    current_test_case += line
            
            if clean_lines:
                # Join the clean lines with commas and wrap in array brackets
                return "[" + ",".join(clean_lines) + "]"
        except Exception as e:
            logger.error(f"Error during JSON rebuilding: {str(e)}")
        
        # If all else fails, try a completely manual approach
        try:
            # Read the raw AI response from the file
            with open('/tmp/raw_ai_response.txt', 'r') as f:
                raw_response = f.read()
            
            # Extract test cases manually
            test_cases = []
            
            # Split by test case markers
            test_sections = re.split(r'Test Case \d+:|Test \d+:', raw_response)
            
            for section in test_sections:
                if not section.strip():
                    continue
                    
                test_case = {}
                
                # Extract description
                description_match = re.search(r'Description:\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
                if description_match:
                    test_case['description'] = description_match.group(1).strip()
                else:
                    # Try to get the first line as description
                    first_line = section.strip().split('\n')[0]
                    test_case['description'] = first_line if first_line else "Unknown test case"
                
                # Extract test type
                test_type_match = re.search(r'Test Type:\s*(positive|negative)', section, re.IGNORECASE)
                if test_type_match:
                    test_case['test_type'] = test_type_match.group(1).lower()
                else:
                    # Default to positive
                    test_case['test_type'] = 'positive'
                
                # Extract expected status code
                status_code_match = re.search(r'Expected Status Code:\s*(\d+)', section, re.IGNORECASE)
                if status_code_match:
                    test_case['expected_status_code'] = int(status_code_match.group(1))
                else:
                    # Default based on test type
                    test_case['expected_status_code'] = 200 if test_case['test_type'] == 'positive' else 400
                
                # Extract curl command
                curl_match = re.search(r'(curl\s+.*?)(?:\n\n|\n(?:[A-Z]|$)|$)', section, re.DOTALL | re.IGNORECASE)
                if curl_match:
                    test_case['curl_command'] = curl_match.group(1).strip()
                
                # Add the test case if it has the required fields
                if test_case.get('description'):
                    test_cases.append(test_case)
            
            if test_cases:
                return json.dumps(test_cases)
        except Exception as e:
            logger.error(f"Error during manual extraction: {str(e)}")
        
        # If all else fails, return the original string
        return json_str
    
    def _process_test_case(self, test_case: Dict[str, Any], original_curl_command: str) -> None:
        """Process a test case to extract method, URL, headers, and body"""
        try:
            curl_command = test_case.get('curl_command', original_curl_command)
            if not curl_command:
                return
            
            # Extract method
            method_match = re.search(r'-X\s+(\w+)', curl_command)
            if method_match:
                test_case['method'] = method_match.group(1)
            else:
                test_case['method'] = 'GET'  # Default to GET
            
            # Extract URL
            url_match = re.search(r'curl\s+(?:-X\s+\w+\s+)?(?:-H\s+[\'"][^\'"]+"[\'"])?\s*([\'"]?)(\S+)\1', curl_command)
            if url_match:
                test_case['url'] = url_match.group(2).strip('\'"')
            
            # Extract headers
            headers = {}
            header_matches = re.finditer(r'-H\s+[\'"]([^:]+):\s*([^\'"]*)[\'"]\s*', curl_command)
            for match in header_matches:
                headers[match.group(1)] = match.group(2)
            test_case['headers'] = headers
            
            # Extract body
            body_match = re.search(r'-d\s+[\'"](.+?)[\'"]', curl_command)
            if body_match:
                body_str = body_match.group(1)
                try:
                    test_case['body'] = json.loads(body_str)
                except json.JSONDecodeError:
                    test_case['body'] = body_str
            
        except Exception as e:
            logger.error(f"Error processing test case: {str(e)}", exc_info=True)
    
    def _generate_curl_command(self, test_case: Dict[str, Any]) -> str:
        """Generate curl command for each test case based on its modifications"""
        curl_parts = ['curl']
        
        # Add method
        if test_case.get('method'):
            curl_parts.extend(['-X', test_case['method']])
        
        # Add headers
        for key, value in test_case.get('headers', {}).items():
            curl_parts.extend(['-H', f"'{key}: {value}'"])
        
        # Add body if present
        if test_case.get('body'):
            if isinstance(test_case['body'], dict):
                body_str = json.dumps(test_case['body'])
            else:
                body_str = str(test_case['body'])
            curl_parts.extend(['-d', f"'{body_str}'"])
        
        # Add URL
        curl_parts.append(f"'{test_case['url']}'")
        
        return ' '.join(curl_parts)
    
    def _get_invalid_value(self, original_value: Any) -> Any:
        """Helper method to generate invalid value based on type"""
        if isinstance(original_value, bool):
            return "not_a_boolean"
        elif isinstance(original_value, (int, float)):
            return "not_a_number"
        elif isinstance(original_value, str):
            return 12345
        elif original_value is None:
            return "not_null"
        return None