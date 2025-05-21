import json
import os
from pathlib import Path

from src.biblio.utils.utils import load_env

CREDENTIALS_PATH = Path(__file__).resolve().parents[1] / 'biblio' / 'config' / 'biblio.json'
PRIORITY_CODES_PATH = Path(__file__).resolve().parents[1] / 'biblio' / 'config' / 'priorities.json'


def get_database_url() -> str:
    load_env()
    return os.getenv('DATABASE_URL')


def get_priorities(priorities_env: str = 'prod'):
    if priorities_env == 'prod':
        priority_codes: dict = os.environ['PRIORITY_CODES']
        priority_codes = json.loads(priority_codes)
    elif priorities_env == 'local':
        with PRIORITY_CODES_PATH.open('r') as f:
            priority_codes = json.load(f)  # NOT json.loads
    else:
        raise ValueError('Wrong mode')
    return priority_codes


def get_token(token_env: str = 'prod'):
    load_env()
    if token_env == 'prod':
        token: str = os.getenv('TELEGRAM_TOKEN')
    elif token_env == 'staging':
        token: str = os.getenv('TELEGRAM_TOKEN_S')
    else:
        raise ValueError('Wrong mode')
    return token
