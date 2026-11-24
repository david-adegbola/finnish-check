"""Finnish requirement checker for internship ads: a small Flask app.

A student pastes or uploads a batch of job/internship ads and lists their skills. For each ad the app
finds how much Finnish it asks for (required / preferred / not needed / unclear), quotes the sentence
that says so, and ranks the ads so the realistic ones come first.

Routes
    GET  /          the input form
    POST /analyze   reads the ads, classifies each one, shows the ranked table
    GET  /samples   the 10 sample ads as JSON (for the "Load sample ads" button)
    GET  /about     the problem, the method, the evaluation results and the limitations

Nothing is stored: the ads and skills live only for the length of one request.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from core import batch, finnish, llm, rank

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")          # ANTHROPIC_API_KEY, LLM_MODEL ... (see .env.example)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300_000      # bytes per request (a pasted batch or a CSV file)

MAX_SKILLS = 30
FINNISH_LEVELS = rank.FINNISH_LEVELS             # the student's own level: none / basic / intermediate / fluent


def read_ads(form, files):
    """Ads from the uploaded CSV if there is one, otherwise from the text box."""
    upload = files.get("csv_file")
    if upload and upload.filename:
        if not upload.filename.lower().endswith(".csv"):
            return {"ads": [], "errors": [{"item": upload.filename, "message": "Upload a .csv file."}]}
        try:
            text = upload.read().decode("utf-8-sig")       # utf-8-sig also accepts Excel's BOM
        except UnicodeDecodeError:
            return {"ads": [], "errors": [{"item": upload.filename, "message": "Save the CSV as UTF-8 and try again."}]}
        return batch.parse_csv(text)
    return batch.parse_pasted(form.get("ads_text", ""))


def read_skills(text):
    """Skills from the text box: separated by commas or new lines."""
    skills = [s.strip() for s in text.replace("\n", ",").split(",") if s.strip()]
    return list(dict.fromkeys(skills))[:MAX_SKILLS]       # no duplicates, at most MAX_SKILLS


def classify_all(ads, settings):
    """{ad id: Finnish result}. In live mode up to 4 ads are sent to the API at the same time."""
    def one(ad):
        try:
            return finnish.classify(ad["ad_text"], settings)
        except llm.LLMError as error:
            return finnish.result("unclear", [], f"The AI service failed for this ad ({error}).", "error")
    with ThreadPoolExecutor(max_workers=4 if settings.live else 1) as pool:
        return dict(zip([ad["id"] for ad in ads], pool.map(one, ads)))


@app.get("/")
def index():
    return render_template("index.html", settings=llm.settings_from_env(), max_ads=batch.MAX_ADS,
                           levels=FINNISH_LEVELS)


@app.get("/samples")
def samples():
    return jsonify(json.loads((ROOT / "data" / "samples.json").read_text(encoding="utf-8")))


@app.post("/analyze")
def analyze():
    settings = llm.settings_from_env()
    parsed = read_ads(request.form, request.files)
    skills = read_skills(request.form.get("skills", ""))
    level = request.form.get("finnish_level", "none")
    if level not in FINNISH_LEVELS:
        level = "none"
    if not parsed["ads"]:
        errors = parsed["errors"] or [{"item": "input", "message": "Paste at least one ad, or upload a CSV file."}]
        return render_template("index.html", settings=settings, max_ads=batch.MAX_ADS, levels=FINNISH_LEVELS,
                               errors=errors, form=request.form), 400
    results = classify_all(parsed["ads"], settings)
    rows = rank.rank(parsed["ads"], skills, results, level)
    return render_template("results.html", rows=rows, errors=parsed["errors"], skills=skills,
                           settings=settings, level=level)


@app.get("/about")
def about():
    summary_file = ROOT / "eval" / "summary.json"
    summary = json.loads(summary_file.read_text(encoding="utf-8")) if summary_file.exists() else None
    return render_template("about.html", summary=summary)


@app.errorhandler(413)
def too_large(error):
    return render_template("index.html", settings=llm.settings_from_env(), max_ads=batch.MAX_ADS,
                           levels=FINNISH_LEVELS,
                           errors=[{"item": "input", "message": "That's too much text at once (over 300 KB). "
                                                                f"Send at most {batch.MAX_ADS} ads."}]), 413


if __name__ == "__main__":
    app.run(debug=False, port=5050)     # not 5000: macOS uses port 5000 for AirPlay Receiver
