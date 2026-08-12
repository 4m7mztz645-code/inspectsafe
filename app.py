
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
import os, csv, io
import psycopg

app = Flask(__name__)
secret = os.environ.get("RIDESAFE_SECRET_KEY")
if not secret:
    raise RuntimeError("RIDESAFE_SECRET_KEY environment variable is required.")
app.secret_key = secret

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required.")

DEFAULT_CHECKS = [
    "General visual inspection of ride structure and framework",
    "Check foundations, supports, packing, levelling and stabilisers",
    "Check anchors, ballast and restraints where applicable",
    "Check safety-critical nuts, bolts, pins, clips and locking devices",
    "Check welds and structural members for cracks, damage or distortion",
    "Check platforms, steps, handrails, barriers and non-slip surfaces",
    "Check fencing, gates, gate interlocks and access control",
    "Check passenger restraints, lap bars, belts and locking mechanisms",
    "Check restraint indicators / interlocks where fitted",
    "Check cars, seats, floors and passenger compartments",
    "Check wheels, tyres, guide wheels, bearings and axles",
    "Check drive system, motors, gearboxes, chains, belts and couplings",
    "Check brakes and emergency stopping systems",
    "Check hydraulic / pneumatic systems for leaks and correct pressure",
    "Check electrical cables, plugs, sockets, enclosures and earthing",
    "Check control panel, operator controls, warning lights and alarms",
    "Test emergency stop(s)",
    "Test start / stop and dead-man controls where applicable",
    "Check limit switches, sensors and safety devices",
    "Check lighting and signage required for safe operation",
    "Check fire extinguisher / emergency equipment where required",
    "Check operating area for obstructions, trip hazards and public access",
    "Carry out empty test cycle / test run",
    "Listen for unusual noise and check for abnormal vibration",
    "Confirm all defects from previous inspection have been closed or controlled"
]

def db():
    return psycopg.connect(DATABASE_URL, autocommit=False, row_factory=psycopg.rows.dict_row)

def init_db():
    with db() as conn:
        with conn.cursor() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS company(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS users(
                id BIGSERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'staff',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL,
                last_login_at TIMESTAMPTZ
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS login_log(
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT,
                username TEXT,
                full_name TEXT,
                logged_in_at TIMESTAMPTZ NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS rides(
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                serial TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS checklist(
                id BIGSERIAL PRIMARY KEY,
                item TEXT NOT NULL,
                sort_order INTEGER NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS ride_checklist(
                id BIGSERIAL PRIMARY KEY,
                ride_id BIGINT NOT NULL,
                item TEXT NOT NULL,
                sort_order INTEGER NOT NULL
            )""")
            c.execute("ALTER TABLE rides ADD COLUMN IF NOT EXISTS adips_id TEXT")
            c.execute("ALTER TABLE rides ADD COLUMN IF NOT EXISTS photo BYTEA")
            c.execute("ALTER TABLE rides ADD COLUMN IF NOT EXISTS photo_mime TEXT")
            c.execute("""CREATE TABLE IF NOT EXISTS maintenance_logs(
                id BIGSERIAL PRIMARY KEY,
                ride_id BIGINT NOT NULL,
                ride_name TEXT NOT NULL,
                log_date DATE NOT NULL,
                category TEXT,
                description TEXT NOT NULL,
                action_taken TEXT,
                parts_used TEXT,
                out_of_service BOOLEAN NOT NULL DEFAULT FALSE,
                returned_to_service BOOLEAN NOT NULL DEFAULT FALSE,
                user_id BIGINT,
                user_name TEXT,
                username TEXT,
                created_at TIMESTAMPTZ NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS accident_reports(
                id BIGSERIAL PRIMARY KEY,
                ride_id BIGINT NOT NULL,
                ride_name TEXT NOT NULL,
                incident_date DATE NOT NULL,
                incident_time TEXT,
                location TEXT,
                person_name TEXT,
                person_contact TEXT,
                injury_details TEXT,
                incident_description TEXT NOT NULL,
                immediate_action TEXT,
                witnesses TEXT,
                reported_to TEXT,
                ride_stopped BOOLEAN NOT NULL DEFAULT FALSE,
                user_id BIGINT,
                user_name TEXT,
                username TEXT,
                created_at TIMESTAMPTZ NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS inspections(
                id BIGSERIAL PRIMARY KEY,
                ride_id BIGINT,
                ride_name TEXT,
                ride_serial TEXT,
                check_date DATE,
                user_id BIGINT,
                user_name TEXT,
                username TEXT,
                weather TEXT,
                notes TEXT,
                fit_for_service BOOLEAN,
                signature TEXT,
                status TEXT,
                created_at TIMESTAMPTZ
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS inspection_items(
                id BIGSERIAL PRIMARY KEY,
                inspection_id BIGINT,
                item_text TEXT,
                result TEXT,
                note TEXT,
                sort_order INTEGER
            )""")
            c.execute("SELECT COUNT(*) AS n FROM company")
            if c.fetchone()["n"] == 0:
                c.execute("INSERT INTO company(id,name) VALUES(1,%s)",("My Amusement Company",))
            c.execute("SELECT COUNT(*) AS n FROM checklist")
            if c.fetchone()["n"] == 0:
                for i,item in enumerate(DEFAULT_CHECKS):
                    c.execute("INSERT INTO checklist(item,sort_order) VALUES (%s,%s)",(item,i))
        conn.commit()

@app.before_request
def ensure_schema():
    if not getattr(app, "_db_initialized", False):
        init_db()
        app._db_initialized = True

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Administrator access required.")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_company():
    company = None
    try:
        with db() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM company WHERE id=1")
                company = c.fetchone()
    except Exception:
        pass
    return {"company": company}

@app.route("/health")
def health():
    try:
        with db() as conn:
            with conn.cursor() as c:
                c.execute("SELECT 1 AS ok")
                c.fetchone()
        return {"status":"ok"},200
    except Exception as e:
        return {"status":"error","detail":str(e)},500

@app.route("/setup", methods=["GET","POST"])
def setup():
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) AS n FROM users")
            count = c.fetchone()["n"]
            if count > 0:
                return redirect(url_for("login"))
            if request.method == "POST":
                company_name = request.form.get("company_name","").strip()
                full_name = request.form.get("full_name","").strip()
                username = request.form.get("username","").strip().lower()
                password = request.form.get("password","")
                if not company_name or not full_name or not username or len(password) < 8:
                    flash("Complete all fields. Password must be at least 8 characters.")
                else:
                    c.execute("UPDATE company SET name=%s WHERE id=1",(company_name,))
                    c.execute("""INSERT INTO users(full_name,username,password_hash,role,active,created_at)
                                 VALUES (%s,%s,%s,%s,TRUE,%s)""",
                              (full_name,username,generate_password_hash(password),"admin",datetime.now()))
                    conn.commit()
                    return redirect(url_for("login"))
    return render_template("setup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) AS n FROM users")
            count = c.fetchone()["n"]
            if count == 0:
                return redirect(url_for("setup"))

            if request.method == "POST":
                username = request.form.get("username","").strip().lower()
                password = request.form.get("password","")
                c.execute("SELECT * FROM users WHERE username=%s",(username,))
                user = c.fetchone()
                if not user or not user["active"] or not check_password_hash(user["password_hash"],password):
                    flash("Incorrect username or password.")
                else:
                    session.clear()
                    session["user_id"] = user["id"]
                    session["full_name"] = user["full_name"]
                    session["username"] = user["username"]
                    session["role"] = user["role"]
                    now = datetime.now()
                    c.execute("UPDATE users SET last_login_at=%s WHERE id=%s",(now,user["id"]))
                    c.execute("INSERT INTO login_log(user_id,username,full_name,logged_in_at) VALUES (%s,%s,%s,%s)",
                              (user["id"],user["username"],user["full_name"],now))
                    conn.commit()
                    return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rides WHERE active=TRUE ORDER BY name")
            rides = c.fetchall()
    return render_template("home.html", rides=rides, today=date.today().isoformat())


@app.route("/ride/<int:ride_id>/checklist.json")
@login_required
def ride_checklist_json(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id,item,sort_order FROM ride_checklist WHERE ride_id=%s ORDER BY sort_order,id",(ride_id,))
            checks=c.fetchall()
    return {"checks":checks}

@app.route("/save-check", methods=["POST"])
@login_required
def save_check():
    with db() as conn:
        with conn.cursor() as c:
            ride_id = int(request.form["ride_id"])
            c.execute("SELECT * FROM rides WHERE id=%s AND active=TRUE",(ride_id,))
            ride = c.fetchone()
            c.execute("SELECT * FROM ride_checklist WHERE ride_id=%s ORDER BY sort_order,id",(ride_id,))
            checks = c.fetchall()
            if not ride:
                flash("Ride not found.")
                return redirect(url_for("home"))
            if not checks:
                flash("No checklist has been set up for this ride yet.")
                return redirect(url_for("home"))

            items=[]
            failures=0
            for idx,ch in enumerate(checks):
                result=request.form.get(f"result_{ch['id']}","")
                note=request.form.get(f"note_{ch['id']}","").strip()
                if result not in ("PASS","FAIL","N/A"):
                    return f"Checklist item {idx+1} has not been answered.",400
                if result=="FAIL":
                    failures += 1
                    if not note:
                        return f"Checklist item {idx+1} failed and requires a note.",400
                items.append((ch["item"],result,note,idx))

            fit=request.form.get("fit_for_service")=="on"
            status="PASS" if failures==0 and fit else "ATTENTION"
            signature=request.form.get("signature","").strip()
            if not signature:
                return "Signature is required.",400

            c.execute("""INSERT INTO inspections(
                ride_id,ride_name,ride_serial,check_date,user_id,user_name,username,weather,notes,
                fit_for_service,signature,status,created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(
                ride["id"],ride["name"],ride["serial"] or "",request.form.get("check_date",date.today().isoformat()),
                session["user_id"],session["full_name"],session["username"],request.form.get("weather","").strip(),
                request.form.get("notes","").strip(),fit,signature,status,datetime.now()
            ))
            inspection_id=c.fetchone()["id"]
            for item_text,result,note,sort_order in items:
                c.execute("""INSERT INTO inspection_items(inspection_id,item_text,result,note,sort_order)
                             VALUES (%s,%s,%s,%s,%s)""",(inspection_id,item_text,result,note,sort_order))
            conn.commit()
    flash("Daily check saved.")
    return redirect(url_for("history"))

@app.route("/history")
@login_required
def history():
    with db() as conn:
        with conn.cursor() as c:
            if session.get("role")=="admin":
                c.execute("SELECT * FROM inspections ORDER BY check_date DESC,id DESC")
            else:
                c.execute("SELECT * FROM inspections WHERE user_id=%s ORDER BY check_date DESC,id DESC",
                          (session["user_id"],))
            rows=c.fetchall()
    return render_template("history.html", inspections=rows)

@app.route("/inspection/<int:inspection_id>")
@login_required
def inspection(inspection_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM inspections WHERE id=%s",(inspection_id,))
            insp=c.fetchone()
            if not insp:
                return "Not found",404
            if session.get("role")!="admin" and insp["user_id"] != session["user_id"]:
                return "Forbidden",403
            c.execute("SELECT * FROM inspection_items WHERE inspection_id=%s ORDER BY sort_order,id",(inspection_id,))
            items=c.fetchall()
    return render_template("inspection.html", insp=insp, items=items)

@app.route("/admin")
@admin_required
def admin_dashboard():
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM users ORDER BY active DESC, full_name")
            staff=c.fetchall()
            c.execute("SELECT * FROM login_log ORDER BY id DESC LIMIT 50")
            recent_logins=c.fetchall()
            c.execute("SELECT * FROM inspections ORDER BY id DESC LIMIT 50")
            recent_checks=c.fetchall()
            c.execute("""SELECT
              (SELECT COUNT(*) FROM users WHERE active=TRUE) active_users,
              (SELECT COUNT(*) FROM rides WHERE active=TRUE) active_rides,
              (SELECT COUNT(*) FROM inspections) total_checks,
              (SELECT COUNT(*) FROM inspections WHERE status='ATTENTION') attention_checks
            """)
            totals=c.fetchone()
    return render_template("admin.html", staff=staff, recent_logins=recent_logins, recent_checks=recent_checks, totals=totals)

@app.route("/admin/users", methods=["GET","POST"])
@admin_required
def users():
    with db() as conn:
        with conn.cursor() as c:
            if request.method=="POST":
                full_name=request.form.get("full_name","").strip()
                username=request.form.get("username","").strip().lower()
                password=request.form.get("password","")
                role=request.form.get("role","staff")
                if role not in ("staff","admin"):
                    role="staff"
                if not full_name or not username or len(password)<8:
                    flash("Name, username and a password of at least 8 characters are required.")
                else:
                    try:
                        c.execute("""INSERT INTO users(full_name,username,password_hash,role,active,created_at)
                                     VALUES (%s,%s,%s,%s,TRUE,%s)""",
                                  (full_name,username,generate_password_hash(password),role,datetime.now()))
                        conn.commit()
                        flash("User created.")
                    except Exception:
                        conn.rollback()
                        flash("That username already exists.")
            c.execute("SELECT * FROM users ORDER BY full_name")
            rows=c.fetchall()
    return render_template("users.html", users=rows)

@app.route("/admin/user/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot disable your own account.")
        return redirect(url_for("users"))
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM users WHERE id=%s",(user_id,))
            u=c.fetchone()
            if u:
                c.execute("UPDATE users SET active=%s WHERE id=%s",(not u["active"],user_id))
                conn.commit()
    return redirect(url_for("users"))

@app.route("/admin/user/<int:user_id>/password", methods=["POST"])
@admin_required
def reset_password(user_id):
    password=request.form.get("password","")
    if len(password)<8:
        flash("Password must be at least 8 characters.")
        return redirect(url_for("users"))
    with db() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE users SET password_hash=%s WHERE id=%s",(generate_password_hash(password),user_id))
            conn.commit()
    flash("Password updated.")
    return redirect(url_for("users"))

@app.route("/admin/rides", methods=["GET","POST"])
@admin_required
def rides():
    with db() as conn:
        with conn.cursor() as c:
            if request.method=="POST":
                name=request.form.get("name","").strip()
                serial=request.form.get("serial","").strip()
                adips_id=request.form.get("adips_id","").strip()
                photo_file=request.files.get("photo")
                photo=None
                photo_mime=None
                if photo_file and photo_file.filename:
                    data=photo_file.read()
                    if len(data) > 5 * 1024 * 1024:
                        flash("Ride photo must be 5 MB or smaller.")
                        c.execute("SELECT * FROM rides ORDER BY active DESC,name")
                        return render_template("rides.html", rides=c.fetchall())
                    photo=data
                    photo_mime=photo_file.mimetype or "image/jpeg"
                if name:
                    c.execute("""INSERT INTO rides(name,serial,adips_id,photo,photo_mime,active)
                                 VALUES (%s,%s,%s,%s,%s,TRUE)""",
                              (name,serial,adips_id,photo,photo_mime))
                    conn.commit()
                    flash("Ride added.")
            c.execute("SELECT * FROM rides ORDER BY active DESC,name")
            rows=c.fetchall()
    return render_template("rides.html", rides=rows)

@app.route("/admin/ride/<int:ride_id>/edit", methods=["GET","POST"])
@admin_required
def edit_ride(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rides WHERE id=%s",(ride_id,))
            ride=c.fetchone()
            if not ride:
                return "Ride not found",404
            if request.method=="POST":
                name=request.form.get("name","").strip()
                serial=request.form.get("serial","").strip()
                adips_id=request.form.get("adips_id","").strip()
                photo_file=request.files.get("photo")
                if photo_file and photo_file.filename:
                    data=photo_file.read()
                    if len(data) > 5 * 1024 * 1024:
                        flash("Ride photo must be 5 MB or smaller.")
                        return render_template("edit_ride.html", ride=ride)
                    c.execute("""UPDATE rides SET name=%s,serial=%s,adips_id=%s,photo=%s,photo_mime=%s WHERE id=%s""",
                              (name,serial,adips_id,data,photo_file.mimetype or "image/jpeg",ride_id))
                else:
                    c.execute("UPDATE rides SET name=%s,serial=%s,adips_id=%s WHERE id=%s",(name,serial,adips_id,ride_id))
                conn.commit()
                flash("Ride updated.")
                return redirect(url_for("rides"))
    return render_template("edit_ride.html", ride=ride)

@app.route("/ride/<int:ride_id>/photo")
@login_required
def ride_photo(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT photo,photo_mime FROM rides WHERE id=%s",(ride_id,))
            ride=c.fetchone()
            if not ride or not ride["photo"]:
                return "",404
            return Response(bytes(ride["photo"]), mimetype=ride["photo_mime"] or "image/jpeg")

@app.route("/admin/ride/<int:ride_id>/toggle",methods=["POST"])
@admin_required
def toggle_ride(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rides WHERE id=%s",(ride_id,))
            r=c.fetchone()
            if r:
                c.execute("UPDATE rides SET active=%s WHERE id=%s",(not r["active"],ride_id))
                conn.commit()
    return redirect(url_for("rides"))

@app.route("/admin/ride/<int:ride_id>/checklist",methods=["GET","POST"])
@admin_required
def ride_checklist(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rides WHERE id=%s",(ride_id,))
            ride=c.fetchone()
            if not ride:
                return "Ride not found",404
            if request.method=="POST":
                item=request.form.get("item","").strip()
                if item:
                    c.execute("SELECT COALESCE(MAX(sort_order),-1)+1 AS next_order FROM ride_checklist WHERE ride_id=%s",(ride_id,))
                    next_order=c.fetchone()["next_order"]
                    c.execute("INSERT INTO ride_checklist(ride_id,item,sort_order) VALUES (%s,%s,%s)",(ride_id,item,next_order))
                    conn.commit()
                    flash("Check added to this ride.")
            c.execute("SELECT * FROM ride_checklist WHERE ride_id=%s ORDER BY sort_order,id",(ride_id,))
            checks=c.fetchall()
    return render_template("ride_checklist.html", ride=ride, checks=checks)

@app.route("/admin/ride/<int:ride_id>/checklist/<int:check_id>/delete", methods=["POST"])
@admin_required
def delete_ride_check(ride_id,check_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM ride_checklist WHERE id=%s AND ride_id=%s",(check_id,ride_id))
            conn.commit()
    flash("Check removed from this ride.")
    return redirect(url_for("ride_checklist",ride_id=ride_id))


@app.route("/ride/<int:ride_id>")
@login_required
def ride_detail(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rides WHERE id=%s",(ride_id,))
            ride=c.fetchone()
            if not ride:
                return "Ride not found",404
            c.execute("SELECT * FROM maintenance_logs WHERE ride_id=%s ORDER BY log_date DESC,id DESC",(ride_id,))
            maintenance=c.fetchall()
            c.execute("SELECT * FROM accident_reports WHERE ride_id=%s ORDER BY incident_date DESC,id DESC",(ride_id,))
            accidents=c.fetchall()
    return render_template("ride_detail.html", ride=ride, maintenance=maintenance, accidents=accidents)

@app.route("/ride/<int:ride_id>/maintenance/add", methods=["GET","POST"])
@login_required
def add_maintenance(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rides WHERE id=%s",(ride_id,))
            ride=c.fetchone()
            if not ride:
                return "Ride not found",404
            if request.method=="POST":
                description=request.form.get("description","").strip()
                if not description:
                    flash("Maintenance description is required.")
                else:
                    c.execute("""INSERT INTO maintenance_logs(ride_id,ride_name,log_date,category,description,action_taken,parts_used,out_of_service,returned_to_service,user_id,user_name,username,created_at)
                                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(
                        ride["id"],ride["name"],request.form.get("log_date",date.today().isoformat()),request.form.get("category","").strip(),description,request.form.get("action_taken","").strip(),request.form.get("parts_used","").strip(),request.form.get("out_of_service")=="on",request.form.get("returned_to_service")=="on",session["user_id"],session["full_name"],session["username"],datetime.now()))
                    conn.commit()
                    flash("Maintenance log added.")
                    return redirect(url_for("ride_detail",ride_id=ride_id))
    return render_template("maintenance_form.html", ride=ride, today=date.today().isoformat())

@app.route("/ride/<int:ride_id>/accident/add", methods=["GET","POST"])
@login_required
def add_accident(ride_id):
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rides WHERE id=%s",(ride_id,))
            ride=c.fetchone()
            if not ride:
                return "Ride not found",404
            if request.method=="POST":
                description=request.form.get("incident_description","").strip()
                if not description:
                    flash("Incident description is required.")
                else:
                    c.execute("""INSERT INTO accident_reports(ride_id,ride_name,incident_date,incident_time,location,person_name,person_contact,injury_details,incident_description,immediate_action,witnesses,reported_to,ride_stopped,user_id,user_name,username,created_at)
                                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(
                        ride["id"],ride["name"],request.form.get("incident_date",date.today().isoformat()),request.form.get("incident_time","").strip(),request.form.get("location","").strip(),request.form.get("person_name","").strip(),request.form.get("person_contact","").strip(),request.form.get("injury_details","").strip(),description,request.form.get("immediate_action","").strip(),request.form.get("witnesses","").strip(),request.form.get("reported_to","").strip(),request.form.get("ride_stopped")=="on",session["user_id"],session["full_name"],session["username"],datetime.now()))
                    conn.commit()
                    flash("Accident report added.")
                    return redirect(url_for("ride_detail",ride_id=ride_id))
    return render_template("accident_form.html", ride=ride, today=date.today().isoformat())

@app.route("/admin/export.csv")
@admin_required
def export_csv():
    with db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM inspections ORDER BY check_date DESC,id DESC")
            rows=c.fetchall()
            out=io.StringIO()
            w=csv.writer(out)
            w.writerow(["Date","Ride","Ride ID","Staff Name","Username","Status","Fit for Service","Failed Items","Weather","Notes","Signature","Saved"])
            for r in rows:
                c.execute("""SELECT item_text,note FROM inspection_items
                             WHERE inspection_id=%s AND result='FAIL' ORDER BY sort_order""",(r["id"],))
                failed=c.fetchall()
                failed_text=" | ".join([f"{x['item_text']}: {x['note']}" for x in failed])
                w.writerow([r["check_date"],r["ride_name"],r["ride_serial"],r["user_name"],r["username"],r["status"],
                            "Yes" if r["fit_for_service"] else "No",failed_text,r["weather"],r["notes"],r["signature"],r["created_at"]])
    return Response(out.getvalue(),mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=RideSafe_Company_Inspections.csv"})

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
