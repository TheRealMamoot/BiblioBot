import logging
import re

def validate_email(email: str) -> bool:

    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_pattern, email))

def validate_codice_fiscale(codice_fiscale: str) -> bool:

    codice_pattern = r'^[A-Za-z]{6}\d{2}[A-Za-z]\d{2}[A-Za-z]\d{3}[A-Za-z]$'
    return bool(re.match(codice_pattern, codice_fiscale))

def validate_user_data(user_data):

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