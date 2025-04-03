import json
from datetime import datetime
from typing import List, Dict
import os
import pytest

@pytest.mark.no_collect
class TestReporter:
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = f"/Users/girish.shimpi/api_test_gen/{output_dir}"
        os.makedirs(self.output_dir, exist_ok=True)
        self.test_results = []

    def add_result(self, scenario: Dict, response: Dict, success: bool, error: str = None):
        result = {
            "test_name": scenario.get('description', 'Unnamed Test'),
            "test_type": scenario.get('test_type', 'Unknown'),
            "status": "PASS" if success else "FAIL",
            "error_message": error if error else None,
            "method": scenario.get('method'),
            "endpoint": scenario.get('endpoint'),
            "headers": scenario.get('headers'),
            "params": scenario.get('params'),
            "actual_response": response  # Store complete actual response
        }
        self.test_results.append(result)

    def generate_report(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        summary = {
            "total_tests": len(self.test_results),
            "passed": sum(1 for r in self.test_results if r["status"] == "PASS"),
            "failed": sum(1 for r in self.test_results if r["status"] == "FAIL"),
            "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        report = {
            "summary": summary,
            "test_results": self.test_results
        }

        report_path = f"{self.output_dir}/test_report_{timestamp}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary to console
        print("\n=== Test Execution Summary ===")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Report saved to: {report_path}")
        
        return report_path