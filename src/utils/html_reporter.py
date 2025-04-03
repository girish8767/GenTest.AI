import jinja2
import os
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd

class HTMLReporter:
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = f"/Users/girish.shimpi/api_test_gen/{output_dir}"
        self.template_dir = f"/Users/girish.shimpi/api_test_gen/templates"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)

    def create_trend_chart(self, historical_data):
        df = pd.DataFrame(historical_data)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['pass_rate'], name='Pass Rate'))
        fig.update_layout(title='Test Pass Rate Trend')
        return fig.to_html(full_html=False)

    def format_dict(self, d):
        if not d:
            return "None"
        if isinstance(d, dict):
            return "<br>".join(f"{k}: {v}" for k, v in d.items())
        if isinstance(d, list):
            return "<br>".join(str(item) for item in d)
        return str(d)

    def format_response_data(self, data):
        if isinstance(data, list):
            return "<br>".join(
                f"- {item.get('name', 'Unknown')}: {item.get('instrumentType', 'Unknown Type')}"
                for item in data
            )
        return self.format_dict(data)

    def generate_html_report(self, test_results, historical_data=None):
        style = """
            body { font-family: Arial; padding: 20px; }
            .summary { background: #f5f5f5; padding: 20px; margin-bottom: 20px; }
            .test-case { border: 1px solid #ddd; padding: 15px; margin: 15px 0; }
            .PASS { border-left: 5px solid #4CAF50; }
            .FAIL { border-left: 5px solid #f44336; }
            .request-details, .response-details { 
                background: #f8f8f8; 
                padding: 10px; 
                margin: 10px 0;
                font-family: monospace;
            }
            .error { color: #f44336; }
        """
        
        summary = {
            'total': len(test_results),
            'passed': sum(1 for r in test_results if r['status'] == 'PASS'),
            'failed': sum(1 for r in test_results if r['status'] == 'FAIL'),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        html_content = f"""
        <html>
            <head>
                <title>API Test Report</title>
                <style>{style}</style>
            </head>
            <body>
                <h1>API Test Report</h1>
                <div class="summary">
                    <h2>Summary</h2>
                    <p>Total Tests: {summary['total']}</p>
                    <p>Passed: {summary['passed']}</p>
                    <p>Failed: {summary['failed']}</p>
                    <p>Execution Time: {summary['time']}</p>
                </div>
        """
    
        for result in test_results:
            html_content += f"""
                <div class="test-case {result['status']}">
                    <h3>{result['test_name']}</h3>
                    <p><strong>Type:</strong> {result['test_type']}</p>
                    <p><strong>Status:</strong> {result['status']}</p>
                    
                    <div class="request-details">
                        <h4>Request Details:</h4>
                        <p><strong>Method:</strong> {result.get('method', 'None')}</p>
                        <p><strong>Endpoint:</strong> {result.get('endpoint', 'None')}</p>
                        <p><strong>Headers:</strong><br>{self.format_dict(result.get('headers'))}</p>
                        <p><strong>Parameters:</strong><br>{self.format_dict(result.get('params'))}</p>
                    </div>
                    
                    <div class="response-details">
                        <h4>Response Details:</h4>
                        <p><strong>Status:</strong> {result.get('response_status', 'None')}</p>
                        <p><strong>Message:</strong> {result.get('response_message', 'None')}</p>
                        <p><strong>Data:</strong><br>{self.format_response_data(result.get('response_data'))}</p>
                    </div>
                    
                    {f'<p class="error">Error: {result["error_message"]}</p>' if result.get('error_message') else ''}
                </div>
            """
        
        html_content += """
            </body>
        </html>
        """
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"{self.output_dir}/test_report_{timestamp}.html"
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return report_path