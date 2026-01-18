from pydantic import BaseModel
from typing import Optional, List, Dict, Union

class HospitalStatusModel(BaseModel):
    row: int
    hospital_id: Optional[Union[str, int]]
    name: str
    status: str

class BulkUploadAsyncResponse(BaseModel):
    batch_id: str
    message: str

class BulkUploadSyncResponse(BaseModel):
    batch_id: str
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    batch_activated: bool
    hospitals: List[HospitalStatusModel]

class ProgressResponse(BaseModel):
    progress: int
    total: int
    status: str
    result: Optional[BulkUploadSyncResponse] = None

class CSVValidationResponse(BaseModel):
    valid: bool
    errors: Optional[List[str]] = None
    row_count: Optional[int] = None
    errored_rows: Optional[List[Dict]] = None
    columns: Optional[List[str]] = None
    sample_row: Optional[Dict] = None
