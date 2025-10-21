import sqlite3
from datetime import datetime
from smartcard.System import readers
from smartcard.util import toHexString
import time
import requests
from gpiozero import LED

red = LED(17)     # Error
yellow = LED(27)  # Unregistered card
green = LED(22)   # Successful log

BLINK_DURATION = 2  # seconds

def led_clear():
    red.off()
    yellow.off()
    green.off()

def led_error():
    led_clear()
    red.on()
    time.sleep(BLINK_DURATION)
    red.off()

def led_unregistered():
    led_clear()
    yellow.on()
    time.sleep(BLINK_DURATION)
    yellow.off()

def led_success():
    led_clear()
    green.on()
    time.sleep(BLINK_DURATION)
    green.off()

DB_FILE = "RM_ers.db"

def db():
    conn = sqlite3.connect(DB_FILE)
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

def load_uid():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT uid, name FROM students")
    students = {uid: name for uid, name in c.fetchall()}
    conn.close()
    return students

def save_uid(uid, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO students (uid, name) VALUES (?, ?)", (uid, name))
    conn.commit()
    conn.close()

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzrpKS0YejsJEfJEs3dXQ_4cYo-TOGerj6ZrjhtozNJ5N5nHb9O9V4XqSODv6l7098bEg/exec"

def write_attendance(name, in_time, out_time):
    data = {"sts": "writelog", "name": name}
    if in_time and not out_time:
        data["inout"] = "IN"
    elif in_time and out_time:
        data["inout"] = f"{in_time} -> {out_time}"
    else:
        data["inout"] = ""
    try:
        response = requests.get(WEB_APP_URL, params=data, timeout=5)
        if response.status_code == 200:
            print(f"[DEBUG] Attendance sent → HTTP {response.status_code}: {response.text}")
            return True
        else:
            print(f"[DEBUG] Web response error → HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print("Attendance log error:", e)
        return False

def write_unknown(uid):
    try:
        uid_clean = uid.replace(" ", "")
        response = requests.get(WEB_APP_URL, params={"sts": "writeuid", "uid": uid_clean}, timeout=20)
        print(f"[DEBUG] UID={uid_clean} → HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print("Unknown UID error:", e)

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
        led_error()

r = readers()
reader = r[0]
l_seen = {}
d_sec = 1.5  # debounce time

def get_uid(connection):
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(GET_UID)
    if sw1 == 0x90 and sw2 == 0x00:
        return toHexString(data).replace(" ", "")
    return None

def log(uid, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    n_time = datetime.now().strftime("%H:%M:%S")
    try:
        # Close previous open sessions
        c.execute("SELECT id, date, in_time, out_time FROM attendance WHERE uid=? AND out_time IS NULL ORDER BY date ASC", (uid,))
        rows = c.fetchall()
        for r_id, r_date, r_in, r_out in rows:
            if r_date < today:
                c.execute("UPDATE attendance SET out_time=? WHERE id=?", ("23:59:59", r_id))
                write_attendance(name, r_in, "23:59:59")

        # Handle today's session
        c.execute("SELECT id, in_time, out_time FROM attendance WHERE uid=? AND date=? ORDER BY id DESC LIMIT 1", (uid, today))
        today_row = c.fetchone()

        if today_row is None or today_row[2] is not None:
            c.execute("INSERT INTO attendance (uid, name, date, in_time) VALUES (?,?,?,?)", (uid, name, today, n_time))
            print(f"{name} - IN at {n_time}")
            success = write_attendance(name, n_time, "")
        else:
            c.execute("UPDATE attendance SET out_time=? WHERE id=?", (n_time, today_row[0]))
            success = write_attendance(name, today_row[1], n_time)
            print(f"{name} - OUT at {n_time}")

        conn.commit()

        if success:
            led_success()
        else:
            led_error()

    except Exception as e:
        print("Logging error:", e)
        led_error()
    finally:
        conn.close()

def main():
    db()
    sync_members()
    students = load_uid()
    last_sync = time.time()
    print("Ready. Tap cards. Ctrl+C to exit.")
    try:
        while True:
            connection = reader.createConnection()
            uid = None
            try:
                connection.connect()
                uid = get_uid(connection)
                print(f"[DEBUG] UID detected: {uid}")
            except Exception as e:
                print("Reader connect error:", e)
                uid = None
            finally:
                try:
                    connection.disconnect()
                except Exception:
                    pass

            if uid:
                now_epo = time.time()
                if uid in l_seen and (now_epo - l_seen[uid]) < d_sec:
                    time.sleep(0.1)
                    continue
                l_seen[uid] = now_epo

                # Sync members on every tap
                sync_members()
                students = load_uid()

                # Hourly sync
                if now_epo - last_sync > 3600:
                    print("[DEBUG] Performing hourly sync...")
                    sync_members()
                    students = load_uid()
                    last_sync = now_epo

                if uid not in students:
                    print(f"Unknown card detected: {uid}")
                    write_unknown(uid)
                    led_unregistered()
                    # Resync after sending UID
                    sync_members()
                    students = load_uid()
                else:
                    name = students[uid]
                    log(uid, name)

            time.sleep(0.3)
    except KeyboardInterrupt:
        print("BYE!")
        led_clear()
        try:
            connection.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    main()
