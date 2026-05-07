from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta
import json
import uuid
import requests
import os
from pywebpush import webpush
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
import os

app.secret_key = os.environ.get("SECRET_KEY")

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
            f"Ονοματεπώνυμο: {name}\n"
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

    greek_days = {
        "Monday": "Δευτέρα",
        "Tuesday": "Τρίτη",
        "Wednesday": "Τετάρτη",
        "Thursday": "Πέμπτη",
        "Friday": "Παρασκευή",
        "Saturday": "Σάββατο",
        "Sunday": "Κυριακή"
    }

    for i in range(10):
        day = today + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")

        english_day = day.strftime("%A")
        greek_day = greek_days[english_day]
        formatted_date = f"{greek_day} {day.strftime('%d/%m/%Y')}"

        slots = generate_slots(day.weekday())
        day_slots = []

        for s in slots:
            full_time = f"{date_str} {s}"

            booking = None

            for idx, d in enumerate(data):
                if d["time"] == full_time:
                    booking = d.copy()
                    booking["index"] = idx
                    break

            day_slots.append({
                "time": s,
                "booking": booking
            })

        days.append({
            "date": formatted_date,
            "real_date": date_str,
            "slots": day_slots
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

PUSH_FILE = "push_subscriptions.json"

def load_push_subscriptions():
    try:
        with open(PUSH_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_push_subscriptions(data):
    with open(PUSH_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/vapid-public-key")
def vapid_public_key():
    return {"publicKey": os.environ.get("VAPID_PUBLIC_KEY")}

@app.route("/subscribe", methods=["POST"])
def subscribe():
    payload = request.get_json()

    phone = payload.get("phone")
    subscription = payload.get("subscription")

    if not phone or not subscription:
        return {"success": False}

    subs = load_push_subscriptions()

    # σβήνουμε παλιό ίδιο phone
    subs = [s for s in subs if s.get("phone") != phone]

    subs.append({
        "phone": phone,
        "subscription": subscription
    })

    save_push_subscriptions(subs)

    return {"success": True}

def send_push_to_phone(phone, title, body):
    subs = load_push_subscriptions()

    for item in subs:
        if item.get("phone") == phone:
            try:
                webpush(
                    subscription_info=item["subscription"],
                    data=json.dumps({
                        "title": title,
                        "body": body
                    }),
                    vapid_private_key=os.environ.get("VAPID_PRIVATE_KEY"),
                    vapid_claims={
                        "sub": os.environ.get("VAPID_EMAIL")
                    }
                )
            except Exception as e:
                print("Push error:", e)

# 4 ώρες πριν (λόγω UTC)
if timedelta(hours=3, minutes=59) <= time_left <= timedelta(hours=4, minutes=1):

def check_reminders():

    data = load()

    now = datetime.now()

    changed = False

    for d in data:

        if d.get("reminder_sent"):
            continue

        try:

            appointment_time = datetime.strptime(
                d["time"],
                "%Y-%m-%d %H:%M"
            )

        except:
            continue

        time_left = appointment_time - now

        # 4 ώρες πριν (λόγω UTC)
        if timedelta(hours=3, minutes=59) <= time_left <= timedelta(hours=4, minutes=1):

            phone = d.get("phone")

            send_push_to_phone(
                phone,
                "Polutelias 💈",
                "Το ραντεβού σας είναι σε 1 ώρα"
            )

            d["reminder_sent"] = True

            changed = True

    if changed:
        save(data)


scheduler = BackgroundScheduler()

scheduler.add_job(
    check_reminders,
    "interval",
    minutes=1
)

scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
