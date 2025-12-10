import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pandas import DataFrame
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import Status
from src.biblio.db.fetch import fetch_user_reservations


def validate_email(email: str) -> bool:
    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(email_pattern, email))


def validate_codice_fiscale(codice_fiscale: str) -> bool:
    codice_pattern = r"^[A-Za-z]{6}\d{2}[A-Za-z]\d{2}[A-Za-z]\d{3}[A-Za-z]$"
    return bool(re.match(codice_pattern, codice_fiscale))


def validate_user_data(user_data: dict):
    required_fields = ["codice_fiscale", "cognome_nome", "email"]
    for field in required_fields:
        if field not in user_data or not user_data[field]:
            raise ValueError(f"Missing or empty field: {field}")

    codice_fiscale = user_data.get("codice_fiscale")
    if not codice_fiscale or not validate_codice_fiscale(codice_fiscale):
        raise ValueError("Invalid codice fiscale format.")

    email = user_data.get("email")
    if not email or not validate_email(email):
        raise ValueError("Invalid email format. Please provide a valid email address.")

    logging.info("User data validated successfully.")


def normalize_slot_input(hour: str) -> str | None:
    hour = hour.strip()

    if re.fullmatch(r"\d{1,2}", hour):
        h = int(hour)
        return f"{h:02}:00" if 0 <= h < 24 else None

    if re.fullmatch(r"\d{1,2}:\d{1,4}", hour):
        h_str, m_str = hour.split(":")
        try:
            h = int(h_str)
            m = int(m_str)

            if not (0 <= h < 24):
                return None

            if m >= 60:
                return None
            if m < 0:
                return None

            return f"{h:02}:{m:02}"
        except ValueError:
            return None

    return None


async def duration_overlap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    codice = context.user_data["codice_fiscale"]
    email = context.user_data["email"]
    selected_date = context.user_data["selected_date"]
    history: DataFrame = await fetch_user_reservations(
        codice, email, selected_date, include_date=True
    )
    if len(history) == 0:
        return False

    reserving_start = datetime.strptime(context.user_data["selected_time"], "%H:%M")
    reserving_end = reserving_start + timedelta(hours=int(update.message.text.strip()))
    for _, row in history.iterrows():
        existing_start = datetime.strptime(row["start_time"].strftime("%H:%M"), "%H:%M")
        existing_end = datetime.strptime(row["end_time"].strftime("%H:%M"), "%H:%M")
        if row["status"] in (Status.TERMINATED, Status.CANCELED):
            continue
        if reserving_start < existing_end and reserving_end > existing_start:
            return True
    return False


async def time_not_overlap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    codice = context.user_data["codice_fiscale"]
    email = context.user_data["email"]
    selected_date = context.user_data["selected_date"]
    history: DataFrame = await fetch_user_reservations(
        codice, email, selected_date, include_date=True
    )
    input = update.message.text.strip()
    reserving_start = datetime.strptime(input, "%H:%M").replace(
        tzinfo=ZoneInfo("Europe/Rome")
    )
    for _, row in history.iterrows():
        existing_start = datetime.strptime(
            row["start_time"].strftime("%H:%M"), "%H:%M"
        ).replace(tzinfo=ZoneInfo("Europe/Rome"))
        existing_end = datetime.strptime(
            row["end_time"].strftime("%H:%M"), "%H:%M"
        ).replace(tzinfo=ZoneInfo("Europe/Rome"))
        if row["status"] in (Status.TERMINATED, Status.CANCELED):
            continue
        if (
            reserving_start >= existing_start - timedelta(minutes=30)
            and reserving_start < existing_end
        ):
            return False
    return True
