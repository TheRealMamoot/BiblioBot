import asyncio
import logging

import httpx

from src.biblio.utils.validation import validate_user_data


def calculate_timeout(retries: int, base: int = 10, step: int = 15, max_read: int = 150) -> httpx.Timeout:
    read = base + retries * step
    return httpx.Timeout(connect=10.0, read=min(read, max_read), write=10.0, pool=10.0)


async def set_reservation(
    start_time: int, end_time: int, duration: int, user_data: dict, timeout: httpx.Timeout
) -> dict:
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

    async with httpx.AsyncClient(timeout=timeout) as client:
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

        except httpx.ReadTimeout as e:
            logging.error(f'[SET] Timeout: Server took too long to respond – {repr(e)}')
            raise TimeoutError('Reservation request timed out') from e

        except httpx.RequestError as e:
            logging.error(f'[SET] Request failed: {type(e).__name__} - {repr(e)}')
            raise ConnectionError('Network error during reservation') from e
        except ValueError as e:
            logging.error(f'[SET] Value error: {type(e).__name__} - {e}')
            raise

        except Exception as e:
            logging.exception(f'[SET] Unexpected error: {type(e).__name__} - {repr(e)}')
            raise


async def confirm_reservation(booking_code: int, max_retries: int = 3) -> dict:
    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/confirm/{booking_code}'

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url)
                response.raise_for_status()
                logging.info('[CONFIRM] Reservation confirmed.')
                return response.json()

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    logging.warning(f'[CONFIRM] 404 Not Found — Attempt {attempt + 1}/{max_retries}')
                    await asyncio.sleep(1.5 + attempt * 0.5)  # backoff
                    continue
                elif status == 400:
                    logging.error('[CONFIRM] 400 Bad Request — Invalid booking_code or payload.')
                    raise
                elif status == 401:
                    logging.error('[CONFIRM] 401 Unauthorized — Authentication failed.')
                    raise
                else:
                    logging.error(f'[CONFIRM] HTTP error: {status} - {repr(e)}')
                    raise

            except httpx.ReadTimeout as e:
                logging.error(f'[CONFIRM] Timeout: Server took too long to respond – {repr(e)}')
                raise
            except httpx.RequestError as e:
                logging.error(f'[CONFIRM] Request error: {type(e).__name__} - {repr(e)}')
                raise
            except Exception as e:
                logging.exception(f'[CONFIRM] Unexpected error: {type(e).__name__} - {repr(e)}')
                raise

        raise RuntimeError('[CONFIRM] Gave up after max retries — booking code not found.')


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
            status = e.response.status_code
            if status == 400:
                logging.error('[CANCEL] 400 Bad Request: Possibly invalid booking code or expired reservation')
                raise RuntimeError('Possibly invalid booking code or expired reservation') from e
            elif status == 404:
                logging.error('[CANCEL] 404 Not found: Cancel slot not found (?).')
                raise FileNotFoundError('Cancel slot not found (?).') from e
            elif status == 409:
                logging.error('[CANCEL] 409 Conflict: Another process may be modifying the reservation.')
                raise RuntimeError('Conflict during cancellation') from e
            else:
                logging.error(f'[CANCEL] HTTP error: {status} — {e.response.text}')
                raise RuntimeError(f'HTTP error during cancellation: {status}') from e

        except httpx.ReadTimeout as e:
            logging.error(f'[CANCEL] Timeout: Server took too long to respond – {repr(e)}')
            raise TimeoutError('Cancellation request timed out') from e

        except httpx.RequestError as e:
            logging.error(f'[CANCEL] Network error: {type(e).__name__} - {repr(e)}')
            raise ConnectionError('Network error during cancellation') from e

        except Exception as e:
            logging.exception(f'[CANCEL] Unexpected error: {type(e).__name__} - {repr(e)}')
            raise RuntimeError('Unexpected cancellation error') from e
