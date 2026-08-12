from flask import Flask, render_template_string, request, jsonify
import psycopg2 # PostgreSQL compiler for cloud databases
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

app = Flask(__name__)

# Cloud Environment Variable se database URL lena (Heroku/Render auto-provide karte hain)
DATABASE_URL = os.environ.get('DATABASE_URL', 'dbname=cycle_db user=postgres password=secret')

def get_db_connection():
    # SSL mode jaruri hai cloud database secure rakhne ke liye
    conn = psycopg2.connect(DATABASE_URL, sslmode='require' if 'DATABASE_URL' in os.environ else 'disable')
    return conn

# Database Table Initialize karna
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cycle_logs (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL,
            student_name VARCHAR(100),
            cycle_qr VARCHAR(100) NOT NULL,
            action VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@app.route('/api/log_transaction', methods=['POST'])
def log_transaction():
    data = request.json
    student_id = data.get('student_id')
    student_name = data.get('student_name', '')
    cycle_qr = data.get('cycle_qr')
    action = data.get('action')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cycle_logs (student_id, student_name, cycle_qr, action)
        VALUES (%s, %s, %s, %s) RETURNING timestamp;
    ''', (student_id, student_name, cycle_qr, action))
    
    timestamp = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({"status": "success", "message": f"Cycle {action}ed successfully!", "timestamp": formatted_time})

@app.route('/api/get_records', methods=['GET'])
def get_records():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT student_id, student_name, cycle_qr, action, to_char(timestamp, \'YYYY-MM-DD HH24:MI:SS\') as timestamp FROM cycle_logs ORDER BY id DESC')
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(records)

# ---- Frontend HTML Code (Same dynamic camera interface) ----
HTML_CODE = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud Cycle System</title>
    <script src="https://unpkg.com"></script>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 20px; background-color: #f4f4f9; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        button { background-color: #007bff; color: white; border: none; padding: 12px 20px; margin: 10px; cursor: pointer; border-radius: 5px; font-size: 16px; font-weight: bold;}
        button:hover { background-color: #0056b3; }
        .return-btn { background-color: #28a745; }
        #reader { width: 100%; margin-top: 15px; border-radius: 8px; overflow: hidden; }
        #form-container, #scanner-container { display: none; margin-top: 20px; }
        input { width: 85%; padding: 12px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
        .log-table { width: 100%; margin-top: 20px; border-collapse: collapse; }
        .log-table th, .log-table td { border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 14px; }
        .log-table th { background-color: #007bff; color: white; }
    </style>
</head>
<body>
<div class="container">
    <h2>🚀 Institute Cloud Cycle Portal</h2>
    <p>Apna option chunein:</p>
    <button onclick="startProcess('ISSUE')">Issue Cycle (Lein)</button>
    <button class="return-btn" onclick="startProcess('DROP')">Drop Cycle (Dene)</button>

    <div id="form-container">
        <h3 id="form-title">Student Details</h3>
        <input type="text" id="studentId" placeholder="Student Roll No / ID">
        <input type="text" id="studentName" placeholder="Student Name">
        <br>
        <button onclick="openScanner()">Scan QR Code</button>
    </div>

    <div id="scanner-container">
        <h3>Camera ke samne Cycle QR layein...</h3>
        <div id="reader"></div>
        <button style="background-color: #dc3545;" onclick="resetSystem()">Cancel</button>
    </div>

    <h3>📋 Live Central Database Log</h3>
    <table class="log-table">
        <thead>
            <tr>
                <th>Student ID</th>
                <th>Naam</th>
                <th>Cycle QR</th>
                <th>Status</th>
                <th>Date & Time</th>
            </tr>
        </thead>
        <tbody id="logBody"></tbody>
    </table>
</div>

<script>
    let currentAction = "";
    let html5QrcodeScanner;

    window.onload = function() { loadRecords(); };

    function startProcess(action) {
        currentAction = action;
        document.getElementById('form-container').style.display = 'block';
        document.getElementById('scanner-container').style.display = 'none';
        document.getElementById('form-title').innerText = action === 'ISSUE' ? "Cycle Issue Form" : "Cycle Drop Form";
        document.getElementById('studentName').style.display = action === 'DROP' ? 'none' : 'inline-block';
    }

    function openScanner() {
        const studentId = document.getElementById('studentId').value;
        if (!studentId) { alert("Kripya Student ID dalein!"); return; }
        document.getElementById('form-container').style.display = 'none';
        document.getElementById('scanner-container').style.display = 'block';

        html5QrcodeScanner = new Html5QrcodeScanner("reader", { fps: 15, qrbox: 250 });
        html5QrcodeScanner.render(onScanSuccess);
    }

    function onScanSuccess(decodedText) {
        html5QrcodeScanner.clear();
        const studentId = document.getElementById('studentId').value;
        const studentName = document.getElementById('studentName').value;

        fetch('/api/log_transaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id: studentId, student_name: studentName, cycle_qr: decodedText, action: currentAction })
        })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            loadRecords();
            resetSystem();
        });
    }

    function loadRecords() {
        fetch('/api/get_records')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('logBody');
            tbody.innerHTML = "";
            data.forEach(row => {
                const tr = tbody.insertRow();
                tr.insertCell(0).innerText = row.student_id;
                tr.insertCell(1).innerText = row.student_name || "N/A";
                tr.insertCell(2).innerText = row.cycle_qr;
                tr.insertCell(3).innerText = row.action;
                tr.insertCell(4).innerText = row.timestamp;
            });
        });
    }

    function resetSystem() {
        if(html5QrcodeScanner) { html5QrcodeScanner.clear().catch(e => {}); }
        document.getElementById('form-container').style.display = 'none';
        document.getElementById('scanner-container').style.display = 'none';
        document.getElementById('studentId').value = "";
        document.getElementById('studentName').value = "";
    }
</script>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
