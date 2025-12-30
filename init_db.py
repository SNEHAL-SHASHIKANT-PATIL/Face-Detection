import sqlite3
import pandas as pd

# Load Excel data
excel_file = 'DATASET OF COTY STUDENT.CSV.xlsx'
df = pd.read_excel(excel_file)

# Connect to SQLite
conn = sqlite3.connect('outpass.db')
cursor = conn.cursor()

# -------------------------------
# Create Students table
# -------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS Students (
    Enrollment_No TEXT PRIMARY KEY,
    Name TEXT NOT NULL,
    Department TEXT NOT NULL
)
''')

# -------------------------------
# Create OutpassRequests table
# -------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS OutpassRequests (
    Request_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Enrollment_No TEXT NOT NULL,
    From_Date TEXT NOT NULL,
    To_Date TEXT NOT NULL,
    Reason TEXT NOT NULL,
    Status TEXT DEFAULT 'Pending',
    FOREIGN KEY (Enrollment_No) REFERENCES Students (Enrollment_No)
)
''')

# -------------------------------
# Insert student data from Excel
# -------------------------------
for _, row in df.iterrows():
    cursor.execute("INSERT OR IGNORE INTO Students VALUES (?, ?, ?)", (
        str(row['ENROLLMENT NO']),
        row['NAME'],
        row['DEPARTMENT']
    ))

conn.commit()
conn.close()
print("✅ Database created successfully from Excel!")
