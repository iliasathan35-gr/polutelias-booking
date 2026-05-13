from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime, timedelta
import json
import uuid
import requests
import os
from pywebpush import webpush
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)


app = Flask(__name__)
import os

app.secret_key = os.environ.get("SECRET_KEY")

from datetime import timedelta

app.permanent_session_lifetime = timedelta(days=180)

DATA_FILE = "data.json"


# ---------------- DATA ----------------
def load():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, phone, service, time
        FROM appointments
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []

    for row in rows:
        data.append({
            "id": row[0],
            "name": row[0],
            "phone": row[1],
            "service": row[2],
            "time": row[3]
        })

    return data


def save(data):
    pass


BLOCKED_FILE = "blocked.json"


def load_blocked():

    try:

        with open(BLOCKED_FILE, "r") as f:
            return json.load(f)

    except:

        return {
            "days": [],
            "slots": []
        }


def save_blocked(data):

    with open(BLOCKED_FILE, "w") as f:
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

    blocked = load_blocked()

    # ❌ blocked whole day
    if date in blocked["days"]:
        return jsonify([])

    slots = generate_slots(dt.weekday())

    booked = []

    for d in data:

        if d["time"].startswith(date):

            booked.append(
                d["time"].split(" ")[1]
            )

    blocked_slots = [
        b["time"]
        for b in blocked["slots"]
        if b["date"] == date
    ]

    result = []

    for s in slots:

        # blocked ώρες να μη φαίνονται καθόλου
        if s in blocked_slots:
            continue

        if s in booked:
            result.append({
                "time": s,
                "status": "booked"
            })
        else:
            result.append({
                "time": s,
                "status": "free"
            })

    return jsonify(result)
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



# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    customer_name = session.get("customer_name")
    customer_phone = session.get("customer_phone")
    
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

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO appointments
            (name, phone, service, time)
            VALUES (%s, %s, %s, %s)
        """, (
            name,
            phone,
            service,
            f"{date} {time}"
        ))

        conn.commit()
        cur.close()
        conn.close()

        send_push_to_admins(
            "💈 Νέο ραντεβού",
            f"{name} - {service} - {date} {time}"
        )

        send_telegram(
            f"💈 ΝΕΟ ΡΑΝΤΕΒΟΥ!\n"
            f"Ονοματεπώνυμο: {name}\n"
            f"Τηλ: {phone}\n"
            f"Υπηρεσία: {service}\n"
            f"Ώρα: {date} {time}"
        )

        return redirect("/success")

    today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")
    max_date = (today_dt + timedelta(days=7)).strftime("%Y-%m-%d")

    return render_template(
    "index.html",
    services=SERVICES,
    today=today,
    max_date=max_date,
    customer_name=customer_name,
    customer_phone=customer_phone
)

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
            return redirect("/admin?enable_notifications=1")
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
    blocked = load_blocked()
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
                    
                    booking["id"] = d["id"]
                    
                    break

            is_blocked = False

            if date_str in blocked["days"]:
                is_blocked = True

            for b in blocked["slots"]:
                if b["date"] == date_str and b["time"] == s:
                    is_blocked = True

            day_slots.append({
                "time": s,
                "booking": booking,
                "blocked": is_blocked
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

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM appointments
        WHERE id=%s
    """, (index,))

    conn.commit()

    cur.close()
    conn.close()

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

        # 4 ώρες πριν λόγω UTC
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


try:
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(check_reminders, "interval", minutes=1)
    scheduler.start()

except Exception as e:
    print("Scheduler error:", e)

ADMIN_PUSH_FILE = "admin_push_subscriptions.json"


def load_admin_push_subscriptions():
    try:
        with open(ADMIN_PUSH_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_admin_push_subscriptions(data):
    with open(ADMIN_PUSH_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/admin/subscribe", methods=["POST"])
def admin_subscribe():
    if not session.get("admin"):
        return {"success": False}

    sub = request.get_json()

    subs = load_admin_push_subscriptions()

    if sub not in subs:
        subs.append(sub)
        save_admin_push_subscriptions(subs)

    return {"success": True}


def send_push_to_admins(title, body):
    subs = load_admin_push_subscriptions()

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
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
            print("Admin push error:", e)

@app.route("/admin/block-day/<date>")
def block_day(date):
    if not session.get("admin"):
        return redirect("/login")

    blocked = load_blocked()

    if date not in blocked["days"]:
        blocked["days"].append(date)

    save_blocked(blocked)

    return redirect("/admin")


@app.route("/admin/unblock-day/<date>")
def unblock_day(date):
    if not session.get("admin"):
        return redirect("/login")

    blocked = load_blocked()

    blocked["days"] = [
        d for d in blocked["days"]
        if d != date
    ]

    save_blocked(blocked)

    return redirect("/admin")


@app.route("/admin/block-slot/<date>/<path:time>")
def block_slot(date, time):
    if not session.get("admin"):
        return redirect("/login")

    blocked = load_blocked()

    item = {
        "date": date,
        "time": time
    }

    if item not in blocked["slots"]:
        blocked["slots"].append(item)

    save_blocked(blocked)

    return redirect("/admin")


@app.route("/admin/unblock-slot/<date>/<path:time>")
def unblock_slot(date, time):
    if not session.get("admin"):
        return redirect("/login")

    blocked = load_blocked()

    blocked["slots"] = [
        b for b in blocked["slots"]
        if not (b["date"] == date and b["time"] == time)
    ]

    save_blocked(blocked)

    return redirect("/admin")

# ---------------- CUSTOMER REGISTER ----------------
@app.route("/customer/register", methods=["GET", "POST"])
def customer_register():

    if request.method == "POST":

        name = request.form.get("name")
        phone = request.form.get("phone")
        password = request.form.get("password")

        if not name or not phone or not password:
            return "❌ Συμπλήρωσε όλα τα πεδία"

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM customers WHERE phone=%s",
            (phone,)
        )

        exists = cur.fetchone()

        if exists:

            cur.close()
            conn.close()

            return "❌ Υπάρχει ήδη λογαριασμός"

        cur.execute("""
            INSERT INTO customers
            (name, phone, password)
            VALUES (%s,%s,%s)
            RETURNING id
        """, (
            name,
            phone,
            password
        ))

        customer_id = cur.fetchone()[0]

        conn.commit()

        cur.close()
        conn.close()

        session.permanent = True

        session["customer_id"] = customer_id
        session["customer_name"] = name
        session["customer_phone"] = phone

        # μετά το register
        return redirect("/?enable_notifications=1")

    return render_template("customer_register.html")


# ---------------- CUSTOMER LOGIN ----------------
@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():

    if request.method == "POST":

        phone = request.form.get("phone")
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name, phone
            FROM customers
            WHERE phone=%s
            AND password=%s
        """, (
            phone,
            password
        ))

        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return "❌ Λάθος στοιχεία"

        session.permanent = True

        session["customer_id"] = user[0]
        session["customer_name"] = user[1]
        session["customer_phone"] = user[2]

        # μετά το login
        return redirect("/?enable_notifications=1")

    return render_template("customer_login.html")


# ---------------- CUSTOMER LOGOUT ----------------
@app.route("/customer/logout")
def customer_logout():

    session.clear()

    return redirect("/")

# ---------------- CUSTOMERS ----------------
@app.route("/admin/customers")
def admin_customers():

    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            name,
            phone,
            COUNT(*) as visits,
            MAX(time) as last_visit
        FROM appointments
        GROUP BY name, phone
        ORDER BY last_visit DESC
    """)

    rows = cur.fetchall()

    customers = []

    for r in rows:

        name = r[0]
        phone = r[1]
        visits = r[2]
        last_visit = r[3]

        # αγαπημένη υπηρεσία
        cur.execute("""
            SELECT service, COUNT(*) as c
            FROM appointments
            WHERE phone=%s
            GROUP BY service
            ORDER BY c DESC
            LIMIT 1
        """, (phone,))

        fav = cur.fetchone()

        favorite_service = fav[0] if fav else "-"

        # μέση συχνότητα
        cur.execute("""
            SELECT time
            FROM appointments
            WHERE phone=%s
            ORDER BY time ASC
        """, (phone,))

        dates = []
        
        for x in cur.fetchall():
            
            try:
                
                dates.append(
                    
                    datetime.strptime(
                        
                        x[0],
                        
                        "%Y-%m-%d %H:%M"
                    
                    )
                
                )
                
            except:
                
                pass

        avg_days = "-"

        if len(dates) >= 2:

            diffs = []

            for i in range(1, len(dates)):

                d1 = dates[i-1]
                d2 = dates[i]

                diffs.append(
                    (d2 - d1).days
                )

            avg_days = round(
                sum(diffs) / len(diffs)
            )

        customers.append({
            "name": name,
            "phone": phone,
            "visits": visits,
            "last_visit": last_visit,
            "favorite_service": favorite_service,
            "avg_days": avg_days
        })

    cur.close()
    conn.close()

    return render_template(
        "customers.html",
        customers=customers
    )

# ---------------- STATS ----------------
@app.route("/admin/stats")
def admin_stats():

    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # συνολικά
    cur.execute("""
        SELECT COUNT(*)
        FROM appointments
    """)

    total_appointments = cur.fetchone()[0]

    # σήμερα
    today = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE time LIKE %s
    """, (f"{today}%",))

    today_appointments = cur.fetchone()[0]

    # δημοφιλέστερη υπηρεσία
    cur.execute("""
        SELECT service, COUNT(*) as c
        FROM appointments
        GROUP BY service
        ORDER BY c DESC
        LIMIT 1
    """)

    fav = cur.fetchone()

    favorite_service = fav[0] if fav else "-"

    # top πελάτης
    cur.execute("""
        SELECT name, COUNT(*) as c
        FROM appointments
        GROUP BY name
        ORDER BY c DESC
        LIMIT 1
    """)

    top = cur.fetchone()

    top_customer = top[0] if top else "-"
    top_visits = top[1] if top else 0

    cur.close()
    conn.close()

    return render_template(
        "stats.html",
        total_appointments=total_appointments,
        today_appointments=today_appointments,
        favorite_service=favorite_service,
        top_customer=top_customer,
        top_visits=top_visits
    )

# ---------------- CUSTOMER PROFILE ----------------
@app.route("/admin/customer/<phone>")
def admin_customer_profile(phone):

    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # ραντεβού πελάτη
    cur.execute("""
        SELECT service, time
        FROM appointments
        WHERE phone=%s
        ORDER BY time DESC
    """, (phone,))

    appointments = cur.fetchall()

    # notes
    cur.execute("""
        SELECT note
        FROM customer_notes
        WHERE customer_phone=%s
        ORDER BY id DESC
    """, (phone,))

    notes = [x[0] for x in cur.fetchall()]

    customer_name = "-"

    if appointments:

        cur.execute("""
            SELECT name
            FROM appointments
            WHERE phone=%s
            LIMIT 1
        """, (phone,))

        row = cur.fetchone()

        if row:
            customer_name = row[0]

    cur.close()
    conn.close()

    return render_template(
        "customer_profile.html",
        customer_name=customer_name,
        phone=phone,
        appointments=appointments,
        notes=notes
    )

# ---------------- ADD CUSTOMER NOTE ----------------
@app.route("/admin/add-note", methods=["POST"])
def admin_add_note():

    if not session.get("admin"):
        return redirect("/login")

    phone = request.form.get("phone")
    note = request.form.get("note")

    if not phone or not note:
        return redirect("/admin/customers")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO customer_notes
        (customer_phone, note)
        VALUES (%s,%s)
    """, (
        phone,
        note
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect(f"/admin/customer/{phone}")

# ---------------- WAITLIST ----------------
@app.route("/waitlist/add", methods=["POST"])
def waitlist_add():

    data = request.get_json()

    name = data.get("name")
    phone = data.get("phone")
    service = data.get("service")
    date = data.get("date")
    time = data.get("time")

    if not all([name, phone, service, date, time]):
        return jsonify({
            "success": False
        })

    # trusted customer
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT priority
        FROM customers
        WHERE phone=%s
    """, (phone,))

    row = cur.fetchone()

    priority = False

    if row:
        priority = row[0]

    cur.execute("""
        INSERT INTO waitlist
        (name, phone, service, date, time, priority)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        name,
        phone,
        service,
        date,
        time,
        priority
    ))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "success": True
    })
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
