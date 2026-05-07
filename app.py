from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import uuid
import requests

app = Flask(__name__)
GREECE_TZ = ZoneInfo("Europe/Athens")
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


SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]
from flask import jsonify

@app.route("/slots")
def slots_api():
    date = request.args.get("date")
    data = load()

    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except:
        return jsonify([])

    # ❌ Κυριακή
    if dt.weekday() == 6:
        return jsonify([])

    slots = generate_slots(dt.weekday())

    booked = []
    for d in data:
        if d["time"].startswith(date):
            booked.append(d["time"].split(" ")[1])

    available = [s for s in slots if s not in booked]

    return jsonify(available)


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

        datetime.now()

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

        # ✅ SAVE
        data.append({
            "name": name,
            "phone": phone,
            "service": service,
            "time": f"{date} {time}"
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

    # ---------------- GET ----------------

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
                t = d["time"].split(" ")[1]
                booked_times.append(t)

                day_bookings.append({
                    "index": idx,
                    "name": d["name"],
                    "phone": d["phone"],
                    "service": d["service"],
                    "time": d["time"],
                    "status": "booked"
                })

        # 🔥 FREE slots
        free_slots = []
        for s in slots:
            if s not in booked_times:
                free_slots.append({
                    "time": s,
                    "status": "free"
                })

        days.append({
            "date": date_str,
            "bookings": day_bookings,
            "free_slots": free_slots
        })

    return render_template("admin.html", days=days)


# ---------------- ADD (ADMIN) ----------------
@app.route("/admin/add", methods=["POST"])
def admin_add():
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    name = request.form.get("name")
    phone = request.form.get("phone")
    service = request.form.get("service")
    date = request.form.get("date")
    time = request.form.get("time")

    if not date or not time:
        return "❌ Missing date/time"

    full_time = f"{date} {time}"

    for d in data:
        if d["time"] == full_time:
            return "❌ Ώρα κατειλημμένη"

    data.append({
        "name": name,
        "phone": phone,
        "service": service,
        "time": full_time,
        "token": str(uuid.uuid4())
    })

    save(data)

    send_telegram(f"💈 ADMIN ΝΕΟ ΡΑΝΤΕΒΟΥ!\n{name}\n{phone}\n{service}\n{full_time}")

    return redirect("/admin")


# ---------------- EDIT ----------------
@app.route("/admin/edit/<int:index>", methods=["POST"])
def admin_edit(index):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    date = request.form.get("date")
    time = request.form.get("time")

    data[index] = {
        "name": request.form.get("name"),
        "phone": request.form.get("phone"),
        "service": request.form.get("service"),
        "time": f"{date} {time}",
        "token": data[index].get("token", str(uuid.uuid4()))
    }

    save(data)
    return redirect("/admin")


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


# ---------------- SUCCESS ----------------
@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True)
