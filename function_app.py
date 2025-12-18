import azure.functions as func  # type: ignore
import os
import io
import json
import base64
import logging
import math
import uuid
import requests  # type: ignore
from PIL import Image, ImageEnhance, ImageFilter, ImageOps  # type: ignore

# Optional CompreFace SDK for on-prem face verification
try:
    from compreface import CompreFace  # type: ignore
    from compreface.service import VerificationService  # type: ignore
    COMPRE_FACE_AVAILABLE = True
except Exception as e:  # pragma: no cover - optional dependency
    COMPRE_FACE_AVAILABLE = False
    logging.warning(f"CompreFace SDK not available or failed to import: {e}")

# ------------------ APP INIT ------------------
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ------------------ ENV VARS ------------------
FACE_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")  # https://<resource>.cognitiveservices.azure.com
FACE_KEY = os.getenv("AZURE_FACE_KEY")

HEADERS = {
    "Ocp-Apim-Subscription-Key": FACE_KEY,
    "Content-Type": "application/octet-stream"
}

# CompreFace configuration (see https://github.com/exadel-inc/CompreFace)
COMPRE_FACE_DOMAIN = os.getenv("COMPRE_FACE_DOMAIN", "http://localhost")
COMPRE_FACE_PORT = os.getenv("COMPRE_FACE_PORT", "8000")
# API key of a Face Verification service created in CompreFace UI
COMPRE_FACE_API_KEY = os.getenv("COMPRE_FACE_API_KEY")

# ------------------ IMAGE PREPROCESS ------------------
def preprocess_image(image: Image.Image) -> Image.Image:
    # Fix EXIF orientation
    image = ImageOps.exif_transpose(image)

    # Ensure RGB
    if image.mode in ("RGBA", "LA"):
        image = image.convert("RGB")

    # Slight contrast boost
    image = ImageEnhance.Contrast(image).enhance(1.15)

    # Mild sharpening
    image = image.filter(
        ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3)
    )

    return image

    
# ------------------ AZURE FACE HELPERS ------------------
def detect_face_id(image_bytes: bytes) -> str | None:
    """
    Detect the first face in the given image bytes using Azure Face API and
    return its faceId. Returns None if no face is found or on error.
    """
    if not FACE_ENDPOINT or not FACE_KEY:
        logging.error("AZURE_FACE_ENDPOINT or AZURE_FACE_KEY is not configured.")
        return None

    url = (
        f"{FACE_ENDPOINT}/face/v1.0/detect"
        "?returnFaceId=true"
        "&detectionModel=detection_03"
        "&recognitionModel=recognition_04"
        "&returnRecognitionModel=false"
    )
    try:
        resp = requests.post(url, headers=HEADERS, data=image_bytes)
        if resp.status_code != 200:
            logging.error("Face detect failed: %s %s", resp.status_code, resp.text)
            return None
        faces = resp.json()
        if not faces:
            return None
        return faces[0].get("faceId")
    except Exception:
        logging.exception("Error calling Face Detect API")
        return None


def verify_face_ids(face_id1: str, face_id2: str) -> dict | None:
    """
    Call Azure Face Verify API for one-to-one face verification.
    Returns the JSON result with keys like 'isIdentical' and 'confidence'.
    """
    if not FACE_ENDPOINT or not FACE_KEY:
        logging.error("AZURE_FACE_ENDPOINT or AZURE_FACE_KEY is not configured.")
        return None

    url = f"{FACE_ENDPOINT}/face/v1.0/verify"
    payload = {"faceId1": face_id1, "faceId2": face_id2}
    headers = {
        "Ocp-Apim-Subscription-Key": FACE_KEY,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            logging.error("Face verify failed: %s %s", resp.status_code, resp.text)
            return None
        return resp.json()
    except Exception:
        logging.exception("Error calling Face Verify API")
        return None


# ------------------ COMPRE-FACE HELPERS ------------------
_COMPRE_VERIFICATION_SERVICE: "VerificationService | None" = None


def get_compreface_verification() -> "VerificationService | None":
    """
    Lazily initialize and return the CompreFace VerificationService.
    """
    global _COMPRE_VERIFICATION_SERVICE

    if not COMPRE_FACE_AVAILABLE:
        logging.error("CompreFace SDK is not available. Install 'compreface-sdk'.")
        return None

    if not COMPRE_FACE_API_KEY:
        logging.error("COMPRE_FACE_API_KEY is not configured in environment.")
        return None

    if _COMPRE_VERIFICATION_SERVICE is None:
        try:
            cf = CompreFace(COMPRE_FACE_DOMAIN, COMPRE_FACE_PORT)
            _COMPRE_VERIFICATION_SERVICE = cf.init_face_verification(COMPRE_FACE_API_KEY)
        except Exception:
            logging.exception("Failed to initialize CompreFace VerificationService")
            return None

    return _COMPRE_VERIFICATION_SERVICE

# ------------------ HEALTH CHECK ------------------
@app.route(route="ping")
def ping(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        "Face extraction service running",
        status_code=200
    )

# ------------------ FACE EXTRACTION ------------------
@app.route(route="extract_kyc", methods=["POST"])
async def extract_kyc(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # ---------- Read file ----------
        file = req.files.get("file")
        if not file:
            return func.HttpResponse(
                "Upload image via form-data key 'file'",
                status_code=400
            )

        original_filename = file.filename or "image"
        base_name, _ = os.path.splitext(original_filename)
        img_bytes = file.stream.read()

        # ---------- Face detection ----------
        detect_url = f"{FACE_ENDPOINT}/face/v1.0/detect?returnFaceId=false"
        resp = requests.post(detect_url, headers=HEADERS, data=img_bytes)

        if resp.status_code != 200:
            logging.error(f"Face detect failed: {resp.text}")
            return func.HttpResponse("Face detection failed", status_code=500)

        faces = resp.json()
        if not faces:
            return func.HttpResponse("No face detected", status_code=404)

        # ---------- Load & preprocess ----------
        image = Image.open(io.BytesIO(img_bytes))
        image = preprocess_image(image)

        # ---------- Output directory ----------
        output_dir = os.path.join(os.getcwd(), "output_faces")
        os.makedirs(output_dir, exist_ok=True)

        # ---------- Save enhanced full image ----------
        enhanced_path = os.path.join(
            output_dir, f"{base_name}_enhanced.jpg"
        )
        image.save(enhanced_path, format="JPEG", quality=95)
        print(" Enhanced image saved:", enhanced_path)

        results = []

        # ---------- Crop & save faces ----------
        for idx, face in enumerate(faces, start=1):
            r = face["faceRectangle"]
            left, top = r["left"], r["top"]
            right = left + r["width"]
            bottom = top + r["height"]

            crop = image.crop((left, top, right, bottom))

            if crop.mode in ("RGBA", "LA"):
                crop = crop.convert("RGB")

            buffer = io.BytesIO()
            crop.save(buffer, format="JPEG", quality=95)

            face_path = os.path.join(
                output_dir, f"{base_name}_face_{idx}.jpg"
            )
            with open(face_path, "wb") as f:
                f.write(buffer.getvalue())

            print("Face saved:", face_path)

            results.append({
                "filename": f"{base_name}_face_{idx}.jpg",
                "saved_path": face_path,
                "image_base64": base64.b64encode(
                    buffer.getvalue()
                ).decode("utf-8")
            })

        # ---------- Response ----------
        return func.HttpResponse(
            json.dumps({
                "original_file": original_filename,
                "enhanced_image": enhanced_path,
                "faces": results
            }),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Unhandled error")
        return func.HttpResponse(
            f"Internal error: {str(e)}",
            status_code=500
        )

# ------------------ FACE COMPARISON ------------------
@app.route(route="compare_faces", methods=["POST"])
async def compare_faces(req: func.HttpRequest) -> func.HttpResponse:
    """
    Compare a reference image with cropped faces from extract_kyc.
    Expects:
    - reference_image: Reference image file (form-data)
    - cropped_faces: List of base64-encoded cropped face images OR face_paths from extract_kyc
    - tolerance: Optional, default 0.5 (lower = stricter)
    - threshold: Optional, default 0.8 (confidence threshold for match)
    """
    try:
        # ---------- Get reference image ----------
        reference_file = req.files.get("reference_image")
        if not reference_file:
            return func.HttpResponse(
                "Missing 'reference_image' in form-data",
                status_code=400
            )
        
        reference_bytes = reference_file.stream.read()
        reference_image = Image.open(io.BytesIO(reference_bytes))
        
        # Convert to RGB if needed
        if reference_image.mode != "RGB":
            reference_image = reference_image.convert("RGB")

        # Get reference faceId via Azure Face Detect
        ref_face_id = detect_face_id(reference_bytes)
        if not ref_face_id:
            return func.HttpResponse(
                "No face found in reference image",
                status_code=400
            )
        
        # ---------- Get parameters ----------
        tolerance = float(req.form.get("tolerance", 0.5))
        threshold = float(req.form.get("threshold", 0.8))
        
        # ---------- Get cropped faces ----------
        # Option 1: Get face_paths from previous extract_kyc call
        face_paths_json = req.form.get("face_paths")
        cropped_faces_data = []
        
        if face_paths_json:
            try:
                face_paths = json.loads(face_paths_json)
                for face_path in face_paths:
                    if os.path.exists(face_path):
                        cropped_faces_data.append({
                            "type": "path",
                            "value": face_path
                        })
            except json.JSONDecodeError:
                pass
        
        # Option 2: Get base64-encoded images
        base64_faces = req.form.getlist("cropped_faces")
        for base64_face in base64_faces:
            if base64_face:
                cropped_faces_data.append({
                    "type": "base64",
                    "value": base64_face
                })
        
        # Option 3: Get uploaded face files
        uploaded_faces = req.files.getlist("cropped_face_files")
        for uploaded_face in uploaded_faces:
            if uploaded_face:
                face_bytes = uploaded_face.stream.read()
                cropped_faces_data.append({
                    "type": "bytes",
                    "value": face_bytes
                })
        
        if not cropped_faces_data:
            return func.HttpResponse(
                "No cropped faces provided. Use 'face_paths', 'cropped_faces' (base64), or 'cropped_face_files'",
                status_code=400
            )
        
        # ---------- Compare faces ----------
        comparison_results = []

        for idx, face_data in enumerate(cropped_faces_data, start=1):
            try:
                # Load face image based on type and get raw bytes
                if face_data["type"] == "path":
                    with open(face_data["value"], "rb") as f:
                        face_bytes = f.read()
                elif face_data["type"] == "base64":
                    face_bytes = base64.b64decode(face_data["value"])
                else:  # bytes
                    face_bytes = face_data["value"]

                # Detect faceId in target image
                face_id = detect_face_id(face_bytes)
                if not face_id:
                    comparison_results.append({
                        "face_index": idx,
                        "face_found": False,
                        "match": False,
                        "confidence": 0.0,
                        "error": "No face detected in target image"
                    })
                    continue

                # Verify reference vs target using Azure Face Verify
                verify_result = verify_face_ids(ref_face_id, face_id)
                if not verify_result:
                    comparison_results.append({
                        "face_index": idx,
                        "face_found": True,
                        "match": False,
                        "confidence": 0.0,
                        "error": "Azure Face verify call failed"
                    })
                    continue

                is_identical = bool(verify_result.get("isIdentical"))
                confidence = float(verify_result.get("confidence") or 0.0)
                match = bool(is_identical and confidence >= threshold)

                comparison_results.append({
                    "face_index": idx,
                    "face_found": True,
                    "match": match,
                    "is_identical": is_identical,
                    "confidence": round(confidence, 4),
                })

            except Exception as e:
                comparison_results.append({
                    "face_index": idx,
                    "face_found": False,
                    "match": False,
                    "confidence": 0.0,
                    "error": str(e)
                })

        # ---------- Calculate overall match ----------
        valid_comparisons = [r for r in comparison_results if r.get("face_found", False)]
        if valid_comparisons:
            avg_confidence = float(sum(r["confidence"] for r in valid_comparisons) / len(valid_comparisons))
            any_match = bool(any(r["match"] for r in valid_comparisons))
        else:
            avg_confidence = 0.0
            any_match = False

        # ---------- Response ----------
        return func.HttpResponse(
            json.dumps({
                "reference_image_processed": True,
                "tolerance": tolerance,
                "threshold": threshold,
                "overall_match": any_match,
                "average_confidence": round(avg_confidence, 4),
                "comparisons": comparison_results,
                "summary": {
                    "total_faces": len(cropped_faces_data),
                    "faces_found": len(valid_comparisons),
                    "matches": sum(1 for r in comparison_results if r.get("match", False))
                }
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logging.exception("Unhandled error in compare_faces")
        return func.HttpResponse(
            f"Internal error: {str(e)}",
            status_code=500
        )


# ------------------ COMPRE-FACE VERIFICATION API ------------------
@app.route(route="compare_faces_compreface", methods=["POST"])
async def compare_faces_compreface(req: func.HttpRequest) -> func.HttpResponse:
    """
    Compare a reference image with one or more target faces using CompreFace
    Face Verification service.

    Expects (multipart/form-data):
    - reference_image: Reference image file (form-data)
    - cropped_face_files: One or more target face files (same as /compare_faces)
      OR
    - face_paths: JSON array of file paths on disk
    - cropped_faces: base64-encoded images

    Optional:
    - threshold: float (0-1), default 0.8, applied to CompreFace similarity score.
    """
    try:
        verification = get_compreface_verification()
        if verification is None:
            return func.HttpResponse(
                "CompreFace verification is not configured or SDK is missing.",
                status_code=500,
            )

        # ---------- Get reference image ----------
        reference_file = req.files.get("reference_image")
        if not reference_file:
            return func.HttpResponse(
                "Missing 'reference_image' in form-data",
                status_code=400,
            )

        reference_bytes = reference_file.stream.read()

        # Save reference to a temporary file (CompreFace SDK API uses file paths)
        temp_dir = os.path.join(os.getcwd(), "compreface_temp")
        os.makedirs(temp_dir, exist_ok=True)
        ref_temp_path = os.path.join(temp_dir, f"ref_{uuid.uuid4().hex}.jpg")
        with open(ref_temp_path, "wb") as f:
            f.write(reference_bytes)

        # ---------- Get parameters ----------
        threshold = float(req.form.get("threshold", 0.8))

        # ---------- Get target faces ----------
        cropped_faces_data = []

        # Option 1: paths on disk
        face_paths_json = req.form.get("face_paths")
        if face_paths_json:
            try:
                face_paths = json.loads(face_paths_json)
                for face_path in face_paths:
                    if os.path.exists(face_path):
                        cropped_faces_data.append(
                            {"type": "path", "value": face_path}
                        )
            except json.JSONDecodeError:
                pass

        # Option 2: base64 images
        base64_faces = req.form.getlist("cropped_faces")
        for base64_face in base64_faces:
            if base64_face:
                cropped_faces_data.append(
                    {"type": "base64", "value": base64_face}
                )

        # Option 3: uploaded files
        uploaded_faces = req.files.getlist("cropped_face_files")
        for uploaded_face in uploaded_faces:
            if uploaded_face:
                face_bytes = uploaded_face.stream.read()
                cropped_faces_data.append(
                    {"type": "bytes", "value": face_bytes}
                )

        if not cropped_faces_data:
            return func.HttpResponse(
                "No target faces provided. Use 'face_paths', 'cropped_faces' (base64), or 'cropped_face_files'",
                status_code=400,
            )

        # ---------- Compare via CompreFace ----------
        comparison_results = []
        temp_files_to_cleanup = [ref_temp_path]

        for idx, face_data in enumerate(cropped_faces_data, start=1):
            try:
                # Resolve target image path for CompreFace
                if face_data["type"] == "path":
                    target_path = face_data["value"]
                else:
                    # Need to write bytes/base64 to temp file
                    if face_data["type"] == "base64":
                        target_bytes = base64.b64decode(face_data["value"])
                    else:
                        target_bytes = face_data["value"]

                    target_path = os.path.join(
                        temp_dir, f"target_{idx}_{uuid.uuid4().hex}.jpg"
                    )
                    with open(target_path, "wb") as f:
                        f.write(target_bytes)
                    temp_files_to_cleanup.append(target_path)

                # Call CompreFace verification
                verify_resp = verification.verify(
                    source_image_path=ref_temp_path,
                    target_image_path=target_path,
                )

                # Heuristic extraction of match/confidence from CompreFace response
                # Different versions/plugins may structure result slightly differently.
                result = verify_resp.get("result") or verify_resp
                is_match = bool(
                    result.get("match")
                    or result.get("verified")
                    or result.get("is_match")
                )
                similarity = result.get("similarity")
                if similarity is None:
                    similarity = result.get("confidence")
                confidence = float(similarity or 0.0)
                meets_threshold = bool(confidence >= threshold)

                # If SDK only returns similarity, treat match as confidence >= threshold
                if not is_match:
                    is_match = meets_threshold

                comparison_results.append(
                    {
                        "face_index": idx,
                        "face_found": True,
                        "match": is_match,
                        "confidence": round(confidence, 4),
                        "meets_threshold": meets_threshold,
                        "raw_result": verify_resp,
                    }
                )

            except Exception as e:
                logging.exception("CompreFace verification failed for face %s", idx)
                comparison_results.append(
                    {
                        "face_index": idx,
                        "face_found": False,
                        "match": False,
                        "confidence": 0.0,
                        "error": str(e),
                    }
                )

        # Cleanup temp files
        try:
            for p in temp_files_to_cleanup:
                if p and os.path.exists(p):
                    os.remove(p)
        except Exception:
            logging.warning("Failed to clean up some CompreFace temp files")

        # ---------- Aggregate ----------
        valid = [r for r in comparison_results if r.get("face_found")]
        if valid:
            avg_conf = float(
                sum(r["confidence"] for r in valid) / len(valid)
            )
            any_match = bool(any(r["match"] for r in valid))
        else:
            avg_conf = 0.0
            any_match = False

        return func.HttpResponse(
            json.dumps(
                {
                    "reference_image_processed": True,
                    "threshold": threshold,
                    "overall_match": any_match,
                    "average_confidence": round(avg_conf, 4),
                    "comparisons": comparison_results,
                    "summary": {
                        "total_faces": len(cropped_faces_data),
                        "faces_found": len(valid),
                        "matches": sum(
                            1 for r in comparison_results if r.get("match")
                        ),
                    },
                }
            ),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.exception("Unhandled error in compare_faces_compreface")
        return func.HttpResponse(
            f"Internal error: {str(e)}",
            status_code=500,
        )
