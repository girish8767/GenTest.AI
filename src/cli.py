import click
from .test_suite import TestSuite
import json

@click.group()
def cli():
    """REST API Testing Tool with AI integration"""
    pass

@cli.command()
@click.argument('spec_path', type=click.Path(exists=True))
@click.option('--env', default='development', help='Environment to run tests against')
def run(spec_path, env):
    """Run API tests based on OpenAPI specification"""
    try:
        suite = TestSuite(name="default")
        suite.load_api_spec(spec_path)
        results = suite.run_tests()
        
        # Print results
        print("\nTest Results:")
        for result in results:
            status = "✅ Passed" if result.get('success') else "❌ Failed"
            test = result['test']
            print(f"\n{status} - {test['method']} {test['endpoint']}")
            if not result.get('success'):
                print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error running tests: {str(e)}")

if __name__ == '__main__':
    cli()