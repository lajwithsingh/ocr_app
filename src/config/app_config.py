import os
import yaml
from pathlib import Path

class AppConfig:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance.config_path = Path("config.yaml")
            cls._instance.data = cls._instance._load_defaults()
            cls._instance.load()
        return cls._instance

    def _load_defaults(self):
        return {
            "processing": {
                "dpi": 200,
                "upscale": 1.5,
                "contrast": 1.2,
                "sharpen": 1.5,
                "use_gpu": False
            },
            "ui": {
                "theme_mode": "light"
            },
            "output": {
                "default_dir": str(Path.home() / "Documents" / "OCR_Output")
            }
        }

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded = yaml.safe_load(f)
                    if loaded:
                        self.data.update(loaded)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.data, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, section, key, default=None):
        return self.data.get(section, {}).get(key, default)

config = AppConfig()
