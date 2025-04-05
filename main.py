from datetime import datetime, timedelta
import logging
import os

import numpy as np
import pygsheets
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
import textwrap

import utils
from validation import validate_email, validate_codice_fiscale

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# States
CREDENTIALS, RESERVE_TYPE, CHOOSING_DATE, CHOOSING_TIME, CHOOSING_DUR, CONFIRMING, RETRY = range(7)

TOKEN = os.getenv('TELEGRAM_TOKEN')

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    user = update.effective_user
    name = user.first_name if user.first_name else user.username
    context.user_data['user'] = name
    logging.info(f"User {user} started chat at {datetime.now()}")

    gif_url = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ2F6cWowaG5oYjdkejhqamQxaWJ5bmxhcXQxY2w5azhieGlkZWwyNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xTiIzJSKB4l7xTouE8/giphy.gif' 
    await update.message.reply_animation(gif_url)
    await update.message.reply_text(
        textwrap.dedent(
            f"""
            Ciao {name}! 👋 The name's *Biblio*.

            I'm here to make your biblioteca reservations because you're too lazy and disorganized to do it yourself. 📚

            First, tell me who exactly you are. I will need: 
             
            your _Codice Fiscale_, _Full Name_, and _Email_.

            Example: *ABCDEF12G34H567I*, *Mamoot Real*, *brain@rot.com*

            Shouldn't be too hard.
            """
        ),
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return CREDENTIALS

# Handlers
async def user_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        await update.message.reply_text('Sure, waste your time why not ? I can do this all day. 🥱')
        return CREDENTIALS
    
    user_input = update.message.text.strip()

    try:
        codice, name, email = [part.strip() for part in user_input.split(',')]
    except ValueError:
        await update.message.reply_text(
            "Wow so it WAS too hard for you. 🙃\nTry again: `Codice, Full Name, Email`",
            parse_mode='Markdown'
        )
        return CREDENTIALS
    
    if not validate_codice_fiscale(codice):
        await update.message.reply_text("🚫 Nice try with a fake codice fiscale. Try again!")
        return CREDENTIALS
    
    if not validate_email(email):
        await update.message.reply_text("🚫 Nice try with a fake email. Try again!")
        return CREDENTIALS

    context.user_data['codice_fiscale'] = codice
    context.user_data['name'] = name
    context.user_data['email'] = email

    keyboard = utils.generate_reservation_type_keyboard()
    await update.message.reply_text(
                textwrap.dedent(
            f"""
            There we go! Your data is saved. FOREVER! 😈
            Now, you can plan ahead for future days or,
            If you're so desperate and need a slot for today, try to book now. No promises!
            """
        ),
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    logging.info(f"User {update.effective_user} info validated at {datetime.now()}")
    return RESERVE_TYPE

async def reservation_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    keyboard = utils.generate_reservation_type_keyboard()

    if user_input == '⬅️ Edit credentials':
        await update.message.reply_text(
                textwrap.dedent(
            f"""
            Messed it up already ?! _sighs_
            your _Codice Fiscale_, _Full Name_, and _Email_.
            Example: *ABCDEF12G34H567I*, *Mamoot Real*, *brain@rot.com*
            """
        ),
            parse_mode='Markdown', 
            reply_markup=ReplyKeyboardRemove()
        )
        return CREDENTIALS
    
    elif user_input == '⏳ I need a slot for later.':
        keyboard = utils.generate_date_keyboard()
        await update.message.reply_text(
            'So, when will it be ? 📅',
            reply_markup=keyboard
        )
        logging.info(f"User {update.effective_user} selected slot at {datetime.now()}")
        return CHOOSING_DATE

    elif user_input == '⚡️ I need a slot for today.':
        await update.message.reply_text(
            '🔧 In development 🔧',
            reply_markup=keyboard
        )
        return RESERVE_TYPE
    
    else:
        await update.message.reply_text(
            "The options are right there you know. Pick one, that's it.",
            reply_markup=keyboard
        )
        return RESERVE_TYPE

async def date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️ Edit reservation':
        await update.message.reply_text(
            'Fine, just be quick. 🙄',
            parse_mode='Markdown', 
            reply_markup=utils.generate_reservation_type_keyboard()
        )
        return RESERVE_TYPE

    try:
        datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(
            'Umm, that does not look like a date to me. 🤨 Just pick one from the list.')
        return CHOOSING_DATE
    
    available_dates = utils.generate_days()
    available_dates = [datetime.strptime(date.split(' ')[-1], '%Y-%m-%d') for date in available_dates]

    if datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d') not in available_dates:
        await update.message.reply_text(
            '🚫 Not available! Choose again from the list.'
        )
        return CHOOSING_DATE
    
    context.user_data['selected_date'] = user_input
    keyboard = utils.generate_time_keyboard(user_input)
    
    if len(keyboard.keyboard) <= 1:
        await update.message.reply_text(
            'Oops! There are no available time slots for that date.\nCry about it ☺️. Choose another one.')
        return CHOOSING_DATE  
    
    await update.message.reply_text(
        f'Fine. You picked *{user_input}*.\nNow choose a starting time.',
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    logging.info(f"User {update.effective_user} selected date at {datetime.now()}")
    return CHOOSING_TIME

async def time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️':
        keyboard = utils.generate_date_keyboard()
        await update.message.reply_text('Choose a date, AGAIN! 😒', reply_markup=keyboard)
        return CHOOSING_DATE

    try:
        datetime.strptime(user_input, '%H:%M')
    except ValueError:
        await update.message.reply_text(
            'Not that difficult to pick an option form the list! Just saying. 🤷‍♂️')
        return CHOOSING_TIME

    context.user_data['selected_time'] = user_input
    keyboard = utils.generate_duration_keyboard(user_input, context)[0] # [0] for the reply, [1] for the values

    await update.message.reply_text(
        f'How long will you absolutely NOT be productive over there ? 🕦 Give me hours.', reply_markup=keyboard)
    logging.info(f"User {update.effective_user} selected time at {datetime.now()}")
    return CHOOSING_DUR

async def duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️':
        keyboard = utils.generate_time_keyboard(context.user_data.get('selected_date'))
        await update.message.reply_text(
            'Make up your mind! choose a time ALREADY 🙄', reply_markup=keyboard)
        return CHOOSING_TIME

    selected_time = context.user_data.get('selected_time')
    duration_selection = utils.generate_duration_keyboard(selected_time, context)[1] # [0] for the reply, [1] for the values
    max_dur = max(duration_selection)

    if not user_input.isdigit():
        await update.message.reply_text(
            "Now you're just messing with me. Just pick the damn duration!")
        return CHOOSING_DUR
    
    if int(user_input) > max_dur:
        await update.message.reply_text(
            "Well they are not going to let you sleep there! Try again. 🤷‍♂️")
        return CHOOSING_DUR

    context.user_data['selected_duration'] = user_input
    logging.info(f"User {update.effective_user} selected duration at {datetime.now()}")

    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')

    keyboard = utils.generate_confirmation_keyboard()
    await update.message.reply_text(
        textwrap.dedent(
            f"""
            All looks good ?

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
    return CONFIRMING

async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')

    if user_input == '✅ Yes, all looks good.':

        await writer(update, context)
        await update.message.reply_text(
        textwrap.dedent(
            f"""
            ✅ Done! That's about it.
            Reservation made at *{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

            Codice Fiscale: *{context.user_data.get('codice_fiscale')}*
            Full Name: *{context.user_data.get('name')}*
            Email: *{context.user_data.get('email')}*
            On *{context.user_data.get('selected_date')}*
            From *{start_time}* - *{end_time}* (*{context.user_data.get('selected_duration')} hours*)

            Do you want to go for a another date?
            I'm not that into you unfortunately, so don't 🚶.
            """
        ),
        parse_mode='Markdown',
        reply_markup=utils.generate_retry_keyboard()
    )
        logging.info(f"User {update.effective_user} confirmed at {datetime.now()}")
        return RETRY 
    
    elif user_input == '⬅️ No, take me back.':
        keyboard = utils.generate_duration_keyboard(context.user_data.get('selected_time'), context)[0]
        await update.message.reply_text(
            'I overestimated you it seems. 😬',
            reply_markup=keyboard
        )
        return CHOOSING_DUR
    
    else:
        await update.message.reply_text(
            "JUST.CLICK...PLEASE!",
            reply_markup=utils.generate_confirmation_keyboard()
        )
        return CONFIRMING 
    
async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == "🆕 Let's go for another date.":
        keyboard = utils.generate_date_keyboard()
        await update.message.reply_text(
            'Ah ****, here we go again! 😪',
            reply_markup=keyboard
        )
        logging.info(f"User {context.user_data['user']} reinitiated the process at {datetime.now()}")
        return CHOOSING_DATE
    
    elif user_input == "👍 I'm done":
        user = update.effective_user
        name = user.first_name if user.first_name else user.username
        await update.message.reply_text(
        textwrap.dedent(
            f"""
            Great! Thank you *{name}* for using *Biblio*.
            Now go tell your friends, but not all of them!
            If anything was not to your liking, I don't really care. Blame the creator not me.
            You should check him out though:
            [Linkedin](https://www.linkedin.com/in/alireza-mahmoudian-5b0276246/)
            [GitHub](https://github.com/TheRealMamoot)
            alireza.mahmoudian.am@gmail.com 📧
            Don't you dare press /start again! 😠
            """
        ),
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
        textwrap.dedent(
            f"""
            Off you go now, Bye. 😘
            Don't you dare press /start again 😠!
            """
        ),
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

# Writer
async def writer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')

    gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'biblio.json'))    
    wks = gc.open('Biblio-logs').worksheet_by_title('logs')
    data = wks.get_all_values(include_tailing_empty_rows=False)
    index = np.array(data).shape[0] - 1 # Checks the number of rows present in sheet. Adds as index.

    values=[
    index,
    context.user_data['user'],
    context.user_data['codice_fiscale'],
    context.user_data['name'],
    context.user_data['email'],
    context.user_data['selected_date'],
    start_time,
    end_time,
    context.user_data['selected_duration'],
    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    ]
    wks.append_table(values=values, start='A1', overwrite=False)
    logging.info(f"User {context.user_data['user']} data successfully added at {datetime.now()}")

# Misc
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hey! who or what do you think I am ? 😑 /start again.')

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Piano Piano eh ? use /start first.')

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update and hasattr(update, 'message'):
        await update.message.reply_text(
            "😵 Oops, something went wrong.\nTry /start to begin again.",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
    print(f'Update {update} caused error {context.error}')

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CREDENTIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_validation)],
            RESERVE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reservation_selection)],
            CHOOSING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_selection)],
            CHOOSING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_selection)],
            CHOOSING_DUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, duration_selection)],
            CONFIRMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmation)],
            RETRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, retry)],
        },
        fallbacks=[
            CommandHandler('start', start),  # Allows /start to reset everything
            MessageHandler(filters.ALL, fallback),
        ],
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, restart))
    app.add_error_handler(error)
    app.run_polling()

if __name__ == '__main__':
    main()