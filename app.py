from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta
import json
import uuid
import requests

# 🇬🇷 Ελληνικές μέρες & μήνες
days_gr = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]

months_gr = [
    "Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου",
    "Μαΐου", "Ιουνίου", "Ιουλίου", "Αυγούστου",
    "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"
]

app = Flask(__name__)
app.secret_key = "secret123"

DATA_FILE = "data.json"

SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]


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

    if request.method == "POST":

        name = request.form.get("name")
        phone = request.form.get("phone")
        service = request.form.get("service")
        date = request.form.get("date")
        time = request.form.get("time")

        if not name or not phone or not service or not date or not time:
            return "❌ Συμπλήρωσε όλα τα πεδία"

        try:
            dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except:
            return "❌ Λάθος ημερομηνία/ώρα"

        now = datetime.now()

        if dt.weekday() == 6:
            return "❌ Κυριακή κλειστά"

        if dt > now + timedelta(days=7):
            return "❌ Μέχρι 7 μέρες"

        if dt - now < timedelta(minutes=15):
            return "❌ Πολύ κοντά"

        for d in data:
            try:
                existing = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
                if abs((existing - dt).total_seconds()) < 2700:
                    return "❌ Ώρα κατειλημμένη"
            except:
                pass

        data.append({
            "name": name,
            "phone": phone,
            "service": service,
            "time": f"{date} {time}"
        })

        save(data)

        send_telegram(
            f"💈 ΝΕΟ ΡΑΝΤΕΒΟΥ!\n{name}\n{phone}\n{service}\n{date} {time}"
        )

        return redirect("/success")

    today_dt = datetime.now()
    slots = generate_slots(today_dt.weekday())

    booked = []
    today_str = today_dt.strftime("%Y-%m-%d")

    for d in data:
        if d["time"].startswith(today_str):
            booked.append(d["time"].split(" ")[1])

    available = [s for s in slots if s not in booked]

    return render_template(
        "index.html",
        services=SERVICES,
        slots=available,
        today=today_dt.strftime("%Y-%m-%d"),
        max_date=(today_dt + timedelta(days=7)).strftime("%Y-%m-%d")
    )


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

        slots = generate_slots(day.weekday())

        day_bookings = []
        booked_times = []

        for idx, d in enumerate(data):
            if d["time"].startswith(date_str):
                time_only = d["time"].split(" ")[1]
                booked_times.append(time_only)

                day_bookings.append({
                    "index": idx,
                    "name": d["name"],
                    "phone": d["phone"],
                    "service": d["service"],
                    "time": time_only
                })

        days.append({
            "date": date_str,
            "label": f"{days_gr[day.weekday()]} {day.day} {months_gr[day.month - 1]} {day.year}",
            "slots": slots,
            "bookings": day_bookings,
            "booked_times": booked_times
        })

    return render_template("admin.html", days=days)


# ---------------- ADMIN BOOK ----------------
@app.route("/admin/book/<date>/<time>")
def admin_book(date, time):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    data.append({
        "name": "ADMIN",
        "phone": "-",
        "service": "Manual booking",
        "time": f"{date} {time}",
        "token": str(uuid.uuid4())
    })

    save(data)
    return redirect("/admin")


# ---------------- EDIT ----------------
@app.route("/admin/edit/<int:index>", methods=["GET", "POST"])
def admin_edit(index):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    if index < 0 or index >= len(data):
        return redirect("/admin")

    if request.method == "POST":
        data[index]["name"] = request.form["name"]
        data[index]["phone"] = request.form["phone"]
        data[index]["service"] = request.form["service"]
        data[index]["time"] = request.form["time"]

        save(data)
        return redirect("/admin")

    return render_template("edit.html", b=data[index], index=index)


# ---------------- DELETE ----------------
@app.route("/admin/delete/<int:index>")
def admin_delete(index):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    if 0 <= index < len(data):
        data.pop(index)

    save(data)
    return redirect("/admin")


# ---------------- CANCEL WHOLE DAY ----------------
@app.route("/admin/delete-day/<date>")
def delete_day(date):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    data = [d for d in data if not d["time"].startswith(date)]

    save(data)
    return redirect("/admin")


# ---------------- SUCCESS ----------------
@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True)
