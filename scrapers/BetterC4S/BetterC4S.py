import sys
import json
import requests
import re
from os import path

# log.debug(path.abspath(path.join(__file__, "../..")))
sys.path.append(path.abspath(path.join(__file__, "../..")))
sys.path.append(path.abspath(path.join(__file__, "../../../community")))

from typing import TypedDict, Literal, TypeAlias
from urllib.parse import urljoin, quote
from py_common import log
from py_common.util import scraper_args
from py_common.cache import cache_to_disk
from py_common.types import ScrapedScene, ScrapedPerformer, ScrapedTag, SceneSearchResult
from py_common.deps import ensure_requirements

ensure_requirements("fp:free-proxy")
from fp.fp import FreeProxy
from Lib_Scrapifier.Scrapifier import parse_date, format_html

try:
    from Types import C4S_Json
    from Util import clean_url
    from Config import set_conf, conf_from_extra, CONFIG_DICT, BANNED_WORDS, Scraper_Conf
except ModuleNotFoundError:
    from BetterC4S.Types import C4S_Json
    from BetterC4S.Util import clean_url
    from BetterC4S.Config import set_conf, conf_from_extra, CONFIG_DICT, BANNED_WORDS, Scraper_Conf

SITE_ROOT = "https://www.clips4sale.com/"
def from_root(link: str):
    return urljoin(SITE_ROOT, link)

def get_proxies() -> dict:
    proxy = FreeProxy(rand=True).get()
    log.debug("proxy: %s" % proxy)
    return { 'http': proxy } if proxy.startswith('http:') else { 'https': proxy }

def handleArgReplacement(x: str, replacer: list[list[str]] | None = None):
    if(replacer):
        for v in replacer:
            x = re.sub(v[0], v[1] if len(v) > 1 else "", x)
    return x

def removeCensored(match: re.Match):
    word = match.group(0)
    # log.debug(word)
    if(word in BANNED_WORDS):
        log.info(f'Removed banned word "{word}" from query!')
        return ""
    else:
        return word

def cleanQuery(query: str) -> str:
    query = query.lower()
    query = re.sub(r'\w+', removeCensored, query)
    query = quote(query)
    query = re.sub(r" {2,}", " ", query)

    return query.strip()

def cleanTitle(clip: C4S_Json) -> str:
    title = clip["title"]
    # log.debug(clip["format"])
    if(not CONFIG_DICT.get("skip_default_title_replacer")):
        title = re.sub(r"<[^>]+>", "", clip["title"])
        # m(?:[ok4]v|p4)|(?:wm|fl)v|avi
        title = re.sub(fr"{clip["format"]}|(?:\d+ ?x ?\d+p?)|(?:1080|720|480|360)p?|4k|[hs]d", "", title, flags=re.IGNORECASE)
        # title = re.sub(r"(?:1080|720|480|360)p?|4k|[hs]d", "", title, flags=re.IGNORECASE)
        title = re.sub(r" {2,}", "", title)

    title = handleArgReplacement(title, CONFIG_DICT.get("title_regex"))
    title = re.sub(r"[\[\(\{\<](?:\s|-)*[\]\)\}\>]", "", title)
    # log.debug(title.strip(" -"))
    # title = re.sub(re.compile())

    return title.strip(" -")

def doRequest(url: str, params: dict | None = None, has_extra = False):
    r = requests.get(
        url=url, params=params,
        proxies=get_proxies() if CONFIG_DICT.get("use_proxy") else None, headers={"User-Agent": CONFIG_DICT.get("user_agent")}
    )
    # log.debug(r.cookies.get_dict())
    log.info(f"Request sent: {r.url}")
    if(r.ok):
        if(has_extra):
            return json.loads(r.text.split("\n\ndata:")[0])
        else:
            # return json.loads(r)
            return r.json()
    else:
        raise requests.exceptions.ConnectionError(f'Request to "{url}" returned a fail status code!', request=r.request, response=r)

class BadwordException(Exception):
    pass

def make_search_link(query: str, studio_link: str | None, page: int = 1):
    if studio_link:
        return urljoin(urljoin(SITE_ROOT, studio_link), f"Cat0-AllCategories/Page{page}/C4SSort-recommended/Limit24/search/{query}")
    else:
        return f"{SITE_ROOT}clips/search/{query}/category/0/storesPage/1/clipsPage/{page}"
    
# def doRanking(query: str, clips: list[C4S_Json]):
#     query = re.split(r"\W", query.lower())
#     retVal: list[C4S_Json] = []

#     for v in clips:
#         ranking = 0
#         for w in query:
#             if(w in v["title"].lower()):
#                 ranking += 1
#         v["ranking"] = ranking
#         placed = False
#         log.debug(f"{v["title"]}: {ranking}")
#         for i,c in enumerate(retVal):
#             if(ranking > c["ranking"]):
#                 retVal.insert(i, v)
#                 placed = True
#                 break
#         if(not placed):
#             retVal.append(v)
#     return retVal
    
def paginateSearch(query: str, studio_link: str | None):
    from_cache = True
    retVal: list[C4S_Json] = []

    def do_cached_search(query, studio_link, page: int = 1):
        nonlocal from_cache
        from_cache = False
        return doRequest(
            make_search_link(query, studio_link, page),
            {"onlyClips": True, "_data": "routes/($lang).studio.$id_.$studioSlug.$" if studio_link else "routes/($lang).clips.search.$"}
        )["clips"]
    
    if(CONFIG_DICT.get("multi_page")):
        page = 1
        while from_cache:
            result = cache_to_disk(600)(do_cached_search)(query, studio_link, page)
            page += 1

            if(result):
                retVal += result
            else:
                break
        log.debug(f"Paginated search complete! Got {page - 1} pages containing {len(retVal)} results!   ")
        return retVal
    else:
        return cache_to_disk(600)(do_cached_search)(query, studio_link, 1)


def doSearch(query: str, studio_link: str | None = None) -> list[C4S_Json]:
    cleaned = cleanQuery(query)

    try:
        return paginateSearch(cleaned, CONFIG_DICT.get("studio_link"))
    except requests.exceptions.ConnectionError as e:
        if(e.response.text == 'badword'):
            raise BadwordException(f'Query "{query}" contains a word that is forbidden in Clips4Sale searches!!')
        else:
            raise e

def getClipFromURL(url: str) -> C4S_Json:
    c = cache_to_disk(600)(doRequest)(url, {"_data": "routes/($lang).studio.$id_.$clipId.$clipSlug"}, True)
    return c["clip"]

def populateScene(clip: C4S_Json, full_scene = True) -> ScrapedScene:
    tags: list[ScrapedTag] = []
    performers: list[ScrapedPerformer] = []

    try:
        tags = list(map(lambda v: {
            "name": v["keyword"]
        }, clip["keyword_links"]))
    except:
        log.warning("FYI this clip has no tags!")

    # try:
    #     performers = list(map(lambda v: {
    #         "name": v["stage_name"],
    #         "disambiguation": clip["studioTitle"]
    #     }, clip["performers"]))
    # except:
        # log.info("FYI this clip has no performers (and that's normal)!")
    if(tags):
        performers = list(map(lambda v: {
            "name": v["name"],
            "disambiguation": clip["studioTitle"]
        }, tags))

    # log.debug(clip)

    title = clip["title_clean"] if "title_clean" in clip else cleanTitle(clip)
    
    scene: SceneSearchResult = {
        "title": title,
        "date": parse_date(clip["dateDisplay"]),
        "image": clip["previewLink"],
        "urls": [from_root(clip["link"])],
        "performers": performers,
        "tags": tags
    }
    
    if(full_scene):
        desc = format_html(clip["description"])
        # desc = format_html_string(clip["description"], "latin-1", strip_tags=True)
        desc = handleArgReplacement(desc, CONFIG_DICT.get("desc_regex"))
        scene: ScrapedScene

        scene["code"] = clip["clipId"]
        scene["details"] = desc.strip()
        scene["studio"] = {
            "name": clip["studioTitle"].title(),
            "url": from_root(clip["studioLink"])
        }
        # log.debug(f"{clip["gifPreviewUrl"]}, {clip["customPreview"]}")
        scene["image"] = clip["gifPreviewUrl"] if CONFIG_DICT.get("use_gif_for_thumb") and clip["gifPreviewUrl"] else clip["cdn_previewlg_link"]
    return scene

def scene_from_url(url: str):
    return populateScene(getClipFromURL(clean_url(url)))

def rank_result(query: list[str], result: SceneSearchResult):
    ranking = 0
    title = result["title"].lower()

    for v in query:
        if(v in title):
            ranking += 1
    return ranking

def get_duration_string(duration: int):
    retVal = f"{duration % 60}min"
    if(duration >= 60):
        retVal = f"{duration // 60}hr {retVal}"
    return retVal

def scene_from_name(name: str):
    search_results = doSearch(name, CONFIG_DICT.get("studio_link"))

    retVal: list[ScrapedScene] = []
    for i, v in enumerate(search_results):
        n = i + 1
        scene = populateScene(v, full_scene=False)

        if(CONFIG_DICT.get("join_search_results")):
            while n < len(search_results):
                o = search_results[n]
                o["title_clean"] = o["title_clean"] if "title_clean" in o else cleanTitle(o)

                if scene["title"].lower() == o["title_clean"].lower():
                    scene["urls"].append(from_root(o["link"]))
                    search_results.pop(n)
                    log.debug(f'"{v["title"]}" is the same as {o["title"]}! Who knew?')
                else:
                    n += 1

        if(CONFIG_DICT.get("include_duration")):
            scene["title"] = f"<{get_duration_string(v["duration"])}> {scene["title"]}"
        
        if(CONFIG_DICT["do_extra_sort"]):
            scene["__ranking"] = rank_result(re.split(r"\W", name.strip()), scene)
            placed = False

            for n, o in enumerate(retVal):
                if(scene["__ranking"] > o["__ranking"]):
                    retVal.insert(n, scene)
                    placed = True
                    break
            if(not placed):
                retVal.append(scene)
        else:
            retVal.append(scene)
    return retVal
    
def scene_from_query_fragment(fragment: ScrapedScene):
    scene = populateScene(getClipFromURL(fragment["urls"][0]))
    scene["urls"] = fragment["urls"]
    return scene

def scene_from_fragment(fragment: ScrapedScene):
    result: ScrapedScene = None
    for v in fragment["urls"]:
        if("clips4sale" in v):
            if(not result):
                result = populateScene(getClipFromURL(clean_url(v)))
    return result

scrape_type: TypeAlias = Literal["scene-by-url"] | Literal["scene-by-fragment"] | Literal["scene-by-name"] | Literal["scene-by-query-fragment"]
def do_scrape(type: scrape_type, data, config: Scraper_Conf | None = None):
    if(config):
        set_conf(config)
    match type:
        case "scene-by-url":
            return scene_from_url(data["url"])
        case "scene-by-fragment":
            return scene_from_fragment(data)
        case "scene-by-name":
            return scene_from_name(data["name"])
        case "scene-by-query-fragment":
            return scene_from_query_fragment(data)
        case _:
            log.error(
                f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}"
            )
            sys.exit(1)

if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    # log.debug(args["extra"])
    # log.debug(CONFIG_DICT)
    log.debug(conf_from_extra(args["extra"]))
    # log.debug(format_html("<body> 0 <p> 1 <p> 2 </p> 3 <p> 4 </p> 5 </p> 6 </body>"))

    result = do_scrape(op, args, conf_from_extra(args["extra"]))

    # match op, args:
    #     case "scene-by-url", {"url": url} if url:
    #         result = scene_from_url(url)
    #     case "scene-by-fragment", {"urls": urls} if len(urls):
    #         result = scene_from_fragment(args)
    #         # result = scene_from_url(url, argsToDict(extra))
    #     case "scene-by-name", {"name": name} if name:
    #         result = scene_from_name(name)
    #     case "scene-by-query-fragment", {}:
    #         # log.debug(args)
    #         result = scene_from_query_fragment(args)
    #     # case "scene-by-name", {"name": name, "extra": extra} if name:
    #     #     log.debug(args)
    #     #     studio = extra[0] if len(extra) > 0 else None
    #     #     result = betterC4sSearch(query=name, studioUrl=studio)
    #     case _:
    #         log.error(
    #             f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}"
    #         )
    #         sys.exit(1)

    # log.debug("result: %s" % result)
    print(json.dumps(result))