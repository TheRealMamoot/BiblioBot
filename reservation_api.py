import requests

def send_reservation_request(start_time: int, end_time: int, duration: int, user_data: dict) -> dict:
    """
    Sends a reservation request to the library API.

    Parameters:
    - start_time (int): Start time as Unix timestamp.
    - end_time (int): End time as Unix timestamp.
    - duration (int): Duration in seconds.
    - user_data (dict): Dictionary containing user information (codice_fiscale, cognome_nome, email).
    -- user_data = {'codice_fiscale': '<your_tax_code>',
                    'cognome_nome': '<your_name>',
                    'email': '<mamoot@gmail.com>'}

    Returns:
    - dict: Response from the API with reservation details.
    """
    url = 'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/store'
    
    payload = {
        "cliente": "biblio",
        "start_time": start_time,
        "end_time": end_time,
        "durata": duration,
        "entry_type": 50,
        "area": 25,
        "public_primary": "number",
        "utente": {
            "codice_fiscale": user_data['codice_fiscale'],
            "cognome_nome": user_data['cognome_nome'],
            "email": user_data['email']
        },
        "servizio": {},
        "risorsa": None,
        "recaptchaToken": None,
        "timezone": "Europe/Rome"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Request failed: {e}")

def confirm_reservation(entry_id: int) -> dict:
    url = f'https://prenotabiblio.sba.unimi.it/portalePlanningAPI/api/entry/confirm/{entry_id}'
    
    try:
        response = requests.post(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f'Request failed: {e}')