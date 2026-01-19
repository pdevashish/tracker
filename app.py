import requests, json, sqlite3
from flask import Flask, render_template, jsonify
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__, static_folder="static", template_folder="templates")

DB_FILE = "playback_log.db"
DATA_URL = "http://www.365gps.com/post_map_marker_list.php?log_state=&timezonemins=-330"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

session = requests.Session()
session.mount("http://", HTTPAdapter(max_retries=Retry(total=3)))

def init_db():
    with sqlite3.connect(DB_FILE) as c:
        cur = c.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS playback
            (id INTEGER PRIMARY KEY, imei TEXT, name TEXT, lat REAL, lng REAL, time TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS devices
            (imei TEXT PRIMARY KEY, name TEXT)""")
        c.commit()

def save_device(imei, name):
    with sqlite3.connect(DB_FILE) as c:
        c.execute("INSERT OR REPLACE INTO devices VALUES (?,?)", (imei, name))
        c.commit()

def get_imei_list():
    with sqlite3.connect(DB_FILE) as c:
        rows = c.execute("SELECT imei,name FROM devices").fetchall()
        return [{"imei": i, "name": n, "password": i[-6:]} for i, n in rows]

def fetch_gps(imei, name):
    try:
        r = session.get(DATA_URL, headers=HEADERS, timeout=10)
        data = json.loads(r.content.decode("utf-8-sig"))
        if data.get("aaData"):
            g = data["aaData"][0]
            t = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            lat, lng = float(g["lat_google"]), float(g["lng_google"])
            with sqlite3.connect(DB_FILE) as c:
                c.execute("INSERT INTO playback VALUES (NULL,?,?,?,?,?)",
                          (imei, name, lat, lng, t))
                c.commit()
            return {"imei": imei, "name": name, "lat": lat, "lng": lng}
    except:
        pass
    return {"imei": imei, "name": name, "lat": None, "lng": None}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/gps_data")
def gps_data():
    return jsonify([fetch_gps(d["imei"], d["name"]) for d in get_imei_list()])

@app.route("/playback_log")
def playback():
    with sqlite3.connect(DB_FILE) as c:
        rows = c.execute("SELECT imei,name,lat,lng,time FROM playback").fetchall()
        return jsonify([dict(zip(
            ["imei","name","lat","lng","time"], r)) for r in rows])

@app.route("/devices")
def devices():
    with sqlite3.connect(DB_FILE) as c:
        rows = c.execute("SELECT imei,name FROM devices").fetchall()
        return jsonify([{"imei":i,"name":n} for i,n in rows])

if __name__ == "__main__":
    init_db()

    # Add IMEIs once
    if not get_imei_list():
        n = int(input("How many IMEIs? "))
        for _ in range(n):
            i = input("IMEI: ")
            name = input("Name: ")
            save_device(i, name)

    print("🚀 http://127.0.0.1:5000")
    app.run(debug=True)
