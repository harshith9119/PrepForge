import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    last_active_date DATE,
                    daily_goal INTEGER DEFAULT 3
                 )''')

    # Topics Table
    c.execute('''CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    icon TEXT NOT NULL
                 )''')

    # Problems Table
    c.execute('''CREATE TABLE IF NOT EXISTS problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    company_tags TEXT,
                    FOREIGN KEY(topic_id) REFERENCES topics(id)
                 )''')

    # User Progress Table (Updated with date_solved for Heatmap)
    c.execute('''CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER,
                    problem_id INTEGER,
                    date_solved DATE, 
                    solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, problem_id),
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(problem_id) REFERENCES problems(id)
                 )''')

    # Insert default topics
    topics = [
        ('Basics', 'fas fa-book'), 
        ('Recursion', 'fas fa-redo'), 
        ('Array', 'fas fa-layer-group'), 
        ('Binary Search', 'fas fa-search'),
        ('Linked List', 'fas fa-link'),
        ('Stack', 'fas fa-database'),
        ('Queue', 'fas fa-stream'),
        ('Tree', 'fas fa-sitemap'),
        ('Graph', 'fas fa-project-diagram'), 
        ('DP', 'fas fa-brain')
    ]
    c.executemany('INSERT OR IGNORE INTO topics (name, icon) VALUES (?, ?)', topics)

    conn.commit()
    conn.close()
    print("Database initialized successfully with the updated schema!")

if __name__ == '__main__':
    init_db()