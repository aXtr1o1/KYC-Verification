# KYC Verification System

AI-powered automated KYC system that verifies user identity by extracting faces from official identity documents and matching them with live selfies. The solution uses Azure Face API for face recognition to generate match scores and enable instant approvals or manual verification via secure backend APIs.

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Frontend UI](#frontend-ui)
- [Testing](#testing)
- [Deployment](#deployment)
- [Notes](#notes)

---

## Overview

This KYC verification system provides:

- **Face Extraction**: Extract and crop faces from identity documents using Azure Face API
- **Face Comparison**: Compare extracted faces with reference images (selfies) using Azure Face API or CompreFace
- **Web UI**: Modern, responsive web interface for easy face comparison
- **REST API**: Secure Azure Functions endpoints for programmatic access

## Project Structure

```
KYC-Verification/
├── function_app.py           # Main Azure Functions application
├── host.json                 # Azure Functions host configuration
├── local.settings.json       # Local environment variables (not in git)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── API_TESTING_CURL_COMMANDS.md  # Detailed API testing guide
├── frontend/                 # Web UI
│   └── index.html           # Face Comparison Tool (single-page app)
├── output_faces/            # Temporary folder for extracted faces
├── temp_images/             # Temporary folder for image processing

```

## Prerequisites

- **Python 3.9+**
- **Azure Subscription** with Azure Face API enabled
- **Azure Functions Core Tools** (for local development)
- **Azure Face API Key** and **Endpoint**
- **(Optional)** CompreFace for on-premise face verification

## Installation & Setup

### 1. Clone the Repository

```bash
cd KYC-Verification
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Azure Functions Core Tools

**Windows (Chocolatey):**
```powershell
choco install azure-functions-core-tools-4
Refer Azure Documentation
```

**macOS (Homebrew):**
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

**Linux (Ubuntu/Debian):**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

## Configuration

### Create `local.settings.json`

Create a `local.settings.json` file in the project root with your Azure service credentials:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "FORM_ENDPOINT": "https://your-form-recognizer.cognitiveservices.azure.com/",
    "FORM_KEY": "your-form-recognizer-api-key",
    "AZURE_OPENAI_ENDPOINT": "https://your-openai-resource.openai.azure.com/",
    "AZURE_OPENAI_KEY": "your-azure-openai-api-key",
    "AZURE_DEPLOYMENT_NAME": "gpt-4o-mini",
    "AZURE_API_VERSION": "2024-07-18",
    "AZURE_VISION_KEY": "your-azure-vision-api-key",
    "AZURE_END_POINT": "https://your-vision-resource.cognitiveservices.azure.com/",
    "AZURE_FACE_KEY": "your-azure-face-api-key",
    "AZURE_FACE_ENDPOINT": "https://your-face-resource.cognitiveservices.azure.com/",
    "COMPRE_FACE_DOMAIN": "http://localhost",
    "COMPRE_FACE_PORT": "8000",
    "COMPRE_FACE_API_KEY": "your-compreface-api-key"
  }
}
```

### Environment Variables Description

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AzureWebJobsStorage` | Azure Storage connection string for Functions runtime | Yes | `UseDevelopmentStorage=true` (local) |
| `FUNCTIONS_WORKER_RUNTIME` | Runtime language for Azure Functions | Yes | `python` |
| `FORM_ENDPOINT` | Azure Form Recognizer endpoint URL for document processing | Optional | - |
| `FORM_KEY` | Azure Form Recognizer API key | Optional | - |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint URL | Optional | - |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | Optional | - |
| `AZURE_DEPLOYMENT_NAME` | Azure OpenAI model deployment name | Optional | `gpt-4o-mini` |
| `AZURE_API_VERSION` | Azure OpenAI API version | Optional | `2024-07-18` |
| `AZURE_VISION_KEY` | Azure Computer Vision API key | Optional | - |
| `AZURE_END_POINT` | Azure Computer Vision endpoint URL | Optional | - |
| `AZURE_FACE_KEY` | **Azure Face API key for face detection and verification** | **Yes** | - |
| `AZURE_FACE_ENDPOINT` | **Azure Face API endpoint URL** | **Yes** | - |
| `COMPRE_FACE_DOMAIN` | CompreFace server domain for on-premise face verification | Optional | `http://localhost` |
| `COMPRE_FACE_PORT` | CompreFace server port | Optional | `8000` |
| `COMPRE_FACE_API_KEY` | CompreFace API key for verification service | Optional | - |

> **⚠️ Security Warning**: Never commit `local.settings.json` to version control. Add it to `.gitignore`.

### Azure Face API Setup (Required)

The Azure Face API is the core service used for face detection and comparison.

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource** → Search for **Face**
3. Create a **Face API** resource:
   - **Subscription**: Select your subscription
   - **Resource Group**: Create new or use existing
   - **Region**: Choose a region (e.g., East US)
   - **Name**: Enter a unique name (e.g., `kyc-face-api`)
   - **Pricing Tier**: Select F0 (free) for testing or S0 for production
4. After deployment, go to **Keys and Endpoint**
5. Copy **Key 1** and **Endpoint** to your `local.settings.json`:
   ```json
   "AZURE_FACE_KEY": "your-key-from-azure-portal",
   "AZURE_FACE_ENDPOINT": "https://your-resource-name.cognitiveservices.azure.com/"
   ```

### CompreFace Setup (Optional)

CompreFace provides on-premise face verification as an alternative to Azure Face API.

1. Follow [CompreFace installation guide](https://github.com/exadel-inc/CompreFace)
2. Start CompreFace using Docker:
   ```bash
   docker-compose up -d
   ```
3. Open CompreFace UI at `http://localhost:8000`
4. Create a new **Face Verification** service
5. Copy the generated API key to `local.settings.json`:
   ```json
   "COMPRE_FACE_API_KEY": "your-api-key-from-compreface-ui"
   ```

## Running the Application

### Start Azure Functions Locally

```bash
func start
```

The API will be available at `http://localhost:7071/api`

### Open the Frontend UI

Open `frontend/index.html` in your browser, or serve it using a simple HTTP server:

```bash
# Python
cd frontend
python -m http.server 8080

# Node.js
npx serve frontend
```

Then navigate to `http://localhost:8080`

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /api/ping`

**Description:** Check if the service is running

**Example:**
```bash
curl http://localhost:7071/api/ping
```

### 2. Extract Faces from Image

**Endpoint:** `POST /api/extract_kyc`

**Description:** Extract and crop faces from an identity document or image

**Parameters:**
- `file` (file, required): Image file containing faces

**Example:**
```bash
curl -X POST "http://localhost:7071/api/extract_kyc" \
  -F "file=@./id_card.jpg"
```

**Response:**
```json
{
  "original_file": "id_card.jpg",
  "enhanced_image": "/path/to/id_card_enhanced.jpg",
  "faces": [
    {
      "filename": "id_card_face_1.jpg",
      "saved_path": "/path/to/id_card_face_1.jpg",
      "image_base64": "base64_encoded_string..."
    }
  ]
}
```

### 3. Compare Faces (Azure Face API)

**Endpoint:** `POST /api/compare_faces`

**Description:** Compare a reference image (selfie) with extracted faces

**Parameters:**
- `reference_image` (file, required): Reference face image (selfie)
- `cropped_face_files` (file(s), required): One or more cropped face images
- `tolerance` (float, optional): Matching tolerance (default: 0.5)
- `threshold` (float, optional): Confidence threshold (default: 0.8)

**Example:**
```bash
curl -X POST "http://localhost:7071/api/compare_faces" \
  -F "reference_image=@./selfie.jpg" \
  -F "cropped_face_files=@./id_card_face_1.jpg" \
  -F "tolerance=0.5" \
  -F "threshold=0.8"
```

**Response:**
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
      "is_identical": true,
      "confidence": 0.9234
    }
  ],
  "summary": {
    "total_faces": 1,
    "faces_found": 1,
    "matches": 1
  }
}
```

### 4. Compare Faces (CompreFace)

**Endpoint:** `POST /api/compare_faces_compreface`

**Description:** Compare faces using on-premise CompreFace service

**Parameters:** Same as `/api/compare_faces`

## Frontend UI

The `frontend/index.html` provides a modern, user-friendly interface for face comparison.

### Features:

- **Drag & Drop Upload**: Easily upload reference and target face images
- **Real-time Preview**: See uploaded images before comparison
- **Configurable Parameters**: Adjust tolerance and threshold values
- **Visual Results**: Clear display of match results with confidence scores
- **Responsive Design**: Works on desktop and mobile devices

### Usage:

1. Open `frontend/index.html` in a browser
2. Upload a **Reference Image** (selfie)
3. Upload one or more **Cropped Face Images** (from ID documents)
4. Adjust **Tolerance** and **Threshold** if needed
5. Click **Compare Faces**
6. View the detailed comparison results

### API Configuration:

By default, the UI connects to `http://localhost:7071/api`. To change this:

- Press `Ctrl+Shift+A` to show the API configuration panel
- Enter your Azure Functions URL
- The setting is saved in the browser session

## Testing

See [API_TESTING_CURL_COMMANDS.md](./API_TESTING_CURL_COMMANDS.md) for comprehensive API testing examples including:

- cURL commands
- PowerShell scripts
- Python examples
- Complete workflow examples

### Quick Test

```bash
# 1. Extract faces from ID card
curl -X POST "http://localhost:7071/api/extract_kyc" \
  -F "file=@./id_card.jpg" \
  -o extract_result.json

# 2. Compare with selfie
curl -X POST "http://localhost:7071/api/compare_faces" \
  -F "reference_image=@./selfie.jpg" \
  -F "cropped_face_files=@./id_card_face_1.jpg" \
  -F "threshold=0.8" | jq '.'
```

## Deployment

### Deploy to Azure Functions

1. **Create Azure Function App:**

```bash
az functionapp create \
  --resource-group YourResourceGroup \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name your-kyc-function-app \
  --storage-account yourstorageaccount
```

2. **Configure Application Settings:**

```bash
az functionapp config appsettings set \
  --name your-kyc-function-app \
  --resource-group YourResourceGroup \
  --settings \
    AZURE_FACE_ENDPOINT="https://your-face-resource.cognitiveservices.azure.com/" \
    AZURE_FACE_KEY="your-azure-face-api-key" \
    FORM_ENDPOINT="https://your-form-recognizer.cognitiveservices.azure.com/" \
    FORM_KEY="your-form-recognizer-api-key" \
    AZURE_VISION_KEY="your-azure-vision-api-key" \
    AZURE_END_POINT="https://your-vision-resource.cognitiveservices.azure.com/"
```

> **Note**: Replace all placeholder values with your actual Azure resource endpoints and keys from the Azure Portal.

3. **Deploy the Function:**

```bash
func azure functionapp publish your-kyc-function-app
```

4. **Update Frontend API URL:**

Edit `frontend/index.html` and change the default API URL to your deployed function:

```javascript
let apiUrl = 'https://your-kyc-function-app.azurewebsites.net/api';
```

## Notes

### Face Matching Parameters

- **Tolerance**: Lower values (0.3-0.4) = stricter matching, Higher values (0.6-0.7) = more lenient
- **Threshold**: Minimum confidence score (0-1) to consider a match. Default 0.8 = 80% confidence

### Supported Image Formats

- JPEG/JPG
- PNG
- BMP
- GIF (first frame)

### Performance Tips

- Use high-quality, well-lit images for best results
- Ensure faces are clearly visible and not obscured
- Recommended minimum face size: 200x200 pixels

### Security Considerations

- **🔒 Never commit `local.settings.json` to version control** - Add it to `.gitignore`
- **🔑 Rotate API keys regularly** - Use Azure Portal to regenerate keys periodically
- **🔐 Use Azure Key Vault for production** - Store all secrets in Azure Key Vault instead of configuration files
- **🌐 Enable CORS only for trusted domains** - Configure CORS in Azure Functions for specific frontend domains only
- **🔐 Implement authentication** - Use Azure AD, API keys, or OAuth for production APIs
- **📊 Monitor API usage** - Set up Azure Monitor to track usage and detect anomalies
- **⚠️ Remove sensitive data from logs** - Ensure no API keys or personal data are logged
- **🔒 Use HTTPS only** - Always use HTTPS endpoints in production

### Create `.gitignore` (if not exists)

Create a `.gitignore` file in your project root to prevent sensitive files from being committed:

```gitignore
# Local settings
local.settings.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/

# Azure Functions
.venv/
.python_packages/
__blobstorage__/
__queuestorage__/
__azurite_db*__.json
.azurefunctions/

# Temporary files
temp_images/
output_faces/
compreface_temp/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
```

### Troubleshooting

**Error: No face detected**
- Ensure the image contains a clear, visible face
- Check image quality and lighting
- Try a different photo angle

**Error: Azure Face API key invalid**
- Verify the endpoint and key in `local.settings.json`
- Check that the Face API resource is active in Azure Portal

**Frontend cannot connect to API**
- Verify Azure Functions is running (`func start`)
- Check the API URL in frontend (press Ctrl+Shift+A)
- Ensure CORS is configured if hosting frontend separately

---

## License

This project is provided as-is for demonstration purposes.

## Support

For issues and questions, please refer to the [API_TESTING_CURL_COMMANDS.md](./API_TESTING_CURL_COMMANDS.md) file or contact the development team.


