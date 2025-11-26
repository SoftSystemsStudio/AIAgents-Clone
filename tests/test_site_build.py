import re
from pathlib import Path


def test_build_index_exists():
    build_index = Path("build/index.html")
    assert build_index.exists(), "build/index.html should exist (run bash build.sh)"


def test_index_contains_title_and_cta():
    html = Path("build/index.html").read_text(encoding="utf-8")
    # Title change we made
    assert "Automation, Engineered" in html
    # Primary CTA - signup link should exist
    assert "/api/v1/auth/signup" in html or "Contact the Studio" in html
