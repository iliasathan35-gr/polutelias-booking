from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta
import json
import uuid
import requests

app = Flask(__name__)
app.secret_key = "secret123"

DATA_FILE = "data.json"

# ---------------- DATA ----------------
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- TELEGRAM ----------------
def send_telegram(text):
    try:
        TOKEN = "8780779879:AAHKpT6H0aLiWQV85-08NvWh3l_xBEyHfLA"
        CHAT_ID = "8780021902"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except:
        pass

# ---------------- SERVICES ----------------
SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]

# ---------------- SLOTS ----------------
def generate_slots(day):
    if day == 6:
        return []

    slots = []

    if day == 5:
        start = datetime(2000, 1, 1, 10, 0)
        end = datetime(2000, 1, 1, 14, 0)
    else:
        start = datetime(2000, 1, 1, 11, 0)
        end = datetime(2000, 1, 1, 20, 0)

    while start <= end:
        slots.append(start.strftime("%H:%M"))
        start += timedelta(minutes=45)

    return slots

# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    data = load()
    today = datetime.now()

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        service = request.form.get("service")
        date = request.form.get("date")
        time = request.form.get("time")

        if not name or not phone or not service or not date or not time:
            return "❌ Συμπλήρωσε όλα τα πεδία"

        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

        # conflict check
        for d in data:
            if d["time"] == f"{date} {time}":
                return "❌ Ώρα κατειλημμένη"

        data.append({
            "name": name,
            "phone": phone,
            "service": service,
            "time": f"{date} {time}",
            "token": str(uuid.uuid4())
        })

        save(data)

        # Telegram
        send_telegram(
            f"💈 ΝΕΟ ΡΑΝΤΕΒΟΥ\n"
            f"{name}\n{phone}\n{service}\n{date} {time}"
        )

        return redirect("/success")

    # GET
    slots = generate_slots(today.weekday())

    today_str = today.strftime("%Y-%m-%d")

    booked = []
    for d in data:
        if d["time"].startswith(today_str):
            booked.append(d["time"].split(" ")[1])

    slot_status = []
    for s in slots:
        slot_status.append({
            "time": s,
            "status": "booked" if s in booked else "free"
        })

    return render_template(
        "index.html",
        services=SERVICES,
        slots=slot_status,
        today=today_str
    )

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    data = load()
    today = datetime.now()

    days = []

    for i in range(10):
        day = today + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")

        bookings = []

        for idx, d in enumerate(data):
            if d["time"].startswith(date_str):
                bookings.append({
                    "index": idx,
                    "name": d["name"],
                    "phone": d["phone"],
                    "service": d["service"],
                    "time": d["time"]
                })

        days.append({
            "date": date_str,
            "bookings": bookings
        })

    return render_template("admin.html", days=days)

# ---------------- EDIT ----------------
@app.route("/admin/edit/<int:index>", methods=["GET", "POST"])
def edit(index):
    data = load()

    if request.method == "POST":
        data[index]["name"] = request.form["name"]
        data[index]["phone"] = request.form["phone"]
        data[index]["service"] = request.form["service"]
        data[index]["time"] = request.form["time"]

        save(data)
        return redirect("/admin")

    return render_template("edit.html", b=data[index])

# ---------------- DELETE ----------------
@app.route("/admin/delete/<int:index>")
def delete(index):
    data = load()

    if 0 <= index < len(data):
        data.pop(index)

    save(data)
    return redirect("/admin")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == "admin":
            session["admin"] = True
            return redirect("/admin")
        return "❌ Λάθος password"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/success")
def success():
    return "✔ ΚΡΑΤΗΣΗ ΕΓΙΝΕ"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
