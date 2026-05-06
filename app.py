from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime, timedelta
import json

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
        import requests

        TOKEN = "8780779879:AAHKpT6H0aLiWQV85-08NvWh3l_xBEyHfLA"
        CHAT_ID = "8780021902"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except:
        pass


# ---------------- SLOTS ----------------
def generate_slots(day):
    slots = []

    # Κυριακή κλειστά
    if day == 6:
        return []

    # Σάββατο
    if day == 5:
        start = datetime(2000, 1, 1, 10, 0)
        end = datetime(2000, 1, 1, 14, 0)
    else:
        # Καθημερινές
        start = datetime(2000, 1, 1, 11, 0)
        end = datetime(2000, 1, 1, 20, 0)

    while start <= end:
        slots.append(start.strftime("%H:%M"))
        start += timedelta(minutes=45)

    return slots


SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]


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

        if not name or not phone or not date or not time:
            return "❌ Συμπλήρωσε όλα τα πεδία"

        try:
            dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except:
            return "❌ Λάθος ημερομηνία ή ώρα"

        now = datetime.now()
        max_date = now + timedelta(days=7)

        if dt.weekday() == 6:
            return "❌ Κυριακή είμαστε κλειστά"

        if dt > max_date:
            return "❌ Μόνο έως 7 μέρες μπροστά"

        if dt - now < timedelta(minutes=15):
            return "❌ Δεν επιτρέπεται κράτηση <15 λεπτά πριν"

        for d in data:
            try:
                existing = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            except:
                continue

            if abs((existing - dt).total_seconds()) < 2700:
                return "❌ Ώρα κατειλημμένη"

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

    today = datetime.now()
    slots = generate_slots(today.weekday())

    booked = []
    for d in data:
        try:
            dt = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            booked.append(dt.strftime("%H:%M"))
        except:
            pass

    available = [s for s in slots if s not in booked]

    return render_template(
        "index.html",
        services=SERVICES,
        slots=available
    )


# ---------------- API ----------------
@app.route("/slots")
def slots_api():
    date = request.args.get("date")
    data = load()

    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except:
        return jsonify([])

    if dt.weekday() == 6:
        return jsonify([])

    slots = generate_slots(dt.weekday())

    booked = []
    for d in data:
        try:
            existing = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            if existing.strftime("%Y-%m-%d") == date:
                booked.append(existing.strftime("%H:%M"))
        except:
            pass

    available = [s for s in slots if s not in booked]

    return jsonify(available)


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
        day_date = today + timedelta(days=i)
        date_str = day_date.strftime("%Y-%m-%d")

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

# ---------------- ADD ----------------
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

    full_time = f"{date} {time}"

    for d in data:
        if d["time"] == full_time:
            return "❌ Ήδη κλεισμένο"

    data.append({
        "name": name,
        "phone": phone,
        "service": service,
        "time": full_time
    })

    save(data)
    return redirect("/admin")


# ---------------- EDIT ----------------
@app.route("/admin/edit/<int:index>", methods=["POST"])
def admin_edit(index):
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    name = request.form.get("name")
    phone = request.form.get("phone")
    service = request.form.get("service")
    date = request.form.get("date")
    time = request.form.get("time")

    full_time = f"{date} {time}"

    for i, d in enumerate(data):
        if i == index:
            continue
        if d["time"] == full_time:
            return "❌ Ήδη κλεισμένο"

    data[index] = {
        "name": name,
        "phone": phone,
        "service": service,
        "time": full_time
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
