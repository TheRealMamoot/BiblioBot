import logging
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from src.biblio.bot.messages import show_help, show_support_message
from src.biblio.config.config import (
    DEFAULT_PRIORITY,
    State,
    UserDataKey,
    get_priorities,
)
from src.biblio.db.insert import insert_user
from src.biblio.utils.keyboards import Keyboard, Label
from src.biblio.utils.validation import validate_codice_fiscale, validate_email


async def user_agreement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.AGREEMENT_DISAGREE:
        (
            await update.message.reply_text(
                "Sorry to see you go! Hope you change your mind. Use /start again in case you do.",
                reply_markup=ReplyKeyboardRemove(),
            ),
        )
        return ConversationHandler.END

    elif user_input == Label.AGREEMENT_AGREE:
        user = update.effective_user
        name = user.first_name if user.first_name else user.username
        logging.info(f"{user} started chat at {datetime.now(ZoneInfo('Europe/Rome'))}")

        user_input = update.message.text.strip()

        gif_url = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ2F6cWowaG5oYjdkejhqamQxaWJ5bmxhcXQxY2w5azhieGlkZWwyNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xTiIzJSKB4l7xTouE8/giphy.gif"
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
            parse_mode="Markdown",
            reply_markup=Keyboard.start(),
        )
        return State.CREDENTIALS

    else:
        await update.message.reply_text("Please agree to the terms.")
        return State.AGREEMENT


async def user_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        await update.message.reply_text(
            "Sure, waste your time why not? I can do this all day. 🥱"
        )
        return State.CREDENTIALS

    user_input = update.message.text.strip()
    user = update.effective_user
    name = user.first_name if user.first_name else user.username

    if user_input == Label.SUPPORT:
        await update.message.reply_text(
            show_support_message(),
            parse_mode="Markdown",
            reply_markup=Keyboard.start(),
        )
        return State.CREDENTIALS

    if user_input == Label.HELP:
        await update.message.reply_text(
            show_help(),
            parse_mode="Markdown",
            reply_markup=Keyboard.start(),
        )
        return State.CREDENTIALS

    if user_input == Label.CREDENTIALS_RETURN:
        await update.message.reply_text(
            "Gotta be kidding me! 😑",
            parse_mode="Markdown",
            reply_markup=Keyboard.reservation_type(
                context.user_data[UserDataKey.IS_ADMIN]
            ),
        )
        return State.RESERVE_TYPE

    try:
        codice, name, email = [part.strip() for part in user_input.split(",")]
    except ValueError:
        await update.message.reply_text(
            "Wow so it WAS too hard for you. 🙃\nTry again: `Codice, Full Name, Email`",
            parse_mode="Markdown",
        )
        return State.CREDENTIALS

    if not validate_codice_fiscale(codice):
        await update.message.reply_text(
            "🚫 Nice try with a fake codice fiscale. Try again!"
        )
        return State.CREDENTIALS

    if not validate_email(email):
        await update.message.reply_text("🚫 Nice try with a fake email. Try again!")
        return State.CREDENTIALS

    priorities = get_priorities()
    context.user_data[UserDataKey.USERNAME] = user.username
    context.user_data[UserDataKey.FIRST_NAME] = user.first_name
    context.user_data[UserDataKey.LAST_NAME] = user.last_name
    context.user_data[UserDataKey.CODICE_FISCALE] = codice.upper()
    context.user_data[UserDataKey.NAME] = name
    context.user_data[UserDataKey.EMAIL] = email.lower()
    context.user_data[UserDataKey.PRIORITY] = int(
        priorities.get(codice.upper(), DEFAULT_PRIORITY)
    )

    keyboard = Keyboard.reservation_type(context.user_data[UserDataKey.IS_ADMIN])
    await update.message.reply_text(
        textwrap.dedent(
            """
            There we go! Your data is saved. FOREVER! 😈 (JUST KIDDING...?)
            Now, you can plan ahead for later or,
            If you're so desperate and need a slot now, try to book instantly. No promises!
            """
        ),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    user_record = {
        "chat_id": update.effective_chat.id,
        "username": context.user_data[UserDataKey.USERNAME],
        "first_name": context.user_data[UserDataKey.FIRST_NAME],
        "last_name": context.user_data[UserDataKey.LAST_NAME],
        "codice_fiscale": context.user_data[UserDataKey.CODICE_FISCALE],
        "priority": context.user_data[UserDataKey.PRIORITY],
        "name": context.user_data[UserDataKey.NAME],
        "email": context.user_data[UserDataKey.EMAIL],
    }

    id = await insert_user(user_record)
    context.user_data[UserDataKey.ID] = id

    logging.info(
        f"🔄 {update.effective_user} info validated at {datetime.now(ZoneInfo('Europe/Rome'))}"
    )
    return State.RESERVE_TYPE


async def user_returning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    if user_input == Label.ADMIN_PANEL and context.user_data[UserDataKey.IS_ADMIN]:
        await update.message.reply_text(
            "Welcome master!",
            reply_markup=Keyboard.admin_panel(),
        )
        return State.ADMIN_PANEL

    elif user_input == Label.CONTINUE:
        await update.message.reply_text(
            "Glad to have you back!",
            parse_mode="Markdown",
            reply_markup=Keyboard.reservation_type(
                context.user_data[UserDataKey.IS_ADMIN]
            ),
        )
        return State.RESERVE_TYPE

    elif user_input == Label.CREDENTIALS_NEW:
        await update.message.reply_text(
            textwrap.dedent(
                """
            your _Codice Fiscale_, _Full Name_, and _Email_.
            Example: 
            *ABCDEF12G34H567I*, 
            *Mamoot Real*, 
            *brain@rot.com*

            📌_Comma placement matters. Spacing does not._
            """
            ),
            parse_mode="Markdown",
            reply_markup=Keyboard.start(edit_credential_stage=True),
        )
        return State.CREDENTIALS
    else:
        await update.message.reply_text(
            textwrap.dedent("Come on now! Just choose."),
        )
        return State.WELCOME_BACK
