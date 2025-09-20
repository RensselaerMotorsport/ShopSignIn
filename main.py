import csv
import os
import json
import sys
from datetime import datetime
from smartcard.System import readers
from smartcard.util import toHexString
import time

# Student information UID : Name (Store this in some file in the future)
# I will change the method later so that we can have an option to register new people if they scan for first time
STUDENTS = { 
    "6B 94 70 56 00" : "Simon"
} 
l_status = {} 

r = readers() 
reader = r[0]

def get_uid(connection): #Get student UID  
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(GET_UID)
    if sw1 == 0x90 and sw2 == 0x00:
        return toHexString(data)
    else:
        return None

def get_csv():
    today_date = datetime.now().strftime("%Y-%m-%d")
    return f"RM_attendance_{today_date}.csv"

#Set up csv
def csv_set():
    attendance = get_csv()
    if not os.path.exists(attendance):
        with open(attendance, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Name", "Status", "Time", "Date"])
    return attendance

# Write info in csv
def write_csv_attendance(name,c_status):
    attendance = csv_set()
    now_date = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")
    with open(attendance, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([name,c_status,now_time,now_date])
    print(f"LOG: {name} - {c_status} - {now_time} - {now_date} ")

def main():
    connection = reader.createConnection() # create connection
    while True:
        try:
            connection.connect()
            uid = get_uid(connection)
            if uid:
                name = STUDENTS.get(uid, "Unknown card")
                print(name)
                c_status = "IN" 
                if l_status.get(uid) == "IN":
                    c_status = "OUT"
                l_status[uid] = c_status
                write_csv_attendance(name,c_status)
                while True:
                    try:
                        connection.connect()
                        time.sleep(0.3)
                    except BaseException:
                        break
            connection.disconnect()
        except KeyboardInterrupt:
            break
        except BaseException:
            pass
if __name__ == "__main__":
    main()