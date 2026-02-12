import os

from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.biblio.admin.action import select_admin_action
from src.biblio.admin.maintenance import (
    block_user_activity,
    maintenance_gate,
    toggle_maintenance_mode,
)
from src.biblio.admin.notif import prepare_notification, push_notification
from src.biblio.admin.services import confirm_option, select_option, select_service
from src.biblio.bot.commands import agreement, donate, feedback, help, start
from src.biblio.bot.fallbacks import error, fallback, restart
from src.biblio.bot.user import user_agreement, user_returning, user_validation
from src.biblio.config.config import State
from src.biblio.jobs import start_jobs
from src.biblio.selection.cancel import cancelation, cancelation_confirmation
from src.biblio.selection.confirm import confirmation
from src.biblio.selection.date import date_history, date_selection
from src.biblio.selection.duration import duration_availability, duration_selection
from src.biblio.selection.retry import retry
from src.biblio.selection.time import (
    filter_end_selection,
    filter_start_selection,
    slot_selection,
    time_selection,
)
from src.biblio.selection.type import type_selection


def build_app():
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            State.AGREEMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, user_agreement)
            ],
            State.CREDENTIALS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, user_validation)
            ],
            State.WELCOME_BACK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, user_returning)
            ],
            State.ADMIN_PANEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_admin_action)
            ],
            State.ADMIN_NOTIF: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, prepare_notification)
            ],
            State.ADMIN_NOTIF_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, push_notification)
            ],
            State.ADMIN_MANAGE_SERVICES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_service)
            ],
            State.ADMIN_SERVICE_OPTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_option)
            ],
            State.ADMIN_OPTION_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_option)
            ],
            State.MAINTENANCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, block_user_activity)
            ],
            State.ADMIN_MAINTANANCE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, toggle_maintenance_mode)
            ],
            State.RESERVE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, type_selection)
            ],
            State.CHOOSING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, date_selection)
            ],
            State.CHOOSING_DATE_HISTORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, date_history)
            ],
            State.CHOOSING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, time_selection)
            ],
            State.CHOOSING_SLOT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, slot_selection)
            ],
            State.CHOOSING_FILTER_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_start_selection)
            ],
            State.CHOOSING_FILTER_END: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_end_selection)
            ],
            State.CHOOSING_DUR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, duration_selection)
            ],
            State.CHOOSING_AVAILABLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, duration_availability)
            ],
            State.CONFIRMING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirmation)
            ],
            State.CANCELATION_SLOT_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cancelation)
            ],
            State.CANCELATION_CONFIRMING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cancelation_confirmation
                )
            ],
            State.RETRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, retry)],
        },
        fallbacks=[
            CommandHandler("start", start),  # Allows /start to reset everything
            CommandHandler("help", help),
            CommandHandler("feedback", feedback),
            CommandHandler("agreement", agreement),
            CommandHandler("donate", donate),
            MessageHandler(filters.ALL, fallback),
            MessageHandler(filters.ALL, maintenance_gate),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, restart))
    app.add_error_handler(error)

    # start_jobs(bot=app.bot) #! temporary

    return app
