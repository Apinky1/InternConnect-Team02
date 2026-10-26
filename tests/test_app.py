import pytest
from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'test.db')})
    return app.test_client()


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
