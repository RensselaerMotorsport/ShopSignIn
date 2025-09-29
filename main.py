import csv
import os
import sqlite3
import sys
from datetime import datetime
from smartcard.System import readers
from smartcard.util import toHexString
import time

# Student information UID : Name (Store this in some file in the future)

RM_ER = "RM_ers.db"
r = readers() 
reader = r[0]
l_status = {}
l_seen = {}
d_sec = 1.5

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
            w.writerow(["Name", "IN_time", "OUT_time", "Date"])
    return attendance

# Write info in csv
def write_csv_attendance(name,in_time,out_time):
    attendance = csv_set()
    now_date = datetime.now().strftime("%Y-%m-%d")
    with open(attendance, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([name,in_time,out_time,now_date])
    print(f"LOG: {name} - IN: {in_time} - OUT: {out_time} - {now_date} ")

def db(): #Set up our initial sqldb file
    conn = sqlite3.connect(RM_ER)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        uid TEXT PRIMARY KEY,
        name TEXT NOT NULL
    )
""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT NOT NULL,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        in_time TEXT,
        out_time TEXT,
        FOREIGN KEY (uid) REFERENCES students(uid)
    )
""")
    conn.commit()
    conn.close()

def load_uid(): #Load db file that have students information
    conn = sqlite3.connect(RM_ER)
    c = conn.cursor()
    c.execute("SELECT uid, name FROM students")
    students = {uid: name for uid, name in c.fetchall()}
    conn.close()
    return students

def save_uid(uid, name):
    conn = sqlite3.connect(RM_ER)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO students (uid, name) VALUES (?,?)", (uid, name))
    conn.commit()
    conn.close()

def log(uid, name):
    conn = sqlite3.connect(RM_ER)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    n_time = datetime.now().strftime("%H:%M:%S")

    # Auto-close any previous open sessions
    c.execute("SELECT id, date, in_time, out_time FROM attendance WHERE uid=? AND out_time IS NULL ORDER BY date ASC", (uid,))
    rows = c.fetchall()
    for r_id, r_date, r_in, r_out in rows:
        if r_date < today:
            c.execute("UPDATE attendance SET out_time=? WHERE id=?", ("23:59:59", r_id))
            write_csv_attendance(name, r_in, "23:59:59")

    # Handle today's session
    c.execute("SELECT id, in_time, out_time FROM attendance WHERE uid=? AND date=? ORDER BY id DESC LIMIT 1", (uid, today))
    today_row = c.fetchone()

    if today_row is None or today_row[2] is not None:  # No open session → IN
        c.execute("INSERT INTO attendance (uid, name, date, in_time) VALUES (?,?,?,?)", (uid, name, today, n_time))
        print(f"{name} - IN at {n_time}")
        write_csv_attendance(name, n_time, "")
    else:  # Open session exists → OUT
        c.execute("UPDATE attendance SET out_time=? WHERE id=?", (n_time, today_row[0]))
        write_csv_attendance(name, today_row[1], n_time)
        print(f"{name} - OUT at {n_time}")
    conn.commit()
    conn.close()
##############################################################################################
def main():
    db()
    students = load_uid()
    print("Ready. Tap cards. Ctrl+C to exit.")
    try:
        while True:
            connection = reader.createConnection() # create connection
            uid = None
            try:
                connection.connect()
                uid = get_uid(connection)
            except Exception:
                uid = None
            finally:
                try:
                    connection.disconnect()
                except Exception:
                    pass
            if uid:
                now_epo = time.time()
                if uid in l_seen and (now_epo - l_seen[uid]) < d_sec: #Prevents the same card from logging multiple times if it stays on the reader.
                    time.sleep(0.1)
                    continue
                l_seen[uid] = now_epo
                if uid not in students:
                    print(f"Unknown card detected: {uid}")
                    choice = input("Do you want to register this card? (y/n): ").strip().lower()
                    if choice == ("y" or "Y"):
                        name = input("Enter student name: ").strip()
                        students[uid] = name
                        save_uid(uid,name)
                        print(f"Registered {name} with UID {uid}! WELCOME TO RPI MOTORSPORTS !!!")
                    else:
                        print("Ignored action!")
                        continue
                else:
                    name = students[uid]
                    log(uid, name)
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("BYE!")
        try:
            connection.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    main()