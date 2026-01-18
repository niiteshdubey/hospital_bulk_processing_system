from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Path, Query
import csv
from .utils import generate_batch_id, set_progress, get_progress
from .services import process_bulk_hospitals, parse_and_validate_csv
from .models import BulkUploadAsyncResponse, BulkUploadSyncResponse, ProgressResponse, CSVValidationResponse
from typing import Union
from logging import getLogger

logger = getLogger("hospital-bulk-processor")

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hospital Bulk Processing API is running"}

@router.post("/hospitals/bulk", response_model=Union[BulkUploadAsyncResponse, BulkUploadSyncResponse])
async def upload_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    wait: bool = Query(True, description="Wait for completion (blocking)")
):
    if not file.filename.endswith(".csv"):
        logger.error(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="File must be a CSV.")

    contents = await file.read()
    clean_rows, errors = parse_and_validate_csv(contents.decode("utf-8"))
    if errors:
        logger.error(f"CSV validation failed: {errors}")
        raise HTTPException(status_code=400, detail=errors)

    batch_id = generate_batch_id()
    set_progress(batch_id, {
        "progress": 0,
        "total": len(clean_rows),
        "status": "processing"
    })

    if wait: # Sync
        process_bulk_hospitals(contents.decode("utf-8"), batch_id)
        result = get_progress(batch_id).get("result")
        if result is None:
            raise HTTPException(status_code=500, detail="Batch processing failed unexpectedly.")
        return result
    else: # Async
        background_tasks.add_task(process_bulk_hospitals, contents.decode("utf-8"), batch_id)
        return {
            "batch_id": batch_id,
            "message": f"Bulk upload accepted. Poll /progress/{batch_id} for status.",
        }

@router.get("/progress/{batch_id}", response_model=ProgressResponse)
def check_progress(batch_id: str = Path(...)):
    progress = get_progress(batch_id)
    return progress

@router.post("/hospitals/validate-csv", response_model=CSVValidationResponse)
async def validate_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        logger.error(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="File must be a CSV.")

    contents = await file.read()
    rows_present, errors = parse_and_validate_csv(contents.decode("utf-8"))
    if errors:
        return {
            "valid": False,
            "errors": errors,
            "row_count": len(rows_present),
            "errored_rows": rows_present,
            "columns": list(rows_present[0].keys()) if rows_present else [],
            "sample_row": rows_present[0] if rows_present else None
        }
    return {
        "valid": True,
        "row_count": len(rows_present),
        "columns": list(rows_present[0].keys()) if rows_present else [],
        "sample_row": rows_present[0] if rows_present else None
    }
