# backend/config.py

import os
import yaml
from dotenv import load_dotenv

load_dotenv()

def load_env_vars():
    return {
        "SERVICE_ACCOUNT_FILE": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        "GOOGLE_SCOPES": os.getenv("GOOGLE_SCOPES", "").split(","),
    }

def load_app_config(path="backend/config/app_config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

env_config = load_env_vars()
app_config = load_app_config()
