import os
import pytest
from anki_vocab.crawler import Crawler


pytestmark = pytest.mark.integration

def test_crawler_search_smoke():
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Set RUN_INTEGRATION=1 to run selenium integration test")

    c = Crawler()
    try:
        htmls = c.search_from_naver("water")
        assert isinstance(htmls, list)
        assert len(htmls) >= 1
        assert all(isinstance(h, str) and len(h) > 100 for h in htmls)
    finally:
        c.driver_close()
