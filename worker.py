#!/usr/bin/env python
import os
import re
from datetime import datetime, tzinfo
from threading import Thread
from zoneinfo import ZoneInfo

from calibre.ebooks.metadata.book.base import Metadata
from lxml.html import fromstring


LANGUAGE_LOOKUP = {
    "norsk": "no",
    "nynorsk": "nn",
    "bokmål": "nb",
    "engelsk": "en",
    "svensk": "sv",
    "dansk": "da",
    "finsk": "fi",
    "tysk": "de",
    "fransk": "fr",
    "spansk": "es",
    "italiensk": "it",
}


class Worker(Thread):  # Get  details
    name = "Ark Worker"
    description = "Fetch metadata from ark.no in worker thread"
    author = "Morten Lied Johansen"
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)

    def __init__(self, url, relevance, result_queue, browser, log, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self._url = url
        self._relevance = relevance
        self._result_queue = result_queue
        self._log = log
        self._timeout = timeout
        self._plugin = plugin
        self._browser = browser.clone_browser()

    def run(self):
        try:
            self.get_details()
        except:
            self._log.exception("Get details failed for url: %s" % self._url)

    def get_details(self):
        # Implement metadata fetching logic here
        self._log.info("Fetching metadata from URL: %s" % self._url)
        resp = self._browser.open_novisit(self._url, timeout=self._timeout)
        if resp.code >= 400:
            return
        raw = resp.read()
        doc = fromstring(raw)

        title = cover_url = isbn = None
        for meta in doc.xpath('//meta'):
            if meta.get("property") == "og:title":
                title = meta.get("content")
                self._log.debug("Found title: %s" % title)
            elif meta.get("property") == "og:image":
                cover_url = meta.get("content")
                self._log.debug("Found cover URL: %s" % cover_url)
            elif meta.get("name") == "evg:sku":
                isbn = meta.get("content")
                self._log.debug("Found ISBN: %s" % isbn)

        authors = [a.text for a in doc.xpath("//div[@data-component='pdp-contributors']//a")]
        self._log.debug("Found authors: %s" % authors)

        if not title or not authors:
            return

        mi = Metadata(title, authors)
        mi.source_relevance = self._relevance
        if isbn:
            mi.set_identifier("isbn", isbn)

        mi.has_cover = bool(cover_url)
        if isbn and cover_url:
            if self._plugin.running_a_test:
                cover_url = "file://" + os.path.abspath("test_data/example_cover.jpeg")
            self._plugin.cache_identifier_to_cover_url(isbn, cover_url)

        # Find product details
        product_details_dts = doc.xpath("//div[@id='acc-product-details']//dt")
        for dt in product_details_dts:
            key = dt.text_content().strip()
            dd = dt.getnext()
            if dd is None:
                continue
            value = dd.text_content().strip()
            if key == "Forlag":
                mi.publisher = value
                self._log.debug(f"Found publisher: {value}")
            elif key == "Første salgsdato":
                pubdate = datetime.strptime(value, "%d.%m.%Y")
                pubdate = pubdate.replace(tzinfo=ZoneInfo("Europe/Oslo"))
                mi.pubdate = pubdate
                self._log.debug(f"Found publication date: {pubdate.isoformat()}")
            elif key == "Språk":
                languages = [LANGUAGE_LOOKUP[v.strip()] for v in value.lower().split(",") if v.strip() in LANGUAGE_LOOKUP]
                mi.languages = languages
                self._log.debug("Set languages: %s" % ", ".join(languages))
            elif key == "Serie":
                mi.series = value
                self._log.debug(f"Found series: {value}")

        series_index_div = doc.xpath("//div[contains(text(), ' av serien')]")
        if series_index_div:
            series_text = series_index_div[0].text_content().strip()
            if match := re.search(r'Del (\d*?) av serien', series_text):
                series_index = match.group(1).strip()
                if series_index:
                    try:
                        mi.series_index = float(series_index)
                        self._log.debug(f"Found series index: {series_index}")
                    except ValueError:
                        pass

        self._plugin.clean_downloaded_metadata(mi)
        self._result_queue.put(mi)
