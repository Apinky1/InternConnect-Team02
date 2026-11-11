import os
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, abort, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
STATUSES = ('Applied', 'Interviewing', 'Offer', 'Rejected')
MAX_TEXT_LENGTH = 120


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


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-only-change-me'), DATABASE=str(BASE_DIR / 'internconnect.db'))
    if test_config:
        app.config.update(test_config)

    def get_db():
        connection = sqlite3.connect(app.config['DATABASE'])
        connection.row_factory = sqlite3.Row
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

    @app.route('/')
    def index():
        with get_db() as connection:
            applications = connection.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()
        counts = {status: sum(a['status'] == status for a in applications) for status in STATUSES}
        return render_template('index.html', applications=applications, statuses=STATUSES, counts=counts)

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

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='127.0.0.1', port=int(os.environ.get('PORT', 5000)))
