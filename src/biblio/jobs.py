import asyncio
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiocron
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pygsheets import Worksheet
from telegram import Bot

from src.biblio.bot.messages import show_notification
from src.biblio.config.config import ReservationConfirmationConflict, Schedule, get_wks
from src.biblio.db.fetch import claim_reservations, fetch_all_reservations
from src.biblio.db.insert import insert_slots
from src.biblio.db.update import sweep_stuck_reservations, update_record
from src.biblio.reservation.reservation import (
    calculate_timeout,
    confirm_reservation,
    get_available_slots,
    set_reservation,
)
from src.biblio.reservation.slot_datetime import reserve_datetime
from src.biblio.utils.notif import (
    notify_donation,
    notify_reminder,
    notify_reservation_activation,
)

JOB_SCHEDULE = Schedule.jobs(daylight_saving=True)
SEMAPHORE_LIMIT = 5
semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)


async def process_reservation(record: dict, bot: Bot) -> dict:
    chat_id = record.get("chat_id")
    user = {
        "codice_fiscale": record["codice_fiscale"],
        "cognome_nome": record["name"],
        "email": record["email"],
    }
    retries = int(record["retries"])
    process_start = time.perf_counter()

    if _is_stale_fail(record):
        return await _finalize(record, "terminated", "CLOSED", retries, chat_id, bot)

    reserve_start = time.perf_counter()
    start, end, duration = await _reserve_phase(record)
    logging.info(
        f"[JOB] 1️⃣ ⏱️ Reserve phase took {time.perf_counter() - reserve_start:.2f}s for ID {record['id']}"
    )
    if start is None:
        return await _finalize(
            record, "fail", record["booking_code"], retries + 1, chat_id, bot
        )

    set_start = time.perf_counter()
    booking_code, entry, set_status = await _set_phase(
        record, start, end, duration, user, retries
    )
    logging.info(
        f"[JOB] 2️⃣ ⏱️ Set phase took {time.perf_counter() - set_start:.2f}s for ID {record['id']}"
    )
    if set_status:  # existing/fail/terminated decided in set phase
        result = await _finalize(
            record,
            set_status,
            booking_code,
            retries + (set_status == "fail"),
            chat_id,
            bot,
        )
        process_end = time.perf_counter()
        logging.info(
            f"[JOB] 🕒 Process for ID {record['id']} took {process_end - process_start:.2f}s"
        )
        return result

    await asyncio.sleep(1)

    confirm_start = time.perf_counter()
    confirm_status = await _confirm_phase(record, entry, retries)
    if confirm_status == "fail":
        confirm_status = "awaiting"

    logging.info(
        f"[JOB] 3️⃣ ⏱️ Confirm phase took {time.perf_counter() - confirm_start:.2f}s for ID {record['id']}"
    )
    result = await _finalize(
        record,
        confirm_status,
        booking_code,
        retries + (confirm_status == "fail"),
        chat_id,
        bot,
    )
    process_end = time.perf_counter()
    logging.info(
        f"[JOB] 🕒 Process for ID {record['id']} took {process_end - process_start:.2f}s"
    )
    return result


async def _reserve_phase(record: dict) -> tuple[int | None, int | None, int | None]:
    try:
        return reserve_datetime(
            record["selected_date"].strftime("%Y-%m-%d"),
            record["start_time"].strftime("%H:%M"),
            int(record["selected_duration"]),
        )
    except Exception as e:
        logging.error(f"[JOB] ❌ Reserve failed for ID {record['id']}: {e}")
        return None, None, None


async def _set_phase(
    record: dict, start: int, end: int, duration: int, user: dict, retries: int
) -> tuple[str | None, str | None, str | None]:
    """
    Attempt to create the reservation entry.
    Returns a tuple of (booking_code, entry, set_status) where:
    - booking_code: user-facing code (may be None if request failed or not returned yet)
    - entry: code required for confirm_reservation (None on failure)
    - set_status: None on success so caller can proceed to confirm; otherwise a terminal status
      like "existing", "fail", or "terminated" to short-circuit the flow.
    """
    booking_code = record.get("booking_code")  # may be None
    entry = None
    try:
        resp = await set_reservation(
            start, end, duration, user, calculate_timeout(retries)
        )
        booking_code = resp.get("codice_prenotazione")
        entry = resp.get("entry")
        logging.info(f"[JOB] 2️⃣✅ Reservation set for ID {record['id']}")
        return booking_code, entry, None
    except ReservationConfirmationConflict as e:
        logging.error(
            f"[JOB] 2️⃣ ❌ Already confirmed during set for ID {record['id']}: {e}"
        )
        return booking_code or "UNKNOWN", entry, "existing"
    except TimeoutError as e:
        logging.warning(f"[JOB] 2️⃣⚠️ Set timed out for ID {record['id']}: {e}")
        return booking_code, entry, "fail"
    except Exception as e:
        logging.error(f"[JOB] 2️⃣ ❌ Set failed for ID {record['id']}: {e}")
        return booking_code, entry, ("terminated" if retries + 1 > 20 else "fail")


async def _confirm_phase(record: dict, entry: str | None, retries: int) -> str:
    if not entry:
        logging.error(
            f"[JOB] 3️⃣ ❌ No entry code available for confirm on ID {record['id']}"
        )
        return "fail"
    try:
        await confirm_reservation(entry)
        logging.info(f"[JOB] 3️⃣✅ Confirmed for ID {record['id']}")
        return "success"
    except ReservationConfirmationConflict:
        logging.warning(
            f"[JOB] 3️⃣ ⚠️ Confirm conflict (already confirmed) for ID {record['id']}"
        )
        return "existing"
    except TimeoutError as e:
        logging.warning(f"[JOB] 3️⃣ ⚠️ Confirm timed out for ID {record['id']}: {e}")
        return "fail"
    except Exception as e:
        logging.error(f"[JOB] 3️⃣ ❌ Confirm failed for ID {record['id']}: {e}")
        return "terminated" if retries + 1 > 20 else "fail"


def _is_stale_fail(record: dict) -> bool:
    if record["status"] not in ("fail", "awaiting", "processing"):
        return False
    scheduled_dt = datetime.combine(
        record["selected_date"], record["start_time"]
    ).replace(tzinfo=ZoneInfo("Europe/Rome"))
    return scheduled_dt + timedelta(minutes=30) < datetime.now(ZoneInfo("Europe/Rome"))


async def _finalize(record, status, booking_code, retries, chat_id, bot: Bot) -> dict:
    old_status = record["status"]
    status_changed = status != old_status
    result = {
        "id": record["id"],
        "status": status,
        "booking_code": booking_code,
        "retries": retries,
        "status_change": status_changed,
        "updated_at": datetime.now(ZoneInfo("Europe/Rome")),
    }

    if chat_id and _should_notify(old_status, status, retries):
        notif = show_notification(status, record, booking_code)
        try:
            await bot.send_message(chat_id=chat_id, text=notif, parse_mode="Markdown")
        except Exception as e:
            logging.error(
                f"[NOTIF] Failed to notify chat_id {chat_id} for ID {record['id']}: {e}"
            )
    return result


# TODO: drop old_status in case of no new development
def _should_notify(old_status: str, new_status: str, retries: int) -> bool:
    if new_status in ("success", "existing", "terminated"):
        return True
    if new_status == "fail":
        return retries > 0 and retries % 11 == 0
    return False


async def throttled_process_reservation(record: dict, bot: Bot) -> dict:
    async with semaphore:
        return await process_reservation(record, bot)


async def execute_reservations(bot: Bot) -> None:
    records: list[dict] = await claim_reservations(limit=SEMAPHORE_LIMIT * 2)
    if not records:
        logging.info("[DB-JOB] No pending reservations to process")
        return
    tasks = [throttled_process_reservation(record, bot) for record in records]
    updates = await asyncio.gather(*tasks)
    await asyncio.gather(
        *(
            update_record(
                "reservations", r["id"], {k: v for k, v in r.items() if k != "id"}
            )
            for r in updates
        )
    )  # Skip the first value since it is an ID
    logging.info(f"[DB-JOB] Reservation job completed: {len(updates)} updated")


async def backup_reservations() -> None:
    df = await fetch_all_reservations()
    if df.empty:
        logging.info("[GSHEET] No data to write to the sheet")
        return

    wks: Worksheet = get_wks()
    wks.clear(start="A1")
    wks.set_dataframe(df, (1, 1))
    logging.info("[GSHEET] Data written to Google Sheet successfully")


async def execute_slot_snapshot() -> None:
    all_slots = await get_available_slots("3600", filter_past=False)  # one-hour slots

    if not all_slots:
        logging.info("[DB-JOB] No slots to insert — snapshot skipped")
        return

    await insert_slots(all_slots)
    logging.info("[DB-JOB] Snapshot saved!")


def schedule_reserve_job(bot: Bot) -> None:
    scheduler = AsyncIOScheduler(timezone="Europe/Rome")
    start, end = JOB_SCHEDULE.get_hours("weekday")  # UTC hours
    trigger = CronTrigger(
        second="*/10",
        minute="0,1,2,3,30,31,32,33",
        hour=f"{start}-{end}",
        day_of_week="mon-fri",
    )
    scheduler.add_job(execute_reservations, trigger, args=[bot])

    trigger = CronTrigger(
        second="*/20",
        minute="5,7,10,12,15,17,20",
        hour=start,
        day_of_week="mon-fri",
    )
    scheduler.add_job(execute_reservations, trigger, args=[bot])

    start, end = JOB_SCHEDULE.get_hours("sat")
    trigger_sat = CronTrigger(
        second="*/10",
        minute="0,1,2,3,30,31,32,33",
        hour=f"{start}-{end}",
        day_of_week="sat",
    )
    scheduler.add_job(execute_reservations, trigger_sat, args=[bot])

    start, end = JOB_SCHEDULE.get_hours("sun")
    trigger_sun = CronTrigger(
        second="*/20",
        minute="0,1,2,3,30,31,32,33",
        hour=f"{start}-{end}",
        day_of_week="sun",
    )
    scheduler.add_job(execute_reservations, trigger_sun, args=[bot])

    scheduler.start()


def schedule_slot_snapshot_job() -> None:
    scheduler = AsyncIOScheduler(timezone="Europe/Rome")

    start, end = JOB_SCHEDULE.get_hours("availability")
    trigger = CronTrigger(
        second="*/10",
        minute="0,1,2,30,31,32",
        hour=f"{start}-{end}",
        day_of_week="mon-fri",
    )
    scheduler.add_job(execute_slot_snapshot, trigger)

    trigger = CronTrigger(
        second="*/45",
        minute="5,10,15,25,35,36,38,40,42,45,55,57,59",
        hour=f"{start}-{end}",
        day_of_week="mon-fri",
    )
    scheduler.add_job(execute_slot_snapshot, trigger)

    trigger = CronTrigger(
        second="*/25",
        minute="11,13,14,17,19,20,21,22,23,27,29,50",
        hour=f"{start}",
        day_of_week="mon-fri",
    )
    scheduler.add_job(execute_slot_snapshot, trigger)

    start, end = JOB_SCHEDULE.get_hours("availability_sat")
    trigger_sat = CronTrigger(
        second="*/15", minute="0,1,2,30,31", hour=f"{start}-{end}", day_of_week="sat"
    )
    scheduler.add_job(execute_slot_snapshot, trigger_sat)

    trigger_sun = CronTrigger(
        second="*/15", minute="0,1,2,30,31", hour=f"{start}-{end}", day_of_week="sun"
    )
    scheduler.add_job(execute_slot_snapshot, trigger_sun)

    scheduler.start()


def schedule_backup_job() -> None:
    @aiocron.crontab("*/1 * * * *", tz=ZoneInfo("Europe/Rome"))
    async def _backup_job():
        logging.info("[GSHEET] Starting Google Sheets backup")
        await backup_reservations()


def schedule_reminder_job(bot: Bot) -> None:
    @aiocron.crontab("30 23 * * 0-5", tz=ZoneInfo("Europe/Rome"))
    async def _reminder_job():
        logging.info("[NOTIF] Sending reminder notification")
        await notify_reminder(bot)


def schedule_activation_reminder_job(bot: Bot) -> None:
    @aiocron.crontab("15,45 8-21 * * 0-5", tz=ZoneInfo("Europe/Rome"))  # Sun - Fri
    async def _reminder_activation_job():
        logging.info("[NOTIF] Sending slot activation reminder notification")
        await notify_reservation_activation(bot)


def schedule_donation_reminder_job(bot: Bot) -> None:
    @aiocron.crontab("0 18 * * 1,3,5", tz=ZoneInfo("Europe/Rome"))  # Mon, Wed & Fri
    async def _reminder_donation_job():
        logging.info("[NOTIF] Sending donation reminder notification")
        await notify_donation(bot)


def schedule_sweeper_job() -> None:
    @aiocron.crontab("*/5 * * * *", tz=ZoneInfo("Europe/Rome"))
    async def _sweeper():
        await sweep_stuck_reservations()


def start_jobs(bot: Bot) -> None:  #! except reservation
    schedule_backup_job()
    schedule_reminder_job(bot)
    schedule_activation_reminder_job(bot)
    schedule_donation_reminder_job(bot)
    schedule_slot_snapshot_job()
