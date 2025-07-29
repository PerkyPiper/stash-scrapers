CACHE_DURATION = 600
SITE_ROOT = "https://www.clips4sale.com/"

import json
import requests
import re
import sys
import os
import urllib.parse

# sys.path.append(os.path.abspath(os.path.join(__file__, "../../../community")))
os.chdir(os.path.abspath(os.path.join(__file__, "../")))
sys.path.append("../../community")

from typing import Literal, TypeAlias
from difflib import SequenceMatcher

from py_common import log
from py_common.util import scraper_args
from py_common.types import ScrapedScene, SceneSearchResult
from py_common.cache import cache_to_disk

from ScrapeBuddy.Util import join_url
from ScrapeBuddy.Parsing import parse_date, format_html
# from ScrapeBuddy import Threads
from ScrapeBuddy.Threads import useThread, awaitThreads

from Config import apply_params, ScraperConfigParams, CONFIG_DICT
from Types import C4S_Clip
from Strings import cleanQuery, cleanDesc, cleanTitle, getDurationString

# _SESSION = requests.Session()
# _SESSION.headers.update({"user-agent": CONFIG_DICT.get("user_agent")})

if(CONFIG_DICT.get("use_proxy")):
    from ScrapeBuddy.Proxy import get_proxy, get_data_url
    # from ScrapeBuddy.Image import img_data_url
    # _SESSION.proxies = get_proxy()

_session: requests.Session | None = None
def _getSession():
    global _session
    if(not _session):
        _session = requests.Session()
        _session.hooks['response'].append(lambda r, *args, **kwargs: log.debug(f"Made a request to: {r.url}"))
        _session.headers.update({"user-agent": CONFIG_DICT.get("user_agent")})
        if(CONFIG_DICT.get("use_proxy")):
            _session.proxies = get_proxy()
    return _session

def _makeSearchLink(query: str, studio_link: str, page = 1):
    if studio_link:
        return join_url(SITE_ROOT, studio_link, f"Cat0-AllCategories/Page{page}/C4SSort-most_popular/Limit24/search/{query}")
    else:
        return join_url(SITE_ROOT, f"clips/search/{query}/category/0/storesPage/1/clipsPage/{page}")

class BadwordException(Exception):
    pass

def _doSearch(query: str) -> list[C4S_Clip]:
    query = urllib.parse.quote(query)
    @cache_to_disk(CACHE_DURATION)
    def cachableSearch(query: str, studio_link: str, page: int):
        r = _getSession().get(
            _makeSearchLink(query, studio_link, page),
            params={"onlyClips": True,
            "_data": "routes/($lang).studio.$id_.$studioSlug.$" if studio_link else "routes/($lang).clips.search.$"}
        )
        # log.debug(f"Request sent to: {r.url}")
        if(not r.ok and r.text == "badword"):
            raise BadwordException(f'Query "{query}" contains a word that is forbidden in Clips4Sale searches!!')
        else:
            return r.json()["clips"]
    return cachableSearch(query, CONFIG_DICT.get("studio_link"), 1)

@cache_to_disk(CACHE_DURATION)
def _clipFromURL(url: str) -> C4S_Clip:
    r = _getSession().get(url, params={"_data": "routes/($lang).studio.$id_.$clipId.$clipSlug"})
    # log.debug(f"Requested page: {r.url}")
    return json.loads(r.text.split("\n\ndata:")[0])["clip"]
    # return r.text.split("\n\ndata:")[0]
    # def cachablePage(url: str):
    #     return _getSession().get(url, params={"_data": "routes/($lang).studio.$id_.$clipId.$clipSlug"}).text.split("\n\ndata:")[0]
    # return json.loads(cache_to_disk(CACHE_DURATION)(cachablePage)(url))["clip"]

_picThreads = []
def _populateScene(clip: C4S_Clip, from_search: bool = False):
    scene: ScrapedScene = {
        "title": clip["title_clean"] if "title_clean" in clip else cleanTitle(clip),
        "date": parse_date(clip["dateDisplay"]),
        "image": clip["previewLink"],
        "urls": [join_url(SITE_ROOT, clip["link"])],
        "tags": [{
            "name": v["keyword"]
        } for v in clip["keyword_links"]] if "keyword_links" in clip else []
    }

    if(not from_search):
        # scene["code"] = clip["clipId"]
        scene["details"] = cleanDesc(clip)
        scene["studio"] = {
            "name": clip["studio"]["name"],
            "url": join_url(SITE_ROOT, clip["studio"]["link"]),
            "image": clip["studio"]["banner"]
        }
        scene["image"] = clip["gifPreviewUrl"] if CONFIG_DICT.get("use_gif_thumbs") and clip["gifPreviewUrl"] else clip["cdn_previewlg_link"]
        scene["performers"] = [{
            "name": v["name"],
            "disambiguation": clip["studioTitle"] if re.match(r"^\w+$", v["name"]) else None
        } for v in scene["tags"]]

    if(CONFIG_DICT.get("use_proxy")):
        @useThread(_picThreads)
        def fetchImage(url: str):
            scene["image"] = get_data_url(url, _getSession())
        fetchImage(scene["image"])
        # scene["image"] = cache_to_disk(CACHE_DURATION)(fetchImage)(scene["image"])
        # Threads.useThread(_picThreads, fetchImage)(scene["image"])
    return scene

def _rankScene(query: str, scene: SceneSearchResult):
    title = scene.get("title_plain", scene["title"]).lower()
    return SequenceMatcher(a=query, b=title).quick_ratio()

def _sceneFromName(query: str):
    query = cleanQuery(query)
    results = _doSearch(query)
    retVal: list[ScrapedScene] = []

    for i, v in enumerate(results):
        scene = _populateScene(v, True)

        if(CONFIG_DICT.get("join_results")):
            n = i + 1
            while n < len(results):
                o = results[n]
                if(not "title_clean" in o):
                    o["title_clean"] = cleanTitle(o)
                title = o["title_clean"]

                if(scene["title"].lower() == title.lower()):
                    scene["urls"].append(join_url(SITE_ROOT, o["link"]))
                    results.pop(n)
                    log.debug(f'"{v["title"]}" is the same as {o["title"]}! Who knew?')
                else:
                    n += 1

        if(CONFIG_DICT.get("include_duration")):
            scene["title_plain"] = scene["title"]
            scene["title"] = f"<{getDurationString(v["duration"])}> {scene["title"]}"

        was_sorted = False
        if(CONFIG_DICT.get("do_extra_sort")):
            # keywords = re.split(r"\W", query)
            scene["_ranking"] = _rankScene(query, scene)
            for n, o in enumerate(retVal):
                if(scene["_ranking"] > o["_ranking"]):
                    retVal.insert(n, scene)
                    was_sorted = True
                    break
        if(not was_sorted):
            retVal.append(scene)
    awaitThreads(_picThreads)
    return retVal


ScraperMode: TypeAlias = Literal["scene-by-url"] | Literal["scene-by-fragment"] | Literal["scene-by-name"] | Literal["scene-by-query-fragment"]
def do_scrape(mode: ScraperMode, data, params: ScraperConfigParams | list[str] | None):
    if(params):
        apply_params(params)

    match mode:
        case "scene-by-url":
            return _populateScene(_clipFromURL(data["url"]))
        case "scene-by-fragment":
            for v in data["urls"]:
                if("clips4sale" in v):
                    return _populateScene(_clipFromURL(v))
        case "scene-by-name":
            return _sceneFromName(data["name"])
        case "scene-by-query-fragment":
            result = _populateScene(_clipFromURL(data["url"]))
            result["urls"] = data["urls"]
            return result
        case _:
            log.error(
                f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}"
            )
            sys.exit(1)

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    # log.debug(conf_from_extra(args["extra"]))
    result = do_scrape(op, args, args["extra"])
    print(json.dumps(result))