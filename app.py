import os
import time
import base64
from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

# ============================================================
# AI TRUTH LENS - FINAL DEMO-SAFE BACKEND
# ============================================================
# Backend for the AI Truth Lens project.
# It never fabricates an authenticity score when Gemini fails.
# ============================================================

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Current stable Flash models listed by Google's Gemini API docs.
# We try the newest first, then fall back through other stable Flash models.
MODEL_CANDIDATES = [
    # This model was confirmed working in the demo. Try it first.
    "gemini-3.1-flash-lite",
    # Compatible multimodal fallbacks, in preferred order.
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
]


def build_client():
    if not GEMINI_API_KEY:
        return None

    # Keep request time bounded and reduce the SDK's own retry delay.
    # The explicit model loop below handles fallback between models.
    try:
        retry_class = getattr(types, "HttpRetryOptions", None)
        if retry_class is not None:
            retry_options = retry_class(
                attempts=1,
                initial_delay=1.0,
                max_delay=2.0,
                exp_base=2.0,
                jitter=0.0,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            )
            http_options = types.HttpOptions(
                timeout=20000,
                retry_options=retry_options,
            )
        else:
            http_options = types.HttpOptions(timeout=20000)

        return genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=http_options,
        )
    except Exception as exc:
        print("Gemini client initialization error:", exc)
        return None


client = build_client()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


def is_transient_error(error_text):
    msg = (error_text or "").upper()
    return any(
        marker in msg
        for marker in (
            "503",
            "UNAVAILABLE",
            "429",
            "RESOURCE_EXHAUSTED",
            "408",
            "TIMEOUT",
            "TIMED OUT",
            "500",
            "502",
            "504",
        )
    )


def gemini_analysis(image_path):
    """Use the current Gemini image-input path with bounded retries.

    The Interactions API is tried first because Google currently documents it
    as the newer API for multimodal model calls. A generateContent fallback
    uses the documented Part.from_bytes() image input format.
    Returns (analysis_text, error_text, model_used).
    """
    if client is None:
        return None, "Gemini API key is missing or the Gemini client could not start.", None

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        with Image.open(image_path) as img:
            mime_type = Image.MIME.get(img.format, "image/png")

        prompt = """
You are an AI image-authenticity assistant for a school demonstration called AI Truth Lens.

Examine the supplied image carefully. Give an AI-assisted estimate of whether the image appears
Likely Real, Suspicious, or AI Generated. This is NOT forensic proof; never claim certainty.

Return ONLY this exact format:

🛡 Authenticity Score : <integer 0-100>/100

🚦 Verdict :
Likely Real ✅
OR
Suspicious 🟡
OR
AI Generated 🔴

🔍 Key Observations :
• <observation 1>
• <observation 2>
• <observation 3>

💡 Confidence :
High / Medium / Low

Keep the observations short, professional, visual and evidence-based.
"""

        last_error = "Unknown Gemini error."

        for model_name in MODEL_CANDIDATES:
            print(f"AI Truth Lens: trying {model_name}")

            # --------------------------------------------------------
            # Primary path: current Interactions API, with explicit
            # base64 image input as documented by Google.
            # --------------------------------------------------------
            try:
                if hasattr(client, "interactions"):
                    interaction = client.interactions.create(
                        model=model_name,
                        input=[
                            {
                                "type": "image",
                                "data": base64.b64encode(image_bytes).decode("utf-8"),
                                "mime_type": mime_type,
                            },
                            {"type": "text", "text": prompt},
                        ],
                    )
                    result = (getattr(interaction, "output_text", None) or "").strip()
                    if result:
                        print(f"AI Truth Lens: success with Interactions API / {model_name}")
                        return result, None, model_name
            except Exception as exc:
                last_error = str(exc)
                print(f"Interactions {model_name} error: {exc}")

            # --------------------------------------------------------
            # Compatibility path: generateContent with the exact
            # documented Part.from_bytes() image input.
            # --------------------------------------------------------
            try:
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=[image_part, prompt],
                    config=types.GenerateContentConfig(
                        max_output_tokens=500,
                    ),
                )
                result = (response.text or "").strip()
                if result:
                    print(f"AI Truth Lens: success with generateContent / {model_name}")
                    return result, None, model_name
            except Exception as exc:
                last_error = str(exc)
                print(f"generateContent {model_name} error: {exc}")

            # Only retry transient capacity/rate failures. Do not loop forever.
            if is_transient_error(last_error):
                time.sleep(2)
                try:
                    interaction = client.interactions.create(
                        model=model_name,
                        input=[
                            {
                                "type": "image",
                                "data": base64.b64encode(image_bytes).decode("utf-8"),
                                "mime_type": mime_type,
                            },
                            {"type": "text", "text": prompt},
                        ],
                    )
                    result = (getattr(interaction, "output_text", None) or "").strip()
                    if result:
                        print(f"AI Truth Lens: success after retry / {model_name}")
                        return result, None, model_name
                except Exception as exc:
                    last_error = str(exc)
                    print(f"Retry {model_name} error: {exc}")

        return None, last_error, None

    except Exception as exc:
        return None, str(exc), None

def offline_analysis(image_path, error_text):
    """Honest local fallback. Never pretends that Gemini analyzed the image."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            image_format = img.format or "Unknown"
            file_size_kb = round(os.path.getsize(image_path) / 1024, 2)
    except Exception:
        width = height = 0
        image_format = "Unknown"
        file_size_kb = 0

    return f"""🛡 Authenticity Score : Not Available

📏 Image Size : {width} × {height}

🚦 Verdict :
AI Analysis Temporarily Unavailable ⚠️

🔍 Key Observations :
• The image was uploaded and processed locally.
• Gemini could not complete the visual analysis during this attempt.
• No authenticity score is fabricated when the AI service is unavailable.

🧪 Local Technical Information :
• Resolution : {width} × {height}
• Format : {image_format}
• File Size : {file_size_kb} KB

💡 Confidence :
Not Available

ℹ️ Demo-safe note :
The app tried multiple current Gemini Flash models and bounded retries.
The technical reason was recorded in the Flask terminal, not hidden behind a fake score.
"""


@app.route("/", methods=["GET", "POST"])
def index():
    ai_result = None
    image_info = None
    image_name = None
    image_path = None
    error_message = None

    if request.method == "POST":
        image = request.files.get("image")

        if not image or not image.filename:
            error_message = "Please select an image first."
            return render_template(
                "index.html",
                ai_result=ai_result,
                image_info=image_info,
                image_name=image_name,
                image_path=image_path,
                error_message=error_message,
            )

        if not allowed_file(image.filename):
            error_message = "Invalid file format. Please upload JPG, JPEG, PNG or WEBP."
            return render_template(
                "index.html",
                ai_result=ai_result,
                image_info=image_info,
                image_name=image_name,
                image_path=image_path,
                error_message=error_message,
            )

        original_filename = image.filename
        safe_filename = secure_filename(original_filename) or "uploaded_image"
        filename = f"{int(time.time() * 1000)}_{safe_filename}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image.save(save_path)

        image_name = original_filename
        image_path = filename

        try:
            with Image.open(save_path) as uploaded_image:
                uploaded_image.verify()

            with Image.open(save_path) as uploaded_image:
                width, height = uploaded_image.size
                image_format = uploaded_image.format or "Unknown"

            file_size_kb = round(os.path.getsize(save_path) / 1024, 2)
            image_info = {
                "width": width,
                "height": height,
                "format": image_format,
                "size": file_size_kb,
            }
        except Exception:
            error_message = "The uploaded file could not be read as a valid image."
            return render_template(
                "index.html",
                ai_result=ai_result,
                image_info=image_info,
                image_name=image_name,
                image_path=image_path,
                error_message=error_message,
            )

        result, ai_error, model_used = gemini_analysis(save_path)

        if result:
            ai_result = result + f"\n\n🤖 AI Model Used : {model_used}"
            print(f"AI Truth Lens: Gemini analysis completed using {model_used}.")
        else:
            ai_result = offline_analysis(save_path, ai_error)
            print("AI Truth Lens: REAL AI analysis did not complete.")
            print("Reason:", ai_error)

    return render_template(
        "index.html",
        ai_result=ai_result,
        image_info=image_info,
        image_name=image_name,
        image_path=image_path,
        error_message=error_message,
    )


@app.errorhandler(413)
def too_large(_error):
    return render_template(
        "index.html",
        error_message="Image is too large. Maximum upload size is 10 MB.",
        ai_result=None,
        image_info=None,
        image_name=None,
        image_path=None,
    ), 413


if __name__ == "__main__":
    app.run(
        debug=False,
        host="127.0.0.1",
        port=5000,
    )
