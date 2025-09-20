import csv
import os
import json
import sys
from datetime import datetime
from smartcard.System import readers
from smartcard.util import toHexString

# Student information UID : Name (Store this in some file in the future)
# I will change the method later so that we can have an option to register new people if they scan for first time
STUDENTS = { 
    "6B 94 70 56 00": "Simon"
}
# attendance = "attendance.csv" 

r = readers()
reader = r[0]

def get_uid(connection):  
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(GET_UID)
    if sw1 == 0x90 and sw2 == 0x00:
        return toHexString(data)
    else:
        return None

def main():
    connection = reader.createConnection() # create connection
    while True:
        try:
            connection.connect()
            uid = get_uid(connection)
            if uid:
                name = STUDENTS.get(uid, "No information")
                print(name)
            connection.disconnect()
        except KeyboardInterrupt:
            break
        except BaseException:
            pass
if __name__ == "__main__":
    main()