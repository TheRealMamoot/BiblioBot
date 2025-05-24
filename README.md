![Version](https://img.shields.io/github/v/release/TheRealMamoot/BiblioBot?label=BiblioBot&style=flat-square)
# 📚 BiblioBot — Your Biblioteca Slot Assistant

**Biblio** is a Telegram bot designed to automate and simplify the reservation of study slots at the University of Milan's Library of Biology, Computer Science, Chemistry and Physics (BICF). 
This project was created to help students book their study slots at BiCF more efficiently, as popular times often fill up quickly if booked late.

## 🤖 Try Biblio

💬 Talk to [@BiblioBablioBot](https://t.me/BiblioBablioBot)


Start the conversation with `/start` to begin reserving your library slots.

## ✨ Features

- ⏰ Automated slot booking with retry logic
- 📊 PostgreSQL-based storage 
- 👥 Priority-based scheduling
- 🔔 Telegram notifications

## ⚙️ Getting Started

Before running the bot, you’ll need:

-  **Telegram Bot Token** → [How to get one](https://core.telegram.org/api/bots)
-  **PostgreSQL Database** 



### 🧰 Setup Instructions

Clone the repository and install dependencies:

```bash
git clone https://github.com/TheRealMamoot/BiblioBot.git
cd bibliobot
pip install -r requirements.txt
```
Create a `.env` file to store your environment variables:
```bash
touch .env
```
Paste this inside `.env` (replacing the placeholder value):
```dotenv
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_TOKEN_S=your_staging_bot_token_here (optional)
DATABASE_URL=your_postgres_url_here
PRIORITIES_CODES=priorities.json
```
Your priorities should look like this:
```json
{
  "ABCDEF12G34H567I": 0,
  "LMNOPQ98R76T543U": 1,
  "XYZABC00A00B000C": 2
}
```
Lower values = higher priority (0 = highest).


### 🗂️ Database Setup
To build the database:

```bash
python src/biblio/db/build.py
```

### ✏️ Required Bot Commands

After setting up your bot, be sure to register these commands in your [BotFather settings](https://core.telegram.org/bots#botfather):
```txt
/start - Restart the bot
/help - Show help and usage instructions
/feedback - Send feedback to the developer
/agreement - Show user agreement
```

## 🚀 Run the Bot

Launch the bot with:
```bash
python main.py
```
Use `--token-env staging` to start the bot with the staging token. 
