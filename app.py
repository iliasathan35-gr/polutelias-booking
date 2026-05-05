from flask import Flask, render_template, request, redirect, session
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET"

# =====================
# ΡΥΘΜΙΣΕΙΣ (ΑΛΛΑΖΕΙΣ ΕΔΩ)
# =====================
ADMIN_PASSWORD = "ilias123579"
FILE = "data.json"

WORK_HOURS = {
    "weekday_start": 11,
    "weekday_end": 20,
    "saturday_start": 10,
    "saturday_end": 14
}

SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]

# =====================
# LOAD / SAVE
# =====================
def load():
    try:
        with open(FILE) as f:
            return json.load(f)
    except:
        return []

def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

# =====================
# SLOTS
# =====================
def generate_slots(day):
    if day == 6:
        return []

    if day == 5:
        start = WORK_HOURS["saturday_start"]
        end = WORK_HOURS["saturday_end"]
    else:
        start = WORK_HOURS["weekday_start"]
        end = WORK_HOURS["weekday_end"]

    slots = []
    current = datetime(2000, 1, 1, start, 0)
    limit = datetime(2000, 1, 1, end, 0)

    while current + timedelta(minutes=45) <= limit:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=45)

    return slots

# =====================
# FREE SLOTS
# =====================
def get_free_slots(data, day):
    all_slots = generate_slots(day)
    booked = {d["time"].split(" ")[1] for d in data}
    return [s for s in all_slots if s not in booked]

# =====================
# HOME
# =====================
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

        # 15 λεπτά rule
        if dt - now < timedelta(minutes=15):
            return "Δεν επιτρέπεται κράτηση < 15 λεπτά πριν 💈"

        day = dt.weekday()

        if day == 6:
            return "Κυριακή κλειστά 💈"

        if day == 5 and (dt.hour < WORK_HOURS["saturday_start"] or dt.hour >= WORK_HOURS["saturday_end"]):
            return "Σάββατο 10:00 - 14:00"

        if day <= 4 and (dt.hour < WORK_HOURS["weekday_start"] or dt.hour >= WORK_HOURS["weekday_end"]):
            return "Ωράριο 11:00 - 20:00"

        for d in data:
            existing = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            if abs((existing - dt).total_seconds()) < 2700:
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
        slots=get_free_slots(load(), datetime.now().weekday())
    )

# =====================
# LOGIN
# =====================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        return "Λάθος password"

    return render_template("login.html")

# =====================
# ADMIN
# =====================
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    return render_template("admin.html", data=load())

# =====================
# CANCEL
# =====================
@app.route("/cancel/<int:index>")
def cancel(index):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    if 0 <= index < len(data):
        data.pop(index)
        save(data)

    return redirect("/admin")

# =====================
# LOGOUT
# =====================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =====================
# SUCCESS
# =====================
@app.route("/success")
def success():
    return "Το ραντεβού κλείστηκε 💈"

# =====================
# RUN
# =====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
