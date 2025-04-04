from datetime import datetime, timedelta
from math import ceil

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

from utils import generate_days

# states
CHOOSING_DATE, CHOOSING_TIME, CHOOSING_DUR = range(3)

TOKEN = '****'

user_data = {}

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Restarting the conversation...')
    context.user_data.clear()

    user = update.effective_user
    name = user.first_name if user.first_name else user.username

    keyboard = generate_date_keyboard()
    await update.message.reply_text(
        f"Ciao {name}! 👋 The name's Biblio. I'm here to make your bibliotecca reservations because you are too lazy and disorganized to do it yourself. 📚\nSo, when will it be ?", reply_markup=keyboard)
    return CHOOSING_DATE

async def handle_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    try:
        # Try to parse to ensure it's a valid date
        datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(
            'Umm, that does not look like a date to me. 🤨 Just pick one from the list.')
        return CHOOSING_DATE
    
    context.user_data['selected_date'] = user_input
    keyboard = generate_time_keyboard(user_input)
    
    if not keyboard.keyboard or all(len(row) == 0 for row in keyboard.keyboard):
        await update.message.reply_text(
            'Oops! There are no available time slots for that date. Cry about it ☺️.')
        return CHOOSING_DATE  
    
    await update.message.reply_text(
        f'Fine. You picked {user_input} 📅\nNow choose a starting time',
        reply_markup=keyboard
    )
    return CHOOSING_TIME

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️':
        keyboard = generate_date_keyboard()
        await update.message.reply_text('Choose a date, AGAIN! 😒', reply_markup=keyboard)
        return CHOOSING_DATE

    try:
        datetime.strptime(user_input, '%H:%M')
    except ValueError:
        await update.message.reply_text(
            'Not that difficult to pick an option form the list! Just saying. 🤷‍♂️')
        return CHOOSING_TIME

    context.user_data['selected_time'] = user_input
    keyboard = generate_duration_keyboard(user_input, context)

    await update.message.reply_text(
        f'How long will you absolutely NOT be productive over there ? Gimme hours.', reply_markup=keyboard)
    return CHOOSING_DUR

async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == '⬅️':
        keyboard = generate_time_keyboard(context.user_data.get('selected_date'))
        await update.message.reply_text(
            'Make up your mind! choose a time ALREADY 🙄', reply_markup=keyboard)
        return CHOOSING_TIME

    if not user_input.isdigit():
        await update.message.reply_text(
            "Now you're just messing with me. Just pick the damn time!")
        return CHOOSING_DUR

    context.user_data['selected_duration'] = user_input
    await update.message.reply_text(
        f'✅ Reservation saved for {context.user_data["selected_date"]}.'
    )
    keyboard = generate_date_keyboard()
    await update.message.reply_text(
        "Finally! That's about it. Going for a second date ?\nI'm not that into you unfortunately but whatever.\nTry again if you want. 😏",
        reply_markup=keyboard
    )

    return CHOOSING_DATE

# Responses
async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hey who or what do you think I am ? 😑 /start again.')
    
# Utils
def generate_date_keyboard():
    dates = generate_days()
    keyboard_buttons = []
    for i in range(0, len(dates), 3):
        row = [KeyboardButton(date) for date in dates[i:i+3]]
        keyboard_buttons.append(row)

    return ReplyKeyboardMarkup(keyboard_buttons)

def generate_time_keyboard(selected_date: str):
    date_obj = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')
    today = datetime.today()
    year = today.year if today.month <= date_obj.month else today.year + 1
    full_date = datetime(year, date_obj.month, date_obj.day)

    end_hour = 13 if full_date.weekday() == 5 else 22 # Saturdays

    # Check starting time.
    if full_date.date() == today.date():
        hour = today.hour
        minute = 0 if today.minute < 30 else 30
        current = datetime(year, date_obj.month, date_obj.day, hour, minute)
    else:
        current = datetime(year, date_obj.month, date_obj.day, 9, 0)
    
    times = []
    while current.hour < end_hour or (current.hour == end_hour and current.minute == 0):
        times.append(current.strftime('%H:%M'))
        current += timedelta(minutes=30)

    keyboard_buttons = [
        [KeyboardButton(time) for time in times[i:i+5]]
        for i in range(0, len(times), 5)
    ]
    keyboard_buttons.insert(0, [KeyboardButton('⬅️')])

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_duration_keyboard(selected_time: str, context: ContextTypes.DEFAULT_TYPE):
    selected_date = context.user_data.get('selected_date')
    selected_date = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')

    time_obj = datetime.strptime(selected_time, '%H:%M')
    date_obj = datetime(selected_date.year, selected_date.month, selected_date.day, time_obj.hour, time_obj.minute)

    end_hour = 14 if selected_date.weekday() == 5 else 23 # Saturdays
    selected_date = selected_date + timedelta(hours=end_hour)

    durations = ceil((selected_date - date_obj + timedelta(minutes=30)).seconds / 3600) # ceil in case of **:30 start time formats
    durations = list(range(1, durations))

    keyboard_buttons = [
        [KeyboardButton(dur) for dur in durations[i:i+10]]
        for i in range(0, len(durations), 10)
    ]
    keyboard_buttons.insert(0, [KeyboardButton('⬅️')])

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_selection)],
            CHOOSING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_selection)],
            CHOOSING_DUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_duration_selection)],
        },
        fallbacks=[
            CommandHandler('start', start),  # Allows /start to reset everything
            MessageHandler(filters.ALL, fallback_handler),
        ],
        allow_reentry=True
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()