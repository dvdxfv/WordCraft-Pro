# -*- coding: utf-8 -*-
"""Shared fixtures for browser E2E tests."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

import pytest

try:
    from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None
    Browser = BrowserContext = Page = object


ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
ARTIFACT_ROOT = ROOT / "tests" / "artifacts"
NO_PROXY_OPENER = build_opener(ProxyHandler({}))

BACKEND_HEALTH_URL = "http://127.0.0.1:5000/api/getSystemInfo"
FRONTEND_LOGIN_URL = "http://127.0.0.1:8081/wordcraft_landing.html"
FRONTEND_INDEX_URL = "http://127.0.0.1:8081/index.html"
_SAMPLE_CANDIDATES = (
    ROOT / "samples" / "南海鸢乌贼捕捞量智能反演文献综述.docx",
    ROOT / "samples" / "南海鸢乌贼捕捞量智能反演文献综述_导出.docx",
)
DEFAULT_SAMPLE_DOC = next((p for p in _SAMPLE_CANDIDATES if p.exists()), _SAMPLE_CANDIDATES[0])


def _is_port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _wait_url_ready(url: str, timeout_sec: int = 60) -> None:
    start = time.time()
    while True:
        try:
            with NO_PROXY_OPENER.open(url, timeout=3) as resp:
                if 200 <= resp.status < 500:
                    return
        except HTTPError as e:
            if 400 <= e.code < 600:
                return
        except (URLError, OSError, TimeoutError):
            # Python 3.14: socket.timeout / TimeoutError is no longer wrapped
            # inside URLError by urllib, so catch OSError/TimeoutError explicitly.
            pass
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"service not ready: {url}")
        time.sleep(1)


def _stop_proc(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def e2e_artifact_dir() -> Path:
    run_id = time.strftime("%Y%m%d_%H%M%S")
    path = ARTIFACT_ROOT / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def running_services() -> tuple[subprocess.Popen | None, subprocess.Popen | None]:
    backend_proc = None
    frontend_proc = None

    if not _is_port_open("127.0.0.1", 5000):
        backend_proc = subprocess.Popen(
            [sys.executable, "flask_app.py"],
            cwd=str(WEB_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if not _is_port_open("127.0.0.1", 8081):
        frontend_proc = subprocess.Popen(
            [sys.executable, "run_web.py"],
            cwd=str(WEB_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    _wait_url_ready(BACKEND_HEALTH_URL, 60)
    _wait_url_ready(FRONTEND_LOGIN_URL, 60)

    yield backend_proc, frontend_proc

    _stop_proc(frontend_proc)
    _stop_proc(backend_proc)


@pytest.fixture(scope="session")
def playwright_browser(running_services) -> Browser:
    if sync_playwright is None:
        pytest.skip("Playwright not installed. run: pip install playwright && python -m playwright install chromium")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def context(playwright_browser: Browser) -> BrowserContext:
    ctx = playwright_browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 900})
    yield ctx
    ctx.close()


@pytest.fixture()
def page(context: BrowserContext) -> Page:
    pg = context.new_page()
    yield pg


@pytest.fixture()
def credentials() -> tuple[str, str]:
    email = os.getenv("WC_TEST_EMAIL", "")
    password = os.getenv("WC_TEST_PASSWORD", "")
    return email, password


@pytest.fixture()
def sample_doc_path() -> Path:
    if not DEFAULT_SAMPLE_DOC.exists():
        pytest.skip(f"sample doc not found: {DEFAULT_SAMPLE_DOC}")
    return DEFAULT_SAMPLE_DOC


def login_to_index(page: Page, credentials: tuple[str, str]) -> None:
    email, password = credentials
    page.goto(FRONTEND_LOGIN_URL, wait_until="networkidle")
    page.fill("#email-input", email)
    page.fill("#password-input", password)
    page.click("#email-login-btn")
    page.wait_for_url("**/index.html", timeout=30000)
    page.wait_for_selector("#docPage", timeout=30000)


def upload_document(page: Page, file_path: Path) -> None:
    input_el = page.locator('input[type="file"][accept*=".txt"][accept*=".md"]')
    input_el.set_input_files(str(file_path))
    file_name = file_path.name
    file_name_locator = page.locator("#fileTree .fi-name", has_text=file_name)
    file_name_locator.first.wait_for(timeout=60000)
    file_name_locator.first.locator("..").click()
    page.wait_for_timeout(1500)


@pytest.fixture()
def logged_in_page(page: Page, credentials: tuple[str, str]) -> Page:
    login_to_index(page, credentials)
    return page

