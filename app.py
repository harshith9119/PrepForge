from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from datetime import date, timedelta
import csv
import io

from flask import jsonify
from datetime import datetime, timedelta
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # Change this!

# --- Helper Functions ---
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def update_streak(user_id):
    conn = get_db()
    user = conn.execute('SELECT current_streak, last_active_date FROM users WHERE id = ?', (user_id,)).fetchone()
    
    today = date.today()
    last_active = date.fromisoformat(user['last_active_date']) if user['last_active_date'] else None

    if last_active != today:
        if last_active == today - timedelta(days=1):
            new_streak = user['current_streak'] + 1
        else:
            new_streak = 1 # Streak broken, reset to 1
        
        conn.execute('UPDATE users SET current_streak = ?, last_active_date = ? WHERE id = ?', 
                     (new_streak, today.isoformat(), user_id))
        conn.commit()
    conn.close()

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash("Admin access required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes: Authentication ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name, email, password = request.form['name'], request.form['email'], request.form['password']
        hashed_pw = generate_password_hash(password)
        
        conn = get_db()
        try:
            # Set first user as admin automatically for convenience
            is_admin = 1 if conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0 else 0
            conn.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)', 
                         (name, email, hashed_pw, is_admin))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists.", "danger")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['is_admin'] = user['is_admin']
            update_streak(user['id'])
            return redirect(url_for('dashboard'))
        flash("Invalid email or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

# --- Routes: Core Features ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    user_id = session['user_id']
    
    # Stats
    total_probs = conn.execute('SELECT COUNT(*) FROM problems').fetchone()[0]
    solved_probs = conn.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ?', (user_id,)).fetchone()[0]
    user_data = conn.execute('SELECT current_streak FROM users WHERE id = ?', (user_id,)).fetchone()
    
    # Recent Activity
    recent = conn.execute('''
        SELECT p.title, t.name as topic 
        FROM user_progress up 
        JOIN problems p ON up.problem_id = p.id 
        JOIN topics t ON p.topic_id = t.id
        WHERE up.user_id = ? 
        ORDER BY up.solved_at DESC LIMIT 5
    ''', (user_id,)).fetchall()
    
    conn.close()
    progress = int((solved_probs / total_probs * 100) if total_probs > 0 else 0)
    
    return render_template('dashboard.html', total=total_probs, solved=solved_probs, 
                           progress=progress, streak=user_data['current_streak'], recent=recent)

@app.route('/DSA_Roadmap')
@login_required
def roadmap():
    conn = get_db()
    user_id = session['user_id']
    
    # Get topics with progress calculation
    topics_data = conn.execute('''
        SELECT t.id, t.name, t.icon, 
               COUNT(p.id) as total_problems,
               COUNT(up.problem_id) as solved_problems
        FROM topics t
        LEFT JOIN problems p ON t.id = p.topic_id
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        GROUP BY t.id
    ''', (user_id,)).fetchall()
    conn.close()
    
    return render_template('roadmap.html', topics=topics_data)

@app.route('/topic/<int:topic_id>')
@login_required
def topic(topic_id):
    conn = get_db()
    topic_info = conn.execute('SELECT * FROM topics WHERE id = ?', (topic_id,)).fetchone()
    
    problems = conn.execute('''
        SELECT p.*, CASE WHEN up.problem_id IS NOT NULL THEN 1 ELSE 0 END as is_solved
        FROM problems p
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        WHERE p.topic_id = ?
    ''', (session['user_id'], topic_id)).fetchall()
    conn.close()
    
    return render_template('topic.html', topic=topic_info, problems=problems)

@app.route('/toggle_problem', methods=['POST'])
@login_required
def toggle_problem():
    data = request.get_json()
    p_id = data.get('problem_id')
    user_id = session['user_id']
    
    conn = get_db()
    existing = conn.execute('SELECT * FROM user_progress WHERE user_id = ? AND problem_id = ?', (user_id, p_id)).fetchone()
    
    if existing:
        conn.execute('DELETE FROM user_progress WHERE user_id = ? AND problem_id = ?', (user_id, p_id))
        status = 'unsolved'
    else:
        conn.execute('INSERT INTO user_progress (user_id, problem_id, date_solved) VALUES (?, ?, ?)', 
                     (user_id, p_id, date.today().isoformat()))
        status = 'solved'
        update_streak(user_id)
        
    conn.commit()
    conn.close()
    return jsonify({'status': status})

# --- Routes: Admin Panel ---
@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    conn = get_db()
    if request.method == 'POST':
        t_id = request.form['topic_id']
        title = request.form['title']
        url = request.form['url']
        diff = request.form['difficulty']
        tags = request.form['company_tags']
        
        conn.execute('INSERT INTO problems (topic_id, title, url, difficulty, company_tags) VALUES (?, ?, ?, ?, ?)',
                     (t_id, title, url, diff, tags))
        conn.commit()
        flash("Problem added successfully!", "success")
        
    topics = conn.execute('SELECT * FROM topics').fetchall()
    problems = conn.execute('SELECT p.*, t.name as topic_name FROM problems p JOIN topics t ON p.topic_id = t.id ORDER BY p.id DESC').fetchall()
    conn.close()
    return render_template('admin.html', topics=topics, problems=problems)

@app.route('/admin/delete/<int:problem_id>')
@admin_required
def delete_problem(problem_id):
    conn = get_db()
    conn.execute('DELETE FROM problems WHERE id = ?', (problem_id,))
    conn.execute('DELETE FROM user_progress WHERE problem_id = ?', (problem_id,))
    conn.commit()
    conn.close()
    flash("Problem deleted.", "success")
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:problem_id>', methods=['GET', 'POST'])
@admin_required
def edit_problem(problem_id):
    conn = get_db()
    if request.method == 'POST':
        title = request.form['title']
        url = request.form['url']
        difficulty = request.form['difficulty']
        company_tags = request.form['company_tags']
        topic_id = request.form['topic_id']
        
        conn.execute('''UPDATE problems SET title=?, url=?, difficulty=?, 
                        company_tags=?, topic_id=? WHERE id=?''',
                     (title, url, difficulty, company_tags, topic_id, problem_id))
        conn.commit()
        flash("Problem updated successfully!", "success")
        return redirect(url_for('admin'))
    
    problem = conn.execute('SELECT * FROM problems WHERE id = ?', (problem_id,)).fetchone()
    topics = conn.execute('SELECT * FROM topics').fetchall()
    conn.close()
    return render_template('edit.html', problem=problem, topics=topics)


@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    user_id = session['user_id']
    
    # Get user details
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    # Get global progress stats
    total_probs = conn.execute('SELECT COUNT(*) FROM problems').fetchone()[0]
    solved_probs = conn.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    # Calculate fully completed topics
    topics = conn.execute('SELECT id FROM topics').fetchall()
    topics_completed = 0
    for t in topics:
        t_total = conn.execute('SELECT COUNT(*) FROM problems WHERE topic_id = ?', (t['id'],)).fetchone()[0]
        if t_total > 0:
            t_solved = conn.execute('''SELECT COUNT(*) FROM user_progress up 
                                       JOIN problems p ON up.problem_id = p.id 
                                       WHERE up.user_id = ? AND p.topic_id = ?''', (user_id, t['id'])).fetchone()[0]
            if t_total == t_solved:
                topics_completed += 1
                
    conn.close()
    
    progress = int((solved_probs / total_probs * 100) if total_probs > 0 else 0)
    
    return render_template('profile.html', user=user, solved=solved_probs, total=total_probs, 
                           progress=progress, topics_completed=topics_completed)

@app.route('/company')
@login_required
def company():
    conn = get_db()
    user_id = session['user_id']
    
    # Fetch all problems that have company tags assigned to them
    problems = conn.execute('''
        SELECT p.*, CASE WHEN up.problem_id IS NOT NULL THEN 1 ELSE 0 END as is_solved
        FROM problems p
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        WHERE p.company_tags IS NOT NULL AND p.company_tags != ''
    ''', (user_id,)).fetchall()
    conn.close()
    
    # Process the comma-separated tags and group problems by company
    company_dict = {}
    for p in problems:
        # Split tags like "Amazon, Google" into a list and strip whitespace
        tags = [tag.strip() for tag in p['company_tags'].split(',')]
        for tag in tags:
            if tag:
                if tag not in company_dict:
                    company_dict[tag] = []
                company_dict[tag].append(p)
                
    # Sort companies alphabetically so the UI looks clean
    sorted_companies = dict(sorted(company_dict.items()))
    
    return render_template('company.html', companies=sorted_companies)

@app.route('/admin/bulk_upload', methods=['POST'])
@admin_required
def bulk_upload():
    if 'file' not in request.files:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin'))
    
    if file and file.filename.endswith('.csv'):
        # Read the CSV file dynamically
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        conn = get_db()
        success_count = 0
        
        try:
            for row in csv_input:
                conn.execute('''
                    INSERT INTO problems (topic_id, title, url, difficulty, company_tags) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (row['topic_id'], row['title'], row['url'], row['difficulty'], row['company_tags']))
                success_count += 1
            conn.commit()
            flash(f'Success! {success_count} problems added to the database.', 'success')
        except Exception as e:
            flash(f'Error processing CSV: Make sure your column headers are correct.', 'danger')
        finally:
            conn.close()
    else:
        flash('Please upload a valid .csv file.', 'danger')
        
    return redirect(url_for('admin'))


@app.route('/api/get-activity')
def get_activity():
    if 'user_id' not in session:
        return jsonify([])
        
    conn = get_db()
    # Fetches counts per day for the last year
    activity = conn.execute('''
        SELECT date_solved, COUNT(*) as count 
        FROM user_progress 
        WHERE user_id = ? AND date_solved >= date('now', '-365 days')
        GROUP BY date_solved
    ''', (session['user_id'],)).fetchall()
    
    return jsonify([dict(row) for row in activity])


if __name__ == '__main__':
    app.run(debug=True)