from flask import Flask, render_template, request, redirect, session
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "change_this_secret_key"

FILE = "data.json"

SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]
ADMIN_PASSWORD = "1234"

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
# SLOTS (RULES)
# --------------------
def generate_slots(day):
    slots = []

    # Κυριακή κλειστά
    if day == 6:
        return []

    # Σάββατο 10:00 - 14:00
    if day == 5:
        start_hour = 10
        end_hour = 14
    else:
        # Δευτέρα - Παρασκευή 11:00 - 20:00
        start_hour = 11
        end_hour = 20

    current = datetime(2000, 1, 1, start_hour, 0)
    end = datetime(2000, 1, 1, end_hour, 0)

    while current + timedelta(minutes=45) <= end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=45)

    return slots

# --------------------
# HOME (BOOKING)
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

        # ❗ 15 λεπτά πριν rule
        if dt - now < timedelta(minutes=15):
            return "Δεν επιτρέπεται κράτηση λιγότερο από 15 λεπτά πριν 💈"

        day = dt.weekday()

        # ❌ Κυριακή
        if day == 6:
            return "Κυριακή δεν λειτουργεί 💈"

        # ❌ Σάββατο εκτός ωραρίου
        if day == 5 and (dt.hour < 10 or dt.hour >= 14):
            return "Σάββατο μόνο 10:00 - 14:00"

        # ❌ Δευτέρα - Παρασκευή εκτός ωραρίου
        if day <= 4 and (dt.hour < 11 or dt.hour >= 20):
            return "Ωράριο 11:00 - 20:00"

        new_start = dt
        new_end = dt + timedelta(minutes=45)

        # overlap check
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

    return render_template(
        "index.html",
        services=SERVICES,
        slots=generate_slots(datetime.now().weekday())
    )

# --------------------
# LOGIN (ADMIN)
# --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        return "Λάθος password"

    return render_template("login.html")

# --------------------
# ADMIN DASHBOARD
# --------------------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    data = load()
    return render_template("admin.html", data=data)

# --------------------
# CANCEL APPOINTMENT
# --------------------
@app.route("/cancel/<int:index>")
def cancel(index):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    if 0 <= index < len(data):
        data.pop(index)
        save(data)

    return redirect("/admin")

# --------------------
# LOGOUT
# --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --------------------
# SUCCESS PAGE
# --------------------
@app.route("/success")
def success():
    return "Το ραντεβού κλείστηκε! 💈"

# --------------------
# RUN SERVER
# --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
