import logging

import httpx

from src.biblio.utils.validation import validate_user_data


async def set_reservation(start_time: int, end_time: int, duration: int, user_data: dict) -> dict:
    url = 'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/store'

    try:
        validate_user_data(user_data)
    except ValueError as e:
        logging.error(f'[SET] User data validation failed: {e}')
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
                logging.info(f'[SET] Reservation successful. Booking Code: {response_data["codice_prenotazione"]}')
                return response_data
            else:
                logging.error('[SET] Unexpected response format: "Booking Code" not found.')
                raise ValueError('[SET] Unexpected response format: "Booking Code" not found.')
        except httpx.RequestError as e:
            logging.error(f'[SET] Request failed: {e}')
            raise RuntimeError(f'[SET] Request error: {e}')
        except ValueError as e:
            logging.error(f'[SET] Value error: {e}')
            raise RuntimeError(f'[SET] Value error: {e}')


async def confirm_reservation(booking_code: int) -> dict:
    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/confirm/{booking_code}'

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url)
            response.raise_for_status()
            logging.info('[CONFIRM] Reservation confirmed.')
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logging.error('[CONFIRM] 400 Bad Request – Check booking_code or payload format.')
                raise RuntimeError('Reservation confirmation failed: Invalid request. Please try again.')

            elif e.response.status_code == 401:
                logging.error('[CONFIRM] 401 Unauthorized – Authentication failed.')
                raise RuntimeError('Reservation confirmation failed: Unauthorized. Please check your credentials.')

            else:
                logging.error(f'[CONFIRM] HTTP error: {e}')
                raise RuntimeError(f'Unexpected HTTP error: {e}')

        except httpx.RequestError as e:
            logging.error(f'[CONFIRM] Request failed: {e}')
            raise RuntimeError(f'Connection error: {e}')


async def cancel_reservation(codice: str, booking_code: str, mode: str = 'delete') -> dict:
    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/{mode}/{booking_code}?chiave={codice}'

    payload = {'type': 'libera_posto'} if mode == 'update' else None
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logging.info(f'Reservation canceled. mode: {mode}')
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logging.warning('[CANCEL] 400 Bad Request: Possibly invalid booking code or reservation expired')
                raise RuntimeError('Reservation not found or already canceled.')
            elif e.response.status_code == 409:
                logging.warning('[CANCEL] 409 Conflict: Another process may be modifying the reservation.')
                raise RuntimeError('Reservation conflict detected.')
            else:
                logging.error(f'[CANCEL] HTTP error: {e.response.status_code} — {e.response.text}')
                raise RuntimeError(f'Unexpected HTTP error: {e.response.status_code}')

        except httpx.RequestError as e:
            logging.error(f'[CANCEL] Network error: {e}')
            raise RuntimeError('Network error while canceling reservation.')

        except Exception as e:
            logging.exception('[CANCEL] Unexpected error')
            raise RuntimeError(f'Unexpected cancel error: {e}')
