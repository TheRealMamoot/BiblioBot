import logging
import requests

from src.biblio.validation import validate_user_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def set_reservation(start_time: int, end_time: int, duration: int, user_data: dict) -> dict:
    """
    Sends a reservation request to the library API.

    Parameters:
    - start_time (int): Start time as Unix timestamp.
    - end_time (int): End time as Unix timestamp.
    - duration (int): Duration in seconds.
    - user_data (dict): Dictionary containing user information (codice_fiscale, cognome_nome, email).
    -- user_data = {'codice_fiscale': '<your_tax_code>',
                    'cognome_nome': '<your_name>',
                    'email': '<mamoot@gmail.com>'}

    Returns:
    - dict: Response from the API with reservation details.
    """
    url = 'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/store'

    try:
        validate_user_data(user_data)
    except ValueError as e:
        logging.error(f'User data validation failed: {e}')
        raise

    payload = {
        "cliente": "biblio",
        "start_time": start_time,
        "end_time": end_time,
        "durata": duration,
        "entry_type": 50,
        "area": 25,
        "public_primary": user_data['codice_fiscale'],
        "utente": {
            "codice_fiscale": user_data['codice_fiscale'],
            "cognome_nome": user_data['cognome_nome'],
            "email": user_data['email']
        },
        "servizio": {},
        "risorsa": None,
        "recaptchaToken": None,
        "timezone": "Europe/Rome"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        response_data = response.json()
        if 'entry' in response_data: # entry = Booking Code
            logging.info(f'Reservation successful. Booking Code: {response_data["codice_prenotazione"]}')
            return response_data
        else:
            logging.error('Unexpected response format: "Booking Code" not found.')
            raise ValueError('Unexpected response format: "Booking Code" not found.')
    except requests.exceptions.RequestException as e:
        logging.error(f'Request failed: {e}')
        raise RuntimeError(f'Value error: {e}')
    except ValueError as e:
        logging.error(f'Value error: {e}')
        raise RuntimeError(f'Value error: {e}')

def confirm_reservation(booking_code: int) -> dict:

    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/confirm/{booking_code}'
    
    try:
        response = requests.post(url)
        response.raise_for_status()
        logging.info(f'Reservation confirmed.')
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f'Request failed: {e}')
        raise RuntimeError(f'Value error: {e}')
    except ValueError as e:
        logging.error(f'Value error: {e}')
        raise RuntimeError(f'Value error: {e}')
    
def cancel_reservation(codice: str, booking_code: str, mode: str = 'delete') -> dict:

    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/{mode}/{booking_code}?chiave={codice}'

    payload = None
    if mode == 'update':
        payload = {
            "type": "libera_posto"
        }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f'Reservation canceled. mode: {mode}')
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f'Request failed: {e}')
        raise RuntimeError(f'Value error: {e}')
    except ValueError as e:
        logging.error(f'Value error: {e}')
        raise RuntimeError(f'Value error: {e}')