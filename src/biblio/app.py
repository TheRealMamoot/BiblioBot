from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.biblio.bot.commands import feedback, help, start
from src.biblio.bot.fallbacks import error, fallback, restart
from src.biblio.bot.user import user_agreement, user_validation
from src.biblio.config.config import States
from src.biblio.gsheets import schedule_backup_job
from src.biblio.jobs import schedule_jobs
from src.biblio.selection.cancel import cancelation, cancelation_confirmation
from src.biblio.selection.confirm import confirmation
from src.biblio.selection.date import date_selection
from src.biblio.selection.duration import duration_selection
from src.biblio.selection.retry import retry
from src.biblio.selection.time import time_selection
from src.biblio.selection.type import type_selection
from src.biblio.utils.utils import get_token


def build_app(token_env='prod'):
    app = Application.builder().token(get_token(token_env)).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.AGREEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_agreement)],
            States.CREDENTIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_validation)],
            States.RESERVE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_selection)],
            States.CHOOSING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_selection)],
            States.CHOOSING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_selection)],
            States.CHOOSING_DUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, duration_selection)],
            States.CONFIRMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmation)],
            States.CANCELATION_SLOT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancelation)],
            States.CANCELATION_CONFIRMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancelation_confirmation)],
            States.RETRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, retry)],
        },
        fallbacks=[
            CommandHandler('start', start),  # Allows /start to reset everything
            CommandHandler('help', help),
            CommandHandler('feedback', feedback),
            MessageHandler(filters.ALL, fallback),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help))
    app.add_handler(CommandHandler('feedback', feedback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, restart))
    app.add_error_handler(error)

    schedule_jobs(app.bot)
    schedule_backup_job()

    return app
