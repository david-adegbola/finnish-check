"""Reading many ads at once: pasted text or a CSV file.

Both readers return {"ads": [...], "errors": [...]}:
    ad    = {"id": "ad-1", "title": first line, "url": "", "ad_text": the whole ad}
    error = {"item": what was skipped, "message": a friendly explanation}
A problem with one ad never stops the batch: 19 good ads and one clear message are better than nothing.

parse_pasted(text)  ads separated by a line containing only --- (three or more dashes)
parse_csv(text)     a CSV with an "ad_text" column; "title" and "url" are optional
"""

import csv
import io
import re

MAX_ADS = 20             # ads per request: each one is an API call in live mode
MAX_AD_CHARS = 10_000    # characters per ad: an internship ad is rarely longer
SEPARATOR = re.compile(r"^\s*-{3,}\s*$", re.M)


def make_ad(number, text, title="", url=""):
    text = text.strip()
    title = (title.strip() or text.splitlines()[0]).strip()
    return {"id": f"ad-{number}", "title": title[:200], "url": url.strip(), "ad_text": text}


def too_long(ad):
    return len(ad["ad_text"]) > MAX_AD_CHARS


def parse_pasted(text):
    ads, errors = [], []
    blocks = [block.strip() for block in SEPARATOR.split(text or "") if block.strip()]
    if len(blocks) > MAX_ADS:
        errors.append({"item": "input", "message": f"Only the first {MAX_ADS} ads were read."})
        blocks = blocks[:MAX_ADS]
    for number, block in enumerate(blocks, start=1):
        ad = make_ad(number, block)
        if too_long(ad):
            errors.append({"item": ad["title"], "message": f"Longer than {MAX_AD_CHARS:,} characters; paste only the ad."})
        else:
            ads.append(ad)
    return {"ads": ads, "errors": errors}


def parse_csv(text):
    ads, errors = [], []
    try:
        reader = csv.DictReader(io.StringIO(text or ""))
        columns = [name.strip().lower() for name in (reader.fieldnames or [])]
        if "ad_text" not in columns:
            return {"ads": [], "errors": [{"item": "CSV file",
                                           "message": "The CSV needs a column called ad_text (title and url are optional)."}]}
        for number, row in enumerate(reader, start=1):
            if number > MAX_ADS:
                errors.append({"item": "CSV file", "message": f"Only the first {MAX_ADS} rows were read."})
                break
            row = {(key or "").strip().lower(): (value or "") for key, value in row.items() if isinstance(value, str)}
            if not row.get("ad_text", "").strip():
                errors.append({"item": f"row {number}", "message": "The ad_text cell is empty."})
                continue
            ad = make_ad(number, row["ad_text"], row.get("title", ""), row.get("url", ""))
            if too_long(ad):
                errors.append({"item": f"row {number}", "message": f"Longer than {MAX_AD_CHARS:,} characters."})
            else:
                ads.append(ad)
    except csv.Error as error:
        errors.append({"item": "CSV file", "message": f"The file couldn't be read as CSV ({error})."})
    return {"ads": ads, "errors": errors}
