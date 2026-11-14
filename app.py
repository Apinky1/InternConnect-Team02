import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from flask import Flask, abort, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
STATUSES = ('Applied', 'Interviewing', 'Offer', 'Rejected')
EVENT_TYPES = ('Interview', 'Deadline')
MAX_TEXT_LENGTH = 120
MAX_NOTES_LENGTH = 500
UPCOMING_EVENT_LIMIT = 5
DEFAULT_CHECKLIST_ITEMS = (
    'Update your resume',
    'Get your resume reviewed by career services',
    'Create or update your LinkedIn profile',
    'Write a general cover letter template',
    'Build a list of target companies',
    'Prepare a 30-second introduction about yourself',
    'Practice a mock interview',
    'Ask a professor or mentor for a reference',
    'Attend a career fair or networking event',
    'Set up job and internship alerts',
)


def clean_application_form(form):
    """Validate company, position, and deadline from a submitted form.

    Returns (values, error). values is a dict with the cleaned fields
    (deadline is None when blank); error is a message string or None.
    """
    company = form.get('company', '').strip()
    position = form.get('position', '').strip()
    deadline = form.get('deadline', '').strip()
    values = {'company': company, 'position': position, 'deadline': deadline or None}

    if not company or not position:
        return values, 'Company and position are required.'
    if len(company) > MAX_TEXT_LENGTH or len(position) > MAX_TEXT_LENGTH:
        return values, f'Company and position must be {MAX_TEXT_LENGTH} characters or fewer.'
    if deadline:
        try:
            values['deadline'] = datetime.strptime(deadline, '%Y-%m-%d').date().isoformat()
        except ValueError:
            return values, 'Deadline must be a valid date (YYYY-MM-DD).'
    return values, None


def clean_event_form(form):
    """Validate an interview/deadline event from a submitted form.

    Returns (values, error). Checking that the application actually exists
    needs the database, so the route does that part.
    """
    values = {
        'application_id': None,
        'type': form.get('type', '').strip(),
        'event_date': form.get('event_date', '').strip(),
        'event_time': form.get('event_time', '').strip() or None,
        'notes': form.get('notes', '').strip() or None,
    }
    try:
        values['application_id'] = int(form.get('application_id', ''))
    except ValueError:
        return values, 'Choose an application for this event.'
    if values['type'] not in EVENT_TYPES:
        return values, 'Event type must be Interview or Deadline.'
    if not values['event_date']:
        return values, 'Event date is required.'
    try:
        values['event_date'] = datetime.strptime(values['event_date'], '%Y-%m-%d').date().isoformat()
    except ValueError:
        return values, 'Event date must be a valid date (YYYY-MM-DD).'
    if values['event_time']:
        try:
            values['event_time'] = datetime.strptime(values['event_time'], '%H:%M').strftime('%H:%M')
        except ValueError:
            return values, 'Event time must be a valid time (HH:MM).'
    if values['notes'] and len(values['notes']) > MAX_NOTES_LENGTH:
        return values, f'Notes must be {MAX_NOTES_LENGTH} characters or fewer.'
    return values, None


def clean_checklist_title(form):
    """Validate a custom checklist item title. Returns (title, error)."""
    title = form.get('title', '').strip()
    if not title:
        return title, 'Checklist item text is required.'
    if len(title) > MAX_TEXT_LENGTH:
        return title, f'Checklist items must be {MAX_TEXT_LENGTH} characters or fewer.'
    return title, None


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-only-change-me'),
        # On Render, set DATABASE_PATH to a file on a persistent disk (e.g. /var/data/internconnect.db).
        DATABASE=os.environ.get('DATABASE_PATH', str(BASE_DIR / 'internconnect.db')),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    def get_db():
        connection = sqlite3.connect(app.config['DATABASE'])
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    status_list = ', '.join(f"'{status}'" for status in STATUSES)
    with app.app_context():
        with get_db() as connection:
            connection.execute(f'''CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied' CHECK (status IN ({status_list})),
                deadline TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            event_type_list = ', '.join(f"'{t}'" for t in EVENT_TYPES)
            connection.execute(f'''CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK (type IN ({event_type_list})),
                event_date TEXT NOT NULL,
                event_time TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            connection.execute('''CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            # Seed the starter checklist only into an empty table, so restarts never duplicate items.
            if connection.execute('SELECT COUNT(*) FROM checklist_items').fetchone()[0] == 0:
                connection.executemany(
                    'INSERT INTO checklist_items (title) VALUES (?)',
                    [(title,) for title in DEFAULT_CHECKLIST_ITEMS],
                )

    def checklist_progress(connection):
        total, done = connection.execute(
            'SELECT COUNT(*), COALESCE(SUM(completed), 0) FROM checklist_items'
        ).fetchone()
        percent = round(done / total * 100) if total else 0
        return {'done': done, 'total': total, 'percent': percent}

    @app.route('/')
    def index():
        with get_db() as connection:
            applications = connection.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()
            upcoming_events = connection.execute(
                '''SELECT events.*, applications.company, applications.position
                   FROM events JOIN applications ON applications.id = events.application_id
                   WHERE events.event_date >= ?
                   ORDER BY events.event_date, COALESCE(events.event_time, ''), events.id
                   LIMIT ?''',
                (date.today().isoformat(), UPCOMING_EVENT_LIMIT),
            ).fetchall()
            checklist = checklist_progress(connection)
        counts = {status: sum(a['status'] == status for a in applications) for status in STATUSES}
        return render_template(
            'index.html',
            applications=applications,
            statuses=STATUSES,
            counts=counts,
            upcoming_events=upcoming_events,
            checklist=checklist,
        )

    @app.post('/applications')
    def add_application():
        values, error = clean_application_form(request.form)
        if error:
            flash(error, 'error')
            return redirect(url_for('index'))
        with get_db() as connection:
            connection.execute(
                'INSERT INTO applications (company, position, deadline) VALUES (?, ?, ?)',
                (values['company'], values['position'], values['deadline']),
            )
        flash('Application added.', 'success')
        return redirect(url_for('index'))

    @app.get('/applications/<int:application_id>/edit')
    def edit_application_form(application_id):
        with get_db() as connection:
            application = connection.execute('SELECT * FROM applications WHERE id = ?', (application_id,)).fetchone()
        if application is None:
            abort(404)
        return render_template('edit.html', application=application)

    @app.post('/applications/<int:application_id>/edit')
    def edit_application(application_id):
        values, error = clean_application_form(request.form)
        if error:
            flash(error, 'error')
            # Re-show the form with what the user typed, keeping the real id.
            return render_template('edit.html', application={'id': application_id, **values}), 400
        with get_db() as connection:
            cursor = connection.execute(
                'UPDATE applications SET company = ?, position = ?, deadline = ? WHERE id = ?',
                (values['company'], values['position'], values['deadline'], application_id),
            )
        if cursor.rowcount == 0:
            abort(404)
        flash('Application updated.', 'success')
        return redirect(url_for('index'))

    @app.post('/applications/<int:application_id>/status')
    def update_status(application_id):
        status = request.form.get('status', '')
        if status not in STATUSES:
            flash('Invalid status.', 'error')
            return redirect(url_for('index'))
        with get_db() as connection:
            cursor = connection.execute('UPDATE applications SET status = ? WHERE id = ?', (status, application_id))
        if cursor.rowcount == 0:
            abort(404)
        flash('Application updated.', 'success')
        return redirect(url_for('index'))

    @app.post('/applications/<int:application_id>/delete')
    def delete_application(application_id):
        with get_db() as connection:
            cursor = connection.execute('DELETE FROM applications WHERE id = ?', (application_id,))
        if cursor.rowcount == 0:
            abort(404)
        flash('Application deleted.', 'success')
        return redirect(url_for('index'))

    @app.get('/events')
    def events():
        with get_db() as connection:
            event_rows = connection.execute(
                '''SELECT events.*, applications.company, applications.position
                   FROM events JOIN applications ON applications.id = events.application_id
                   ORDER BY events.event_date, COALESCE(events.event_time, ''), events.id'''
            ).fetchall()
            applications = connection.execute('SELECT id, company, position FROM applications ORDER BY company').fetchall()
        return render_template(
            'events.html',
            events=event_rows,
            applications=applications,
            event_types=EVENT_TYPES,
            today=date.today().isoformat(),
        )

    @app.post('/events')
    def add_event():
        values, error = clean_event_form(request.form)
        if error:
            flash(error, 'error')
            return redirect(url_for('events'))
        with get_db() as connection:
            exists = connection.execute('SELECT 1 FROM applications WHERE id = ?', (values['application_id'],)).fetchone()
            if exists is None:
                flash('That application does not exist.', 'error')
                return redirect(url_for('events'))
            connection.execute(
                'INSERT INTO events (application_id, type, event_date, event_time, notes) VALUES (?, ?, ?, ?, ?)',
                (values['application_id'], values['type'], values['event_date'], values['event_time'], values['notes']),
            )
        flash(f"{values['type']} added.", 'success')
        return redirect(url_for('events'))

    @app.post('/events/<int:event_id>/delete')
    def delete_event(event_id):
        with get_db() as connection:
            cursor = connection.execute('DELETE FROM events WHERE id = ?', (event_id,))
        if cursor.rowcount == 0:
            abort(404)
        flash('Event deleted.', 'success')
        return redirect(url_for('events'))

    @app.get('/checklist')
    def checklist():
        with get_db() as connection:
            items = connection.execute('SELECT * FROM checklist_items ORDER BY id').fetchall()
            progress = checklist_progress(connection)
        return render_template('checklist.html', items=items, progress=progress)

    @app.post('/checklist')
    def add_checklist_item():
        title, error = clean_checklist_title(request.form)
        if error:
            flash(error, 'error')
            return redirect(url_for('checklist'))
        with get_db() as connection:
            connection.execute('INSERT INTO checklist_items (title) VALUES (?)', (title,))
        flash('Checklist item added.', 'success')
        return redirect(url_for('checklist'))

    @app.post('/checklist/<int:item_id>/toggle')
    def toggle_checklist_item(item_id):
        with get_db() as connection:
            cursor = connection.execute(
                'UPDATE checklist_items SET completed = 1 - completed WHERE id = ?', (item_id,)
            )
        if cursor.rowcount == 0:
            abort(404)
        return redirect(url_for('checklist'))

    @app.post('/checklist/<int:item_id>/delete')
    def delete_checklist_item(item_id):
        with get_db() as connection:
            cursor = connection.execute('DELETE FROM checklist_items WHERE id = ?', (item_id,))
        if cursor.rowcount == 0:
            abort(404)
        flash('Checklist item deleted.', 'success')
        return redirect(url_for('checklist'))

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='127.0.0.1', port=int(os.environ.get('PORT', 5000)))
