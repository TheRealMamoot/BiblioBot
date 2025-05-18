from src.biblio.reservation.reservation import cancel_reservation, confirm_reservation, set_reservation
from src.biblio.reservation.slot_datetime import reserve_datetime


def main():
    date = '2025-04-11'
    start_time = '20:00'
    duration = 1
    user_data = {'codice_fiscale': '***', 'cognome_nome': '***', 'email': '***'}
    start, end, duration = reserve_datetime(date, start_time, duration)
    reservation_response = set_reservation(start, end, duration, user_data)
    confirm_reservation(reservation_response['entry'])
    print(reservation_response)
    cancel_reservation(user_data['codice_fiscale'], reservation_response['codice_prenotazione'])


if __name__ == '__main__':
    main()
