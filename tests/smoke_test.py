import requests
import time

BASE = "http://127.0.0.1:8000"

def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"

def test_create_csv():
    fname = f"smoke_test_{int(time.time())}.csv"
    r = requests.post(f"{BASE}/create-csv", data={"filename": fname})
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_create_answerkey():
    block = "Python\n1 - a\n2 - b\n"
    r = requests.post(f"{BASE}/create-bulk-answerkey", data={"set_name": "S", "block": block})
    assert r.status_code == 200
    data = r.json()
    assert "Saved sectionwise key" in data.get("message","") or "questions" in data.get("message","")
    assert "Saved sectionwise key" in data.get("message","") or "questions" in data.get("message","")
