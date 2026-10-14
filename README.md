# AI Truth Lens

**AI-powered image authenticity estimation** — a Flask web application that lets a user upload an image and request an AI-assisted visual assessment from Google's Gemini models.

> **Important limitation:** the result is an AI-assisted estimate, not forensic proof. The system can make mistakes. If Gemini cannot complete an analysis, the application does not invent a score.

## Features

- Upload images in JPG, JPEG, PNG, or WEBP format.
- Validate the file using its extension and Pillow image verification.
- Sanitize uploaded filenames and add a timestamp to reduce filename collisions.
- Limit uploads to 10 MB.
- Send the image and a structured instruction to Gemini for a score, verdict, observations, and confidence.
- Try compatible Gemini model candidates and bounded retry handling for temporary service errors.
- Show which model completed the analysis.
- Use a transparent no-score fallback when the AI service is unavailable.
- Keep the API key in a local `.env` file rather than in the source code.

## Technology stack

- Python
- Flask
- HTML and Jinja templates
- CSS
- Pillow
- Google GenAI Python SDK
- python-dotenv
- Werkzeug

## Project structure

```text
AI-Truth-Lens/
├── app.py
├── .env.example
├── requirements.txt
├── RUN_AI_TRUTH_LENS.bat
├── README.md
├── README_FIRST.txt
├── .gitignore
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── uploads/
    └── .gitkeep
```

## Run on Windows

1. Install Python 3.11 or newer and Git if you plan to contribute.
2. Create a file named `.env` in the same folder as `app.py` with this single line:

   ```env
   GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_API_KEY
   ```

3. Double-click `RUN_AI_TRUTH_LENS.bat`.
4. Wait for dependency installation and the Flask server to start.
5. Open <http://127.0.0.1:5000> and upload a supported image.

The `.env` file is deliberately not included in this repository. Never commit or share your real API key.

## Run manually

From the project folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Then open <http://127.0.0.1:5000>.

## Error handling notes

- The upload handler rejects unsupported file extensions and files over 10 MB.
- Pillow verification catches files that have an image-looking extension but are not readable images.
- Gemini requests use a bounded timeout, transient-error recognition, model fallback, and limited retries.
- HTTP 429 can indicate rate limiting or resource exhaustion; HTTP 503 can indicate temporary service unavailability.
- When no AI response is available, the app shows local technical image information and `Authenticity Score: Not Available`. It does not pretend that local metadata proves an image is authentic.

Model availability and API limits depend on Google's service and the credentials being used; no client-side code can guarantee that a remote model will always respond.

## Security notes

- Keep `.env` private. `.gitignore` excludes it.
- The repository must not contain real API keys, personal uploaded images, `.venv`, or Python cache files.
- The app binds to `127.0.0.1` for a local demonstration; it is not configured as a production deployment.
- Do not treat the AI-generated score as a calibrated probability or forensic conclusion.

## Project goal

AI Truth Lens demonstrates how a simple web application can combine upload validation, image metadata handling, and multimodal AI to provide an accessible first-look assessment of image authenticity.
