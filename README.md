![Version](https://img.shields.io/github/v/release/TheRealMamoot/BiblioBot?label=BiblioBot&color=blueviolet)
![Status](https://img.shields.io/website?url=https://bibliobot-production.up.railway.app/&label=Status&up_message=ONLINE&down_message=OFFLINE)
![Users](https://img.shields.io/badge/dynamic/json?url=https://bibliobot-production.up.railway.app/stats&label=Users&query=users&color=blue)
![Reservations](https://img.shields.io/badge/dynamic/json?url=https://bibliobot-production.up.railway.app/stats&label=Reservations&query=reservations&color=lightblue)

# 📚 BiblioBot: Your Biblioteca Slot Assistant

**Biblio** is a Telegram bot designed to automate and simplify the reservation of study slots at the University of Milan's Library of Biology, Computer Science, Chemistry and Physics (BICF).
This project was created to help students book their study slots at BICF more efficiently, as popular times often fill up quickly if booked late.

## 🤖 Try Biblio

💬 Give it a go [@BiblioBablioBot](https://t.me/BiblioBablioBot)

Start the conversation with `/start` to begin reserving your library slots.

## ✨ Features

#### Reservation Engine

- Automated daily reservation workflow with priority-based queuing.
- Intelligent retry logic with adaptive timeouts for long-running reservation attempts.
- Adaptive delays for load distribution and better API reliability.

#### Database & Backend

- Fully asynchronous PostgreSQL backend (Railway-hosted) with connection pooling.
- Concurrency safeguarded via async semaphores to prevent server overload.

#### Real-Time Monitoring

- Live and historical seat availability lookup with continuous state tracking and custom time-range filtering.
- Periodic Google Sheets backups using service accounts.

#### Deployment

- Reproducible builds via Docker & Docker Compose (local, staging, prod).

## ⚙️ Getting Started

Before running the bot, you’ll need:

- **Telegram Bot Token** → [How to get one](https://core.telegram.org/api/bots)
- **Google Service Account Credentials** → [How to get one](https://docs.cloud.google.com/iam/docs/service-account-creds)

### Setup Instructions

Clone the repository:

```bash
git clone https://github.com/TheRealMamoot/BiblioBot.git
```

Place your _Google Account Service Credentails_ json at `src/biblio/confifg`.

Create a `.env` file to store your environment variables:

```bash
touch .env
```

Paste this inside `.env` (replacing the placeholder values):

```dotenv
TELEGRAM_TOKEN=<YOUR_BOT_TOKEN>
PRIORITIES_CODES=<YOUR_PRIORITES_JSON>
DATABASE_URL=postgresql://biblio:biblio@postgres:5432/biblio_db
GSHEETS_NAME=Biblio-logs
GSHEETS_TAB=backup
```

Priorities are based on _Codice Fiscale_ and should look like this:

```json
{"ABCDEF12G34H567I": 0, "LMNOPQ98R76T543U": 1, "XYZABC00A00B000C": 2} # noqa
```

Lower values = higher priority (0 = highest).

❗ If you are deploying the code, you have to add the contents of the credentials json as an **_environment varibale_** in the hosting service's **_secrets section_** along with the previous env vars. Be sure to change the **`DATABASE_URL`** as well.

```dotenv
TELEGRAM_TOKEN=<YOUR_BOT_TOKEN>
PRIORITIES_CODES=<YOUR_PRIORITES_JSON>
DATABASE_URL=<YOUR_DATABASE_URL> # change this accordingly
GSHEETS=<YOUR_SERVICE_ACOUNT_JSON_CONTENT> # new variable
GSHEETS_NAME=Biblio-logs
GSHEETS_TAB=backup
ENV=<YOUR_ENV_NAME> # optional: staging or prod
BOTLORD_CHAT_ID=<YOUR_TELEGRAM_CHAT_ID> # optional: for admin panel
RAILWAY_ENV_ID=<YOUR_RAILWAY_ENV_ID> # optional: for admin panel if you use railway
RAILWAY_PROJECT_ID=<YOUR_RAILWAY_PROJECT_ID> # optional
RAILWAY_TOKEN=<YOUR_RAILWAY_TOKEN> # optional
```

#### Google Sheets

You **must** create a new sheet, rename it as **"Biblio-logs"** and rename the tab as **"backup"**. You would also have to share the sheet with the **email address** you obtain from the credentials as an **_editor_**. Finally you need to enable **_The Google Sheets API_** in the Google cloud console. (Instructions found [here](https://support.google.com/googleapi/answer/6158841?hl=en))

#### Required Bot Commands

After setting up your bot, be sure to register the commands in `src/biblio/bot/commands.txt` in your [BotFather settings](https://core.telegram.org/bots#botfather):

```txt
donate - Shows donation links ❤️
start - Restarts the Bot
help - Shows user guide
feedback - Shows author's contacts
agreement - Shows user agreement
```

## 🚀 Run the Bot

Launch the bot with:

```bash
docker compose up --build
```

If you want different enviroments, you can set up `.env.production` and `.env.staging` in the root of the project. This lets you keep different API keys, database URLs, and credentials for each environment.
You can then start the bot using the same command as above, but simply add a flag such as `-f docker-compose.staging.yml` to include the corresponding compose file.
For convenience, you can also use the provided `Makefile`:

```makefile
make staging-ub
# equivelant to: docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build
```

or:

```makefile
make prod-bnc
# equivelant to: docker compose build -f docker-compose.yml -f docker-compose.prod.yml --no-cache
```
