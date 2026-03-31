from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import psycopg2, os, random, pandas as pd
from datetime import datetime

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

    # MAIN TABLE
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

    # MASTER TABLES
    cur.execute("CREATE TABLE IF NOT EXISTS fabric_master(name TEXT UNIQUE)")
    cur.execute("CREATE TABLE IF NOT EXISTS size_master(name TEXT UNIQUE)")
    cur.execute("CREATE TABLE IF NOT EXISTS colour_master(name TEXT UNIQUE)")

    # CODE MASTER
    cur.execute("""
    CREATE TABLE IF NOT EXISTS code_master(
        id SERIAL PRIMARY KEY,
        code TEXT,
        fabric TEXT,
        gsm TEXT,
        dia TEXT,
        ptype TEXT,
        sizes TEXT,
        colours TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        session["user"] = request.form["username"]
        return redirect("/dashboard")
    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# ---------------- MASTER ----------------
@app.route("/master", methods=["GET","POST"])
def master():

    if "user" not in session:
        return redirect("/")

    conn = get_conn()
    cur = conn.cursor()

    # ADD MASTER DATA
    if request.method == "POST":
        table = request.form["type"]
        name = request.form["name"]

        cur.execute(f"INSERT INTO {table}(name) VALUES (%s) ON CONFLICT DO NOTHING",(name,))
        conn.commit()

    # FETCH MASTER DATA
    cur.execute("SELECT * FROM fabric_master")
    fabrics = cur.fetchall()

    cur.execute("SELECT * FROM size_master")
    sizes = cur.fetchall()

    cur.execute("SELECT * FROM colour_master")
    colours = cur.fetchall()

    conn.close()

    return render_template("master.html", fabrics=fabrics, sizes=sizes, colours=colours)

# ---------------- ADD CODE MASTER ----------------
@app.route("/add_code", methods=["POST"])
def add_code():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO code_master(code,fabric,gsm,dia,ptype,sizes,colours)
    VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        request.form["code"],
        request.form["fabric"],
        request.form["gsm"],
        request.form["dia"],
        request.form["ptype"],
        request.form["sizes"],
        request.form["colours"]
    ))

    conn.commit()
    conn.close()

    return redirect("/master")

# ---------------- PROGRAM ----------------
@app.route("/program", methods=["GET","POST"])
def program():

    if "user" not in session:
        return redirect("/")

    conn = get_conn()
    cur = conn.cursor()

    # SAVE PROGRAM
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

    # FETCH PROGRAM DATA
    cur.execute("SELECT * FROM programs ORDER BY id DESC")
    data = cur.fetchall()

    # LOAD CODE LIST
    cur.execute("SELECT code FROM code_master")
    codes = [x[0] for x in cur.fetchall()]

    conn.close()

    return render_template("program.html", data=data, codes=codes)

# ---------------- GET CODE DETAILS ----------------
@app.route("/get_code/<code>")
def get_code(code):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM code_master WHERE code=%s",(code,))
    row = cur.fetchone()

    conn.close()

    if row:
        return jsonify({
            "fabric": row[2],
            "dia": row[4]
        })
    else:
        return jsonify({})

# ---------------- DELETE PROGRAM ----------------
@app.route("/delete/<int:id>")
def delete(id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM programs WHERE id=%s",(id,))

    conn.commit()
    conn.close()

    return redirect("/program")

# ---------------- REPORT ----------------
@app.route("/report")
def report():

    if "user" not in session:
        return redirect("/")

    conn = get_conn()
    cur = conn.cursor()

    status = request.args.get("status")

    if status and status != "ALL":
        cur.execute("SELECT * FROM programs WHERE status=%s ORDER BY id DESC",(status,))
    else:
        cur.execute("SELECT * FROM programs ORDER BY id DESC")

    data = cur.fetchall()

    conn.close()

    return render_template("report.html", data=data)

# ---------------- STATUS UPDATE ----------------
@app.route("/status/<int:id>", methods=["POST"])
def update_status(id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE programs SET status=%s WHERE id=%s",
                (request.form["status"], id))

    conn.commit()
    conn.close()

    return redirect("/report")

# ---------------- EXPORT EXCEL ----------------
@app.route("/export")
def export():

    conn = get_conn()

    df = pd.read_sql("SELECT * FROM programs", conn)

    conn.close()

    file = "cutting_report.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
