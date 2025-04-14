# 📚 BiblioBot — Your Biblioteca Slot Assistant

**Biblio** is a Telegram bot designed to automate and simplify the reservation of study slots at the University of Milan's Library of Biology, Computer Science, Chemistry and Physics (BICF). 
This project was created to help students book their study slots at BiCF more efficiently, as popular times often fill up quickly if booked late.

## 🤖 Talk to Biblio

💬 [@BiblioBablioBot](https://t.me/BiblioBablioBot)

Start the conversation with `/start` to begin reserving your library slots.

## ⚙️ Getting Started

Before running the bot, you’ll need:

- 👉 A **Telegram Bot Token** → [How to get one](https://core.telegram.org/api/bots)
- 👉 A **Google Service Account JSON** → [Set it up here](https://cloud.google.com/iam/docs/service-account-overview)

> 📌 _Make sure to enable both **Google Sheets API** and **Google Drive API** in your Google Cloud Console after creating your service account._

### 🔧 Setup Instructions

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
```bash
TELEGRAM_TOKEN=your_telegram_bot_token
```

### 🗃️ Google Sheet Setup
Create a **Google Sheet** titled Biblio-logs with a tab named logs.
These names **can be changed**, but you must update the corresponding lines in the code wherever pygsheets is used:

```python
wks: pygsheets.Worksheet = gc.open('Biblio-logs').worksheet_by_title('logs')
```
#### 🧱 Column Format Requirement:

Your **Google Sheet** must contain the following **columns in this exact order**, and the entire sheet must be formatted as **Plain Text**:
```txt
id
chat_id
username
first_name
last_name
codice_fiscale
priority
name
email
selected_date
start
end
selected_dur
booking_code
created_at
retries
status
updated_at
instant
status_change
notified
```
> _⚠️ If these are not matched exactly, the bot may fail to read or write data correctly._

### 🧠 User Priorities

Users are prioritized based on their **Codice Fiscale**. Lower values indicate higher priority (e.g. 0 is the highest):

Your priorities.json file should look like this:
```json
{
  "ABCDEF12G34H567I": 0,
  "LMNOPQ98R76T543U": 1,
  "XYZABC00A00B000C": 2
}
```

### 🧰 Configuration

Place both your **Google credentials JSON** and your **priority list JSON** in the same directory as your Python files.

In `main.py` and `jobs.py`, replace:
```python
with open(os.path.join(os.getcwd(), '<your_priority_codes>.json'), 'r') as f:
    PRIORITY_CODES = json.load(f)

gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(), '<your_google_credentials>.json'))
```
And **comment or remove**:
```pyhton
PRIORITY_CODES: dict = os.environ['PRIORITY_CODES']
PRIORITY_CODES = json.loads(PRIORITY_CODES)

gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS'])
```
### ✏️ Required Bot Commands

After setting up your bot, be sure to register these commands in your[BotFather settings](https://core.telegram.org/bots#botfather):
```txt
/start - Start the bot
/help - Show help and usage instructions
/feedback - Send feedback to the developer
```

## 🚀 Run the Bot

Launch the bot with:
```bash
python main.py
```
