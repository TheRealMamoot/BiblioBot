import os

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.admin.railway import (
    get_env_id,
    get_last_deployment_id,
    get_service_id,
    redeploy_deployment,
    remove_deployment,
    restart_deployment,
)
from src.biblio.config.config import RAILWAY_SERVICES, State, UserDataKey
from src.biblio.utils.keyboards import Keyboard, Label


async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_input = update.message.text.strip()

    if admin_input == Label.BACK:
        await update.message.reply_text(
            "Sure thing!", reply_markup=Keyboard.admin_panel()
        )
        return State.ADMIN_PANEL

    service_name = admin_input
    for emoji in set(RAILWAY_SERVICES.values()):
        prefix = f"{emoji} "
        if admin_input.startswith(prefix):
            service_name = admin_input[len(prefix) :]
            break

    service_id = await get_service_id(service_name)
    environment_id = await get_env_id()
    last_deployment = await get_last_deployment_id(service_id, environment_id)
    last_deployment_id = last_deployment.get("id")

    context.user_data[UserDataKey.ENV_ID] = environment_id
    context.user_data[UserDataKey.CHOSEN_SERVICE_ID] = service_id
    context.user_data[UserDataKey.CHOSEN_SERVICE_NAME] = service_name
    context.user_data[UserDataKey.SERVICE_DEPLOYMENT_ID] = last_deployment_id

    await update.message.reply_text(
        "Please choose an option.", reply_markup=Keyboard.admin_service_options()
    )
    return State.ADMIN_SERVICE_OPTIONS


async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_input = update.message.text.strip()

    service_options = {
        Label.ADMIN_DEPLOYMENT_REDEPLOY,
        Label.ADMIN_DEPLOYMENT_REMOVE,
        Label.ADMIN_DEPLOYMENT_RESTART,
    }
    services = context.user_data[UserDataKey.AMDMIN_SERVICES]
    env = os.getenv("ENV")

    if admin_input == Label.BACK:
        await update.message.reply_text(
            "Will do!", reply_markup=Keyboard.admin_services(services, env)
        )
        return State.ADMIN_MANAGE_SERVICES

    elif admin_input not in service_options:
        await update.message.reply_text(
            "Please choose from the list!",
            reply_markup=Keyboard.admin_services(services, env),
        )
        return State.ADMIN_MANAGE_SERVICES

    context.user_data[UserDataKey.CHOSEN_SERVICE_OPTION] = admin_input
    chosen_option = (admin_input.split(" ", 1)[-1]).upper()
    chosen_service_name = context.user_data[UserDataKey.CHOSEN_SERVICE_NAME]

    await update.message.reply_text(
        f"Are you sure you want to *{chosen_option}* deployment for *{chosen_service_name}*?",
        reply_markup=Keyboard.confirmation(),
        parse_mode="Markdown",
    )
    return State.ADMIN_OPTION_CONFIRM


async def confirm_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_input = update.message.text.strip()

    if admin_input == Label.CONFIRM_NO:
        await update.message.reply_text(
            "As you wish!", reply_markup=Keyboard.admin_service_options()
        )
        return State.ADMIN_SERVICE_OPTIONS

    elif admin_input == Label.CONFIRM_YES:
        deployment_id = context.user_data[UserDataKey.SERVICE_DEPLOYMENT_ID]
        chosen_service_option = context.user_data[UserDataKey.CHOSEN_SERVICE_OPTION]

        if chosen_service_option == Label.ADMIN_DEPLOYMENT_REDEPLOY:
            resp = await redeploy_deployment(deployment_id)

        elif chosen_service_option == Label.ADMIN_DEPLOYMENT_REMOVE:
            resp = await remove_deployment(deployment_id)

        elif chosen_service_option == Label.ADMIN_DEPLOYMENT_RESTART:
            resp = await restart_deployment(deployment_id)

        else:
            await update.message.reply_text(
                "Unknown.",
                reply_markup=Keyboard.confirmation(),
            )
            return State.ADMIN_OPTION_CONFIRM

        await update.message.reply_text(
            f"As you wish. *{chosen_service_option}* in progress.\nResponse: *{resp}*",
            reply_markup=Keyboard.admin_panel(),
            parse_mode="Markdown",
        )
        return State.ADMIN_PANEL
