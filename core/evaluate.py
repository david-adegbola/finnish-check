"""Evaluation: how well do baseline_v1 and the classifier agree with hand labels?

Run:  python -m core.evaluate          (mock mode without an API key; live with ANTHROPIC_API_KEY)
Reads data/eval/ads.jsonl and writes eval/REPORT.md and eval/summary.json (used by the /about page).

Each line of ads.jsonl is one labelled ad:
    {"id", "source_url", "language", "ad_text_excerpt", "label", "evidence", "note", "invented"?}
label is required / preferred / not_needed / unclear (rules in data/eval/GUIDE.md).

Two comparisons:
  * Four levels: the classifier against the labels. baseline_v1 can't take part, because it only says
    required / not_required.
  * Collapsed: preferred and not_needed both become "not_required", so both classifiers can be compared
    on the question baseline_v1 answers. Ads labelled "unclear" are left out of this table (and
    counted), because "unclear" has no fair yes/no equivalent.

Words used:
  accuracy  = correct answers / all answers
  precision = of the ads the classifier put in a class, how many really belong there
  recall    = of the ads really in a class, how many the classifier found
"""

import json
import sys
from datetime import date
from pathlib import Path

from core import finnish, llm

ROOT = Path(__file__).resolve().parent.parent
COLLAPSED = ("required", "not_required")


def load_dataset(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("label") in finnish.LEVELS and row.get("ad_text_excerpt"):
                rows.append(row)
    return rows


def collapse(label):
    if label == "required":
        return "required"
    if label in ("preferred", "not_needed", "not_required"):
        return "not_required"
    return "unclear"


def scores(gold, predicted, labels):
    """Accuracy, a confusion matrix {true label: {predicted: count}} and precision/recall per class."""
    columns = list(labels) + sorted(set(predicted) - set(labels))
    matrix = {g: {p: 0 for p in columns} for g in labels}
    for g, p in zip(gold, predicted):
        matrix[g][p] += 1
    correct = sum(g == p for g, p in zip(gold, predicted))
    per_class = {}
    for label in labels:
        predicted_as = sum(matrix[g][label] for g in labels)
        actual = sum(matrix[label].values())
        per_class[label] = {"precision": matrix[label][label] / predicted_as if predicted_as else None,
                            "recall": matrix[label][label] / actual if actual else None, "ads": actual}
    return {"total": len(gold), "correct": correct, "accuracy": correct / len(gold) if gold else None,
            "matrix": matrix, "columns": columns, "per_class": per_class}


def evaluate(rows, baseline, predicted):
    """baseline / predicted: {ad id: label}."""
    kept = [r for r in rows if r["label"] != "unclear"]
    gold_collapsed = [collapse(r["label"]) for r in kept]
    return {
        "ads": len(rows), "real_ads": sum(not r.get("invented") for r in rows),
        "excluded_unclear": len(rows) - len(kept),
        "four_levels": scores([r["label"] for r in rows], [predicted[r["id"]] for r in rows], finnish.LEVELS),
        "baseline_collapsed": scores(gold_collapsed, [baseline[r["id"]] for r in kept], COLLAPSED),
        "classifier_collapsed": scores(gold_collapsed, [collapse(predicted[r["id"]]) for r in kept], COLLAPSED),
        "baseline_collapsed_real": scores([collapse(r["label"]) for r in kept if not r.get("invented")],
                                          [baseline[r["id"]] for r in kept if not r.get("invented")], COLLAPSED),
    }


def pct(value):
    return "–" if value is None else f"{100 * value:.0f}%"


def table(result, title):
    lines = [f"### {title}", "", f"Accuracy: **{pct(result['accuracy'])}** ({result['correct']} of {result['total']})", "",
             "| true label \\ predicted | " + " | ".join(result["columns"]) + " |",
             "|---|" + "---|" * len(result["columns"])]
    lines += [f"| {g} | " + " | ".join(str(row[c]) for c in result["columns"]) + " |" for g, row in result["matrix"].items()]
    lines += ["", "| class | precision | recall | ads |", "|---|---|---|---|"]
    lines += [f"| {label} | {pct(s['precision'])} | {pct(s['recall'])} | {s['ads']} |" for label, s in result["per_class"].items()]
    return lines + [""]


def report(summary, rows, baseline, results, mode, model):
    lines = ["# Evaluation report", "",
             f"Date: {date.today().isoformat()} · Classifier mode: **{mode}**" + (f" ({model})" if model else ""),
             f" · Ads: {summary['ads']} ({summary['real_ads']} real excerpts, {summary['ads'] - summary['real_ads']} invented)", ""]
    if mode == "mock":
        lines += ["> **Mock mode:** the classifier column is the app's keyword guess, not the LLM. The guess was "
                  "written after seeing these ads, so its score is not a fair result; it is shown only so the report "
                  "format can be checked. Run with ANTHROPIC_API_KEY set for real LLM numbers.", ""]
    lines += ["## Collapsed: required vs not required", "",
              f"Preferred and not_needed count as not_required; {summary['excluded_unclear']} ads labelled unclear are left out.", ""]
    lines += table(summary["baseline_collapsed"], "baseline_v1 (JobDesk's keyword rule), all ads")
    lines += table(summary["baseline_collapsed_real"], "baseline_v1, real ads only")
    lines += table(summary["classifier_collapsed"], f"Classifier ({mode}), all ads")
    lines += ["## Four levels (classifier only)", ""] + table(summary["four_levels"], f"Classifier ({mode})")
    lines += ["## Disagreements", ""]
    for r in rows:
        res = results[r["id"]]
        base_wrong = r["label"] != "unclear" and baseline[r["id"]] != collapse(r["label"])
        if not base_wrong and res["level"] == r["label"]:
            continue
        lines += [f"**{r['id']}**" + (" (invented)" if r.get("invented") else f" – [source]({r['source_url']})"),
                  f"- Label: **{r['label']}** · baseline_v1: {baseline[r['id']]}{' ✗' if base_wrong else ''} · "
                  f"classifier: {res['level']}{' ✗' if res['level'] != r['label'] else ''}",
                  f"- Evidence: “{r['evidence']}”" if r["evidence"] else "- Evidence: (the ad doesn't mention Finnish)",
                  f"- Note: {r['note']}" if r.get("note") else "", ""]
    return "\n".join(lines) + "\n"


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    settings = llm.settings_from_env()
    rows = load_dataset(ROOT / "data" / "eval" / "ads.jsonl")
    baseline = {r["id"]: finnish.baseline_v1(r["ad_text_excerpt"]) for r in rows}
    results = {}
    for number, r in enumerate(rows, start=1):
        print(f"[{number}/{len(rows)}] {r['id']}", file=sys.stderr)
        try:
            results[r["id"]] = finnish.classify(r["ad_text_excerpt"], settings)
        except llm.LLMError as error:
            # Stop at the first failure and write nothing: a report full of failed calls (for example with a
            # wrong API key) would look like real results and overwrite the good one.
            print(f"Stopped: {r['id']}: {error} No report was written.", file=sys.stderr)
            sys.exit(1)
    mode = "live" if settings.live else "mock"
    summary = evaluate(rows, baseline, {i: res["level"] for i, res in results.items()})
    out = ROOT / "eval"
    out.mkdir(exist_ok=True)
    (out / "REPORT.md").write_text(report(summary, rows, baseline, results, mode, settings.model if settings.live else ""),
                                   encoding="utf-8")
    # A small summary for the /about page: just the headline numbers
    headline = {"date": date.today().isoformat(), "mode": mode, "ads": summary["ads"],
                "real_ads": summary["real_ads"], "excluded_unclear": summary["excluded_unclear"]}
    for key in ("baseline_collapsed", "baseline_collapsed_real", "classifier_collapsed", "four_levels"):
        headline[key] = {"accuracy": summary[key]["accuracy"], "correct": summary[key]["correct"],
                         "total": summary[key]["total"]}
    (out / "summary.json").write_text(json.dumps(headline, indent=2), encoding="utf-8")
    print(f"Wrote eval/REPORT.md and eval/summary.json ({mode} mode).")


if __name__ == "__main__":
    main()
