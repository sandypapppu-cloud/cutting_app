from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# DB CONNECTION
def get_conn():
    return psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")

# INIT DB
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS programs(
        id SERIAL PRIMARY KEY,
        program_no TEXT,
        fabric TEXT,
        dia TEXT,
        ptype TEXT,
        code TEXT,
        colour TEXT,
        size TEXT,
        ratio TEXT,
        roll TEXT,
        status TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        session["user"] = request.form["username"]
        return redirect("/dashboard")
    return render_template("login.html")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# PROGRAM PAGE
@app.route("/program", methods=["GET","POST"])
def program():

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    if request.method == "POST":
        program_no = "CP" + str(random.randint(1000,9999))
        date = datetime.now().strftime("%d-%m-%Y")

        cur.execute("""
        INSERT INTO programs
        (program_no,fabric,dia,ptype,code,colour,size,ratio,roll,status,date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            program_no,
            request.form["fabric"],
            request.form["dia"],
            request.form["ptype"],
            request.form["code"],
            request.form["colour"],
            request.form["size"],
            request.form["ratio"],
            request.form["roll"],
            "PENDING",
            date
        ))

        conn.commit()

    cur.execute("SELECT * FROM programs ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("program.html", data=data)

# DELETE (ONLY PROGRAM PAGE)
@app.route("/delete/<int:id>")
def delete(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM programs WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect("/program")

# REPORT PAGE
@app.route("/report")
def report():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM programs ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()
    return render_template("report.html", data=data)

# STATUS UPDATE (ONLY REPORT)
@app.route("/status/<int:id>", methods=["POST"])
def status(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE programs SET status=%s WHERE id=%s",
                (request.form["status"], id))
    conn.commit()
    conn.close()
    return redirect("/report")

# RUN
if __name__ == "__main__":
    app.run()
