#!/usr/bin/env python
import os
from threading import Thread

from calibre.ebooks.metadata.book.base import Metadata
from lxml.html import fromstring


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

        self._plugin.clean_downloaded_metadata(mi)
        self._log.info("Fetched metadata: %s" % mi)
        self._result_queue.put(mi)
