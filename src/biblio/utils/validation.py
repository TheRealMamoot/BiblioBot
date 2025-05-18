import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes


def validate_email(email: str) -> bool:
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_pattern, email))


def validate_codice_fiscale(codice_fiscale: str) -> bool:
    codice_pattern = r'^[A-Za-z]{6}\d{2}[A-Za-z]\d{2}[A-Za-z]\d{3}[A-Za-z]$'
    return bool(re.match(codice_pattern, codice_fiscale))


def validate_user_data(user_data: dict):
    required_fields = ['codice_fiscale', 'cognome_nome', 'email']
    for field in required_fields:
        if field not in user_data or not user_data[field]:
            raise ValueError(f'Missing or empty field: {field}')

    codice_fiscale = user_data.get('codice_fiscale')
    if not codice_fiscale or not validate_codice_fiscale(codice_fiscale):
        raise ValueError('Invalid codice fiscale format.')

    email = user_data.get('email')
    if not email or not validate_email(email):
        raise ValueError('Invalid email format. Please provide a valid email address.')

    logging.info('User data validated successfully.')


def duration_overlap(update: Update, context: ContextTypes.DEFAULT_TYPE, history: pd.DataFrame) -> bool:
    filtered = history[
        (history['codice_fiscale'] == context.user_data['codice_fiscale'])
        & (history['email'] == context.user_data['email'])
        & (history['selected_date'] == context.user_data['selected_date'])
    ]
    if len(filtered) == 0:
        return False

    reserving_start = datetime.strptime(context.user_data['selected_time'], '%H:%M')
    reserving_end = reserving_start + timedelta(hours=int(update.message.text.strip()))
    for _, row in filtered.iterrows():
        existing_start = datetime.strptime(row['start'], '%H:%M')
        existing_end = datetime.strptime(row['end'], '%H:%M')
        if row['status'] == 'terminated':
            continue
        if reserving_start < existing_end and reserving_end > existing_start:
            return True
    return False


def time_not_overlap(update: Update, context: ContextTypes.DEFAULT_TYPE, history: pd.DataFrame) -> bool:
    filtered = history[
        (history['codice_fiscale'] == context.user_data['codice_fiscale'])
        & (history['email'] == context.user_data['email'])
        & (history['selected_date'] == context.user_data['selected_date'])
    ]
    reserving_start = datetime.strptime(update.message.text.strip(), '%H:%M').replace(tzinfo=ZoneInfo('Europe/Rome'))
    for _, row in filtered.iterrows():
        existing_start = datetime.strptime(row['start'], '%H:%M').replace(tzinfo=ZoneInfo('Europe/Rome'))
        existing_end = datetime.strptime(row['end'], '%H:%M').replace(tzinfo=ZoneInfo('Europe/Rome'))
        if row['status'] == 'terminated':
            continue
        if reserving_start >= existing_start - timedelta(minutes=30) and reserving_start < existing_end:
            return False
    return True
