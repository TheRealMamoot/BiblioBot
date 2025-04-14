from datetime import datetime, timedelta
from enum import IntEnum, auto
import json
import logging
import os
import threading
import uuid

from dotenv import load_dotenv
from pandas import DataFrame
import pygsheets
from pygsheets import Worksheet
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, CallbackContext, filters
import textwrap
from zoneinfo import ZoneInfo

import utils
from jobs import run_reserve_job, run_notify_job
from reservation import set_reservation, confirm_reservation, cancel_reservation
from slot_datetime import reserve_datetime
from validation import validate_email, validate_codice_fiscale, duration_overlap, time_not_overlap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Env Vars

# ~Local~
# with open(os.path.join(os.getcwd(), 'priorities.json'), 'r') as f:
#     PRIORITY_CODES = json.load(f)  # NOT json.loads
# gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'biblio.json'))

# ~Global~
PRIORITY_CODES: dict = os.environ['PRIORITY_CODES']
PRIORITY_CODES = json.loads(PRIORITY_CODES)
gc =  pygsheets.authorize(service_account_json=os.environ['GSHEETS']) 

# ~Data Location~
wks: Worksheet = gc.open('Biblio-logs').worksheet_by_title('logs')
# wks: Worksheet = gc.open('Biblio-logs').worksheet_by_title('tests') # Only for tests. Must be commented.

load_dotenv()
# TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TOKEN: str = os.getenv('TELEGRAM_TOKEN') # Staging environmet. Commented by default

# States
class States(IntEnum):
    AGREEMENT = auto()
    CREDENTIALS = auto()
    RESERVE_TYPE = auto()
    CHOOSING_DATE = auto()
    CHOOSING_TIME = auto()
    CHOOSING_DUR = auto()
    CONFIRMING = auto()
    CANCELATION_SLOT_CHOICE = auto()
    CANCELATION_CONFIRMING = auto()
    RETRY = auto()

user_chat_ids = {}

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        textwrap.dedent(
        """
        *📄 User Agreement*
        *📣 Data Usage Notice*

        ❗ By using this bot, you agree to the collection and temporary storage of the following *data*:

        📌 Your *Telegram username*, *first name*, and *last name* (if available)
        📌 Your provided *Codice Fiscale*, *full name*, and *email address*
        📌 Your selected *reservation date*, *time*, and *duration* at Università degli Studi di Milano's Library of Biology, Computer Science, Chemistry and Physics (*BICF*)
        📌 The *status* of your reservation (*active* or *cancelled*) 
        📌 *General activity data*, including your *interactions* with the bot during the reservation process

        ❕ This data is used *exclusively* for making and managing *BICF reservations* more easily on your behalf.
        ❕ Your data is *never shared* with third parties and is used solely to assist with *reservation automation* and *troubleshooting*.

        🤝🏻 By continuing to use this bot, you *agree to these terms*.
        """
        ),
        parse_mode='Markdown', 
        reply_markup=utils.generate_agreement_keyboard()
    )
    return States.AGREEMENT

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        utils.show_help(),
        parse_mode='Markdown'
    )

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        utils.show_support_message(),
        parse_mode='Markdown'
    )

# Handlers
async def user_agreement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == "👎 No, I don't agree.":
        await update.message.reply_text(
            "Sorry to see you go! Hope you change your mind. Use /start again in case you do.",
            reply_markup=ReplyKeyboardRemove()
        ),
        return ConversationHandler.END

    elif user_input == "👍 Yes, I agree.":
        user = update.effective_user
        name = user.first_name if user.first_name else user.username
        context.user_data['username'] = user.username
        context.user_data['user_firstname'] = user.first_name
        context.user_data['user_lastname'] = user.last_name
        logging.info(f"{user} started chat at {datetime.now(ZoneInfo('Europe/Rome'))}")

        user_input = update.message.text.strip()

        gif_url = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ2F6cWowaG5oYjdkejhqamQxaWJ5bmxhcXQxY2w5azhieGlkZWwyNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xTiIzJSKB4l7xTouE8/giphy.gif' 
        await update.message.reply_animation(gif_url)
        await update.message.reply_text(
            textwrap.dedent(
                f"""
                Ciao *{name}*! 
                👋 The name's *Biblio*.
                I'm here to make your BICF reservations because you're too lazy and disorganized to do it yourself. 📚

                First, tell me who exactly you are. I will need: 
                your _Codice Fiscale_, _Full Name_, and _Email_.

                E.g. 
                *ABCDEF12G34H567I*, 
                *Mamoot Real*, 
                *brain@rot.com*

                📌_Comma placement matters. Spacing does not._

                Shouldn't be too hard.
                """
            ),
            parse_mode='Markdown',
            reply_markup=utils.generate_start_keyboard()
        )
        return States.CREDENTIALS
    
    else:
        await update.message.reply_text(
            "Please agree to the terms."
        )
        return States.AGREEMENT

async def user_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        await update.message.reply_text('Sure, waste your time why not? I can do this all day. 🥱')
        return States.CREDENTIALS
    
    user_input = update.message.text.strip()
    name = update.effective_user.first_name if update.effective_user.first_name else update.effective_user.username

    if user_input == "🤝 Reach out!":
        await update.message.reply_text(
            utils.show_support_message(),
            parse_mode='Markdown', 
            reply_markup=utils.generate_start_keyboard()
        )
        return States.CREDENTIALS
    
    if user_input == "❓ Help":
        await update.message.reply_text(
            utils.show_help(),
            parse_mode='Markdown', 
            reply_markup=utils.generate_start_keyboard()
        )
        return States.CREDENTIALS
    
    if user_input == "➡️ Changed my mind.":
        await update.message.reply_text(
        'Gotta be kidding me! 😑',
            parse_mode='Markdown', 
            reply_markup=utils.generate_reservation_type_keyboard()
        )
        return States.RESERVE_TYPE

    try:
        codice, name, email = [part.strip() for part in user_input.split(',')]
    except ValueError:
        await update.message.reply_text(
            "Wow so it WAS too hard for you. 🙃\nTry again: `Codice, Full Name, Email`",
            parse_mode='Markdown'
        )
        return States.CREDENTIALS
    
    if not validate_codice_fiscale(codice):
        await update.message.reply_text("🚫 Nice try with a fake codice fiscale. Try again!")
        return States.CREDENTIALS
    
    if not validate_email(email):
        await update.message.reply_text("🚫 Nice try with a fake email. Try again!")
        return States.CREDENTIALS

    context.user_data['codice_fiscale'] = codice.upper()
    context.user_data['name'] = name
    context.user_data['email'] = email.lower()
    context.user_data['priority'] = PRIORITY_CODES.get(codice.upper(), 2) # Default: 2. For everyone else
    user_chat_ids[context.user_data['codice_fiscale']] = update.effective_chat.id

    keyboard = utils.generate_reservation_type_keyboard()
    await update.message.reply_text(
                textwrap.dedent(
            f"""
            There we go! Your data is saved. FOREVER! 😈 (JUST KIDDING!)
            Now, you can plan ahead for later or,
            If you're so desperate and need a slot now, try to book instantly. No promises!
            """
        ),
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    logging.info(f"🔄 {update.effective_user} info validated at {datetime.now(ZoneInfo('Europe/Rome'))}")
    return States.RESERVE_TYPE

async def reservation_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    keyboard = utils.generate_reservation_type_keyboard()

    if user_input == '⬅️ Edit credentials':
        await update.message.reply_text(
                textwrap.dedent(
            f"""
            Messed it up already?! _sighs_
            your _Codice Fiscale_, _Full Name_, and _Email_.
            Example: 
            *ABCDEF12G34H567I*, 
            *Mamoot Real*, 
            *brain@rot.com*
            """
        ),
            parse_mode='Markdown', 
            reply_markup=utils.generate_start_keyboard(edit_credential_stage=True)
        )
        return States.CREDENTIALS

    elif user_input == '⏳ I need a slot for later.':
        keyboard = utils.generate_date_keyboard()
        await update.message.reply_text(
            'So, when will it be? 📅',
            reply_markup=keyboard
        )
        context.user_data['instant'] = False
        logging.info(f"🔄 {update.effective_user} selected REGULAR reservation at {datetime.now(ZoneInfo('Europe/Rome'))}")
        return States.CHOOSING_DATE

    elif user_input == '⚡️ I need a slot for now.':
        now = datetime.now(ZoneInfo('Europe/Rome'))
        now_day = now.strftime('%A')
        now_date = now.strftime('%Y-%m-%d')
        week_day = now.weekday()

        open_time = 9
        close_time = 22
        if week_day == 5:
            close_time = 13
        if now.hour < open_time or now.hour >= close_time:
            await update.message.reply_text(
                "It's over for today! Go home. 😌", 
                reply_markup=utils.generate_reservation_type_keyboard()
                )
            return States.RESERVE_TYPE

        if week_day == 6: #Sunday
            await update.message.reply_text(
                "It's Sunday! Come on, chill. 😌", 
                reply_markup=utils.generate_reservation_type_keyboard()
                )
            return States.RESERVE_TYPE
        
        date = f'{now_day}, {now_date}'
        await update.message.reply_text(
            'So, when will it be? 🕑',
            reply_markup=utils.generate_time_keyboard(date, instant=True)
        )
        context.user_data['instant'] = True
        context.user_data['selected_date'] = date
        logging.info(f"🔄 {update.effective_user} selected INSTANT reservation at {datetime.now(ZoneInfo('Europe/Rome'))}")
        return States.CHOOSING_TIME
    
    elif user_input == '🗓️ Current reservations':
        await update.message.reply_text(
            utils.show_existing_reservations(update, context, wks.get_as_df()),
            parse_mode='Markdown',
        )
        return States.RESERVE_TYPE
    
    elif user_input == '🚫 Cancel reservation':
        reservations = utils.show_existing_reservations(update, 
                                                        context, 
                                                        history=wks.get_as_df(), 
                                                        cancel_stage=True)
        choices = {}
        buttons = []

        if not isinstance(reservations, DataFrame):
            await update.message.reply_text(
                '_You have no reservations at the moment._',
                parse_mode='Markdown'
            )
            return States.RESERVE_TYPE
        
        for _, row in reservations.iterrows():
            if row['status'] == 'terminated':
                continue
            status = '🔄' if row['status']=='pending' else '⚠️' if row['status']=='fail' else '✅' if row['status']=='success' else ''
            button = f"{status} {row['selected_date']} at {row['start']} - {row['end']}"

            choices[f"{row['id']}"] = {
                'selected_date':row['selected_date'],
                'start':row['start'],
                'end':row['end'],
                'selected_dur':row['selected_dur'],
                'booking_code':row['booking_code'],
                'status':row['status'],
                'button':button
            }
            buttons.append(button)

        if len(buttons) == 0:
            await update.message.reply_text(
                '_You have no reservations at the moment._',
                parse_mode='Markdown'
            )
            return States.RESERVE_TYPE
        
        context.user_data['cancelation_choices'] = choices
        keyboard = utils.generate_cancelation_options_keyboard(buttons)

        logging.info(f"🔄 {update.effective_user} started cancelation at {datetime.now(ZoneInfo('Europe/Rome'))}")
        await update.message.reply_text(
                textwrap.dedent(
                    f"""
                    ❗ *Please make sure your reservation time has not ended*❗
                    🔄 *Pending*: Reservation will be processed when slots open.
                    ⚠️ *Failed*: Reservation request will be retried at :00 and :30 again.
                    ✅ *Success*: Reservation was succesful.

                    That being said, which one will it be?
                    """
                ),
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        return States.CANCELATION_SLOT_CHOICE
    
    elif user_input == "❓ Help":
        await update.message.reply_text(
            utils.show_help(),
            parse_mode='Markdown', 
            reply_markup=utils.generate_reservation_type_keyboard()
        )
        return States.RESERVE_TYPE

    else:
        await update.message.reply_text(
            "The options are right there you know. Pick one, that's it.",
            reply_markup=keyboard
        )
        return States.RESERVE_TYPE

async def date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️ Edit reservation type':
        await update.message.reply_text(
            'Fine, just be quick. 🙄',
            parse_mode='Markdown', 
            reply_markup=utils.generate_reservation_type_keyboard()
        )
        return States.RESERVE_TYPE
    
    elif user_input == '🗓️ Current reservations':
        await update.message.reply_text(
            utils.show_existing_reservations(update, context, wks.get_as_df()),
            parse_mode='Markdown',
        )
        return States.CHOOSING_DATE

    try:
        datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(
            'Umm, that does not look like a date to me. 🤨 Just pick one from the list.')
        return States.CHOOSING_DATE
    
    available_dates = utils.generate_days()
    available_dates = [datetime.strptime(date.split(' ')[-1], '%Y-%m-%d') for date in available_dates]

    if datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d') not in available_dates:
        await update.message.reply_text(
            '🚫 Not available! Choose again from the list.'
        )
        return States.CHOOSING_DATE
    
    context.user_data['selected_date'] = user_input
    keyboard = utils.generate_time_keyboard(user_input)
    
    if len(keyboard.keyboard) <= 1:
        await update.message.reply_text(
            'Oops! There are no available time slots for that date.\nCry about it ☺️. Choose another one.')
        return States.CHOOSING_DATE  
    
    await update.message.reply_text(
        f'Fine. You picked *{user_input}*.\nNow choose a starting time.',
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    logging.info(f"🔄 {update.effective_user} selected date at {datetime.now(ZoneInfo('Europe/Rome'))}")
    return States.CHOOSING_TIME

async def time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️':
        if context.user_data['instant']:
            await update.message.reply_text(
                    textwrap.dedent(
                f"""
                Just decide already!
                """
            ),
                parse_mode='Markdown', 
                reply_markup=utils.generate_reservation_type_keyboard()
            )
            return States.RESERVE_TYPE
        
        keyboard = utils.generate_date_keyboard()
        await update.message.reply_text('Choose a date, AGAIN! 😒', reply_markup=keyboard)
        return States.CHOOSING_DATE
    
    elif user_input == '🗓️ Current reservations':
        await update.message.reply_text(
            utils.show_existing_reservations(update, context, wks.get_as_df()),
            parse_mode='Markdown',
        )
        return States.CHOOSING_TIME
    
    try:
        datetime.strptime(user_input, '%H:%M')
        time_obj = datetime.strptime(user_input, '%H:%M').replace(tzinfo=ZoneInfo('Europe/Rome'))
        if (time_obj.hour + time_obj.minute / 60) < 9:
            await update.message.reply_text(
                    textwrap.dedent(
                f"""
                ⚠️ Starting time can't be before 09:00! 
                Choose a different time.
                """
            ))
            return States.CHOOSING_TIME
        
    except ValueError:
        await update.message.reply_text(
            'Not that difficult to pick an option form the list! Just saying. 🤷‍♂️')
        return States.CHOOSING_TIME
    
    if not time_not_overlap(update, context, wks.get_as_df()): 
        await update.message.reply_text(
                textwrap.dedent(
            f"""
            ⚠️ Your reservation overlaps with an existing one! 
            Choose a different time.
            """
        ))
        return States.CHOOSING_TIME

    context.user_data['selected_time'] = user_input
    keyboard = utils.generate_duration_keyboard(user_input, context)[0] # [0] for the reply, [1] for the values

    await update.message.reply_text(
        f'How long will you absolutely NOT be productive over there? 🕦 Give me hours.', reply_markup=keyboard)
    
    res_type = 'INSTANT' if context.user_data['instant'] else 'REGULAR'
    logging.info(f"🔄 {update.effective_user} selected {res_type} time at {datetime.now(ZoneInfo('Europe/Rome'))}")
    return States.CHOOSING_DUR

async def duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️':
        keyboard = utils.generate_time_keyboard(context.user_data.get('selected_date'), 
                                                instant=context.user_data['instant'])
        await update.message.reply_text(
            'Make up your mind! choose a time ALREADY 🙄', reply_markup=keyboard)
        return States.CHOOSING_TIME

    selected_time = context.user_data.get('selected_time')
    duration_selection = utils.generate_duration_keyboard(selected_time, context)[1] # [0] for the reply, [1] for the values
    max_dur = max(duration_selection)

    if not user_input.isdigit():
        await update.message.reply_text(
            "Now you're just messing with me. Just pick the duration!")
        return States.CHOOSING_DUR
    
    if int(user_input) > max_dur:
        await update.message.reply_text(
            "Well they are not going to let you sleep there! Try again. 🤷‍♂️")
        return States.CHOOSING_DUR
    
    if duration_overlap(update, context, wks.get_as_df()): 
        await update.message.reply_text(
                textwrap.dedent(
            f"""
            ⚠️ Your reservation overlaps with an existing one! 
            Choose a different duration.
            """
        ))
        return States.CHOOSING_DUR

    context.user_data['selected_duration'] = user_input
    res_type = 'INSTANT' if context.user_data['instant'] else 'REGULAR'
    logging.info(f"🔄 {update.effective_user} selected {res_type} duration at {datetime.now(ZoneInfo('Europe/Rome'))}")

    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')

    keyboard = utils.generate_confirmation_keyboard()
    await update.message.reply_text(
        textwrap.dedent(
            f"""
            All looks good?
            Codice Fiscale: *{context.user_data.get('codice_fiscale')}*
            Full Name: *{context.user_data.get('name')}*
            Email: *{context.user_data.get('email')}*
            On *{context.user_data.get('selected_date')}*
            From *{start_time}* - *{end_time}* (*{context.user_data.get('selected_duration')} Hours*)
            """
        ),
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return States.CONFIRMING

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
            'email': context.user_data['email']
        }
        request_status_message = f"📌 Registration for slot *successful*!"
        retry_status_message = f'‼️ Reservation request will be processed when slots *reset*. *Be patient!* you will be notified.'
        res_type = 'INSTANT' if context.user_data['instant'] else 'REGULAR'

        logging.info(f'✅ **1** {res_type} Slot identified for {user_data['cognome_nome']}')
        logging.info(f"{update.effective_user} request confirmed at {datetime.now(ZoneInfo('Europe/Rome'))}")
        context.user_data['created_at'] = datetime.now(ZoneInfo('Europe/Rome'))
        context.user_data['status'] = 'pending'
        context.user_data['booking_code'] = 'TBD'
        context.user_data['retries'] = '0'

        if context.user_data['instant']:
            try:
                reservation_response = set_reservation(start, end, duration, user_data)
                logging.info(f'✅ **2** {res_type} Reservation set for {user_data['cognome_nome']}')
                confirm_reservation(reservation_response['entry'])
                logging.info(f'✅ **3** {res_type} Reservation confirmed for {user_data['cognome_nome']}')
                context.user_data['status'] = 'success'
                context.user_data['booking_code'] = reservation_response['codice_prenotazione']
                context.user_data['updated_at'] = datetime.now(ZoneInfo('Europe/Rome'))
                context.user_data['notified'] = 'True'
                request_status_message = f"✅ Reservation *successful*!"
                retry_status_message=''

            except Exception as e:
                logging.error(f'❌ {res_type} Reservation failed for {user_data['cognome_nome']} — {e}')
                context.user_data['retries'] = '1'
                context.user_data['status'] = 'fail'
                context.user_data['booking_code'] = 'NA'
                context.user_data['updated_at'] = datetime.now(ZoneInfo('Europe/Rome'))
                request_status_message = f"⛔ Reservation *failed*! *Slot not available*."
                retry_status_message = f'‼️ *No need to try again!* I will automatically try to get it when slots open, unless the time for the requested slot *has passed*.'

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
            reply_markup=utils.generate_retry_keyboard()
        )

        await writer(update, context)
        return States.RETRY 

    elif user_input == '⬅️ No, take me back.':
        keyboard = utils.generate_duration_keyboard(context.user_data.get('selected_time'), context)[0]
        await update.message.reply_text(
            'I overestimated you it seems. Duration please. 😬',
            reply_markup=keyboard
        )
        return States.CHOOSING_DUR
    
    else:
        await update.message.reply_text(
            "JUST.CLICK...PLEASE!",
            reply_markup=utils.generate_confirmation_keyboard()
        )
        return States.CONFIRMING 
    
# Canelation
async def cancelation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️ Back to reservation type':
        await update.message.reply_text(
            'You are so determined, wow!',
            reply_markup=utils.generate_reservation_type_keyboard()
        )
        return States.RESERVE_TYPE

    choices: dict = context.user_data['cancelation_choices']
    cancelation_id = next((id for id, deatils in choices.items() if deatils['button'] == user_input), None)
    
    if not cancelation_id:
        await update.message.reply_text(
            "Pick from the list!",
        )
        return States.CANCELATION_SLOT_CHOICE 

    context.user_data['cancelation_chosen_slot_id'] = cancelation_id
    logging.info(f"🔄 {update.effective_user} selected cancelation slot at {datetime.now(ZoneInfo('Europe/Rome'))}")

    await update.message.reply_text(
        textwrap.dedent(
            f"""
            Are you sure you want to cancel this slot ?
            Codice Fiscale: *{context.user_data.get('codice_fiscale')}*
            Full Name: *{context.user_data.get('name')}*
            Email: *{context.user_data.get('email')}*
            On *{choices[cancelation_id]['selected_date']}*
            From *{choices[cancelation_id]['start']}* - *{choices[cancelation_id]['end']}* (*{choices[cancelation_id]['selected_dur']}* hours)
            Satus: *{(choices[cancelation_id]['status']).title()}*
            """
        ),
        parse_mode='Markdown',
        reply_markup=utils.generate_cancelation_confirm_keyboard()
    )
    return States.CANCELATION_CONFIRMING

async def cancelation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    if user_input == '⬅️ No, take me back.':
        choices: dict = context.user_data['cancelation_choices']
        reservation_buttons = [choice['button'] for choice in choices.values()]
        await update.message.reply_text(
            'God kill me now! 😭',
            reply_markup=utils.generate_cancelation_options_keyboard(reservation_buttons)
        )
        return States.CANCELATION_SLOT_CHOICE
    
    elif user_input == "📅❌ Yes, I'm sure.":
        history = wks.get_as_df()
        cancelation_chosen_slot_id: str = context.user_data['cancelation_chosen_slot_id']
        row_idx = history.index[history['id'] == cancelation_chosen_slot_id].tolist()
        faiulure = False
        if row_idx:
            booking_code = history.loc[row_idx,'booking_code'].values[0]
            if booking_code not in ['TBD','NA']:
                try:
                    cancel_reservation(context.user_data['codice_fiscale'], booking_code)
                except RuntimeError as e:
                    logging.error(f"🔄 {update.effective_user} cancelation was not completed at {datetime.now(ZoneInfo('Europe/Rome'))} -- {e}")
                    faiulure = True
                    await update.message.reply_text(
                        "⚠️ Something went wrong while canceling! The time of the slot has most likely passed or it was canceled manually by you.")

            sheet_row = row_idx[0] + 2  # +2 because: 1 for zero-based index, 1 for header row
            col_number = history.columns.get_loc('status') + 1 # 1-based for pygsheets 
            wks.update_value((sheet_row, col_number), 'terminated')
            col_number = history.columns.get_loc('notified') + 1 
            wks.update_value((sheet_row, col_number), 'True')
            col_number = history.columns.get_loc('status_change') + 1 
            wks.update_value((sheet_row, col_number), 'True')

            logging.info(f"✔️ {update.effective_user} confirmed cancelation at {datetime.now(ZoneInfo('Europe/Rome'))}")
            if not faiulure:
                await update.message.reply_text(
                    '✔️ Reservation canceled successfully!',
                    reply_markup=utils.generate_reservation_type_keyboard()
                )
            return States.RESERVE_TYPE

        else:
            logging.info(f"⚠️ {update.effective_user} cancelation slot NOT FOUND at {datetime.now(ZoneInfo('Europe/Rome'))}")
            await update.message.reply_text(
                '⚠️ Reservation cancelation usuccessfull!',
                reply_markup=utils.generate_reservation_type_keyboard()
            )
            return States.RESERVE_TYPE
        
    else:
        await update.message.reply_text(
            'Just click. Please! 😭',
        )
        return States.CANCELATION_CONFIRMING

# Retry   
async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == "🆕 Let's go again!":
        keyboard = utils.generate_date_keyboard()
        result = States.CHOOSING_DATE

        if context.user_data['instant']:
            keyboard = utils.generate_reservation_type_keyboard()
            result = States.RESERVE_TYPE

        await update.message.reply_text(
            'Ah ****, here we go again! 😪',
            reply_markup=keyboard
        )
        logging.info(f"⏳ {update.effective_user} reinitiated the process at {datetime.now(ZoneInfo('Europe/Rome'))}")
        return result
    
    elif user_input == "💡 Feedback":
        await update.message.reply_text(
        utils.show_support_message(),
        parse_mode='Markdown',
        )
        return States.RETRY

    elif user_input == '🗓️ Current reservations':
        await update.message.reply_text(
            utils.show_existing_reservations(update, context, wks.get_as_df()),
            parse_mode='Markdown',
        )
        return States.RETRY

    else:
        await update.message.reply_text(
        textwrap.dedent(
            f"""
            Off you go now, Bye. 😘
            Don't you dare /start again 😠!
            """
        ),
        parse_mode='Markdown',
        )
        return States.RETRY
    
# Writer
async def writer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    unique_id = str(uuid.uuid4())
    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')
    context.user_data['updated_at'] = datetime.now(ZoneInfo('Europe/Rome')) if context.user_data.get('updated_at') is None else context.user_data.get('updated_at')
    instant = str(context.user_data.get('instant'))
    status_change = 'False'
    notified = 'False' if context.user_data.get('notified') is None else context.user_data.get('notified')
    chat_id = 'NA' if user_chat_ids.get(context.user_data['codice_fiscale']) is None else user_chat_ids.get(context.user_data['codice_fiscale'])

    values=[
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
    notified
    ]
    values = list(map(str, values))
    wks.append_table(values=values, start='A1', overwrite=False)
    logging.info(f"✔️ {update.effective_user} data successfully added at {datetime.now(ZoneInfo('Europe/Rome'))}")

# Notif
async def send_reservation_update(context: CallbackContext):
    history = wks.get_as_df()
    for _, row in history.iterrows():
        codice = row['codice_fiscale']
        transaction_id = row['id']
        id = user_chat_ids.get(codice)

        if not id:
            continue 
        
        if row['notified']=='True':
            continue

        now = datetime.now(ZoneInfo('Europe/Rome'))
        today = datetime(year=now.year, month=now.month, day=now.day, tzinfo= ZoneInfo('Europe/Rome'))
        date = datetime.strptime(row['selected_date'].split(' ')[-1], '%Y-%m-%d').replace(tzinfo=ZoneInfo('Europe/Rome'))

        if row['status_change']=='True':
            if today > date:
                continue
            state = f"SUCCESFUL! ✅" if row['status']=='success' else f"TERMINATED! ❌" if row['status']=='terminated' else ''
            retry_message = f"❗️ _You should try reserving another slot. No more retries will be made for this slot!_" if row['status']=='terminated' else \
            f"❇️ _You should be able to go to the library now._" if row['status']=='success' else ''
            notification = textwrap.dedent(
                f"""
                Reservation for
                *{row['name']}*
                on: *{row['selected_date']}*
                at: *{row['start']}* - *{row['end']}* (*{row['selected_dur']}* *hours*)
                was *{state}*
                Booking Code: *{row['booking_code']}*
                {retry_message}
                """
            )
            utils.update_gsheet_data_point(history, transaction_id, 'notified', 'True', wks)
            await context.bot.send_message(chat_id=id, text=notification, parse_mode='Markdown')
            
# Misc
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hey! who or what do you think I am? 😑 use /start again if NOTHING is working.')

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Piano piano eh? use /start first.')

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update and hasattr(update, 'message'):
        await update.message.reply_text(
            "😵 Oops, something went wrong.\nTry /start to begin again.",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
    print(f'Update {update} caused error {context.error}')

async def post_init(application):
    run_notify_job(application, send_reservation_update)

# App
def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)], 
        states={
            States.AGREEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_agreement)],
            States.CREDENTIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_validation)],
            States.RESERVE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reservation_selection)],
            States.CHOOSING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_selection)],
            States.CHOOSING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_selection)],
            States.CHOOSING_DUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, duration_selection)],
            States.CONFIRMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmation)],
            States.CANCELATION_SLOT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancelation)],
            States.CANCELATION_CONFIRMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancelation_confirmation)],
            States.RETRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, retry)],
        },
        fallbacks=[
            CommandHandler('start', start), # Allows /start to reset everything
            CommandHandler('help', help),
            CommandHandler('feedback', feedback),
            MessageHandler(filters.ALL, fallback)
        ],
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help))
    app.add_handler(CommandHandler('feedback', feedback))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, restart))

    app.add_error_handler(error)
    threading.Thread(target=run_reserve_job, daemon=True).start()

    app.run_polling()

if __name__ == '__main__':
    main()