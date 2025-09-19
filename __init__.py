import os
import queue
import re
from datetime import datetime

from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.book.base import Metadata
from calibre.ebooks.metadata.sources.base import Source
from lxml.html import fromstring

BOOK_URL_TEMPLATE = "https://www.ark.no/produkt/{id}"
QUERY_URL_TEMPLATE = "https://www.ark.no/search?forfatter={author}&format=E-Bok%20%28EPUB%29%2C%20nedlastbar&text={title}"
ISBN_URL_PATTERN = r"https?://(www\.)?ark\.no/produkt/.*-(\d{10}|\d{13})"


def log_print(*args, **kwargs):
    print(f"[ArkMetadata|{datetime.now().isoformat()}]", *args, **kwargs)


class ArkMetadata(Source):
    name = "Ark"
    description = "Fetch metadata from ark.no"
    author = "Morten Lied Johansen"
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)
    capabilities = frozenset(["identify", "cover"])
    touched_fields = frozenset(["title", "authors", "identifier:isbn"])

    def get_book_url(self, identifiers):
        log_print("Getting book URL from identifiers:", identifiers)
        isbn = check_isbn(identifiers.get('isbn', None))
        if isbn:
            if self.running_a_test:
                log_print("Running a test, returning test URL")
                return "file://" + os.path.abspath(f"test_data/{isbn}.html")
            return BOOK_URL_TEMPLATE.format(id=isbn)
        return None

    def id_from_url(self, url):
        log_print("Extracting ID from URL:", url)
        if m := re.match(ISBN_URL_PATTERN, url):
            isbn = m.group(2)
            log_print("Matched ISBN:", isbn)
            return "isbn", check_isbn(isbn)
        return None

    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30):
        log.info("Identifying book with title:", title, ", authors:", authors, ", identifiers:", identifiers)
        book_url = self.get_book_url(identifiers)
        if book_url:
            book_urls = [book_url]
        else:
            log.info("No book URL found using identifiers, searching by title and authors.")
            book_urls = list(self._search(title, authors, timeout, log))
            if not book_urls:
                log.info("No book URL found from search.")
                return
        log.info("Found %d book URLs." % len(book_urls))
        for url in book_urls:
            if abort.is_set():
                return
            mi = self._fetch_metadata(url, timeout, log)
            if not mi:
                log.info("No metadata found at URL: %s" % book_url)
            result_queue.put(mi)

    def get_cached_cover_url(self, identifiers):
        log_print("Getting cached cover URL with identifiers:", identifiers)
        url = None
        isbn = check_isbn(identifiers.get('isbn', None))
        if isbn is not None:
            url = self.cached_identifier_to_cover_url(isbn)
        return url

    def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30):
        log_print("Downloading cover with title:", title, ", authors:", authors, ", identifiers:", identifiers)
        cached_url = self.get_cached_cover_url(identifiers)
        if cached_url is None:
            log.info('No cached cover found, running identify')
            rq = queue.Queue()
            self.identify(log, rq, abort, title=title, authors=authors, identifiers=identifiers)
            if abort.is_set():
                return
            results = []
            while True:
                try:
                    results.append(rq.get_nowait())
                except queue.Empty:
                    break
            results.sort(key=self.identify_results_keygen(title=title, authors=authors, identifiers=identifiers))
            for mi in results:
                cached_url = self.get_cached_cover_url(mi.identifiers)
                if cached_url is not None:
                    break
        if cached_url is None:
            log.info('No cover found')
            return

        if abort.is_set():
            return

        log.info('Downloading cover from:', cached_url)
        try:
            cdata = self.browser.open_novisit(cached_url, timeout=timeout).read()
            result_queue.put((self, cdata))
        except:
            log.exception('Failed to download cover from:', cached_url)

    def _search(self, title, authors, timeout, log):
        # Implement search logic here if needed
        query_url = QUERY_URL_TEMPLATE.format(title=title or "", author=authors[0] if authors else "")
        if self.running_a_test:
            log.info("Loading test data from search_example.html")
            with open("test_data/search_example.html", "rb") as f:
                raw = f.read()
        else:
            log.info("Searching URL: %s" % query_url)
            resp = self.browser.open_novisit(query_url, timeout=timeout)
            if resp.code >= 400:
                return
            raw = resp.read()
        doc = fromstring(raw)
        items = doc.xpath("//div[@id='produkter']//ul/li[@id]")
        for item in items:
            product_id = item.get("id")
            if product_id:
                book_url = self.get_book_url({"isbn": product_id})
                if book_url:
                    log.info("Found book URL: %s" % book_url)
                    yield book_url

    def _fetch_metadata(self, book_url, timeout, log):
        # Implement metadata fetching logic here
        log.info("Fetching metadata from URL: %s" % book_url)
        resp = self.browser.open_novisit(book_url, timeout=timeout)
        if resp.code >= 400:
            return None
        raw = resp.read()
        doc = fromstring(raw)
        title = cover_url = isbn = None
        for meta in doc.xpath('//meta'):
            if meta.get("property") == "og:title":
                title = meta.get("content")
                log.debug("Found title: %s" % title)
            elif meta.get("property") == "og:image":
                cover_url = meta.get("content")
                log.debug("Found cover URL: %s" % cover_url)
            elif meta.get("name") == "evg:sku":
                isbn = meta.get("content")
                log.debug("Found ISBN: %s" % isbn)
        authors = [a.text for a in doc.xpath("//div[@data-component='pdp-contributors']//a")]
        log.debug("Found authors: %s" % authors)
        if not title or not authors:
            return None
        mi = Metadata(title, authors)
        if isbn:
            mi.set_identifier("isbn", isbn)
        mi.has_cover = bool(cover_url)
        if isbn and cover_url:
            if self.running_a_test:
                cover_url = "file://" + os.path.abspath("test_data/example_cover.jpeg")
            self.cache_identifier_to_cover_url(isbn, cover_url)
        self.clean_downloaded_metadata(mi)
        log.info("Fetched metadata: %s" % mi)
        return mi


if __name__ == '__main__':  # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
                                                      title_test, authors_test, series_test)

    test_identify_plugin(ArkMetadata.name,
                         [
                             (  # A book with a ISBN
                                 {
                                     "title": "Diamanter og rust - en Hanne Wilhelmsen-roman",
                                     "authors": ["Anne Holt"],
                                     "identifiers": {"isbn": "9788205598980"},
                                 },
                                 [
                                     title_test("Diamanter og rust - en Hanne Wilhelmsen-roman", exact=True),
                                     authors_test(["Anne Holt"])
                                 ]
                             ),
                             (  # A book with a title/author search
                                 {
                                     "title": "Personlig",
                                     "authors": ["Lee Child"],
                                 },
                                 [
                                     title_test("Personlig", exact=True),
                                     authors_test(["Lee Child"])
                                 ]
                             ),
                         ])
