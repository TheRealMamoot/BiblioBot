from reservation import set_reservation, confirm_reservation
from slot_datetime import reserve_datetime

date = '2025-04-09'
start_time = '22:00'
duration = 1

user_data = {'codice_fiscale':'***',
             'cognome_nome':'***',
             'email':'***'}

def main():
    start, end, duration = reserve_datetime(date, start_time, duration)
    reservation_response = set_reservation(start, end, duration, user_data)
    confirm_reservation(reservation_response['entry'])

if __name__ == '__main__':
    main()