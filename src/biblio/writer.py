import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.access import get_wks


async def writer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheet_env = context.bot_data.get('sheet_env')
    auth_mode = context.bot_data.get('auth_mode')

    unique_id = str(uuid.uuid4())
    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')
    context.user_data['updated_at'] = (
        datetime.now(ZoneInfo('Europe/Rome'))
        if context.user_data.get('updated_at') is None
        else context.user_data.get('updated_at')
    )
    instant = str(context.user_data.get('instant'))
    status_change = 'False'
    notified = 'False' if context.user_data.get('notified') is None else context.user_data.get('notified')
    chat_id = (
        'NA'
        if context.bot_data['user_chat_ids'].get(context.user_data['codice_fiscale']) is None
        else context.bot_data['user_chat_ids'].get(context.user_data['codice_fiscale'])
    )

    values = [
        unique_id,
        chat_id,
        context.user_data['username'],
        context.user_data['user_firstname'],
        context.user_data['user_lastname'],
        context.user_data['codice_fiscale'],
        context.user_data['priority'],
        context.user_data['name'],
        context.user_data['email'],
        context.user_data['selected_date'],
        start_time,
        end_time,
        context.user_data['selected_duration'],
        context.user_data['booking_code'],
        context.user_data['created_at'],
        context.user_data['retries'],
        context.user_data['status'],
        context.user_data['updated_at'],
        instant,
        status_change,
        notified,
    ]
    values = list(map(str, values))
    get_wks(sheet_env, auth_mode).append_table(values=values, start='A1', overwrite=False)
    logging.info(f'✔️ {update.effective_user} data successfully added at {datetime.now(ZoneInfo("Europe/Rome"))}')
