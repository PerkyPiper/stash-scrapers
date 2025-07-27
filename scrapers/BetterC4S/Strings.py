import re
import urllib.parse

from py_common import log
from Config import CONFIG_DICT
from Types import C4S_Clip

from ScrapeBuddy.Parsing import format_html

BANNED_WORDS: set[str] = set()
with open("./banned_words.txt", "r") as wordFile:
    for word in wordFile:
        if(not word.startswith("#")):
            BANNED_WORDS.add(word.strip())

def _removeCensored(match: re.Match):
    word = match.group()
    if(word in BANNED_WORDS):
        log.info(f"Removed banned word '{word}' from query!")
        return ""
    else:
        return word
    
def cleanQuery(query: str):
    query = query.lower()
    if(CONFIG_DICT.get("remove_banned_words")):
        query = re.sub(r"\w+", _removeCensored, query)
    # query = urllib.parse.quote(query)
    query = re.sub(r" {2,}", "", query)
    return query.strip()

def _paramReplacement(x: str, replacers: list[list[str]] | None = None):
    if(replacers):
        for v in replacers:
            x = re.sub(v[0], v[1] if len(v) > 1 else "", x)
    return x

def cleanTitle(clip: C4S_Clip):
    res = f"{clip["resolution"]}?" if clip["resolution"] and clip["resolution"].endswith("p") else clip["resolution"]
    # Remove things like: <em></em>, 1920x1080, 1080p?, MP4, HD/SD, 60 ?fps
    title = re.sub(f"<[^>]+>|{clip["screen_size"]}|{res}|\\b{clip["format"]}\\b|\\b[hs]d\\b|\\d+ ?fps", "", clip["title"], flags=re.IGNORECASE)
    # Do configured replacements
    title = _paramReplacement(title, CONFIG_DICT.get("title_regex"))
    # Remove empty bracket pairs, strip seperator characters
    title = re.sub(r"[\[\(\{\<]\s*[\]\)\}\>]", "", title).strip(" -|")
    # Normalize spaces
    title = re.sub(r" {2,}", " ", title)
    return title

def cleanDesc(clip: C4S_Clip):
    # Parse the RAW, unsanitized description! This contains the actual original html entered by the creator, rather than the nerfed version displayed on the site!
    # My experience is this gets better results, but could technically be considered deviating from the exact on-site description!
    # It seems like this is often just html copied from the creator's own site, however, which is arguably going to be more "accurate"
    desc = format_html(clip["description"])
    desc = _paramReplacement(desc, CONFIG_DICT.get("desc_regex"))
    return desc.strip()

def getDurationString(duration: int):
    retVal = f"{duration % 60}min"
    if(duration >= 60):
        retVal = f"{duration // 60}hr {retVal}"
    return retVal