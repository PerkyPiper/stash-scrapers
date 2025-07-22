# NOTE: I am not very familiar with Python, so much of this was copied from
# https://github.com/stashapp/CommunityScrapers/blob/master/scrapers/AShemaleTube/AShemaleTube.py
# So big thanks to the developer of that, for saving my sanity!

# https://girlsgonehypnotized.com is a site clearly made by non-developers,
# as it has a lot of ideosynchratic quirks! This made scraping the site accurately,
# while maintaining human readable formatting quite a challenge! This scraper
# is NOT guaranteed to work as expected for all pages, but should work well for most!

# PLEASE NOTE: Some older videos have been removed from Clips4Sale, but the links remain!
# In this event, the scraped thumbnail will default to that of the most recent upload!
# Always double check the thumnbail for older titles!

DO_C4S_SCRAPE = True
# USE_GGH_THUMB = True

from datetime import datetime
import json
import re
import sys
import urllib.parse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedScene,
)
from py_common.util import scraper_args

ensure_requirements("cloudscraper", "fp:free-proxy", "lxml")
import cloudscraper  # noqa: E402
from fp.fp import FreeProxy
from lxml import html
import urllib

scraper = cloudscraper.create_scraper()

free_proxies = None


def get_proxies() -> dict:
    proxy = FreeProxy(rand=True).get()
    log.debug("proxy: %s" % proxy)
    return { 'http': proxy } if proxy.startswith('http:') else { 'https': proxy }

# def li_value(key: str) -> str:
#     return f'//div[@class="info-box info"]/ul/li/span[text()="{key}:"]/../text()[2]'


def parse_date(date_string: str) -> str:
    try:
        return datetime.strftime(datetime.strptime(date_string, "%m/%d/%y %I:%M %p"), "%Y-%m-%d")
    except Exception as e:
        log.error(e)
        return date_string

def format_page(doc: str) -> str:
    # XPath seems to maintain linebreak characters (\n), but not linebreak tags (<br>)!
    # This is the opposite of how html treats them, so it causes annoying inconsistencies!
    # This step is the entire reason I needed Python for this scraper!

    # Strip out all existing linebreaks (prevents accidental word merging for some older videos)
    retVal = doc.replace("\n", " ")
    # Replace <br> tags (and surrounding spaces) with linebreak character!
    retVal = re.sub(r" *<br> *", "\n", retVal)
    # Get rid of extra spaces, so previous html indentation doesn't affect output!
    # PS: Who puts a non-breaking space next to a normal space? I see ZERO benefit to that, except to troll me!
    retVal = re.sub(r"(&nbsp;| ){2,}", " ", retVal)
    return retVal

def scrape_url(url: str, format: bool = False):
    log.debug("Scraping url: " + url)
    doc = scrape_url_to_string(url)

    return html.document_fromstring(format_page(doc) if format else doc)
    # doc = re.sub(r" {2,}", " ", scrape_url_to_string(url).replace("\n", " "))
    # return html.document_fromstring(doc)


def scrape_url_to_string(url, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            log.debug('about to execute scraper.get, attempt %d' % (retries + 1))
            global free_proxies
            free_proxies = get_proxies()
            scraped = scraper.get(url, proxies=free_proxies)
            if scraped.status_code == 200:
                log.debug('HTTP Status: 200')
                return scraped.text
            log.error('HTTP Error: %s' % scraped.status_code)
        except Exception as e:
            log.error("scraper.get error: %s" % e)

        retries += 1
        log.debug('Retrying (%d/%d)...' % (retries, max_retries))

    raise Exception('Failed to scrape the URL after %d retries' % max_retries)


def scene_from_url(_url: str) -> ScrapedScene | None:
    scene: ScrapedScene = {}
    tree = scrape_url(_url, True)
    try:

        #title
        # Title is always bold, usually with css, occasionally with <b> tag
        if (title := next(iter(tree.xpath('//td//span[contains(@style, "bold")]/text() | //td//b/text()')), None)) is not None:
            scene["title"] = title.strip()

        # #image COMMENTED OUT BECAUSE THE OFFICIAL THUMBNAILS ARE LOW QUALITY AND POORLY PROPORTIONED FOR STASH!!!
        # if (USE_GGH_THUMB):
        #     scene["image"] = "https://girlsgonehypnotized.com/GGH%20Thumbnails/" + urllib.parse.quote(title + " Thumbnail.jpg")

        #studio
        # Studio is always the same. If someone ever makes a scraper for other gg fetish sites, this may be the only change needed!
        scene["studio"] = {
            "name": "Girls Gone Hypnotized"
        }

        #details
        # Pretty much all page text is in the same div, or a span within that div! We gotta use more string manipulation to get the right section!
        if (details := tree.xpath('//div[contains(@style, "justify;")]')) is not None:
            # D = " ".join(details)
            D = details[0].text_content()

            # Split description from everything else in the same div, while maintaining span text.
            if(D.find("Full Download Details") != -1):
                # Usually this
                D = D.split("Full Download Details")[0]
            else:
                # Sometimes this
                D = D.split("Full Video Details")[0]

            # The highlights are the only <li> elements present in the page, if that ever changes this will break!!!
            Highlights = list(map(lambda v: v.text_content().replace("\n", ""), tree.xpath('//li')))
            
            # Retain the list-like formatting, would be extra cool if stash included markdown!
            H = "\n- ".join(["Key highlights of video include:"] + Highlights)
            scene["details"] = (re.sub(r" *\n *", "\n", D).strip() + "\n\n" + H.strip())

        #urls
        # All buy links use the same png image!
        if (urls := tree.xpath('//img[contains(@src, "images/buynow.png")]/../@href')) is not None:
            # GGH uses so many different storefronts, only some of which are allowed on StashDB
            urls.insert(0, _url)
            scene["urls"] = urls

    except Exception as e:
        log.error(_url)
        log.error("Uh oh an error!: %s" % e)

    # Scrape some extra data from Clips4Sale! XPath rules yoinked from the Clips4Sale scraper!
    # May be worth adding more sub-scrapers for files that aren't on c4s
    if(DO_C4S_SCRAPE and urls is not None):
        try:
        # Find a clips4sale link and scrape the date/portrait. Quick, dirty, high failure rate!
            c4s = list(filter(lambda x: x.find("clips4sale") != -1, urls))

            if (len(c4s)):
                    c4sTree = scrape_url(c4s[0])

                    #date
                    if (date := next(iter(c4sTree.xpath('//div[contains(@class, \'border-b border-white/20 lg:border-0 pb-3 lg:pb-0 mb-3 lg:mb-0\')]/span[contains(text(),\'/\')]/text()')), None)) is not None:
                        scene["date"] = parse_date(date)
                    
                    # ALERT: Deleted videos redirect to main store page! This means they will default to the MOST RECENTLY POSTED VIDEO'S THUMBNAIL!!!
                    #image
                    # if not USE_GGH_THUMB and (image := next(iter(c4sTree.xpath('//figure[contains(@class, "mediabook-preview")]//img/@src')), None)) is not None:
                    if (image := next(iter(c4sTree.xpath('//figure[contains(@class, "mediabook-preview")]//img/@src')), None)) is not None:
                        scene["image"] = image
        except Exception as e:
            log.error("An error occurred while scraping c4s! The link may be broken! Error: %s" % e)
    return scene

# This sorta works, but naming conventions are inconsistent. Also messes up some models' names because I was too lazy to do it properly.
# lowerCasedWords = ["The", "An", "By", "To", "And", "In", "On"]

def applyCaseRules(FileName: str) -> str:
    FileName = FileName.title()
    # for v in lowerCasedWords:
    #     FileName = re.sub(v, v.lower(), FileName)
    return FileName

def doReplacements(FileName: str) -> str:
    # Buncha things to remove, should probably make this more readable but leaving this note here instead!
    FileName = applyCaseRules(re.sub(r"-|_", " ", re.sub(r"GirlsGoneHypnotized|GGH|Ggh|\.mp4|\.wmv|\.avi|\.flv|\.m4v|\(|\)|,|'", "", FileName)))
    return FileName.replace(" ", "")

def sceneFromFragment(Fragment) -> ScrapedScene:
    MatchUrl = list(filter(lambda v: v.startswith("https://girlsgonehypnotized.com/"), Fragment['urls']))

    if (len(MatchUrl)):
        # If the file already has a studio url saved, scrape that
        url = MatchUrl[0]
        log.debug("Using existing saved url: " + url)
    else:
        # Otherwise, attempt to infer a url based on file name!
        # This is pretty janky, but has worked frequently enough to be worth the attempt.
        Title = doReplacements(Fragment["title"] if Fragment["title"] is not None else re.search(r"[^\\/]+$", Fragment["files"][0]["path"]).group())
        log.debug("Inferred URL: " + Title)
        url = "https://girlsgonehypnotized.com/" + Title + ".html"

    return scene_from_url(url)
        

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        # case "performer-by-url", {"url": url}:
        #     result = performer_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-fragment", {}:
            result = sceneFromFragment(args)
        case _:
            log.error(
                f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}"
            )
            sys.exit(1)

    log.debug("result: %s" % result)
    print(json.dumps(result))