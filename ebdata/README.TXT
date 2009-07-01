======
ebdata
======

Code to help write scripts that import/crawl/parse data into ebpub.

ebdata.blobs
============

The blobs package is a Django app responsible for crawling, scraping,
extracting, and geocoding news articles from the web.

The blobs app contains two models, Seed and Page. Seed is a news source, like
the Chicago Tribune, and a Page is a particular html page that was crawled from
a Seed.


ebdata.nlp
==========

The nlp package contains utilities for detecting locations in text. This
package is used by blobs, but if you want to use it directly, check out the
docstrings for the functions in ebdata.parsing.addresses.


ebdata.parsing
==============

The parsing package contains helpers for reading different file types.

The dbf, excel, mdb, and unicodecsv modules are for reading stuctured data,
and generally follow the python csv reader api. See the code for more details
on how to use the.

The pdf module is for converting pdf to text, and requires Xpdf.
http://www.foolabs.com/xpdf/download.html


ebdata.retrieval
================

The retrieval package contains a framework for writing scrapers for structured
data. There are many examples of how to use this framework in different
situation in the everyblock package.

The most commonly used scraper is the NewsItemListDetailScraper. It handles
scraping list/detail types of sites, and creating or updating NewsItem
objects.

Generally, to run a scraper, you need to instantiate it, and then call its
update method. Sometimes the scraper will take arguments, but it varies on a
case-by-case basis. You can read the scrapers in the everyblock package for
examples. You can also run a scraper by calling its display_data method. This
will run the scraper, but won't actually save any of the scraped data. It's
very useful for debugging, or when writing a scraper for the first time.

All of the methods and parameters you'll need to use are documented in
docstrings of ebdata.retrieval.scrapers.list_detail.ListDetailScraper and in
ebdata.retrieval.scrapers.newsitem_list_detail.NewsItemListDetailScraper.
ListDetailScraper is a base class of NewsItemListDetailScraper that handles
scraping, but doesn't actually have any methods for saving data.

The retrieval package also contains updaterdaemon, which is a cron-like
facility for running scrapers. It comes with a unix-style init script, and its
configuration and examples are in ebdata/retrieval/updaterdaemon/config.py.


ebdata.templatemaker
====================

The templatemaker package contains utilities for detecting the actual content
given a set of html pages that were generated from a template. For instance,
templatemaker helps detect and extract the actual article from a page that
could also contain navigation links, ads, etc.


ebdata.textmining
=================

The textmining package contains utilities for preprocessing html to strip out
things that templatemaker doesn't care about like comments, scripts, styles,
meta information, etc.
