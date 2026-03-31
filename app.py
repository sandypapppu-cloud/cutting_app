from flask import Flask, render_template, request, redirect, session, send_file
import psycopg2
import os
import random
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB CONNECTION ----------------
def get_conn():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        sslmode="require"
    )

# ---------------- INIT DB ----------------
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
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- USERS ----------------
users = {
    "admin": "123",
    "user": "123"
}

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        if u in users and users[u] == p:
            session["user"] = u
            return redirect("/")
        return "Invalid Login"

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- HOME ----------------
@app.route("/", methods=["GET","POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        program_no = "CP" + str(random.randint(1000,9999))

        fabric = request.form["fabric"]
        dia = request.form["dia"]
        ptype = request.form["ptype"]
        code = request.form["code"]

        sizes = request.form["sizes"].split(",")
        ratios = request.form["ratio"].split(",")

        colours = request.form["colours"].split(",")
        rolls = request.form["rolls"].split(",")

        size_text = ":".join([s.strip() for s in sizes])
        ratio_text = ":".join([r.strip() for r in ratios])

        conn = get_conn()
        cur = conn.cursor()

        for i in range(len(colours)):
            if rolls[i].strip() != "":
                cur.execute("""
                INSERT INTO programs
                (program_no,fabric,dia,ptype,code,colour,size,ratio,roll,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    program_no,
                    fabric,
                    dia,
                    ptype,
                    code,
                    colours[i].strip().upper(),
                    size_text,
                    ratio_text,
                    rolls[i].strip(),
                    "PENDING"
                ))

        conn.commit()
        conn.close()

        return redirect("/")

    status_filter = request.args.get("status")

    conn = get_conn()
    cur = conn.cursor()

    if status_filter and status_filter != "ALL":
        cur.execute("SELECT * FROM programs WHERE status=%s", (status_filter,))
    else:
        cur.execute("SELECT * FROM programs ORDER BY id DESC")

    rows = cur.fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        grouped.setdefault(row[1], []).append(row)

    return render_template("index.html", grouped=grouped, user=session["user"])


# ---------------- STATUS ----------------
@app.route("/status/<int:id>", methods=["POST"])
def update_status(id):
    status = request.form["status"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE programs SET status=%s WHERE id=%s", (status, id))

    conn.commit()
    conn.close()

    return redirect("/")


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM programs WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect("/")


# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit(id):

    conn = get_conn()
    cur = conn.cursor()

    if request.method == "POST":
        roll = request.form["roll"]
        cur.execute("UPDATE programs SET roll=%s WHERE id=%s", (roll, id))
        conn.commit()
        conn.close()
        return redirect("/")

    cur.execute("SELECT * FROM programs WHERE id=%s", (id,))
    row = cur.fetchone()
    conn.close()

    return render_template("edit.html", row=row)


# ---------------- PROGRAM VIEW ----------------
@app.route("/program/<program_no>")
def program_view(program_no):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM programs WHERE program_no=%s", (program_no,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No Data"

    data = {
        "program_no": rows[0][1],
        "fabric": rows[0][2],
        "dia": rows[0][3],
        "ptype": rows[0][4],
        "code": rows[0][5],
        "size": rows[0][7],
        "ratio": rows[0][8],
        "status": rows[0][10]
    }

    colour_data = [(r[6], r[9], r[10]) for r in rows]

    sizes = data["size"].split(":")
    ratios = data["ratio"].split(":")

    return render_template(
        "program.html",
        data=data,
        sizes=sizes,
        ratios=ratios,
        colour_data=colour_data
    )


# ---------------- EXPORT ----------------
@app.route("/export")
def export():

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM programs", conn)
    conn.close()

    file = "report.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
