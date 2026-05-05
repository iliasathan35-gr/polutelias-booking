from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = "secret123"

DATA_FILE = "data.json"


# ---------- DATA ----------
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------- TELEGRAM (optional) ----------
def send_telegram(text):
    try:
        import requests

    TELEGRAM_TOKEN = "8780779879:AAHKpT6H0aLiWQV85-08NvWh3l_xBEyHfLA"
    CHAT_ID = "8780021902"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except:
        pass


# ---------- SLOTS ----------
def generate_slots(day):
    return [
        "10:00", "10:30",
        "11:00", "11:30",
        "12:00", "12:30",
        "13:00", "13:30",
        "17:00", "17:30",
        "18:00", "18:30",
        "19:00"
    ]


SERVICES = ["Κούρεμα", "Μούσι", "Κούρεμα + Μούσι"]


# ---------- INDEX (BOOKING) ----------
@app.route("/", methods=["GET", "POST"])
def index():
    data = load()

    if request.method == "POST":

        name = request.form.get("name")
        phone = request.form.get("phone")
        service = request.form.get("service")
        date = request.form.get("date")
        time = request.form.get("time")

        # safety check
        if not name or not phone or not date or not time:
            return "❌ Συμπλήρωσε όλα τα πεδία"

        try:
            dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except:
            return "❌ Λάθος ημερομηνία ή ώρα"

        now = datetime.now()

        # 15 min rule
        if dt - now < timedelta(minutes=15):
            return "Δεν επιτρέπεται κράτηση <15 λεπτά πριν 💈"

        # overlap check
        for d in data:
            try:
                existing = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            except:
                continue

            if abs((existing - dt).total_seconds()) < 2700:
                return "Ώρα κατειλημμένη 💈"

        # save
        data.append({
            "name": name,
            "phone": phone,
            "service": service,
            "time": f"{date} {time}"
        })

        save(data)

        # telegram
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


# ---------- ADMIN ----------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    data = load()

    booked = []
    for d in data:
        try:
            dt = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
            booked.append(dt.strftime("%H:%M"))
        except:
            pass

    return render_template(
        "admin.html",
        data=data,
        slots=generate_slots(datetime.now().weekday()),
        booked=booked
    )


# ---------- EDIT ----------
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

    if not name or not phone or not date or not time:
        return "❌ Συμπλήρωσε όλα τα πεδία"

    try:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except:
        return "❌ Λάθος ημερομηνία ή ώρα"

    for i, d in enumerate(data):
        if i == index:
            continue

        try:
            existing = datetime.strptime(d["time"], "%Y-%m-%d %H:%M")
        except:
            continue

        if abs((existing - dt).total_seconds()) < 2700:
            return "Ώρα κατειλημμένη 💈"

    data[index] = {
        "name": name,
        "phone": phone,
        "service": service,
        "time": f"{date} {time}"
    }

    save(data)
    return redirect("/admin")


# ---------- DELETE ----------
@app.route("/cancel/<int:index>")
def cancel(index):
    data = load()

    if 0 <= index < len(data):
        data.pop(index)
        save(data)

    return redirect("/admin")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "admin":
            session["admin"] = True
            return redirect("/admin")
        return "❌ Λάθος password"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- SUCCESS ----------
@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True)
