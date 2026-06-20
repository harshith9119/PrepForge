from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from datetime import date, datetime, timedelta
import csv
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'prepforge-dev-key-change-in-production')

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')


def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def migrate_db():
    conn = get_db()
    columns = {row[1] for row in conn.execute('PRAGMA table_info(users)').fetchall()}
    if 'daily_goal' not in columns:
        conn.execute('ALTER TABLE users ADD COLUMN daily_goal INTEGER DEFAULT 3')
        conn.commit()
    conn.close()


migrate_db()


def update_streak(user_id):
    conn = get_db()
    user = conn.execute(
        'SELECT current_streak, last_active_date FROM users WHERE id = ?', (user_id,)
    ).fetchone()

    today = date.today()
    last_active = date.fromisoformat(user['last_active_date']) if user['last_active_date'] else None

    if last_active != today:
        if last_active == today - timedelta(days=1):
            new_streak = user['current_streak'] + 1
        else:
            new_streak = 1

        conn.execute(
            'UPDATE users SET current_streak = ?, last_active_date = ? WHERE id = ?',
            (new_streak, today.isoformat(), user_id),
        )
        conn.commit()
    conn.close()


def count_completed_topics(conn, user_id):
    row = conn.execute('''
        SELECT COUNT(*) FROM (
            SELECT t.id
            FROM topics t
            JOIN problems p ON t.id = p.topic_id
            LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
            GROUP BY t.id
            HAVING COUNT(p.id) = COUNT(up.problem_id) AND COUNT(p.id) > 0
        )
    ''', (user_id,)).fetchone()
    return row[0]


def get_difficulty_stats(conn, user_id):
    rows = conn.execute('''
        SELECT p.difficulty,
               COUNT(*) as total,
               SUM(CASE WHEN up.problem_id IS NOT NULL THEN 1 ELSE 0 END) as solved
        FROM problems p
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        GROUP BY p.difficulty
    ''', (user_id,)).fetchall()
    return {row['difficulty']: {'total': row['total'], 'solved': row['solved']} for row in rows}


def get_today_solved_count(conn, user_id):
    return conn.execute('''
        SELECT COUNT(*) FROM user_progress
        WHERE user_id = ? AND date_solved = ?
    ''', (user_id, date.today().isoformat())).fetchone()[0]


def get_user_badges(solved, total, streak, topics_completed):
    badges = []
    if solved >= 1:
        badges.append({'icon': 'fa-star', 'label': 'First Solve', 'color': 'blue'})
    if streak >= 7:
        badges.append({'icon': 'fa-fire', 'label': 'Week Streak', 'color': 'orange'})
    if streak >= 30:
        badges.append({'icon': 'fa-bolt', 'label': 'Monthly Grinder', 'color': 'yellow'})
    if total > 0 and solved >= total * 0.5:
        badges.append({'icon': 'fa-chart-line', 'label': 'Halfway Hero', 'color': 'cyan'})
    if total > 0 and solved >= total:
        badges.append({'icon': 'fa-crown', 'label': 'DSA Master', 'color': 'yellow'})
    if topics_completed >= 5:
        badges.append({'icon': 'fa-trophy', 'label': 'Topic Hunter', 'color': 'purple'})
    return badges


@app.context_processor
def inject_globals():
    return {'current_year': datetime.now().year}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return render_template('register.html')

        hashed_pw = generate_password_hash(password)
        conn = get_db()
        try:
            is_admin = 1 if conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0 else 0
            conn.execute(
                'INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
                (name, email, hashed_pw, is_admin),
            )
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'danger')
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['is_admin'] = user['is_admin']
            update_streak(user['id'])
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    conn = get_db()
    stats = {
        'problems': conn.execute('SELECT COUNT(*) FROM problems').fetchone()[0],
        'topics': conn.execute('SELECT COUNT(*) FROM topics').fetchone()[0],
        'users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
    }
    conn.close()
    return render_template('index.html', stats=stats)


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    user_id = session['user_id']
    total_probs = conn.execute('SELECT COUNT(*) FROM problems').fetchone()[0]
    solved_probs = conn.execute(
        'SELECT COUNT(*) FROM user_progress WHERE user_id = ?', (user_id,)
    ).fetchone()[0]
    user_data = conn.execute(
        'SELECT current_streak, daily_goal FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    daily_goal = user_data['daily_goal'] or 3
    today_solved = get_today_solved_count(conn, user_id)

    recent = conn.execute('''
        SELECT p.title, t.name as topic
        FROM user_progress up
        JOIN problems p ON up.problem_id = p.id
        JOIN topics t ON p.topic_id = t.id
        WHERE up.user_id = ?
        ORDER BY COALESCE(up.solved_at, up.date_solved) DESC
        LIMIT 5
    ''', (user_id,)).fetchall()

    next_problem = conn.execute('''
        SELECT p.id, p.title, p.difficulty, t.name as topic, t.id as topic_id
        FROM problems p
        JOIN topics t ON p.topic_id = t.id
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        WHERE up.problem_id IS NULL
        ORDER BY t.id, p.id
        LIMIT 1
    ''', (user_id,)).fetchone()

    difficulty_stats = get_difficulty_stats(conn, user_id)
    conn.close()

    progress = int((solved_probs / total_probs * 100) if total_probs > 0 else 0)
    return render_template(
        'dashboard.html',
        total=total_probs,
        solved=solved_probs,
        progress=progress,
        streak=user_data['current_streak'],
        recent=recent,
        next_problem=next_problem,
        difficulty_stats=difficulty_stats,
        daily_goal=daily_goal,
        today_solved=today_solved,
    )


@app.route('/DSA_Roadmap')
@login_required
def roadmap():
    conn = get_db()
    user_id = session['user_id']
    topics_data = conn.execute('''
        SELECT t.id, t.name, t.icon,
               COUNT(p.id) as total_problems,
               COUNT(up.problem_id) as solved_problems
        FROM topics t
        LEFT JOIN problems p ON t.id = p.topic_id
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        GROUP BY t.id
        ORDER BY t.id
    ''', (user_id,)).fetchall()
    conn.close()
    return render_template('roadmap.html', topics=topics_data)


@app.route('/topic/<int:topic_id>')
@login_required
def topic(topic_id):
    conn = get_db()
    topic_info = conn.execute('SELECT * FROM topics WHERE id = ?', (topic_id,)).fetchone()
    if not topic_info:
        conn.close()
        flash('Topic not found.', 'warning')
        return redirect(url_for('roadmap'))

    problems = conn.execute('''
        SELECT p.*, CASE WHEN up.problem_id IS NOT NULL THEN 1 ELSE 0 END as is_solved
        FROM problems p
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        WHERE p.topic_id = ?
        ORDER BY
            CASE p.difficulty WHEN 'Easy' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
            p.title
    ''', (session['user_id'], topic_id)).fetchall()

    solved_count = sum(1 for p in problems if p['is_solved'])
    conn.close()
    return render_template(
        'topic.html',
        topic=topic_info,
        problems=problems,
        solved_count=solved_count,
        total_count=len(problems),
    )


@app.route('/toggle_problem', methods=['POST'])
@login_required
def toggle_problem():
    data = request.get_json(silent=True) or {}
    p_id = data.get('problem_id')
    if not p_id:
        return jsonify({'error': 'Missing problem_id'}), 400

    user_id = session['user_id']
    conn = get_db()
    existing = conn.execute(
        'SELECT * FROM user_progress WHERE user_id = ? AND problem_id = ?', (user_id, p_id)
    ).fetchone()

    if existing:
        conn.execute(
            'DELETE FROM user_progress WHERE user_id = ? AND problem_id = ?', (user_id, p_id)
        )
        status = 'unsolved'
    else:
        today = date.today().isoformat()
        conn.execute(
            'INSERT INTO user_progress (user_id, problem_id, date_solved, solved_at) VALUES (?, ?, ?, ?)',
            (user_id, p_id, today, datetime.now().isoformat()),
        )
        status = 'solved'
        update_streak(user_id)

    conn.commit()
    conn.close()
    return jsonify({'status': status})


@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    conn = get_db()
    if request.method == 'POST':
        conn.execute(
            'INSERT INTO problems (topic_id, title, url, difficulty, company_tags) VALUES (?, ?, ?, ?, ?)',
            (
                request.form['topic_id'],
                request.form['title'].strip(),
                request.form['url'].strip(),
                request.form['difficulty'],
                request.form['company_tags'].strip(),
            ),
        )
        conn.commit()
        flash('Problem added successfully!', 'success')

    topics = conn.execute('SELECT * FROM topics ORDER BY id').fetchall()
    problems = conn.execute('''
        SELECT p.*, t.name as topic_name
        FROM problems p
        JOIN topics t ON p.topic_id = t.id
        ORDER BY p.id DESC
    ''').fetchall()
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
    flash('Problem deleted.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/edit/<int:problem_id>', methods=['GET', 'POST'])
@admin_required
def edit_problem(problem_id):
    conn = get_db()
    if request.method == 'POST':
        conn.execute('''
            UPDATE problems SET title=?, url=?, difficulty=?,
            company_tags=?, topic_id=? WHERE id=?
        ''', (
            request.form['title'].strip(),
            request.form['url'].strip(),
            request.form['difficulty'],
            request.form['company_tags'].strip(),
            request.form['topic_id'],
            problem_id,
        ))
        conn.commit()
        flash('Problem updated successfully!', 'success')
        return redirect(url_for('admin'))

    problem = conn.execute('SELECT * FROM problems WHERE id = ?', (problem_id,)).fetchone()
    topics = conn.execute('SELECT * FROM topics ORDER BY id').fetchall()
    conn.close()
    return render_template('edit.html', problem=problem, topics=topics)


@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    user_id = session['user_id']
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    total_probs = conn.execute('SELECT COUNT(*) FROM problems').fetchone()[0]
    solved_probs = conn.execute(
        'SELECT COUNT(*) FROM user_progress WHERE user_id = ?', (user_id,)
    ).fetchone()[0]
    topics_completed = count_completed_topics(conn, user_id)
    difficulty_stats = get_difficulty_stats(conn, user_id)
    conn.close()

    progress = int((solved_probs / total_probs * 100) if total_probs > 0 else 0)
    badges = get_user_badges(solved_probs, total_probs, user['current_streak'], topics_completed)
    return render_template(
        'profile.html',
        user=user,
        solved=solved_probs,
        total=total_probs,
        progress=progress,
        topics_completed=topics_completed,
        difficulty_stats=difficulty_stats,
        badges=badges,
    )


@app.route('/company')
@login_required
def company():
    conn = get_db()
    user_id = session['user_id']
    problems = conn.execute('''
        SELECT p.*, CASE WHEN up.problem_id IS NOT NULL THEN 1 ELSE 0 END as is_solved
        FROM problems p
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        WHERE p.company_tags IS NOT NULL AND p.company_tags != ''
    ''', (user_id,)).fetchall()
    conn.close()

    company_dict = {}
    company_stats = {}
    for p in problems:
        tags = [tag.strip() for tag in p['company_tags'].split(',')]
        for tag in tags:
            if not tag:
                continue
            if tag not in company_dict:
                company_dict[tag] = []
                company_stats[tag] = {'total': 0, 'solved': 0}
            company_dict[tag].append(p)
            company_stats[tag]['total'] += 1
            if p['is_solved']:
                company_stats[tag]['solved'] += 1

    sorted_companies = dict(sorted(company_dict.items()))
    return render_template(
        'company.html',
        companies=sorted_companies,
        company_stats=company_stats,
    )


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
        stream = io.StringIO(file.stream.read().decode('UTF8'), newline=None)
        csv_input = csv.DictReader(stream)

        conn = get_db()
        success_count = 0
        try:
            for row in csv_input:
                conn.execute('''
                    INSERT INTO problems (topic_id, title, url, difficulty, company_tags)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    row['topic_id'],
                    row['title'].strip(),
                    row['url'].strip(),
                    row['difficulty'],
                    row.get('company_tags', '').strip(),
                ))
                success_count += 1
            conn.commit()
            flash(f'Success! {success_count} problems added to the database.', 'success')
        except Exception:
            flash('Error processing CSV: make sure your column headers are correct.', 'danger')
        finally:
            conn.close()
    else:
        flash('Please upload a valid .csv file.', 'danger')

    return redirect(url_for('admin'))


@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    difficulty = request.args.get('difficulty', 'All')
    results = []

    if query or difficulty != 'All':
        conn = get_db()
        user_id = session['user_id']
        sql = '''
            SELECT p.*, t.name as topic_name, t.id as topic_id,
                   CASE WHEN up.problem_id IS NOT NULL THEN 1 ELSE 0 END as is_solved
            FROM problems p
            JOIN topics t ON p.topic_id = t.id
            LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
            WHERE 1=1
        '''
        params = [user_id]

        if query:
            like = f'%{query}%'
            sql += ' AND (p.title LIKE ? OR p.company_tags LIKE ? OR t.name LIKE ?)'
            params.extend([like, like, like])

        if difficulty != 'All':
            sql += ' AND p.difficulty = ?'
            params.append(difficulty)

        sql += ' ORDER BY p.title LIMIT 50'
        results = conn.execute(sql, params).fetchall()
        conn.close()

    return render_template('search.html', query=query, difficulty=difficulty, results=results)


@app.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])

    conn = get_db()
    like = f'%{query}%'
    rows = conn.execute('''
        SELECT p.id, p.title, p.difficulty, p.url, t.name as topic_name, t.id as topic_id,
               CASE WHEN up.problem_id IS NOT NULL THEN 1 ELSE 0 END as is_solved
        FROM problems p
        JOIN topics t ON p.topic_id = t.id
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        WHERE p.title LIKE ? OR p.company_tags LIKE ? OR t.name LIKE ?
        ORDER BY p.title
        LIMIT 8
    ''', (session['user_id'], like, like, like)).fetchall()
    conn.close()

    return jsonify([{
        'id': r['id'],
        'title': r['title'],
        'difficulty': r['difficulty'],
        'url': r['url'],
        'topic_name': r['topic_name'],
        'topic_id': r['topic_id'],
        'is_solved': bool(r['is_solved']),
    } for r in rows])


@app.route('/leaderboard')
@login_required
def leaderboard():
    conn = get_db()
    user_id = session['user_id']
    leaders = conn.execute('''
        SELECT u.id, u.name, u.current_streak,
               COUNT(up.problem_id) as solved,
               RANK() OVER (ORDER BY COUNT(up.problem_id) DESC, u.current_streak DESC) as rank
        FROM users u
        LEFT JOIN user_progress up ON u.id = up.user_id
        GROUP BY u.id
        ORDER BY solved DESC, u.current_streak DESC
        LIMIT 25
    ''').fetchall()

    my_rank = conn.execute('''
        SELECT rank FROM (
            SELECT u.id,
                   RANK() OVER (ORDER BY COUNT(up.problem_id) DESC, u.current_streak DESC) as rank
            FROM users u
            LEFT JOIN user_progress up ON u.id = up.user_id
            GROUP BY u.id
        ) WHERE id = ?
    ''', (user_id,)).fetchone()
    conn.close()

    return render_template('leaderboard.html', leaders=leaders, my_rank=my_rank['rank'] if my_rank else None)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    conn = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        name = request.form['name'].strip()
        try:
            daily_goal = max(1, min(20, int(request.form.get('daily_goal', 3))))
        except (TypeError, ValueError):
            daily_goal = 3

        conn.execute(
            'UPDATE users SET name = ?, daily_goal = ? WHERE id = ?',
            (name, daily_goal, user_id),
        )
        conn.commit()
        session['name'] = name
        flash('Settings saved successfully.', 'success')

    user = conn.execute('SELECT name, email, daily_goal FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return render_template('settings.html', user=user)


@app.route('/practice/random')
@login_required
def random_practice():
    conn = get_db()
    problem = conn.execute('''
        SELECT p.title, p.url, t.name as topic
        FROM problems p
        JOIN topics t ON p.topic_id = t.id
        LEFT JOIN user_progress up ON p.id = up.problem_id AND up.user_id = ?
        WHERE up.problem_id IS NULL
        ORDER BY RANDOM()
        LIMIT 1
    ''', (session['user_id'],)).fetchone()
    conn.close()

    if not problem:
        flash('You have solved every problem. Legend status unlocked!', 'success')
        return redirect(url_for('dashboard'))

    flash(f'Random pick: {problem["title"]} ({problem["topic"]})', 'success')
    return redirect(problem['url'])


@app.route('/api/get-activity')
@login_required
def get_activity():
    conn = get_db()
    activity = conn.execute('''
        SELECT date_solved, COUNT(*) as count
        FROM user_progress
        WHERE user_id = ? AND date_solved >= date('now', '-365 days')
        GROUP BY date_solved
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return jsonify([{'date': row['date_solved'], 'count': row['count']} for row in activity])


@app.route('/admin/clear_all', methods=['POST'])
@admin_required
def clear_all_problems():
    conn = get_db()
    try:
        conn.execute('DELETE FROM user_progress')
        conn.execute('DELETE FROM problems')
        conn.execute('DELETE FROM sqlite_sequence WHERE name="problems"')
        conn.commit()
        flash('All problems and progress have been completely wiped.', 'success')
    except Exception:
        flash('An error occurred while trying to clear the database.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True)
