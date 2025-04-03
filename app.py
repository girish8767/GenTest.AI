import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify
from src.utils.test_generator import TestGenerator
from src.utils.test_executor import TestExecutor
import logging
import requests
import json

# Update the app.py file to correctly find the templates

from flask import Flask, render_template, request, jsonify
import os
import json
import subprocess  # Add this import
import re
from src.utils.test_generator import TestGenerator

# Create the Flask app with the correct template folder
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

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
        
        # Generate test cases using the TestGenerator
        app.logger.info("Generating test cases using AI")
        test_generator = TestGenerator()
        test_cases = test_generator.generate_test_cases(curl_command)
        
        app.logger.info(f"Generated {len(test_cases)} test cases")
        
        return jsonify({
            'status': 'success',
            'test_cases': test_cases
        })
        
    except Exception as e:
        app.logger.error(f"Error in generate_tests: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/run_tests', methods=['POST'])
def run_tests():
    try:
        data = request.get_json()
        if not data or 'curl_command' not in data:
            return jsonify({'success': False, 'error': 'No curl command provided'}), 400
            
        curl_command = data['curl_command']
        app.logger.info(f"Received curl command: {curl_command}")
        
        executor = TestExecutor()
        results = executor.run_all_tests(curl_command)
        
        app.logger.info(f"Generated {len(results)} test results")
        
        return jsonify({
            'success': True,
            'results': results,
            'test_count': len(results)
        })
        
    except Exception as e:
        app.logger.error(f"Error in run_tests: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/check-ai', methods=['GET'])
def check_ai():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        models = response.json()
        return jsonify({
            'status': 'AI service is running',
            'available_models': models
        })
    except requests.exceptions.ConnectionError:
        return jsonify({
            'status': 'AI service is not running',
            'error': 'Cannot connect to Ollama service'
        })
    except Exception as e:
        return jsonify({
            'status': 'Error checking AI service',
            'error': str(e)
        })

@app.route('/execute-curl', methods=['POST'])
def execute_curl():
    try:
        data = request.json
        curl_command = data.get('curl_command', '')
        
        # Clean up the curl command - remove markdown code block indicators
        curl_command = curl_command.strip()
        if curl_command.startswith('```'):
            # Remove opening backticks and any language identifier
            first_newline = curl_command.find('\n')
            if first_newline != -1:
                curl_command = curl_command[first_newline:].strip()
            else:
                curl_command = curl_command[3:].strip()
        
        if curl_command.endswith('```'):
            # Remove closing backticks
            curl_command = curl_command[:-3].strip()
        
        if not curl_command:
            return jsonify({'status': 'error', 'error': 'No curl command provided'})
        
        app.logger.info(f"Executing curl command: {curl_command[:50]}...")
        
        # Extract request body if present
        request_body = None
        body_match = re.search(r"-d\s+'([^']+)'|-d\s+\"([^\"]+)\"|--data\s+'([^']+)'|--data\s+\"([^\"]+)\"", curl_command)
        if body_match:
            body = next(filter(None, body_match.groups()), '')
            try:
                request_body = json.loads(body)
            except:
                request_body = body
        
        # Convert the curl command to a list of arguments
        import shlex
        try:
            curl_args = shlex.split(curl_command)
        except ValueError as e:
            app.logger.error(f"Error parsing curl command: {str(e)}")
            return jsonify({'status': 'error', 'error': f"Error parsing curl command: {str(e)}"})
        
        # Execute the curl command using subprocess
        try:
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
                    'error': f"Curl command failed with exit code {process.returncode}: {stderr}",
                    'request_body': request_body
                })
            
            # Try to parse the response as JSON
            try:
                response_json = json.loads(stdout)
                return jsonify({
                    'status': 'success',
                    'response': response_json,
                    'status_code': 200,  # Assuming success if we got a valid JSON response
                    'request_body': request_body
                })
            except json.JSONDecodeError:
                # If not JSON, return as text
                return jsonify({
                    'status': 'success',
                    'response': stdout,
                    'status_code': 200,  # Assuming success if the command executed without error
                    'request_body': request_body
                })
        except subprocess.TimeoutExpired:
            app.logger.error("Curl command timed out")
            return jsonify({'status': 'error', 'error': 'Curl command timed out', 'request_body': request_body})
        except Exception as e:
            app.logger.error(f"Error executing curl command: {str(e)}")
            return jsonify({'status': 'error', 'error': f"Error executing curl command: {str(e)}", 'request_body': request_body})
            
    except Exception as e:
        app.logger.error(f"Error in execute_curl: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)})

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)