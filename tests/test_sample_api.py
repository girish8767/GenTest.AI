import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.utils.test_generator import TestGenerator
from src.utils.test_executor import TestExecutor
from src.utils.html_reporter import HTMLReporter
from src.utils.test_reporter import TestReporter
from datetime import datetime
import warnings
import urllib3
from pydantic import ConfigDict

# Suppress all warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

def test_sample_api():
    # Initialize the test generator
    generator = TestGenerator()
    
    # Sample API specification
    api_spec = """
    Endpoint: /api/users
    Method: POST
    Request Body:
    {
        "name": "string",
        "email": "string",
        "age": "integer"
    }
    """
    
    # Generate test cases
    test_cases = generator.generate_test_cases(api_spec)
    print("Generated test cases:", test_cases)
    
    # Generate test data
    test_data = generator.generate_test_data("Create user with valid and invalid data")
    print("Generated test data:", test_data)
    
    # Initialize test executor
    executor = TestExecutor(base_url="http://your-api-url")
    
    # Execute a sample test
    response = executor.execute_test(
        method="POST",
        endpoint="/api/users",
        data={
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
    )
    
    # Validate response
    executor.validate_response(
        response,
        expected_status_code=201,
        expected_schema={
            "id": int,
            "name": str,
            "email": str,
            "age": int
        }
    )


def test_payment_options_api(test_generator, test_executor, test_reporter, html_reporter):
    # Sample curl command
    curl_command = '''
    curl -X GET "https://rtss-sit.jioconnect.com/jop/api/v1/payment-options?paymentMethod=ALL" \
    -H "x-merchant-id: DONT_MODIFY_GTEST" \
    -H "x-business-flow: DONT_MODIFY_GTEST" \
    -H "x-transaction-time: 1742910168731" \
    -H "x-signature: B3F4D1BEE344C0F5DC7C069CB40F434A7CCA75DCF7E444C7BD445AF84B570B89"
    '''
    
    # Generate both header and body test scenarios
    test_scenarios = test_generator.generate_test_scenarios(curl_command)
    body_scenarios = test_generator.generate_body_test_scenarios(curl_command)
    test_scenarios.extend(body_scenarios)
    
    for scenario in test_scenarios:
        print(f"\n🧪 Running Test: {scenario.get('description', 'Unnamed Test')}")
        test_data = test_generator.generate_test_data(scenario)
        
        try:
            response = test_executor.execute_test(
                method=test_data['method'],
                endpoint=test_data['endpoint'],
                headers=test_data.get('headers'),
                params=test_data.get('params'),
                json=test_data.get('body')  # Add body parameter
            )
            
            success = True
            error = None
            try:
                test_executor.validate_response(
                    response,
                    expected_status_code=test_data['expected_status_code'],
                    expected_schema=test_data['expected_schema']
                )
                
                # Add body validation if present
                if test_data.get('body') and test_data.get('expected_body_validation'):
                    test_executor.validate_body_response(
                        response,
                        test_data['expected_body_validation']
                    )
                    
            except AssertionError as e:
                success = False
                error = str(e)
                
            # Add test type to scenario for frontend categorization
            scenario['test_type'] = scenario.get('test_type', 'header')
            test_reporter.add_result(scenario, response.json(), success, error)
            
        except Exception as e:
            scenario['test_type'] = scenario.get('test_type', 'header')
            test_reporter.add_result(scenario, None, False, str(e))
    
    # Generate both JSON and HTML reports
    report_path = test_reporter.generate_report()
    html_report_path = html_reporter.generate_html_report(
        test_reporter.test_results,
        historical_data=load_historical_data()
    )
    
    print(f"\n📊 Test Reports generated:")
    print(f"JSON Report: {report_path}")
    print(f"HTML Report: {html_report_path}")


def load_historical_data():
    # Simple initial historical data
    return [{
        'timestamp': datetime.now().strftime('%Y-%m-%d'),
        'pass_rate': 100.0
    }]