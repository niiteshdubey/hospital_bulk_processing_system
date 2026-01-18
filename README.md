# Hospital Bulk Processing API

A FastAPI service for bulk uploading hospital data to the Hospital Directory API with robust error handling and retry mechanisms.

## Features

- **Bulk CSV Upload**: Process hospital data from CSV files
- **Sync/Async Processing**: Choose between blocking or background processing
- **CSV Validation**: Pre-validate CSV structure and data
- **Progress Tracking**: Monitor upload progress with batch IDs
- **Exponential Backoff**: Automatic retry with exponential backoff for API failures
- **Duplicate Detection**: Skip duplicate hospital entries based on name/address fingerprinting

## API Endpoints

### `POST /hospitals/bulk`
Upload CSV file for bulk hospital creation.
- **Query Params**: `wait=true` (sync) or `wait=false` (async)
- **Response**: Immediate results (sync) or batch ID for tracking (async)

### `GET /progress/{batch_id}`
Check processing progress for async uploads.

### `POST /hospitals/validate-csv`
Validate CSV structure without processing.

## CSV Format

Required columns:
- `name`: Hospital name
- `address`: Hospital address

Optional columns:
- `phone`: Phone number

## Quick Start

```bash
# Using Docker
docker-compose up

# Or locally
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/
```

## Error Handling

- **Network failures**: Automatic retry with exponential backoff
- **Server errors (5xx)**: Retry up to 3 times
- **Client errors (4xx)**: No retry, immediate failure
- **Duplicates**: Skipped based on name/address fingerprint

