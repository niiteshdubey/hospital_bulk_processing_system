import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_csv_bytes(text):
    return io.BytesIO(text.encode("utf-8"))

def test_csv_validation_good():
    csv = "name,address,phone\nGH,1 Main,123\nMH,2 Center,456\n"
    files = {"file": ("test.csv", get_csv_bytes(csv), "text/csv")}
    r = client.post("/hospitals/validate-csv", files=files)
    assert r.status_code == 200
    resp = r.json()
    assert resp["valid"] is True
    assert resp["row_count"] == 2

def test_csv_validation_bad():
    csv = "nope,wrong\none,two\n"
    files = {"file": ("test.csv", get_csv_bytes(csv), "text/csv")}
    r = client.post("/hospitals/validate-csv", files=files)
    assert r.status_code == 200
    resp = r.json()
    assert resp["valid"] is False
    assert any("Missing required columns" in e for e in resp["errors"])

def test_bulk_upload_sync(monkeypatch):
    # Monkeypatch remote API calls to avoid real HTTP requests.
    from app import services
    
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
            self.text = str(json_data)
        
        def json(self):
            return self._json_data
    
    def dummy_create_hospital(hospital): 
        return MockResponse(200, {"id": "fake", "name": hospital["name"]})
    def dummy_activate_batch(batch_id): 
        return MockResponse(200, {})
    
    monkeypatch.setattr(services, "create_hospital", dummy_create_hospital)
    monkeypatch.setattr(services, "activate_batch", dummy_activate_batch)

    csv = "name,address\nGH Main,1 Main\n"
    files = {"file": ("test.csv", get_csv_bytes(csv), "text/csv")}
    r = client.post("/hospitals/bulk?wait=true", files=files)
    assert r.status_code == 200
    resp = r.json()
    assert "batch_id" in resp
    assert resp["processed_hospitals"] == 1
    assert resp["failed_hospitals"] == 0
    assert resp["batch_activated"] is True
    assert isinstance(resp["hospitals"], list)

def test_bulk_upload_async(monkeypatch):
    # Patch remote calls and speed up background task demo.
    from app import services, utils
    
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
            self.text = str(json_data)
        
        def json(self):
            return self._json_data
    
    def dummy_create_hospital(hospital): 
        return MockResponse(200, {"id": "fake", "name": hospital["name"]})
    def dummy_activate_batch(batch_id): 
        return MockResponse(200, {})
    
    monkeypatch.setattr(services, "create_hospital", dummy_create_hospital)
    monkeypatch.setattr(services, "activate_batch", dummy_activate_batch)

    csv = "name,address\nGH Main,1 Main\n"
    files = {"file": ("test.csv", get_csv_bytes(csv), "text/csv")}
    r = client.post("/hospitals/bulk", files=files)
    assert r.status_code == 200
    resp = r.json()
    assert "batch_id" in resp
    # Optional: Poll progress here if desired...
