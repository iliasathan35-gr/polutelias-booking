from flask import Flask, render_template, request, redirect
import json
from datetime import datetime, timedelta
app = Flask(__name__)
FILE = "data.json"

SERVICES = [
    "Κούρεμα",
    "Μούσι",
    "Κούρεμα + Μούσι"
]

def load():
    try:
        with open(FILE) as f:
            return json.load(f)
    except:
        return []

def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        time = request.form["time"]
        service = request.form["service"]

        for d in data:
            if d["time"] == time:
                return "Η ώρα είναι κατειλημμένη!"

        data.append({
            "name": name,
            "phone": phone,
            "time": time,
            "service": service
        })

        save(data)
        return redirect("/success")

    return render_template("index.html", services=SERVICES)

@app.route("/admin")
def admin():
    data = load()
    return render_template("admin.html", data=data)

@app.route("/success")
def success():
    return "Το ραντεβού κλείστηκε!"

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
