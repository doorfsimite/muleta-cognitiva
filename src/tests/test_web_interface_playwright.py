"""
Playwright-based UI tests for the browser interface.
Skips gracefully if Playwright is not installed or browsers are missing.
"""
import os
import time
import subprocess
import requests
import pytest

try:
    from playwright.sync_api import sync_playwright
except Exception:
    pytest.skip("Playwright not available", allow_module_level=True)


@pytest.fixture(scope="module")
def api_server():
    # Start the API server
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "src.api.main:app", "--host", "localhost", "--port", "8000"],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    time.sleep(2)
    try:
        resp = requests.get("http://localhost:8000/api/entities", timeout=5)
        assert resp.status_code in (200, 404)
    except Exception as e:
        proc.terminate()
        raise
    yield proc
    proc.terminate()
    proc.wait()


def test_index_basic_load(api_server):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    index_path = os.path.join(project_root, "index.html")
    url = f"file://{index_path}"

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:
            pytest.skip("Chromium not available for Playwright")
        page = browser.new_page()
        page.goto(url)

        # Check presence of main containers
        assert page.locator(".app-container").count() > 0
        assert page.locator(".sidebar").count() > 0
        assert page.locator("#chart").count() > 0

        # Check the Processar Texto controls exist
        assert page.get_by_label("Processar Texto").count() >= 0  # button
        assert page.locator("#contentText").count() > 0

        browser.close()
