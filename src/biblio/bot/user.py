import logging
import textwrap
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from src.biblio.access import get_priorities
from src.biblio.bot.messages import show_help, show_support_message
from src.biblio.config.config import States
from src.biblio.db.insert import insert_user
from src.biblio.utils import keyboards
from src.biblio.utils.validation import validate_codice_fiscale, validate_email


async def user_agreement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == "👎 No, I don't agree.":
        (
            await update.message.reply_text(
                'Sorry to see you go! Hope you change your mind. Use /start again in case you do.',
                reply_markup=ReplyKeyboardRemove(),
            ),
        )
        return ConversationHandler.END

    elif user_input == '👍 Yes, I agree.':
        user = update.effective_user
        name = user.first_name if user.first_name else user.username
        context.user_data['username'] = user.username
        context.user_data['user_firstname'] = user.first_name
        context.user_data['user_lastname'] = user.last_name
        logging.info(f'{user} started chat at {datetime.now(ZoneInfo("Europe/Rome"))}')

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
            reply_markup=keyboards.generate_start_keyboard(),
        )
        return States.CREDENTIALS

    else:
        await update.message.reply_text('Please agree to the terms.')
        return States.AGREEMENT


async def user_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    priorities_env = context.bot_data.get('priorities_env')

    if not update.message or not update.message.text:
        await update.message.reply_text('Sure, waste your time why not? I can do this all day. 🥱')
        return States.CREDENTIALS

    user_input = update.message.text.strip()
    name = update.effective_user.first_name if update.effective_user.first_name else update.effective_user.username

    if user_input == '🤝 Reach out!':
        await update.message.reply_text(
            show_support_message(),
            parse_mode='Markdown',
            reply_markup=keyboards.generate_start_keyboard(),
        )
        return States.CREDENTIALS

    if user_input == '❓ Help':
        await update.message.reply_text(
            show_help(),
            parse_mode='Markdown',
            reply_markup=keyboards.generate_start_keyboard(),
        )
        return States.CREDENTIALS

    if user_input == '➡️ Changed my mind.':
        await update.message.reply_text(
            'Gotta be kidding me! 😑',
            parse_mode='Markdown',
            reply_markup=keyboards.generate_reservation_type_keyboard(),
        )
        return States.RESERVE_TYPE

    try:
        codice, name, email = [part.strip() for part in user_input.split(',')]
    except ValueError:
        await update.message.reply_text(
            'Wow so it WAS too hard for you. 🙃\nTry again: `Codice, Full Name, Email`',
            parse_mode='Markdown',
        )
        return States.CREDENTIALS

    if not validate_codice_fiscale(codice):
        await update.message.reply_text('🚫 Nice try with a fake codice fiscale. Try again!')
        return States.CREDENTIALS

    if not validate_email(email):
        await update.message.reply_text('🚫 Nice try with a fake email. Try again!')
        return States.CREDENTIALS

    priorities = get_priorities(priorities_env)
    context.user_data['user_id'] = str(uuid.uuid4())
    context.user_data['codice_fiscale'] = codice.upper()
    context.user_data['name'] = name
    context.user_data['email'] = email.lower()
    context.user_data['priority'] = priorities.get(codice.upper(), 2)  # Default: 2. For everyone else
    context.bot_data['user_chat_ids'][context.user_data['codice_fiscale']] = update.effective_chat.id

    keyboard = keyboards.generate_reservation_type_keyboard()
    await update.message.reply_text(
        textwrap.dedent(
            """
            There we go! Your data is saved. FOREVER! 😈 (JUST KIDDING!)
            Now, you can plan ahead for later or,
            If you're so desperate and need a slot now, try to book instantly. No promises!
            """
        ),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )

    user_record = {
        'chat_id': update.effective_chat.id,
        'username': context.user_data['username'],
        'first_name': context.user_data['user_firstname'],
        'last_name': context.user_data['user_lastname'],
        'codice_fiscale': context.user_data['codice_fiscale'],
        'priority': context.user_data['priority'],
        'name': context.user_data['name'],
        'email': context.user_data['email'],
    }

    user_id = await insert_user(user_record, db_env=context.bot_data['db_env'])
    context.user_data['user_id'] = user_id

    logging.info(f'🔄 {update.effective_user} info validated at {datetime.now(ZoneInfo("Europe/Rome"))}')
    return States.RESERVE_TYPE
