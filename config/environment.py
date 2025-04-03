from typing import Dict, Any
import yaml
import os

class EnvironmentManager:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), 'environments.yaml')
        self.current_env = os.getenv('TEST_ENV', 'development')
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get_config(self) -> Dict[str, Any]:
        return self.config[self.current_env]

    def switch_environment(self, env: str):
        if env not in self.config:
            raise ValueError(f"Environment {env} not found in config")
        self.current_env = env