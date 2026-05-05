from flask import Flask, render_template, request, redirect
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
FILE = "data.json"

SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]

# --------------------
# LOAD / SAVE
# --------------------
def load():
    try:
        with open(FILE) as f:
            return json.load(f)
    except:
        return []

def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

# --------------------
# SLOTS (11:00 - 20:00, 45min)
# --------------------
def generate_slots():
    slots = []
    start_hour = 11
    end_hour = 20

    current = datetime(2000, 1, 1, start_hour, 0)
    end = datetime(2000, 1, 1, end_hour, 0)

    while current + timedelta(minutes=45) <= end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=45)

    return slots

# --------------------
# HOME
# --------------------
@app.route("/", methods=["GET", "POST"])
def index():
    data = load()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        service = request.form["service"]

        date = request.form["date"]
        time = request.form["time"]

        datetime_str = date + " " + time

        new_start = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        new_end = new_start + timedelta(minutes=45)

        # overlap check
        for d in data:
            existing_start = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            existing_end = existing_start + timedelta(minutes=45)

            if new_start < existing_end and new_end > existing_start:
                return "Υπάρχει ήδη ραντεβού σε αυτό το χρονικό διάστημα 💈"

        data.append({
            "name": name,
            "phone": phone,
            "service": service,
            "time": datetime_str
        })

        save(data)
        return redirect("/success")

    return render_template(
        "index.html",
        services=SERVICES,
        slots=generate_slots()
    )

# --------------------
# ADMIN
# --------------------
@app.route("/admin")
def admin():
    data = load()
    return render_template("admin.html", data=data)

# --------------------
# SUCCESS
# --------------------
@app.route("/success")
def success():
    return "Το ραντεβού κλείστηκε! 💈"

# --------------------
# RUN (Render ready)
# --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
