from flask import Flask, render_template, request, jsonify
from src.utils.test_executor import TestExecutor
import logging
import requests
import json

app = Flask(__name__)

# Add JSON filter for Jinja2
@app.template_filter('json')
def json_filter(value):
    return json.dumps(value, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)