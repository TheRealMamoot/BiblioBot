import json
import os
from functools import cache
from pathlib import Path

import pygsheets
from dotenv import load_dotenv

CREDENTIALS_PATH = Path(__file__).resolve().parents[1] / 'biblio' / 'config' / 'biblio.json'
PRIORITY_CODES_PATH = Path(__file__).resolve().parents[1] / 'biblio' / 'config' / 'priorities.json'
ENV_PATH = Path(__file__).resolve().parent


@cache
def get_gsheet_client(auth_mode: str):
    if auth_mode == 'prod':
        return pygsheets.authorize(service_account_json=os.environ['GSHEETS'])
    elif auth_mode == 'local':
        return pygsheets.authorize(service_file=CREDENTIALS_PATH)
    else:
        raise ValueError('Wrong mode')


def get_wks(sheet_env: str = 'prod', auth_mode: str = 'prod'):
    gc = get_gsheet_client(auth_mode)
    sheet_name = 'Biblio-logs'
    if sheet_env == 'prod':
        tab_name = 'logs'
    elif sheet_env == 'test':
        tab_name = 'tests'
    elif sheet_env == 'staging':
        tab_name = 'staging'
    else:
        raise ValueError('Wrong mode')
    return gc.open(sheet_name).worksheet_by_title(tab_name)


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
    load_dotenv(dotenv_path=ENV_PATH)
    if token_env == 'prod':
        token: str = os.getenv('TELEGRAM_TOKEN')
    elif token_env == 'staging':
        token: str = os.getenv('TELEGRAM_TOKEN_S')
    else:
        raise ValueError('Wrong mode')
    return token
