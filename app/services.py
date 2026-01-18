import csv
from .utils import set_progress, create_hospital, activate_batch, get_progress
from logging import getLogger
from .utils import row_fingerprint, global_row_hash_store, create_hospital_with_backoff, activate_batch_with_backoff

logger = getLogger("hospital-bulk-processor")

def parse_and_validate_csv(contents: str, required=("name", "address"), optional=("phone",), max_rows=20):
    """
    Returns (rows, errors) where rows is a list of dicts or None and errors is a list of strings.
    """
    logger.info("Parsing and validating CSV contents...")
    decoded = contents.splitlines()
    reader = csv.DictReader(decoded)
    fieldnames = set(reader.fieldnames or [])
    required = set(required)
    optional = set(optional)

    errors = []

    # Header check
    missing_required = required - fieldnames
    if missing_required:
        errors.append(f"Missing required columns: {missing_required}")

    extra_cols = fieldnames - (required | optional)
    if extra_cols:
        errors.append(f"Unexpected columns found: {extra_cols}")

    rows = list(reader)
    if len(rows) == 0:
        errors.append("CSV has no data rows.")
    if len(rows) > max_rows:
        errors.append(f"CSV cannot have more than {max_rows} rows.")

    # Check each row for empties in required fields
    for idx, row in enumerate(rows, start=1):
        for f in required:
            if not (row.get(f) and row[f].strip()):
                errors.append(f"Row {idx} is missing required value for: {f}")

    if errors:
        errored_rows = [row for row in rows if any(not (row.get(f) and row[f].strip()) for f in required)]
        logger.warning(f"CSV validation failed with {len(errors)} errors.")
        return errored_rows, errors

    # Clean up and return consistent rows
    clean_rows = [
        {
            "name": row.get("name", "").strip(),
            "address": row.get("address", "").strip(),
            "phone": row.get("phone", "").strip() if "phone" in row else None
        }
        for row in rows
    ]
    logger.info(f"CSV validation succeeded with {len(clean_rows)} rows.")
    return clean_rows, []


def process_bulk_hospitals(contents: str, batch_id: str):
    logger.info(f"Processing bulk upload for batch {batch_id}")
    decoded = contents.splitlines()
    reader = csv.DictReader(decoded)
    hospitals = []
    required = {"name", "address"}

    for row in reader:
        hospitals.append({
            "name": row.get("name", "").strip(),
            "address": row.get("address", "").strip(),
            "phone": row.get("phone", "").strip() if "phone" in row else None
        })

    processed = 0
    failed = 0
    hospital_statuses = []
    total = len(hospitals)

    for idx, hospital in enumerate(hospitals, start=1):
        fingerprint = row_fingerprint(hospital)
        if fingerprint in global_row_hash_store:
            logger.warning(f"Duplicate hospital row found (name={hospital['name']}, address={hospital['address']}). Skipping...")
            continue
        
        logger.info(f"Processing hospital {idx} of {total}: {hospital['name']}")
        set_progress(batch_id, {
            "progress": idx - 1,
            "total": total,
            "status": "processing"
        })

        hospital_payload = {**hospital, "creation_batch_id": batch_id}
        resp = create_hospital_with_backoff(hospital_payload)
        if isinstance(resp, dict) and "error" in resp:
            hospital_statuses.append({
                "row": idx,
                "hospital_id": None,
                "name": hospital["name"],
                "status": f"network_failed: {resp['error']}"
            })
            failed += 1
            continue

        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Hospital {hospital['name']} created successfully with id {data['id']}")
            hospital_statuses.append({
                "row": idx,
                "hospital_id": data["id"],
                "name": data["name"],
                "status": "created"
            })
            processed += 1
            # add if new
            global_row_hash_store.add(fingerprint)
        else:
            logger.error(f"Failed to create hospital row {idx}: status={resp.status_code}")
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            hospital_statuses.append({
                "row": idx,
                "hospital_id": None,
                "name": hospital["name"],
                "status": f"api_failed: {resp.status_code} {detail}"
            })
            failed += 1

    batch_activated = False
    if failed == 0:
        activate_resp = activate_batch_with_backoff(batch_id)
        if isinstance(activate_resp, dict) and "error" in activate_resp:
            batch_activated = False
            logger.warning(f"Batch {batch_id} activation failed or partial success")
        elif activate_resp.status_code == 200:
            batch_activated = True
            for h in hospital_statuses:
                h["status"] = "created_and_activated"
            logger.info(f"Batch {batch_id} activated")

    final_status = "completed" if failed == 0 else "failed"
    set_progress(batch_id, {
        "progress": total,
        "total": total,
        "status": final_status,
        "result": {
            "batch_id": batch_id,
            "total_hospitals": total,
            "processed_hospitals": processed,
            "failed_hospitals": failed,
            "batch_activated": batch_activated,
            "hospitals": hospital_statuses
        }
    })
    logger.info(f"Batch {batch_id} finished: {processed} succeeded, {failed} failed.")
