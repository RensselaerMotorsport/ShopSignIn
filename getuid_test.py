##################
# Get student uid
##################
from smartcard.System import readers
from smartcard.util import toHexString
import time
r = readers() # find all the smart card reader connecting to the computer
reader = r[0] # get the first reader

#Get the function based on example file (APDU command to get UID)
def get_uid(connection): 
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(GET_UID)
    if sw1 == 0x90 and sw2 == 0x00:
        return toHexString(data)
    else:
        return None
    
def main():
    while True:
        try:
            connection = reader.createConnection()
            connection.connect()
            uid = get_uid(connection)
            if uid:
                print(uid)
            connection.disconnect()
        except Exception:
            time.sleep(1)
            
if __name__ == "__main__":
    main()