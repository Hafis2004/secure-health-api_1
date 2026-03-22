import pytest
import json
from unittest.mock import patch, MagicMock
import jwt
from server import app
from compliance import data_minimize

@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def viewer_token():
    """Generate a mock viewer JWT token."""
    payload = {
        'sub': 'viewer-user',
        'preferred_username': 'lab_viewer',
        'realm_access': {'roles': ['viewer']},
        'resource_access': {'health-api': {'roles': []}}
    }
    # For testing, we'll use this as a raw JWT string
    return jwt.encode(payload, 'secret', algorithm='HS256')

@pytest.fixture
def editor_token():
    """Generate a mock editor JWT token."""
    payload = {
        'sub': 'editor-user',
        'preferred_username': 'lab_editor',
        'realm_access': {'roles': ['editor']},
        'resource_access': {'health-api': {'roles': ['editor']}}
    }
    return jwt.encode(payload, 'secret', algorithm='HS256')

def test_minimize():
    """Test that data_minimize strips sensitive fields."""
    p = {'id':'1','name':'A','dob':'2000-01-01','consent':True,'ssn':'X'}
    m = data_minimize(p)
    assert 'ssn' not in m and 'name' in m

@patch('auth._jwks')
@patch('storage.get_record')
def test_get_record_viewer(mock_get, mock_jwks, client, viewer_token):
    """Test GET /records/<pid> with viewer role."""
    mock_jwks.return_value = {'keys': []}
    mock_get.return_value = {'id': 'patient123', 'name': 'John Doe', 'dob': '1990-01-01'}
    
    response = client.get(
        '/records/patient123',
        headers={'Authorization': f'Bearer {viewer_token}'}
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == 'patient123'
    assert data['name'] == 'John Doe'

@patch('auth._jwks')
@patch('storage.save_record')
def test_post_record_editor(mock_save, mock_jwks, client, editor_token):
    """Test POST /records with editor role."""
    mock_jwks.return_value = {'keys': []}
    mock_save.return_value = 'patient456'
    
    payload = {
        'patient_id': 'patient456',
        'name': 'Jane Doe',
        'dob': '1992-05-15',
        'consent': True
    }
    
    response = client.post(
        '/records',
        data=json.dumps(payload),
        headers={
            'Authorization': f'Bearer {editor_token}',
            'Content-Type': 'application/json'
        }
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['id'] == 'patient456'

@patch('auth._jwks')
def test_post_record_viewer_forbidden(mock_jwks, client, viewer_token):
    """Test POST /records with viewer role (should be forbidden)."""
    mock_jwks.return_value = {'keys': []}
    
    payload = {
        'patient_id': 'patient789',
        'name': 'Bob Smith',
        'dob': '1980-03-20',
        'consent': True
    }
    
    response = client.post(
        '/records',
        data=json.dumps(payload),
        headers={
            'Authorization': f'Bearer {viewer_token}',
            'Content-Type': 'application/json'
        }
    )
    
    assert response.status_code == 403
    data = json.loads(response.data)
    assert 'forbidden' in data['error'].lower() or data['error'] == 'forbidden'

@patch('auth._jwks')
@patch('storage.get_record')
def test_get_all_records_editor(mock_get, mock_jwks, client, editor_token):
    """Test GET /records with editor role (list all)."""
    mock_jwks.return_value = {'keys': []}
    # Mock multiple records
    mock_get.side_effect = [
        {'id': 'patient1', 'name': 'Patient 1', 'dob': '1990-01-01'},
        {'id': 'patient2', 'name': 'Patient 2', 'dob': '1992-05-15'}
    ]
    
    response = client.get(
        '/records',
        headers={'Authorization': f'Bearer {editor_token}'}
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'records' in data
    assert 'count' in data

@patch('auth._jwks')
def test_missing_token(mock_jwks, client):
    """Test request without token."""
    response = client.get('/records')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'error' in data