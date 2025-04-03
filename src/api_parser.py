import yaml
from typing import Dict, Any, List, Optional
try:
    from pydantic.v1 import BaseModel  # Using v1 for compatibility
except ImportError:
    try:
        from pydantic import BaseModel
    except ImportError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pydantic"])
        from pydantic import BaseModel

class APISpecification(BaseModel):
    path: str
    method: str
    request_body: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None  # Changed from Dict to Optional[Dict]

class APIParser:
    @staticmethod
    def parse_openapi(spec_path: str) -> Dict[str, APISpecification]:
        with open(spec_path, 'r') as file:
            spec = yaml.safe_load(file)
        
        parsed_specs = {}
        paths = spec.get('paths', {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                spec_key = f"{method.upper()}_{path}"
                # Convert parameters list to dict if exists
                params = {}
                if details.get('parameters'):
                    for param in details.get('parameters', []):
                        params[param.get('name')] = param
                
                parsed_specs[spec_key] = APISpecification(
                    path=path,
                    method=method.upper(),
                    request_body=details.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {}),
                    response_schema=details.get('responses', {}).get('201', {}).get('content', {}).get('application/json', {}).get('schema', {}),
                    parameters=params or None  # Set None if empty
                )
        
        return parsed_specs