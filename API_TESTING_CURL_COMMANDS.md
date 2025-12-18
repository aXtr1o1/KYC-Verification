# API Testing - cURL Commands

## Prerequisites
- Azure Function endpoint URL (replace `YOUR_FUNCTION_URL` with your actual function URL)
- Test images: reference image and image with faces to extract

---

## 1. Extract Faces from Image (`/extract_kyc`)

This endpoint extracts faces from an image and returns cropped face images.

### Basic Usage
```bash
curl -X POST "YOUR_FUNCTION_URL/api/extract_kyc" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/image.jpg"
```

### Example with Local File
```bash
curl -X POST "http://localhost:7071/api/extract_kyc" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./test_image.jpg"
```

### Example with Azure Function URL
```bash
curl -X POST "https://your-function-app.azurewebsites.net/api/extract_kyc" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./test_image.jpg"
```

### Expected Response
```json
{
  "original_file": "test_image.jpg",
  "enhanced_image": "/path/to/enhanced.jpg",
  "faces": [
    {
      "filename": "test_image_face_1.jpg",
      "saved_path": "/path/to/test_image_face_1.jpg",
      "image_base64": "base64_encoded_image_string..."
    }
  ]
}
```

---

## 2. Compare Faces (`/compare_faces`)

This endpoint compares a reference image with cropped faces.

### Option 1: Using Face Paths (from extract_kyc response)

```bash
curl -X POST "YOUR_FUNCTION_URL/api/compare_faces" \
  -H "Content-Type: multipart/form-data" \
  -F "reference_image=@/path/to/reference_face.jpg" \
  -F 'face_paths=["/path/to/face1.jpg","/path/to/face2.jpg"]' \
  -F "tolerance=0.5" \
  -F "threshold=0.8"
```

### Option 2: Using Base64-encoded Images

First, get base64 from extract_kyc response, then:

```bash
curl -X POST "YOUR_FUNCTION_URL/api/compare_faces" \
  -H "Content-Type: multipart/form-data" \
  -F "reference_image=@/path/to/reference_face.jpg" \
  -F "cropped_faces=base64_string_1" \
  -F "cropped_faces=base64_string_2" \
  -F "tolerance=0.5" \
  -F "threshold=0.8"
```

### Option 3: Using Uploaded Face Files (Recommended)

```bash
curl -X POST "YOUR_FUNCTION_URL/api/compare_faces" \
  -H "Content-Type: multipart/form-data" \
  -F "reference_image=@/path/to/reference_face.jpg" \
  -F "cropped_face_files=@/path/to/cropped_face1.jpg" \
  -F "cropped_face_files=@/path/to/cropped_face2.jpg" \
  -F "tolerance=0.5" \
  -F "threshold=0.8"
```

### Complete Workflow Example

#### Step 1: Extract faces from an image
```bash
curl -X POST "http://localhost:7071/api/extract_kyc" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./document_with_face.jpg" \
  -o extract_response.json
```

#### Step 2: Extract base64 from response (using jq or manual)
```bash
# Using jq to extract base64
cat extract_response.json | jq -r '.faces[0].image_base64' > face1_base64.txt
```

#### Step 3: Compare with reference image
```bash
curl -X POST "http://localhost:7071/api/compare_faces" \
  -H "Content-Type: multipart/form-data" \
  -F "reference_image=@./reference_id_card.jpg" \
  -F "cropped_face_files=@./document_with_face_face_1.jpg" \
  -F "tolerance=0.5" \
  -F "threshold=0.8" \
  -o comparison_result.json
```

---

## 3. Complete Test Script

### Using Face Files (Easiest Method)

```bash
#!/bin/bash

# Configuration
FUNCTION_URL="http://localhost:7071/api"
# Or for Azure: FUNCTION_URL="https://your-function-app.azurewebsites.net/api"

# Step 1: Extract faces
echo "Step 1: Extracting faces..."
curl -X POST "${FUNCTION_URL}/extract_kyc" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./test_document.jpg" \
  -o extract_result.json

echo "Extraction result saved to extract_result.json"

# Step 2: Compare faces
echo "Step 2: Comparing faces..."
curl -X POST "${FUNCTION_URL}/compare_faces" \
  -H "Content-Type: multipart/form-data" \
  -F "reference_image=@./reference_face.jpg" \
  -F "cropped_face_files=@./test_document_face_1.jpg" \
  -F "tolerance=0.5" \
  -F "threshold=0.8" \
  -o comparison_result.json

echo "Comparison result saved to comparison_result.json"
cat comparison_result.json | jq '.'
```

---

## 4. PowerShell Commands (Windows)

### Extract Faces
```powershell
$uri = "http://localhost:7071/api/extract_kyc"
$filePath = ".\test_image.jpg"

$form = @{
    file = Get-Item -Path $filePath
}

Invoke-RestMethod -Uri $uri -Method Post -Form $form | ConvertTo-Json -Depth 10
```

### Compare Faces
```powershell
$uri = "http://localhost:7071/api/compare_faces"
$referenceImage = ".\reference_face.jpg"
$croppedFace = ".\test_image_face_1.jpg"

$form = @{
    reference_image = Get-Item -Path $referenceImage
    cropped_face_files = Get-Item -Path $croppedFace
    tolerance = "0.5"
    threshold = "0.8"
}

Invoke-RestMethod -Uri $uri -Method Post -Form $form | ConvertTo-Json -Depth 10
```

---

## 5. Python Test Script

```python
import requests
import json

# Configuration
FUNCTION_URL = "http://localhost:7071/api"
# Or: FUNCTION_URL = "https://your-function-app.azurewebsites.net/api"

# Step 1: Extract faces
print("Step 1: Extracting faces...")
with open("test_document.jpg", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{FUNCTION_URL}/extract_kyc", files=files)
    extract_result = response.json()
    print(json.dumps(extract_result, indent=2))

# Step 2: Compare faces
print("\nStep 2: Comparing faces...")
with open("reference_face.jpg", "rb") as ref_file, \
     open("test_document_face_1.jpg", "rb") as face_file:
    files = {
        "reference_image": ref_file,
        "cropped_face_files": face_file
    }
    data = {
        "tolerance": "0.5",
        "threshold": "0.8"
    }
    response = requests.post(f"{FUNCTION_URL}/compare_faces", files=files, data=data)
    comparison_result = response.json()
    print(json.dumps(comparison_result, indent=2))
```

---

## 6. Expected Response Formats

### Extract KYC Response
```json
{
  "original_file": "test_image.jpg",
  "enhanced_image": "/path/to/enhanced.jpg",
  "faces": [
    {
      "filename": "test_image_face_1.jpg",
      "saved_path": "/path/to/test_image_face_1.jpg",
      "image_base64": "iVBORw0KGgoAAAANS..."
    }
  ]
}
```

### Compare Faces Response
```json
{
  "reference_image_processed": true,
  "tolerance": 0.5,
  "threshold": 0.8,
  "overall_match": true,
  "average_confidence": 0.9234,
  "comparisons": [
    {
      "face_index": 1,
      "face_found": true,
      "match": true,
      "confidence": 0.9234,
      "face_distance": 0.3456,
      "meets_threshold": true
    }
  ],
  "summary": {
    "total_faces": 1,
    "faces_found": 1,
    "matches": 1
  }
}
```

---

## 7. Error Responses

### No Face Detected
```json
{
  "error": "No face detected in reference image"
}
```

### Missing Parameters
```json
{
  "error": "Missing 'reference_image' in form-data"
}
```

---

## Notes

- **Tolerance**: Lower values (0.3-0.4) = stricter matching, Higher values (0.6-0.7) = more lenient
- **Threshold**: Minimum confidence score (0-1) to consider a match. Default 0.8 = 80% confidence
- **Face Paths**: Use absolute paths or paths relative to the function's working directory
- **Base64**: Must be valid base64-encoded image strings
- **File Uploads**: Supported formats: JPG, JPEG, PNG

