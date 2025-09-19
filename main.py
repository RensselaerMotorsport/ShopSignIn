##################
#THIS IS AN EXAMPLE FILE ONLY
#(pretty sure the mech-e that made this used chatgpt for it lol)
#I just put it here so you can get an idea of how the library gets the uid of the card
#THIS IS AN EXAMPLE FILE ONLY
##################
import csv
import datetime
import time
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toHexString
from smartcard.Exceptions import CardConnectionException

LOGFILE = "rfid_log.csv"

# APDU command to get UID
GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]

class RFIDObserver(CardObserver):
    """Observer that logs UID whenever a card is inserted"""
    def update(self, observable, actions):
        (added_cards, removed_cards) = actions

        for card in added_cards:
            print("Card detected")
            connection = card.createConnection()
            try:
                connection.connect()
                data, sw1, sw2 = connection.transmit(GET_UID)
                if sw1 == 0x90 and sw2 == 0x00 and data:
                    uid = "".join(f"{x:02X}" for x in data)
                    timestamp = datetime.datetime.now().isoformat()
                    print(f"[{timestamp}] Card UID: {uid}")
                    with open(LOGFILE, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([uid, timestamp])
                else:
                    print(f"APDU failed: {sw1:02X} {sw2:02X}")
            except CardConnectionException:
                print("Card removed too quickly or could not connect.")
            finally:
                try:
                    connection.disconnect()
                except:
                    pass

        for card in removed_cards:
            print("Card removed")

if __name__ == "__main__":
    print("Starting RFID monitor... (Ctrl+C to stop)")
    card_monitor = CardMonitor()
    observer = RFIDObserver()
    card_monitor.addObserver(observer)

    try:
        while True:
            time.sleep(1)  # keep script alive
    except KeyboardInterrupt:
        print("Exiting...")
        card_monitor.deleteObserver(observer)