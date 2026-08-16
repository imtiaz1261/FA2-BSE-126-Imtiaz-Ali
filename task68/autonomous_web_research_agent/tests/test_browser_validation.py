import pytest
from browser.playwright_tool import BrowserTool

def test_url_validation():
    with pytest.raises(ValueError):
        BrowserTool._validate_url("javascript:alert(1)")
    with pytest.raises(ValueError):
        BrowserTool._validate_url("not-a-url")
