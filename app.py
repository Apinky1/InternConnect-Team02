import os
import sqlite3
from pathlib import Path
from flask import Flask, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
STATUSES = ('Applied', 'Interviewing', 'Offer', 'Rejected')


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-only-change-me'), DATABASE=str(BASE_DIR / 'internconnect.db'))
    if test_config:
        app.config.update(test_config)

    def get_db():
        connection = sqlite3.connect(app.config['DATABASE'])
        connection.row_factory = sqlite3.Row
        return connection

    with app.app_context():
        with get_db() as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied',
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
        company = request.form.get('company', '').strip()
        position = request.form.get('position', '').strip()
        deadline = request.form.get('deadline', '').strip()
        if not company or not position:
            flash('Company and position are required.', 'error')
            return redirect(url_for('index'))
        with get_db() as connection:
            connection.execute('INSERT INTO applications (company, position, deadline) VALUES (?, ?, ?)', (company, position, deadline or None))
        flash('Application added.', 'success')
        return redirect(url_for('index'))

    @app.post('/applications/<int:application_id>/status')
    def update_status(application_id):
        status = request.form.get('status', '')
        if status not in STATUSES:
            flash('Invalid status.', 'error')
            return redirect(url_for('index'))
        with get_db() as connection:
            connection.execute('UPDATE applications SET status = ? WHERE id = ?', (status, application_id))
        flash('Application updated.', 'success')
        return redirect(url_for('index'))

    @app.post('/applications/<int:application_id>/delete')
    def delete_application(application_id):
        with get_db() as connection:
            connection.execute('DELETE FROM applications WHERE id = ?', (application_id,))
        flash('Application deleted.', 'success')
        return redirect(url_for('index'))

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='127.0.0.1', port=int(os.environ.get('PORT', 5000)))
