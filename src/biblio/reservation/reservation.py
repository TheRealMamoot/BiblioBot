import logging

import httpx

from src.biblio.utils.validation import validate_user_data


async def set_reservation(start_time: int, end_time: int, duration: int, user_data: dict) -> dict:
    url = 'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/store'

    try:
        validate_user_data(user_data)
    except ValueError as e:
        logging.error(f'User data validation failed: {e}')
        raise

    payload = {
        'cliente': 'biblio',
        'start_time': start_time,
        'end_time': end_time,
        'durata': duration,
        'entry_type': 50,
        'area': 25,
        'public_primary': user_data['codice_fiscale'],
        'utente': {
            'codice_fiscale': user_data['codice_fiscale'],
            'cognome_nome': user_data['cognome_nome'],
            'email': user_data['email'],
        },
        'servizio': {},
        'risorsa': None,
        'recaptchaToken': None,
        'timezone': 'Europe/Rome',
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            if 'entry' in response_data:  # entry = Booking Code
                logging.info(f'Reservation successful. Booking Code: {response_data["codice_prenotazione"]}')
                return response_data
            else:
                logging.error('Unexpected response format: "Booking Code" not found.')
                raise ValueError('Unexpected response format: "Booking Code" not found.')
        except httpx.RequestError as e:
            logging.error(f'Request failed: {e}')
            raise RuntimeError(f'Value error: {e}')
        except ValueError as e:
            logging.error(f'Value error: {e}')
            raise RuntimeError(f'Value error: {e}')


async def confirm_reservation(booking_code: int) -> dict:
    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/confirm/{booking_code}'

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url)
            response.raise_for_status()
            logging.info('Reservation confirmed.')
            return response.json()
        except httpx.RequestError as e:
            logging.error(f'Request failed: {e}')
            raise RuntimeError(f'Value error: {e}')
        except ValueError as e:
            logging.error(f'Value error: {e}')
            raise RuntimeError(f'Value error: {e}')


async def cancel_reservation(codice: str, booking_code: str, mode: str = 'delete') -> dict:
    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/{mode}/{booking_code}?chiave={codice}'
    payload = None
    if mode == 'update':
        payload = {'type': 'libera_posto'}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logging.info(f'Reservation canceled. mode: {mode}')
            return response.json()
        except httpx.RequestError as e:
            logging.error(f'Request failed: {e}')
            raise RuntimeError(f'Value error: {e}')
        except ValueError as e:
            logging.error(f'Value error: {e}')
            raise RuntimeError(f'Value error: {e}')
