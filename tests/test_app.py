import sqlite3

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
