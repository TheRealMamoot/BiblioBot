import asyncio
import logging
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from src.biblio.config.config import ReservationConfirmationConflict
from src.biblio.reservation.slot_datetime import extract_available_seats
from src.biblio.utils.validation import validate_user_data


def calculate_timeout(
    retries: int, base: int = 10, step: int = 15, max_read: int = 150
) -> httpx.Timeout:
    read = base + retries * step
    return httpx.Timeout(connect=10.0, read=min(read, max_read), write=10.0, pool=10.0)


async def set_reservation(
    start_time: int,
    end_time: int,
    duration: int,
    user_data: dict,
    timeout: httpx.Timeout | None = None,
    record: dict | None = None,
) -> dict:
    url = "https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/store"

    try:
        validate_user_data(user_data)
    except ValueError as e:
        logging.error(f"[SET] User data validation failed: {e}")
        raise

    recaptcha_token = await _solve_recaptcha(record)
    payload = {
        "cliente": "biblio",
        "start_time": start_time,
        "end_time": end_time,
        "durata": duration,
        "entry_type": 50,
        "area": 25,
        "public_primary": user_data["codice_fiscale"],
        "utente": {
            "codice_fiscale": user_data["codice_fiscale"],
            "cognome_nome": user_data["cognome_nome"],
            "email": user_data["email"],
        },
        "servizio": {},
        "risorsa": None,
        "recaptchaToken": recaptcha_token,
        "timezone": "Europe/Rome",
    }

    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            if "entry" in response_data:  # entry = NOT Booking Code!
                logging.info(
                    f"[SET] Reservation successful. Booking Code: {response_data['codice_prenotazione']}"
                )
                return response_data
            else:
                logging.error(
                    '[SET] Unexpected response format: "Booking Code" not found.'
                )
                raise ValueError(
                    '[SET] Unexpected response format: "Booking Code" not found.'
                )

        except httpx.ReadTimeout as e:
            logging.error(f"[SET] Timeout: Server took too long to respond – {repr(e)}")
            raise TimeoutError("Reservation request timed out") from e

        except httpx.RequestError as e:
            logging.error(f"[SET] Request failed: {type(e).__name__} - {repr(e)}")
            raise ConnectionError("Network error during reservation") from e
        except ValueError as e:
            logging.error(f"[SET] Value error: {type(e).__name__} - {e}")
            raise

        except Exception as e:
            logging.exception(f"[SET] Unexpected error: {type(e).__name__} - {repr(e)}")
            raise


async def confirm_reservation(
    entry: str, max_retries: int = 3, record: dict | None = None
) -> dict:
    url = f"https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/confirm/{entry}"
    message = f" for ID {record['id']}" if record else ""

    async with httpx.AsyncClient(verify=False) as client:
        for attempt in range(max_retries):
            timeout = calculate_timeout(retries=attempt, base=5, step=5, max_read=60)
            try:
                response = await client.post(url, timeout=timeout)
                response.raise_for_status()
                logging.info(f"[CONFIRM] Success{message} on attempt {attempt + 1}")
                return response.json()

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    logging.warning(
                        f"[CONFIRM] 404 Not Found{message} — Attempt {attempt + 1}/{max_retries}"
                    )
                    await asyncio.sleep(2 + attempt * 1)  # backoff
                    continue
                elif status == 400:
                    logging.error(
                        f"[CONFIRM] 400 Bad Request{message} — Invalid booking_code or payload."
                    )
                    raise
                elif status == 401:
                    logging.error(
                        f"[CONFIRM] 401 Unauthorized{message} — Authentication failed."
                    )
                    raise ReservationConfirmationConflict(
                        "🚫 Reservation already confirmed!"
                    ) from e
                else:
                    logging.error(f"[CONFIRM] HTTP error: {status} - {repr(e)}")
                    raise

            except httpx.ReadTimeout as e:
                logging.warning(
                    f"[CONFIRM] Timeout on attemptz{message} {attempt + 1} – {repr(e)}"
                )
                await asyncio.sleep(1 + attempt * 0.5)
                continue  # retry after timeout

            except httpx.RequestError as e:
                logging.error(
                    f"[CONFIRM] Request error{message}: {type(e).__name__} - {repr(e)}"
                )
                raise
            except Exception as e:
                logging.exception(
                    f"[CONFIRM] Unexpected error: {type(e).__name__} - {repr(e)}"
                )
                raise

        raise RuntimeError(
            f"[CONFIRM] Gave up after max retries{message} — booking code not found."
        )


async def _solve_recaptcha(record: dict | None = None) -> str:
    api_key = os.getenv("CAPTCHA_API_KEY")
    site_key = os.getenv("CAPTCHA_SITE_KEY")
    page_url = os.getenv("CAPTCHA_PAGE_URL")
    message = f" for ID {record['id']}" if record and record.get("id") else ""
    if not api_key or not site_key or not page_url:
        logging.error(
            f"[CAPTCHA] ❌ Missing configuration (API key/site key/page URL){message}."
        )
        raise ValueError("Captcha configuration missing!")

    async with httpx.AsyncClient(timeout=30.0) as client:
        start = time.perf_counter()
        logging.info(f"[CAPTCHA] 🧩 Submitting solve task{message}.")
        submit_resp = await client.post(
            "https://api.2captcha.com/createTask",
            json={
                "clientKey": api_key,
                "task": {
                    "type": "RecaptchaV2TaskProxyless",
                    "websiteURL": page_url,
                    "websiteKey": site_key,
                    "isInvisible": True,
                },
            },
        )
        submit_resp.raise_for_status()
        submit_data = submit_resp.json()
        if submit_data.get("errorId") != 0:
            logging.error(
                f"[CAPTCHA] ❌ Task submit failed{message}: {submit_data.get('errorDescription')}"
            )
            raise RuntimeError(
                f"Captcha submit failed: {submit_data.get('errorDescription')}"
            )
        captcha_id = submit_data.get("taskId")
        logging.info(f"[CAPTCHA] 🧩 Task created{message}: {captcha_id}")

        for _ in range(5):
            await asyncio.sleep(7)
            result_resp = await client.post(
                "https://api.2captcha.com/getTaskResult",
                json={
                    "clientKey": api_key,
                    "taskId": captcha_id,
                },
            )
            result_resp.raise_for_status()
            result_data = result_resp.json()
            if result_data.get("status") == "ready":
                solution = result_data.get("solution", {})
                token = solution.get("gRecaptchaResponse")
                if token:
                    duration = time.perf_counter() - start
                    logging.info(
                        f"[CAPTCHA] ✅ Solve ready{message} in {duration:.2f}s."
                    )
                    return token
                logging.error(f"[CAPTCHA] ⚠️ Solve ready but token missing{message}.")
                raise RuntimeError("Captcha solve returned no token")
            if result_data.get("status") != "processing":
                logging.error(
                    f"[CAPTCHA] ❌ Solve failed{message}: {result_data.get('errorDescription')}"
                )
                raise RuntimeError(
                    f"Captcha solve failed: {result_data.get('errorDescription')}"
                )
            logging.info(f"[CAPTCHA] ⏳ Still processing{message}; retrying.")

    duration = time.perf_counter() - start
    logging.error(f"[CAPTCHA] ⏱️ Solve timed out{message} after {duration:.2f}s.")
    raise TimeoutError("Captcha solve timed out")


async def cancel_reservation(
    codice: str, booking_code: str, mode: str = "delete"
) -> dict:
    url = f"https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/{mode}/{booking_code}?chiave={codice}"

    payload = {"type": "libera_posto"} if mode == "update" else None
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logging.info(f"Reservation canceled. mode: {mode}")
            return response.json()

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 400:
                logging.error(
                    "[CANCEL] 400 Bad Request: Possibly invalid booking code or expired reservation"
                )
                raise RuntimeError(
                    "Possibly invalid booking code or expired reservation"
                ) from e
            elif status == 404:
                logging.error("[CANCEL] 404 Not found: Cancel slot not found (?).")
                raise FileNotFoundError("Cancel slot not found (?).") from e
            elif status == 409:
                logging.error(
                    "[CANCEL] 409 Conflict: Another process may be modifying the reservation."
                )
                raise RuntimeError("Conflict during cancellation") from e
            else:
                logging.error(f"[CANCEL] HTTP error: {status} — {e.response.text}")
                raise RuntimeError(f"HTTP error during cancellation: {status}") from e

        except httpx.ReadTimeout as e:
            logging.error(
                f"[CANCEL] Timeout: Server took too long to respond – {repr(e)}"
            )
            raise TimeoutError("Cancellation request timed out") from e

        except httpx.RequestError as e:
            logging.error(f"[CANCEL] Network error: {type(e).__name__} - {repr(e)}")
            raise ConnectionError("Network error during cancellation") from e

        except Exception as e:
            logging.exception(
                f"[CANCEL] Unexpected error: {type(e).__name__} - {repr(e)}"
            )
            raise RuntimeError("Unexpected cancellation error") from e


async def get_available_slots(
    hour: str, filter_past: bool = True, max_retries: int = 4
) -> dict:
    now = datetime.now(ZoneInfo("Europe/Rome"))
    today = str(now.date())
    url = f"https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/50/schedule/{today}/25/{hour}"

    start_time = time.perf_counter()
    async with httpx.AsyncClient(verify=False) as client:
        for attempt in range(max_retries):
            timeout = calculate_timeout(retries=attempt, base=40, step=20, max_read=100)

            try:
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                response_data: dict = response.json()
                schedule = response_data.get("schedule")

                duration = time.perf_counter() - start_time
                logging.info(
                    f"[SLOT] Slots fetched in {duration:.2f}s on attempt {attempt + 1}"
                )

                if len(schedule) == 0:
                    return schedule
                else:
                    return extract_available_seats(
                        schedule=schedule[today], filter_past=filter_past
                    )

            except httpx.ReadTimeout as e:
                duration = time.perf_counter() - start_time
                logging.warning(
                    f"[SLOT] Timeout on attempt {attempt + 1} after {duration:.2f}s – {repr(e)}"
                )
                await asyncio.sleep(1 + attempt * 0.5)
                continue

            except httpx.RequestError as e:
                logging.error(f"[SLOT] Request failed: {type(e).__name__} - {repr(e)}")
                raise ConnectionError("Network error during reservation") from e

            except ValueError as e:
                logging.error(f"[SLOT] Value error: {type(e).__name__} - {e}")
                raise

            except Exception as e:
                logging.exception(
                    f"[SLOT] Unexpected error: {type(e).__name__} - {repr(e)}"
                )
                raise

        duration = time.perf_counter() - start_time
        raise RuntimeError(
            f"[SLOT] Gave up after {duration:.2f}s — could not fetch data."
        )
