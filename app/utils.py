import uuid
import requests
from .constants import BASE_URL
import hashlib
import time
import random

progress_store = dict()

def set_progress(batch_id, value):
    progress_store[batch_id] = value

def get_progress(batch_id):
    return progress_store.get(
        batch_id, 
        {
            "progress": 0, 
            "total": 0,
            "status": "unknown",
            "result": None
        }
        )

def generate_batch_id():
    return str(uuid.uuid4())

def create_hospital(hospital_data):
    url = f"{BASE_URL}/hospitals/"
    try:
        resp = requests.post(url, json=hospital_data)
        return resp
    except requests.RequestException as e:
        return {"error": str(e)}

def activate_batch(batch_id):
    url = f"{BASE_URL}/hospitals/batch/{batch_id}/activate"
    try:
        resp = requests.patch(url)
        return resp
    except requests.RequestException as e:
        return {"error": str(e)}


global_row_hash_store = set()

def row_fingerprint(row: dict) -> str:
    # Check for exact duplicate if user uploads same CSV in retry
    s = (row['name'].strip().lower() + "|" +
         row['address'].strip().lower() + "|" +
         (row.get('phone', '') or '').strip())
    return hashlib.sha256(s.encode()).hexdigest()

def create_hospital_with_backoff(hospital_data, max_retries=3):
    """Create hospital with exponential backoff retry logic."""
    for attempt in range(max_retries + 1):
        resp = create_hospital(hospital_data)
        
        # Network error - retry
        if isinstance(resp, dict) and "error" in resp:
            if attempt < max_retries:
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
                continue
            return resp
        
        # Success or client error (4xx) - don't retry
        if resp.status_code < 500:
            return resp
            
        # Server error (5xx) - retry
        if attempt < max_retries:
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
            continue
            
        return resp
    
    return resp

def activate_batch_with_backoff(batch_id, max_retries=3):
    """Activate batch with exponential backoff retry logic."""
    for attempt in range(max_retries + 1):
        resp = activate_batch(batch_id)
        
        if isinstance(resp, dict) and "error" in resp:
            if attempt < max_retries:
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
                continue
            return resp
        
        if resp.status_code < 500:
            return resp
            
        if attempt < max_retries:
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
            continue
            
        return resp
    
    return resp
