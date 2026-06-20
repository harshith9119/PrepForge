import sqlite3

def clean_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # 1. Wipe the problems and user progress tables completely
    c.execute('DELETE FROM user_progress')
    c.execute('DELETE FROM problems')
    
    # 2. Reset the problem ID counter back to 1
    c.execute('DELETE FROM sqlite_sequence WHERE name="problems"')
    conn.commit()
    
    print("✅ Success: All mismatched problems have been deleted!")
    print("Your Admin account and topics are safe.\n")

    # 3. Fetch and print your TRUE Topic IDs
    print("📍 HERE ARE YOUR TRUE TOPIC IDs FOR THE CSV:")
    topics = c.execute('SELECT id, name FROM topics ORDER BY id').fetchall()
    for t in topics:
        print(f"Replace with {t[0]} -> {t[1]}")

    conn.close()

if __name__ == '__main__':
    clean_database()