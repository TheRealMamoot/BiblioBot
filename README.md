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
GSHEETS='{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "...",
  "client_id": "...",
  ...
}'
```
Or you can place your google service account credential JSON directly in your directory. 
Make sure to make the following changes in `main.py` and `jobs.py`
```python
gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'<your_json_file>')) # Uncomment this line    
gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS']) # Delete or comment this line
wks = gc.open('<your_spreadsheet_name>').worksheet_by_title('<spreadsheet_tab_name>') # Create a new Google sheet beforehand
```
And finally:
```bash
python main.py
```




























