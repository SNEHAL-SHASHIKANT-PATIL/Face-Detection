from flask import Flask, render_template, render_template_string, request, redirect, url_for
import sqlite3
import os
import pandas as pd

app = Flask(__name__)

DB_PATH = 'outpass.db'
DATA_PATH = 'Dataset.csv.xlsx'
ID_PATH = "New Outpass ID of all Students.xlsx"

# -------------------------------
# Load Dataset Once
# -------------------------------
df = pd.read_excel(DATA_PATH)
df.columns = [c.strip().replace(" ", "_").upper() for c in df.columns]

ID_DF = pd.read_excel(ID_PATH)
ID_DF.columns = ID_DF.columns.str.strip().str.upper()

# -------------------------------
# Home Page
# -------------------------------
@app.route('/')
def welcome():
    return render_template('home.html')

# -------------------------------
# Enrollment Verification Page
# -------------------------------
@app.route('/verify', methods=['GET', 'POST'])
def verify_enrollment():
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Enrollment Verification | GRW Polytechnic Tasgaon</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
            body {
                margin: 0; padding: 0; height: 100vh;
                font-family: 'Poppins', sans-serif;
                background-image: url("{{ url_for('static', filename='college_bg.jpg') }}");
                background-size: cover; background-position: center;
                display: flex; justify-content: center; align-items: center;
                overflow: hidden;
            }
            body::before {
                content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.3); backdrop-filter: blur(8px); z-index: 0;
            }
            .container {
                position: relative; z-index: 1;
                background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px);
                border-radius: 20px; padding: 40px 50px; text-align: center; width: 380px;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4); animation: fadeIn 1s ease-in-out;
            }
            h1 { font-size: 22px; color: #ffffff; margin-bottom: 10px; }
            h2 { font-size: 18px; color: #d9f1ff; margin-bottom: 25px; }
            input { width: 100%; padding: 12px; border: none; border-radius: 8px;
                    margin-bottom: 20px; outline: none; font-size: 15px; text-align: center;
                    background: rgba(255,255,255,0.25); color: #fff; }
            input::placeholder { color: #e6e6e6; }
            button { width: 100%; padding: 12px; border: none; border-radius: 8px;
                     background: linear-gradient(90deg, #007bff, #00c6ff);
                     color: white; font-weight: bold; font-size: 15px; cursor: pointer;
                     transition: 0.3s; }
            button:hover { transform: scale(1.05); background: linear-gradient(90deg, #006be6, #00aaff); }
            .footer { margin-top: 15px; font-size: 13px; color: #e1e1e1; }
            @keyframes fadeIn { from {opacity:0; transform:translateY(30px);} to {opacity:1; transform:translateY(0);} }
        </style>
        <script> function showAlert(msg){ alert(msg); } </script>
    </head>
    <body>
        <div class="container">
            <h1>🏫 Government Residence Women Polytechnic, Tasgaon</h1>
            <h2>Enrollment Verification</h2>
            <form method="POST">
                <input type="text" name="enroll" placeholder="Enter Enrollment Number" required>
                <button type="submit">Verify Enrollment</button>
            </form>
            <div class="footer">© 2025 GRW Polytechnic Tasgaon</div>
        </div>
        {% if alert %}<script>showAlert("{{ alert }}");</script>{% endif %}
    </body>
    </html>
    '''

    if request.method == 'POST':
        enroll = request.form['enroll'].strip()
        student = df.loc[df['ENROLLMENT_NO'].astype(str) == str(enroll)]
        if not student.empty:
            return redirect(url_for('outpass_form', enroll=enroll))
        else:
            return render_template_string(html, alert="❌ Invalid Enrollment Number! Try again.")
    return render_template_string(html)

# -------------------------------
# Outpass Form
# -------------------------------
@app.route('/form', methods=['GET', 'POST'])
def outpass_form():
    enroll_no = request.args.get('enroll', None)
    if request.method == 'POST':
        enroll_no = request.form['enroll']
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        reason = request.form['reason']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS OutpassRequests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Enrollment_No TEXT,
                From_Date TEXT,
                To_Date TEXT,
                Reason TEXT,
                Status TEXT
            )
        ''')
        cursor.execute("""
            INSERT INTO OutpassRequests (Enrollment_No, From_Date, To_Date, Reason, Status)
            VALUES (?, ?, ?, ?, ?)
        """, (enroll_no, from_date, to_date, reason, "Pending"))
        conn.commit()
        conn.close()

        return redirect(url_for('success_page', enroll=enroll_no,
                                from_date=from_date, to_date=to_date, reason=reason))
    return render_template('index.html', enroll_no=enroll_no)

# -------------------------------
# Success Page (with student image + check status link)
# -------------------------------
@app.route('/success/<enroll>')
def success_page(enroll):
    student = df.loc[df['ENROLLMENT_NO'].astype(str) == str(enroll)]
    if student.empty:
        return "<h3 style='color:red;'>Student not found!</h3>"

    record = student.iloc[0].to_dict()
    from_date = request.args.get('from_date', 'N/A')
    to_date = request.args.get('to_date', 'N/A')
    reason = request.args.get('reason', 'N/A')

    img_folder = os.path.join('static', 'IMAGE_DATASET COTY')
    image_found = None
    for ext in ['.jpg', '.jpeg', '.png']:
        possible_path = os.path.join(img_folder, f"{enroll}{ext}")
        if os.path.exists(possible_path):
            image_found = possible_path
            break
    if not image_found:
        image_found = os.path.join('static', 'default.jpg')
    img_url = '/' + image_found.replace('\\', '/')

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Outpass Submitted | GRW Polytechnic</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
            body {{ margin:0; height:100vh; font-family:'Poppins', sans-serif;
                   background-image:url('/static/college_bg.jpg'); background-size:cover;
                   display:flex; justify-content:center; align-items:center; }}
            body::before {{ content:""; position:absolute; top:0; left:0; right:0; bottom:0;
                            background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index:0; }}
            .card {{ position:relative; z-index:1; background: rgba(255,255,255,0.15);
                     backdrop-filter: blur(20px); border-radius: 25px; padding:50px 70px;
                     width:650px; color:#fff; text-align:center; box-shadow:0 8px 40px rgba(0,0,0,0.6); }}
            img {{ width:130px; height:130px; border-radius:50%; border:3px solid white; object-fit:cover; margin-bottom:20px; }}
            h2 {{ font-size:24px; margin-bottom:15px; color:#fff; }}
            table {{ width:100%; color:#f2f2f2; text-align:left; border-collapse:collapse; font-size:16px; margin:0 auto; }}
            td {{ padding:8px 0; }}
            a.btn {{
                background: linear-gradient(90deg,#007bff,#00c6ff);
                color:white; border:none;
                padding:12px 25px; border-radius:10px;
                font-weight:bold; cursor:pointer; margin:10px 5px;
                text-decoration:none; display:inline-block;
                transition:0.3s;
            }}
            a.btn:hover {{ transform:scale(1.05); background: linear-gradient(90deg,#006be6,#00aaff); }}
        </style>
    </head>
    <body>
        <div class="card">
            <img src="{img_url}" alt="Student Photo">
            <h2>{record.get('NAME','N/A')}</h2>
            <table>
                <tr><td><b>Enrollment No:</b></td><td>{enroll}</td></tr>
                <tr><td><b>Roll No:</b></td><td>{record.get('ROLL_NO','N/A')}</td></tr>
                <tr><td><b>Department:</b></td><td>{record.get('DEPARTMENT','N/A')}</td></tr>
                <tr><td><b>Year:</b></td><td>{record.get('YEAR','N/A')}</td></tr>
                <tr><td><b>Academic Year:</b></td><td>{record.get('YEAR.1','N/A')}</td></tr>
                <tr><td><b>Student Phone:</b></td><td>{record.get('STUDENT_PHONE_NO','N/A')}</td></tr>
                <tr><td><b>Parent Phone:</b></td><td>{record.get('PARENTS_PHONE_NO','N/A')}</td></tr>
                <tr><td colspan="2"><hr></td></tr>
                <tr><td><b>From Date:</b></td><td>{from_date}</td></tr>
                <tr><td><b>To Date:</b></td><td>{to_date}</td></tr>
                <tr><td><b>Reason:</b></td><td>{reason}</td></tr>
            </table>

            <!-- 3 Buttons -->
            <a href="/warden" class="btn">📨 Submit (Go to Warden)</a>
            <a href="/" class="btn">🏠 Back to Home</a>
            <a href="/check_status?enroll={enroll}" class="btn">📋 Check Status</a>

        </div>
    </body>
    </html>
    """
    return html

# -------------------------------
# NEW PAGE: Search Student Details (Like 4th output photo)
# -------------------------------
@app.route('/student_info', methods=['GET', 'POST'])
def student_info():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Search Student Details</title>
        <style>
            body {
                font-family: Poppins, sans-serif;
                background: #f0f7ff;
                padding: 30px;
                text-align: center;
            }
            .box {
                width: 420px;
                background: white;
                padding: 25px;
                margin: auto;
                border-radius: 15px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            }
            input, button {
                width: 90%;
                padding: 12px;
                margin-top: 15px;
                border-radius: 8px;
                border: 1px solid #ccc;
                font-size: 16px;
            }
            button {
                background: #007bff;
                color: white;
                border: none;
                cursor: pointer;
            }
            button:hover { background: #0062d3; }

            .card {
                margin-top: 30px;
                padding: 20px;
                background: white;
                border-radius: 15px;
                width: 500px;
                margin-left: auto;
                margin-right: auto;
                box-shadow: 0 5px 20px rgba(0,0,0,0.2);
                text-align: left;
            }
            img {
                width: 130px;
                height: 130px;
                border-radius: 50%;
                object-fit: cover;
                border: 3px solid #007bff;
                margin-bottom: 10px;
            }
            table {
                width: 100%;
                font-size: 15px;
            }
            td { padding: 6px 0; }
        </style>
    </head>
    <body>

        <h2>🔍 Search Student Details</h2>

        <form method="POST" class="box">
            <input type="text" name="enroll" placeholder="Enter Enrollment Number" required>
            <button type="submit">Search</button>
        </form>

        {% if student %}
        <div class="card">
            <center><img src="{{ image }}" alt="Photo"></center>
            <h3 style="text-align:center;">{{ student.NAME }}</h3>
            <table>
                <tr><td><b>Enrollment No:</b></td><td>{{ student.ENROLLMENT_NO }}</td></tr>
                <tr><td><b>Roll No:</b></td><td>{{ student.ROLL_NO }}</td></tr>
                <tr><td><b>Department:</b></td><td>{{ student.DEPARTMENT }}</td></tr>
                <tr><td><b>Year:</b></td><td>{{ student.YEAR }}</td></tr>
                <tr><td><b>Academic Year:</b></td><td>{{ student["YEAR.1"] }}</td></tr>
                <tr><td><b>Student Phone:</b></td><td>{{ student.STUDENT_PHONE_NO }}</td></tr>
                <tr><td><b>Parent Phone:</b></td><td>{{ student.PARENTS_PHONE_NO }}</td></tr>
            </table>
        </div>
        {% endif %}

        {% if error %}
        <script>alert("{{ error }}");</script>
        {% endif %}

    </body>
    </html>
    """

    student = None
    image_path = None

    if request.method == 'POST':
        enroll = request.form['enroll'].strip()
        data = df.loc[df['ENROLLMENT_NO'].astype(str) == str(enroll)]

        if data.empty:
            return render_template_string(html, error="❌ Invalid Enrollment Number!")

        student = data.iloc[0].to_dict()

        # Search image
        img_folder = os.path.join("static", "IMAGE_DATASET COTY")
        for ext in [".jpg", ".jpeg", ".png"]:
            path = os.path.join(img_folder, f"{enroll}{ext}")
            if os.path.exists(path):
                image_path = "/" + path
                break

        if not image_path:
            image_path = "/static/default.jpg"

        return render_template_string(html, student=student, image=image_path)

    return render_template_string(html)

# -------------------------------------------------------------
# STUDENT INFO INPUT PAGE
# -------------------------------------------------------------
@app.route('/student_info_input')
def student_info_input():
    html = """
    <h2>Enter Student ID</h2>

    <form action="/student_info" method="POST">
        <input type="text" name="student_id" placeholder="Enter ID" required
               style="padding:8px; font-size:18px;">
        <button type="submit" style="padding:8px; font-size:18px;">Search</button>
    </form>

    <br><br>
    <a href="/after_output"><button>⬅ Back</button></a>
    """
    return html


# -------------------------------
# Warden Dashboard
# -------------------------------
@app.route('/warden')
def warden_dashboard():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM OutpassRequests")
    rows = cursor.fetchall()
    conn.close()

    enriched = []
    for r in rows:
        req_id, enroll, from_date, to_date, reason, status = r
        student = df.loc[df['ENROLLMENT_NO'].astype(str) == str(enroll)]
        if not student.empty:
            rec = student.iloc[0]
            name = rec.get('NAME', 'N/A')
            student_phone = rec.get('STUDENT_PHONE_NO', 'N/A')
            parent_phone = rec.get('PARENTS_PHONE_NO', 'N/A')
        else:
            name, student_phone, parent_phone = 'N/A', 'N/A', 'N/A'

        enriched.append({
            'id': req_id, 'enroll': enroll, 'name': name,
            'student_phone': student_phone, 'parent_phone': parent_phone,
            'from_date': from_date, 'to_date': to_date,
            'reason': reason, 'status': status
        })

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Warden Dashboard</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f0f7ff; }
            h2 { text-align: center; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; font-size:14px; }
            th { background: #007bff; color: white; }
            tr:nth-child(even) { background: #f9f9f9; }
            a.call-btn, a.whatsapp-btn {
                display: inline-block; color:white; font-weight:bold; padding:6px 10px; border-radius:6px;
                text-decoration:none; margin:2px; transition:0.2s;
            }
            a.call-btn { background: linear-gradient(90deg,#28a745,#4cd964); }
            a.whatsapp-btn { background: linear-gradient(90deg,#25D366,#128C7E); }
            a.call-btn:hover, a.whatsapp-btn:hover { transform: scale(1.05); }
            input { padding:8px; width:300px; margin-bottom:10px; }
        </style>
        <script>
            function searchTable() {
                var input = document.getElementById("searchBox").value.toLowerCase();
                var rows = document.querySelectorAll("#reqTable tbody tr");
                rows.forEach(row => { row.style.display = row.innerText.toLowerCase().includes(input) ? "" : "none"; });
            }
        </script>
    </head>
    <body>
        <h2>🏫 Warden Dashboard - Outpass Requests</h2>
        
         <!-- 🔵 Added Button -->
        <div class="top-btn-box">
            <a href="/student_info">
                <button class="search-btn">🔍 Search Student Info</button>
            </a>
        </div>
                                
        <a href="/guard_dashboard">
            <button class="btn-guard">Open Guard Dashboard</button>
        </a>
         <style>
            .btn-guard {
                background: #ff7b00;
                padding: 12px 20px;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 16px;
                border-radius: 8px;
                margin-top: 15px;
             }

            .btn-guard:hover {
                background: #e56e00;
            }
        </style>

        <input id="searchBox" placeholder="🔍 Search..." onkeyup="searchTable()">
        <table id="reqTable">
          <thead>
            <tr>
              <th>ID</th><th>Enrollment</th><th>Name</th><th>Student Contact</th><th>Parent Contact</th>
              <th>From</th><th>To</th><th>Reason</th><th>Status</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
          {% for r in enriched %}
            <tr>
              <td>{{ r.id }}</td>
              <td>{{ r.enroll }}</td>
              <td>{{ r.name }}</td>
              <td>
                {% if r.student_phone != 'N/A' %}
                  <a href="tel:{{ r.student_phone }}" class="call-btn">📞 Call</a>
                  <a href="https://wa.me/{{ r.student_phone }}" target="_blank" class="whatsapp-btn">💬 WhatsApp</a><br>
                  <small>{{ r.student_phone }}</small>
                {% else %} N/A {% endif %}
              </td>
              <td>
                {% if r.parent_phone != 'N/A' %}
                  <a href="tel:+91{{ r.parent_phone }}" class="call-btn">📞 Call</a>
                  <a href="https://wa.me/91{{ r.parent_phone }}" target="_blank" class="whatsapp-btn">💬 WhatsApp</a><br>
                  <small>+91 {{ r.parent_phone }}</small>
                {% else %} N/A {% endif %}
              </td>
              <td>{{ r.from_date }}</td>
              <td>{{ r.to_date }}</td>
              <td>{{ r.reason }}</td>
              <td>{{ r.status }}</td>
              <td>
                {% if r.status == 'Pending' %}
                  <a href="/update_status/{{ r.id }}/Approved">Approve</a> |
                  <a href="/update_status/{{ r.id }}/Rejected">Reject</a>
                {% else %} - {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
    </body>
    </html>
    """, enriched=enriched)

# -------------------------------
# Update Status
# -------------------------------
@app.route('/update_status/<int:req_id>/<status>')
def update_status(req_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE OutpassRequests SET Status=? WHERE id=?", (status, req_id))
    conn.commit()
    conn.close()
    return redirect(url_for('warden_dashboard'))


# -------------------------------
# Guard dashboard
# -------------------------------
@app.route('/guard_dashboard')
def guard_dashboard():
    # Get search text
    query = request.args.get("query", "").strip().lower()

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    merged_data = df.merge(
        ID_DF[['NAME', 'ID_NO', 'HOSTEL_NAME']], 
        on='NAME', 
        how='left'
    )

    merged_data = merged_data.rename(columns={'ID_NO': 'OUTPASS_ID'})

    count_df = merged_data.groupby('NAME').size().reset_index(name='VISIT_COUNT')
    merged_data = merged_data.merge(count_df, on='NAME', how='left')

    if from_date:
        merged_data['ENTRY_DATE'] = from_date
    if to_date:
        merged_data['EXIT_DATE'] = to_date

    if query:
        merged_data = merged_data[
            merged_data["NAME"].str.lower().str.contains(query) |
            merged_data["OUTPASS_ID"].astype(str).str.contains(query) |
            merged_data["HOSTEL_NAME"].str.lower().str.contains(query)
        ]

    students = merged_data.to_dict(orient='records')

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Guard Dashboard</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #eef5ff; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 10px; border-bottom: 1px solid #ccc; text-align: left; }
            th { background: #0a4dff; color: white; }
            tr:hover { background: #f5f7ff; }
            .btn { padding: 6px 12px; color: white; border: none; border-radius: 5px; cursor: pointer; }
            .search-box { width: 300px; padding: 10px; margin-bottom: 15px; }
        </style>
    </head>
    <body>
        <h2>Guard Dashboard</h2>

        <!-- Search Bar -->
        <form method="get" action="/guard_dashboard">
            <input type="text" name="query" class="search-box" placeholder="Search by Name / Outpass ID / Hostel"
                   value="{{ request.args.get('query', '') }}">
            <button type="submit" class="btn" style="background: green;">Search</button>
        </form>

        <table>
            <tr>
                <th>Outpass ID</th>
                <th>Name</th>
                <th>Hostel Name</th>
                <th>Entry Date</th>
                <th>Exit Date</th>
                <th>Status</th>
                <th>Visits</th>
                <th>Action</th>
            </tr>
            {% for s in students %}
            <tr>
                <td>{{ s.OUTPASS_ID }}</td>
                <td>{{ s.NAME }}</td>
                <td>{{ s.HOSTEL_NAME }}</td>
                <td>{{ s.ENTRY_DATE }}</td>
                <td>{{ s.EXIT_DATE }}</td>
                <td>{{ s.STATUS }}</td>
                <td>{{ s.VISIT_COUNT }}</td>
                <td>
                    <a href="/guard_update_status?id={{ s.OUTPASS_ID }}&action=Approved">
                        <button class="btn" style="background: green;">OUT / IN</button>
                    </a>

                    <a href="/guard_update_status?id={{ s.OUTPASS_ID }}&action=Rejected">
                        <button class="btn" style="background: red; margin-left:5px;">REJECT</button>
                    </a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """

    return render_template_string(html, students=students)
@app.route('/guard_update_status')
def guard_update_status():
    outpass_id = request.args.get('id')
    action = request.args.get('action')

    if not outpass_id or not action:
        return "Invalid request", 400

    # Ensure STATUS column exists
    if 'STATUS' not in df.columns:
        df['STATUS'] = ''

    # IMPORTANT: Your real Outpass ID is in ID_DF, not in df.
    # So we find the NAME using Outpass ID, then update that student's rows.

    # 1. Find student NAME from ID_DF
    match = ID_DF[ID_DF['ID_NO'].astype(str) == str(outpass_id)]

    if match.empty:
        return f"No student found with Outpass ID == {outpass_id}", 404

    student_name = match.iloc[0]['NAME']

    # 2. Update all rows in df for that student's name
    mask = df['NAME'].astype(str).str.lower() == student_name.lower()

    if not mask.any():
        return f"No records found in main df for student: {student_name}", 404

    df.loc[mask, 'STATUS'] = action

    # If saving is needed:
    # df.to_excel(DATA_PATH, index=False)

    return redirect(url_for('guard_dashboard'))


# -------------------------------
# Check Status (Student view)
# -------------------------------
@app.route('/check_status', methods=['GET', 'POST'])
def check_status():
    results = None
    enroll = request.args.get('enroll','')
    if request.method == 'POST':
        enroll = request.form['enroll'].strip()
    if enroll:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT From_Date, To_Date, Reason, Status FROM OutpassRequests WHERE Enrollment_No=?", (enroll,))
        rows = cursor.fetchall()
        conn.close()
        results = [{'from_date': r[0], 'to_date': r[1], 'reason': r[2], 'status': r[3]} for r in rows]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Check Outpass Status</title>
        <style>
            body { font-family: Arial; padding:20px; background:#f0f7ff; }
            h2 { text-align:center; }
            table { border-collapse: collapse; width:60%; margin:20px auto; }
            th, td { border:1px solid #ccc; padding:10px; text-align:center; }
            th { background:#007bff; color:white; }
            td.status-approved { color:green; font-weight:bold; }
            td.status-rejected { color:red; font-weight:bold; }
            td.status-pending { color:orange; font-weight:bold; }
            input, button { padding:10px; margin:5px; }
        </style>
    </head>
    <body>
        <h2>Check Your Outpass Status</h2>
        <form method="POST" style="text-align:center;">
            <input type="text" name="enroll" placeholder="Enter Enrollment No" value="{{ enroll }}" required>
            <button type="submit">Check Status</button>
        </form>
        {% if results %}
        <table>
            <tr><th>From</th><th>To</th><th>Reason</th><th>Status</th></tr>
            {% for r in results %}
            <tr>
                <td>{{ r.from_date }}</td>
                <td>{{ r.to_date }}</td>
                <td>{{ r.reason }}</td>
                <td class="status-{{ r.status|lower }}">{{ r.status }}</td>
            </tr>
            {% endfor %}
        </table>
        {% elif enroll %}<p style="text-align:center;">No outpass found for this enrollment number.</p>{% endif %}
    </body>
    </html>
    """
    return render_template_string(html, results=results, enroll=enroll)

# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
