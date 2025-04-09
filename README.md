# 📚 BiblioBot — Your Biblioteca Slot Assistant

**Biblio** is a Telegram bot designed to automate and simplify the reservation of study slots at the University of Milan's Library of Biology, Computer Science, Chemistry and Physics (BICF). 
> 📝 _This project was created to help students book their study slots at BiCF more efficiently, as popular times often fill up quickly if booked late._
## 🤖 Talk to Biblio

💬 [@BiblioBablioBot](https://t.me/BiblioBablioBot)

Start the conversation with `/start` to begin reserving your library slots.

## ⚙️ Usage

Before anything You will have to get a **Telegram bot token** and a **Google service account** file.
- 👉 Instructions on the bot token [here](https://core.telegram.org/api/bots)
- 👉 Instructions on the service account [here](https://cloud.google.com/iam/docs/service-account-overview)

📌 Make sure to enable ***Google Sheets API*** and ***Google Drive API*** on your cloud console after downloading the service acount JSON file.

For running the code:
```bash
git clone https://github.com/TheRealMamoot/BiblioBot.git
cd bibliobot

pip install -r requirements.txt
```
You will need to create a `.env` file. 
```bash
touch .env
```
Paste the following in `.env` (replace the placeholders with your actual values):
```bash
TELEGRAM_TOKEN=your_telegram_bot_token
```
You can place your Google service account credential and priority JSON directly in your directory. 
Make sure to make the following changes in `main.py` and `jobs.py`. You must create a user priority list and a Google spreadsheet beforehand. Remember to replace your sheet and tab name in ```wks = gc.open('<your_sheet_name>').worksheet_by_title('<your_tab_name>')```
```python
# Uncomment these
with open(os.path.join(os.getcwd(), '<user_priority_codes.json'), 'r') as f:
    PRIORITY_CODES = json.load(f)  # NOT json.loads
gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'<your_google_credentials.json>'))

# Comment or delete these
PRIORITY_CODES: dict = os.environ['PRIORITY_CODES']
PRIORITY_CODES = json.loads(PRIORITY_CODES)
gc =  pygsheets.authorize(service_account_json=os.environ['GSHEETS']) 
```
User priorities for getting slots are based on Coidce Fiscale. Certan codes can have different priorities, Highest being 0.
```bash
PRIORITY_LIST={
  "ABCDEF12G34H567I": 0,
  "LMNOPQ98R76T543U": 1,
  "XYZABC00A00B000C": 2}
```

And finally:
```bash
python main.py
```