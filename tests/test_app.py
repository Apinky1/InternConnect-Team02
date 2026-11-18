import sqlite3
from datetime import date, timedelta

import pytest
from app import create_app


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / 'test.db')


@pytest.fixture
def client(db_path):
    app = create_app({'TESTING': True, 'DATABASE': db_path})
    return app.test_client()


def add(client, company='Example Co', position='Intern', deadline=''):
    return client.post(
        '/applications',
        data={'company': company, 'position': position, 'deadline': deadline},
        follow_redirects=True,
    )


def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'InternConnect' in response.data


def test_add_and_update_application(client):
    response = client.post('/applications', data={'company': 'Example Co', 'position': 'Intern'}, follow_redirects=True)
    assert b'Example Co' in response.data
    response = client.post('/applications/1/status', data={'status': 'Interviewing'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Interviewing' in response.data


def test_required_fields(client):
    response = client.post('/applications', data={'company': '', 'position': ''}, follow_redirects=True)
    assert b'required' in response.data


def test_health(client):
    assert client.get('/health').json == {'status': 'ok'}


# --- Add: validation -------------------------------------------------------

def test_add_with_deadline(client):
    response = add(client, deadline='2026-12-01')
    assert b'2026-12-01' in response.data


def test_add_rejects_invalid_deadline(client):
    response = add(client, deadline='not-a-date')
    assert b'valid date' in response.data
    assert b'Application added.' not in response.data


def test_add_rejects_impossible_date(client):
    response = add(client, deadline='2026-02-31')
    assert b'valid date' in response.data


def test_add_rejects_too_long_company(client):
    response = add(client, company='x' * 121)
    assert b'120 characters' in response.data
    assert b'Application added.' not in response.data


def test_add_trims_whitespace(client):
    response = add(client, company='  Spaced Co  ', position='  Intern  ')
    assert b'Spaced Co' in response.data


# --- Edit ------------------------------------------------------------------

def test_edit_page_is_prefilled(client):
    add(client, company='Nationwide', position='Analyst Intern', deadline='2026-12-01')
    response = client.get('/applications/1/edit')
    assert response.status_code == 200
    assert b'Nationwide' in response.data
    assert b'Analyst Intern' in response.data
    assert b'2026-12-01' in response.data


def test_edit_updates_all_fields(client):
    add(client, company='Old Co', position='Old Role')
    response = client.post(
        '/applications/1/edit',
        data={'company': 'New Co', 'position': 'New Role', 'deadline': '2026-12-15'},
        follow_redirects=True,
    )
    assert b'Application updated.' in response.data
    assert b'New Co' in response.data
    assert b'New Role' in response.data
    assert b'2026-12-15' in response.data
    assert b'Old Co' not in response.data


def test_edit_can_clear_deadline(client):
    add(client, deadline='2026-12-01')
    client.post('/applications/1/edit', data={'company': 'Example Co', 'position': 'Intern', 'deadline': ''})
    assert b'2026-12-01' not in client.get('/').data


def test_edit_keeps_status(client, db_path):
    add(client)
    client.post('/applications/1/status', data={'status': 'Offer'})
    client.post('/applications/1/edit', data={'company': 'Renamed Co', 'position': 'Intern', 'deadline': ''})
    connection = sqlite3.connect(db_path)
    company, status = connection.execute('SELECT company, status FROM applications WHERE id = 1').fetchone()
    connection.close()
    assert (company, status) == ('Renamed Co', 'Offer')


def test_edit_rejects_blank_fields(client):
    add(client)
    response = client.post('/applications/1/edit', data={'company': '', 'position': 'Intern', 'deadline': ''})
    assert response.status_code == 400
    assert b'required' in response.data
    assert b'Example Co' in client.get('/').data  # unchanged


def test_edit_rejects_bad_deadline(client):
    add(client)
    response = client.post('/applications/1/edit', data={'company': 'Example Co', 'position': 'Intern', 'deadline': '12/01/2026'})
    assert response.status_code == 400
    assert b'valid date' in response.data


def test_edit_error_keeps_correct_form_target(client):
    add(client)
    add(client, company='Second Co')
    response = client.post('/applications/2/edit', data={'company': '', 'position': 'Intern', 'deadline': ''})
    assert b'/applications/2/edit' in response.data


def test_edit_missing_application_returns_404(client):
    assert client.get('/applications/999/edit').status_code == 404
    response = client.post('/applications/999/edit', data={'company': 'A', 'position': 'B', 'deadline': ''})
    assert response.status_code == 404


# --- Status and delete -----------------------------------------------------

def test_invalid_status_rejected(client):
    add(client)
    response = client.post('/applications/1/status', data={'status': 'Hired!!'}, follow_redirects=True)
    assert b'Invalid status' in response.data


def test_status_update_missing_application_returns_404(client):
    response = client.post('/applications/999/status', data={'status': 'Offer'})
    assert response.status_code == 404


def test_delete_application(client):
    add(client)
    response = client.post('/applications/1/delete', follow_redirects=True)
    assert b'Application deleted.' in response.data
    assert b'Example Co' not in response.data


def test_delete_missing_application_returns_404(client):
    response = client.post('/applications/999/delete')
    assert response.status_code == 404


# --- Database constraints --------------------------------------------------

def test_database_rejects_invalid_status(client, db_path):
    connection = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO applications (company, position, status) VALUES ('A', 'B', 'Bogus')")
    connection.close()


def test_database_requires_company(client, db_path):
    connection = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO applications (company, position) VALUES (NULL, 'B')")
    connection.close()


# --- Database location -----------------------------------------------------

def test_database_path_comes_from_environment(tmp_path, monkeypatch):
    db_file = tmp_path / 'data' / 'custom.db'  # parent folder does not exist yet
    monkeypatch.setenv('DATABASE_PATH', str(db_file))
    app = create_app({'TESTING': True})
    assert app.config['DATABASE'] == str(db_file)
    assert db_file.exists()
    client = app.test_client()
    client.post('/applications', data={'company': 'Env Co', 'position': 'Intern'})
    assert b'Env Co' in client.get('/').data


# --- Interviews and deadlines (events) ---------------------------------------

def add_event(client, application_id=1, type='Interview', event_date='2026-12-01', event_time='', notes=''):
    return client.post(
        '/events',
        data={
            'application_id': application_id,
            'type': type,
            'event_date': event_date,
            'event_time': event_time,
            'notes': notes,
        },
        follow_redirects=True,
    )


def test_events_page_loads_empty(client):
    response = client.get('/events')
    assert response.status_code == 200
    assert b'Add an application on the dashboard first' in response.data


def test_events_page_lists_applications_in_form(client):
    add(client, company='Nationwide')
    assert b'Nationwide' in client.get('/events').data


def test_add_interview(client):
    add(client, company='Nationwide', position='Analyst')
    response = add_event(client, type='Interview', event_date='2026-12-01', event_time='14:30', notes='Zoom')
    assert b'Interview added.' in response.data
    assert b'2026-12-01' in response.data
    assert b'14:30' in response.data
    assert b'Nationwide' in response.data
    assert b'Zoom' in response.data


def test_add_deadline_without_time_or_notes(client):
    add(client)
    response = add_event(client, type='Deadline')
    assert b'Deadline added.' in response.data


def test_events_are_sorted_by_date(client):
    add(client)
    add_event(client, event_date='2026-12-20', notes='later-one')
    add_event(client, event_date='2026-12-02', notes='sooner-one')
    html = client.get('/events').data
    assert html.index(b'sooner-one') < html.index(b'later-one')


def test_past_events_are_marked(client):
    add(client)
    add_event(client, event_date='2000-01-01')
    assert b'(past)' in client.get('/events').data


def test_event_rejects_invalid_type(client):
    add(client)
    response = add_event(client, type='Party')
    assert b'Interview or Deadline' in response.data
    assert b'Party' not in client.get('/events').data


def test_event_requires_date(client):
    add(client)
    response = add_event(client, event_date='')
    assert b'date is required' in response.data


def test_event_rejects_invalid_date(client):
    add(client)
    assert b'valid date' in add_event(client, event_date='2026-02-31').data
    assert b'valid date' in add_event(client, event_date='tomorrow').data


def test_event_rejects_invalid_time(client):
    add(client)
    assert b'valid time' in add_event(client, event_time='25:99').data
    assert b'valid time' in add_event(client, event_time='noon').data


def test_event_rejects_long_notes(client):
    add(client)
    response = add_event(client, notes='x' * 501)
    assert b'500 characters' in response.data


def test_event_rejects_missing_application(client):
    response = add_event(client, application_id=999)
    assert b'does not exist' in response.data


def test_event_rejects_non_numeric_application(client):
    add(client)
    response = add_event(client, application_id='abc')
    assert b'Choose an application' in response.data


def test_delete_event(client):
    add(client)
    add_event(client, notes='delete-me')
    response = client.post('/events/1/delete', follow_redirects=True)
    assert b'Event deleted.' in response.data
    assert b'delete-me' not in response.data


def test_delete_missing_event_returns_404(client):
    assert client.post('/events/999/delete').status_code == 404


def test_deleting_application_deletes_its_events(client, db_path):
    add(client)
    add_event(client, notes='orphan-check')
    client.post('/applications/1/delete')
    connection = sqlite3.connect(db_path)
    remaining = connection.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    connection.close()
    assert remaining == 0


def test_database_rejects_event_for_missing_application(client, db_path):
    connection = sqlite3.connect(db_path)
    connection.execute('PRAGMA foreign_keys = ON')
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO events (application_id, type, event_date) VALUES (999, 'Interview', '2026-12-01')")
    connection.close()


def test_database_rejects_invalid_event_type(client, db_path):
    add(client)
    connection = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO events (application_id, type, event_date) VALUES (1, 'Party', '2026-12-01')")
    connection.close()


# --- Career-readiness checklist ----------------------------------------------

def checklist_rows(db_path):
    connection = sqlite3.connect(db_path)
    rows = connection.execute('SELECT id, title, completed FROM checklist_items ORDER BY id').fetchall()
    connection.close()
    return rows


def test_checklist_is_seeded_with_defaults(client, db_path):
    rows = checklist_rows(db_path)
    assert len(rows) == 10
    assert all(completed == 0 for _, _, completed in rows)
    assert b'Update your resume' in client.get('/checklist').data


def test_checklist_seeding_does_not_duplicate_on_restart(client, db_path):
    create_app({'TESTING': True, 'DATABASE': db_path})  # simulates restarting the app
    assert len(checklist_rows(db_path)) == 10


def test_checklist_progress_starts_at_zero(client):
    html = client.get('/checklist').data
    assert b'0 of 10' in html
    assert b'(0%)' in html


def test_toggle_marks_complete_and_updates_progress(client, db_path):
    response = client.post('/checklist/1/toggle', follow_redirects=True)
    assert response.status_code == 200
    assert b'1 of 10' in response.data
    assert b'(10%)' in response.data
    assert checklist_rows(db_path)[0][2] == 1


def test_toggle_twice_unchecks(client, db_path):
    client.post('/checklist/1/toggle')
    client.post('/checklist/1/toggle')
    assert checklist_rows(db_path)[0][2] == 0


def test_toggle_missing_item_returns_404(client):
    assert client.post('/checklist/999/toggle').status_code == 404


def test_progress_rounds_to_whole_percent(client):
    for item_id in (1, 2, 3):
        client.post(f'/checklist/{item_id}/toggle')
    assert b'3 of 10' in client.get('/checklist').data
    assert b'(30%)' in client.get('/checklist').data


def test_add_custom_checklist_item(client, db_path):
    response = client.post('/checklist', data={'title': '  Finish portfolio site  '}, follow_redirects=True)
    assert b'Checklist item added.' in response.data
    assert b'Finish portfolio site' in response.data
    assert len(checklist_rows(db_path)) == 11
    assert b'0 of 11' in response.data


def test_add_checklist_item_rejects_blank(client, db_path):
    response = client.post('/checklist', data={'title': '   '}, follow_redirects=True)
    assert b'required' in response.data
    assert len(checklist_rows(db_path)) == 10


def test_add_checklist_item_rejects_too_long(client, db_path):
    response = client.post('/checklist', data={'title': 'x' * 121}, follow_redirects=True)
    assert b'120 characters' in response.data
    assert len(checklist_rows(db_path)) == 10


def test_delete_checklist_item(client, db_path):
    response = client.post('/checklist/1/delete', follow_redirects=True)
    assert b'Checklist item deleted.' in response.data
    assert len(checklist_rows(db_path)) == 9
    assert b'0 of 9' in response.data


def test_delete_missing_checklist_item_returns_404(client):
    assert client.post('/checklist/999/delete').status_code == 404


def test_empty_checklist_shows_message_and_zero_percent(client):
    for item_id in range(1, 11):
        client.post(f'/checklist/{item_id}/delete')
    html = client.get('/checklist').data
    assert b'Your checklist is empty' in html
    assert b'(0%)' in html


def test_database_rejects_invalid_completed_value(client, db_path):
    connection = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO checklist_items (title, completed) VALUES ('x', 5)")
    connection.close()


# --- Dashboard additions -----------------------------------------------------

def days_from_today(days):
    return (date.today() + timedelta(days=days)).isoformat()


def test_dashboard_shows_checklist_progress(client):
    client.post('/checklist/1/toggle')
    client.post('/checklist/2/toggle')
    html = client.get('/').data
    assert b'2 of 10' in html
    assert b'(20%)' in html
    assert b'/checklist' in html


def test_dashboard_with_no_events_shows_empty_message(client):
    assert b'Nothing coming up' in client.get('/').data


def test_dashboard_shows_upcoming_events(client):
    add(client, company='Nationwide')
    add_event(client, type='Interview', event_date=days_from_today(3), event_time='09:30')
    html = client.get('/').data
    assert b'Nationwide' in html
    assert days_from_today(3).encode() in html
    assert b'09:30' in html


def test_dashboard_hides_past_events(client):
    add(client)
    add_event(client, event_date='2000-01-01', notes='old')
    assert b'2000-01-01' not in client.get('/').data


def test_dashboard_includes_events_happening_today(client):
    add(client)
    add_event(client, type='Deadline', event_date=days_from_today(0))
    assert b'Nothing coming up' not in client.get('/').data


def test_dashboard_limits_and_orders_upcoming_events(client):
    add(client)
    for offset in (9, 2, 7, 4, 6, 3, 8):  # 7 events, added out of order
        add_event(client, event_date=days_from_today(offset))
    html = client.get('/').data.decode()
    # Sorted, the events are +2, +3, +4, +6, +7, +8, +9; only the first five are shown.
    assert days_from_today(2) in html
    assert days_from_today(7) in html
    assert days_from_today(8) not in html
    assert days_from_today(9) not in html
    assert html.index(days_from_today(2)) < html.index(days_from_today(3)) < html.index(days_from_today(4))
