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
# SLOTS BY DAY
# --------------------
def generate_slots(day):
    slots = []

    if day == 6:  # Κυριακή ❌
        return []

    if day == 5:  # Σάββατο 10-14
        start_hour = 10
        end_hour = 14
    else:  # Δευ-Παρ 11-20
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

        dt = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M")

        now = datetime.now()

        # ❗ CUT-OFF 15 λεπτά πριν
        if dt - now < timedelta(minutes=15):
            return "Δεν επιτρέπεται κράτηση λιγότερο από 15 λεπτά πριν 💈"

        day = dt.weekday()

        # ❌ Κυριακή
        if day == 6:
            return "Κυριακή δεν λειτουργεί 💈"

        # ❌ Σάββατο εκτός ωραρίου
        if day == 5 and (dt.hour < 10 or dt.hour >= 14):
            return "Σάββατο μόνο 10:00 - 14:00"

        # ❌ Δευ-Παρ εκτός ωραρίου
        if day <= 4 and (dt.hour < 11 or dt.hour >= 20):
            return "Ωράριο 11:00 - 20:00"

        new_start = dt
        new_end = new_start + timedelta(minutes=45)

        for d in data:
            existing_start = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            existing_end = existing_start + timedelta(minutes=45)

            if new_start < existing_end and new_end > existing_start:
                return "Υπάρχει ήδη ραντεβού 💈"

        data.append({
            "name": name,
            "phone": phone,
            "service": service,
            "time": date + " " + time
        })

        save(data)
        return redirect("/success")

    today = datetime.now().weekday()

    return render_template(
        "index.html",
        services=SERVICES,
        slots=generate_slots(today)
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
# RUN
# --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
