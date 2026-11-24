import io
import json

import app as app_module


def test_pages_return_200(client):
    assert client.get("/").status_code == 200
    assert client.get("/about").status_code == 200
    response = client.get("/samples")
    assert response.status_code == 200
    assert len(response.get_json()) == 10


def test_analyze_samples_in_mock_mode(client):
    samples = json.loads(client.get("/samples").data)
    ads_text = "\n---\n".join(sample["text"] for sample in samples)
    response = client.post("/analyze", data={"ads_text": ads_text, "skills": "Python, SQL", "finnish_level": "none"})
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert page.count('<tr data-level=') == 10
    assert "MOCK" in page
    assert "Mock mode" in page


def test_empty_input_gives_a_friendly_error(client):
    response = client.post("/analyze", data={"ads_text": "   ", "skills": ""})
    assert response.status_code == 400
    assert "Paste at least one ad" in response.get_data(as_text=True)


def test_too_many_ads_are_capped_with_a_message(client):
    ads_text = "\n---\n".join(f"Ad number {i}. Finnish is an advantage." for i in range(25))
    page = client.post("/analyze", data={"ads_text": ads_text}).get_data(as_text=True)
    assert page.count('<tr data-level=') == 20
    assert "Only the first 20 ads were read." in page


def upload(client, content, filename="ads.csv"):
    data = {"skills": "SQL", "csv_file": (io.BytesIO(content.encode("utf-8")), filename)}
    return client.post("/analyze", data=data, content_type="multipart/form-data")


def test_valid_csv_upload(client):
    response = upload(client, "title,url,ad_text\nData intern,https://example.org/1,Finnish is not required.\n")
    assert response.status_code == 200
    assert "Data intern" in response.get_data(as_text=True)


def test_csv_validation(client):
    response = upload(client, "name,text\nA,B\n")
    assert response.status_code == 400
    assert "needs a column called ad_text" in response.get_data(as_text=True)
    response = upload(client, "ad_text\nhello\n", filename="ads.txt")
    assert response.status_code == 400
    assert "Upload a .csv file" in response.get_data(as_text=True)


def test_hide_required_filter_is_on_the_results_page(client):
    page = client.post("/analyze", data={"ads_text": "Trainee\nEdellytämme sujuvaa suomen kielen taitoa."}).get_data(as_text=True)
    assert 'id="hide-required"' in page
    assert 'data-level="required"' in page


def test_live_mode_uses_the_classifier(client, monkeypatch):
    calls = []

    def fake_classify(text, settings, call=None):
        calls.append(text)
        return app_module.finnish.result("not_needed", ["Finnish is not required."], "Says so.", "llm", "test-model")
    monkeypatch.setenv("LLM_MODE", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(app_module.finnish, "classify", fake_classify)
    page = client.post("/analyze", data={"ads_text": "Intern\nFinnish is not required."}).get_data(as_text=True)
    assert calls == ["Intern\nFinnish is not required."]
    assert "Finnish not needed" in page
    assert "Mock mode" not in page
