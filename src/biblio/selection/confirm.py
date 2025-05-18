import logging
import textwrap
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import States
from src.biblio.reservation.reservation import confirm_reservation, set_reservation
from src.biblio.reservation.slot_datetime import reserve_datetime
from src.biblio.utils import keyboards
from src.biblio.writer import writer


async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')
    date = context.user_data['selected_date'].split(' ')[-1]
    selected_dur = int(context.user_data['selected_duration'])
    start, end, duration = reserve_datetime(date, start_time, selected_dur)

    if user_input == '✅ Yes, all looks good.':
        user_data = {
            'codice_fiscale': context.user_data['codice_fiscale'],
            'cognome_nome': context.user_data['name'],
            'email': context.user_data['email'],
        }
        request_status_message = '📌 Registration for slot *successful*!'
        retry_status_message = (
            '‼️ Reservation request will be processed when slots *reset*. *Be patient!* you will be notified.'
        )
        res_type = 'INSTANT' if context.user_data['instant'] else 'REGULAR'

        logging.info(f'✅ **1** {res_type} Slot identified for {user_data["cognome_nome"]}')
        logging.info(f'{update.effective_user} request confirmed at {datetime.now(ZoneInfo("Europe/Rome"))}')
        context.user_data['created_at'] = datetime.now(ZoneInfo('Europe/Rome'))
        context.user_data['status'] = 'pending'
        context.user_data['booking_code'] = 'TBD'
        context.user_data['retries'] = '0'
        context.user_data['notified'] = 'False'

        if context.user_data['instant']:
            try:
                reservation_response = set_reservation(start, end, duration, user_data)
                logging.info(f'✅ **2** {res_type} Reservation set for {user_data["cognome_nome"]}')
                confirm_reservation(reservation_response['entry'])
                logging.info(f'✅ **3** {res_type} Reservation confirmed for {user_data["cognome_nome"]}')
                context.user_data['status'] = 'success'
                context.user_data['booking_code'] = f'{reservation_response["codice_prenotazione"]}'
                context.user_data['updated_at'] = datetime.now(ZoneInfo('Europe/Rome'))
                context.user_data['notified'] = 'True'
                request_status_message = '✅ Reservation *successful*!'
                retry_status_message = ''

            except Exception as e:
                logging.error(f'❌ {res_type} Reservation failed for {user_data["cognome_nome"]} — {e}')
                context.user_data['retries'] = '1'
                context.user_data['status'] = 'fail'
                context.user_data['booking_code'] = 'NA'
                context.user_data['updated_at'] = datetime.now(ZoneInfo('Europe/Rome'))
                request_status_message = '⛔ Reservation *failed*! *Slot not available*.'
                retry_status_message = '‼️ *No need to try again!* I will automatically try to get it when slots open, unless the time for the requested slot *has passed*.'

        await update.message.reply_text(
            textwrap.dedent(
                f"""
                    {request_status_message}
                    Requested at *{datetime.now(ZoneInfo('Europe/Rome')).strftime('%Y-%m-%d %H:%M:%S')}*

                    Codice Fiscale: *{context.user_data.get('codice_fiscale')}*
                    Full Name: *{context.user_data.get('name')}*
                    Email: *{context.user_data.get('email')}*
                    On: *{context.user_data.get('selected_date')}*
                    From: *{start_time}* - *{end_time}* (*{context.user_data.get('selected_duration')}* hours)
                    Booking Code: *{context.user_data['booking_code'].upper()}*
                    Reservation Type: *{res_type.title()}*
                    {retry_status_message}

                    Do you want to go for another slot?
                    """
            ),
            parse_mode='Markdown',
            reply_markup=keyboards.generate_retry_keyboard(),
        )

        await writer(update, context)
        return States.RETRY

    elif user_input == '⬅️ No, take me back.':
        keyboard = keyboards.generate_duration_keyboard(context.user_data.get('selected_time'), context)[0]
        await update.message.reply_text('I overestimated you it seems. Duration please. 😬', reply_markup=keyboard)
        return States.CHOOSING_DUR

    else:
        await update.message.reply_text(
            'JUST.CLICK...PLEASE!',
            reply_markup=keyboards.generate_confirmation_keyboard(),
        )
        return States.CONFIRMING
