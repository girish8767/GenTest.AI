# Fix the app.py file to remove duplicates and ensure test cases are displayed

from flask import Flask, request, jsonify, render_template
import subprocess
import json
import logging
import os
from utils.test_generator import TestGenerator
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add this import if not already present
from flask import Flask, render_template, request, jsonify, send_from_directory

# Make sure your app is configured to serve static files
app = Flask(__name__, static_folder='static')

# Add this route to serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-tests', methods=['POST'])
def generate_tests():
    try:
        data = request.get_json()
        curl_command = data.get('curl_command', '')
        
        if not curl_command:
            return jsonify({
                'status': 'error',
                'error': 'No curl command provided'
            }), 400
        
        # Parse the curl command to extract key components for optimization
        parsed_curl = parse_curl_command(curl_command)
        
        # Execute the original curl command to get the response
        app.logger.info(f"Executing original curl command: {curl_command[:50]}...")
        original_response = None
        try:
            # Execute the curl command directly
            process = subprocess.Popen(
                curl_command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(timeout=10)
            
            if process.returncode == 0:
                try:
                    original_response = json.loads(stdout.decode('utf-8'))
                except json.JSONDecodeError:
                    original_response = stdout.decode('utf-8')
            else:
                original_response = {"error": stderr.decode('utf-8')}
                
        except Exception as e:
            app.logger.error(f"Error executing original curl command: {str(e)}")
            original_response = {"error": str(e)}
        
        # Generate test cases using the TestGenerator with optimization
        app.logger.info("Generating test cases using AI")
        test_generator = TestGenerator()
        
        # Use the parsed curl information for more efficient test generation
        test_cases, raw_ai_response = test_generator.generate_test_cases(
            curl_command, 
            return_raw=True,
            parsed_curl=parsed_curl  # Changed from parsed_data to parsed_curl
        )
        
        app.logger.info(f"Generated {len(test_cases)} test cases")
        
        # Return both original response and test cases
        return jsonify({
            'status': 'success',
            'original_response': original_response,
            'test_cases': test_cases,
            'raw_ai_response': raw_ai_response
        })
        
    except Exception as e:
        app.logger.error(f"Error in generate_tests: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

def parse_curl_command(curl_command):
    """
    Parse a curl command to extract key components for optimization.
    This helps reduce the complexity of the prompt sent to the AI.
    """
    parsed_data = {
        'method': 'GET',  # Default method
        'url': '',
        'headers': {},
        'params': {},
        'body': None
    }
    
    # Extract URL
    url_match = re.search(r"--url '([^']+)'|--url \"([^\"]+)\"|curl '([^']+)'|curl \"([^\"]+)\"|curl ([^\s]+)", curl_command)
    if url_match:
        url = next(filter(None, url_match.groups()), '')
        parsed_data['url'] = url
    
    # Extract method
    if '-X' in curl_command or '--request' in curl_command:
        method_match = re.search(r"-X\s+([^\s]+)|--request\s+([^\s]+)", curl_command)
        if method_match:
            parsed_data['method'] = next(filter(None, method_match.groups()), 'GET')
    
    # Extract headers
    header_matches = re.finditer(r"-H\s+'([^']+)'|-H\s+\"([^\"]+)\"|--header\s+'([^']+)'|--header\s+\"([^\"]+)\"", curl_command)
    for match in header_matches:
        header = next(filter(None, match.groups()), '')
        if ':' in header:
            key, value = header.split(':', 1)
            parsed_data['headers'][key.strip()] = value.strip()
    
    # Extract body if present
    body_match = re.search(r"-d\s+'([^']+)'|-d\s+\"([^\"]+)\"|--data\s+'([^']+)'|--data\s+\"([^\"]+)\"", curl_command)
    if body_match:
        body = next(filter(None, body_match.groups()), '')
        try:
            parsed_data['body'] = json.loads(body)
        except:
            parsed_data['body'] = body
    
    return parsed_data

@app.route('/execute-test', methods=['POST'])
def execute_test():
    try:
        data = request.get_json()
        curl_command = data.get('curl_command', '')
        
        if not curl_command:
            return jsonify({
                'status': 'error',
                'error': 'No curl command provided'
            }), 400
        
        # Execute the curl command
        logger.info(f"Executing test curl command: {curl_command[:50]}...")
        process = subprocess.Popen(
            curl_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(timeout=10)
        
        if process.returncode == 0:
            try:
                response_data = json.loads(stdout.decode('utf-8'))
            except json.JSONDecodeError:
                response_data = stdout.decode('utf-8')
            
            return jsonify({
                'status': 'success',
                'response': response_data
            })
        else:
            return jsonify({
                'status': 'error',
                'error': stderr.decode('utf-8')
            }), 500
            
    except Exception as e:
        logger.error(f"Error in execute_test: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/execute-curl', methods=['POST'])
def execute_curl():
    try:
        data = request.json
        curl_command = data['curl_command'] if data else ''
        
        if not curl_command:
            return jsonify({'status': 'error', 'error': 'No curl command provided'})
        
        app.logger.info(f"Executing curl command: {curl_command[:50]}...")
        
        # Clean up the curl command - remove backslashes that might be causing issues
        curl_command = curl_command.replace('\\\n', ' ').replace('\\', '')
        
        # Check for placeholder values and warn if found
        placeholders = re.findall(r'<[A-Z_]+>', curl_command)
        if placeholders:
            placeholder_warning = f"Warning: Found placeholder values that need to be replaced: {', '.join(placeholders)}"
            app.logger.warning(placeholder_warning)
            return jsonify({
                'status': 'error',
                'error': placeholder_warning
            })
        
        # Convert the curl command to a list of arguments
        import shlex
        try:
            curl_args = shlex.split(curl_command)
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'error': f"Failed to parse curl command: {str(e)}"
            })
        
        # Execute the curl command using subprocess
        process = subprocess.Popen(
            curl_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=30)
        
        if process.returncode != 0:
            app.logger.error(f"Error executing curl command: {stderr}")
            return jsonify({
                'status': 'error',
                'error': f"Curl command failed with exit code {process.returncode}: {stderr}"
            })
        
        # Try to parse the response as JSON
        try:
            response_json = json.loads(stdout)
            return jsonify({
                'status': 'success',
                'response': response_json,
                'status_code': 200  # Assuming success if we got a valid JSON response
            })
        except json.JSONDecodeError:
            # If not JSON, return as text
            return jsonify({
                'status': 'success',
                'response': stdout,
                'status_code': 200  # Assuming success if the command executed without error
            })
            
    except subprocess.TimeoutExpired:
        app.logger.error("Curl command timed out")
        return jsonify({'status': 'error', 'error': 'Curl command timed out'})
    except Exception as e:
        app.logger.error(f"Error executing curl command: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)