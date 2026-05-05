from flask import Flask, render_template, request, redirect, session
import json
import os
from datetime import datetime, timedelta
import requests

app = Flask(__name__)
app.secret_key = "change_this_key"

FILE = "data.json"

SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]
ADMIN_PASSWORD = "1234"

# ---------------- TELEGRAM ----------------
TELEGRAM_TOKEN = "8780779879:AAHKpT6H0aLiWQV85-08NvWh3l_xBEyHfLA"
CHAT_ID = "8780021902"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ---------------- LOAD / SAVE ----------------
def load():
    try:
        with open(FILE) as f:
            return json.load(f)
    except:
        return []

def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- SLOTS ----------------
def generate_slots(day):
    if day == 6:
        return []

    if day == 5:
        start, end = 10, 14
    else:
        start, end = 11, 20

    slots = []
    current = datetime(2000, 1, 1, start, 0)
    limit = datetime(2000, 1, 1, end, 0)

    while current + timedelta(minutes=45) <= limit:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=45)

    return slots

# ---------------- HOME ----------------
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

        if dt - now < timedelta(minutes=15):
            return "Δεν επιτρέπεται κράτηση <15 λεπτά πριν 💈"

        # overlap check
        for d in data:
            existing = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            if abs((existing - dt).total_seconds()) < 2700:
                return "Ώρα κατειλημμένη 💈"

        data.append({
            "name": name,
            "phone": phone,
            "service": service,
            "time": date + " " + time
        })

        save(data)

        # 🔔 TELEGRAM NOTIFICATION
        send_telegram(
            f"💈 ΝΕΟ ΡΑΝΤΕΒΟΥ!\n"
            f"Όνομα: {name}\n"
            f"Τηλ: {phone}\n"
            f"Υπηρεσία: {service}\n"
            f"Ώρα: {date} {time}"
        )

        return redirect("/success")

    return render_template(
        "index.html",
        services=SERVICES,
        slots=generate_slots(datetime.now().weekday())
    )

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        return "Λάθος password"

    return render_template("login.html")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    return render_template("admin.html", data=load())

# ---------------- CANCEL ----------------
@app.route("/cancel/<int:index>")
def cancel(index):
    if not session.get("admin"):
        return redirect("/login")

    data = load()
    if 0 <= index < len(data):
        data.pop(index)
        save(data)

    return redirect("/admin")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- SUCCESS ----------------
@app.route("/success")
def success():
    return render_template("success.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
