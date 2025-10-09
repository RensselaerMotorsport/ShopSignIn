import sqlite3
from datetime import datetime
from smartcard.System import readers
from smartcard.util import toHexString
import time
import requests

# Student information UID : Name (Store this in some file in the future)

RM_ER = "RM_ers.db"
r = readers() 
reader = r[0]
l_status = {}
l_seen = {}
d_sec = 1.5

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzJfvdoW4c50LsLfNNI6oZ2pqCHhX7eG98QW24g5lm9cl1Y5xBJpS2TGTN0eES3spXB/exec"

def get_uid(connection): #Get student UID  
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(GET_UID)
    if sw1 == 0x90 and sw2 == 0x00:
        return toHexString(data).replace(" ", "")
    else:
        return None

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

def save_uid(uid,name):
    conn = sqlite3.connect(RM_ER)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO students (uid, name) VALUES (?, ?)", (uid, name))
    conn.commit()
    conn.close()

def write_attendance(name,in_time,out_time): #Send attendance to GG Sheet via Web App
    data = {"sts": "writelog", "name": name} #sts is to tell webapp what type of action is this
    if in_time and not out_time:
        data["inout"] = "IN"
    elif in_time and out_time:
        data["inout"] = f"{in_time} -> {out_time}"
    else:
        data["inout"] = ""
    try:
        response = requests.get(WEB_APP_URL, params=data, timeout=5)
    except:
        pass

def write_unknown(uid): 
    try:
        uid_clean = uid.replace(" ", "")
        response = requests.get(WEB_APP_URL, params={"sts": "writeuid", "uid": uid_clean}, timeout=20)
        print(f"DEBUG: UID={uid_clean} → HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def sync_members():
    try:
        response = requests.get(WEB_APP_URL, params={"sts": "getmembers"}, timeout=5)
        if response.status_code == 200:
            members = response.json()
            print("DEBUG: Syncing members from Web App:", members)
            for m in members:
                uid = m.get("uid")
                name = m.get("name")
                if uid and name:
                    save_uid(uid, name)
    except Exception as e:
        print("SYNC ERROR:", e)
   
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
            write_attendance(name, r_in, "23:59:59")

    # Handle today's session
    c.execute("SELECT id, in_time, out_time FROM attendance WHERE uid=? AND date=? ORDER BY id DESC LIMIT 1", (uid, today))
    today_row = c.fetchone()

    if today_row is None or today_row[2] is not None:  # No open session → IN
        c.execute("INSERT INTO attendance (uid, name, date, in_time) VALUES (?,?,?,?)", (uid, name, today, n_time))
        print(f"{name} - IN at {n_time}")
        write_attendance(name, n_time, "")
    else:  # Open session exists → OUT
        c.execute("UPDATE attendance SET out_time=? WHERE id=?", (n_time, today_row[0]))
        write_attendance(name, today_row[1], n_time)
        print(f"{name} - OUT at {n_time}")
    conn.commit()
    conn.close()
##############################################################################################
def main():
    db()
    sync_members()
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
                    write_unknown(uid)
                    sync_members()
                    students = load_uid()
                else:
                    name = students[uid]
                    log(uid,name)
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("BYE!")
        try:
            connection.disconnect()
        except Exception:
            pass
if __name__ == "__main__":
    main()