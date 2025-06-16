import sqlite3

conn = sqlite3.connect("consultations.db")
cursor = conn.cursor()

cursor.execute("SELECT id, filename, LENGTH(data), timestamp FROM summaries")
rows = cursor.fetchall()

if rows:
    for row in rows:
        print(f"ID: {row[0]} | Filename: {row[1]} | Size: {row[2]} bytes | Time: {row[3]}")
else:
    print("⚠️ No summaries found in the database.")

conn.close()
