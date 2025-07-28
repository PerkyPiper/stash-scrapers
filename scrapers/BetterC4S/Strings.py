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
    # format = clip["format"] if clip["format"] != "other" else r"(?:flv|mkv|m4v)"
    # format = clip["format"]
    # res = clip["resolution"]

    # Match html tags, HD/SD, and framerate
    pattern = r"<[^>]+>|\b[hs]d\b|\d+ ?fps"

    if(clip["resolution"]):
        # Match screen size (1920x1080) and resolution (1080p, 4k)
        pattern += f"|{clip["screen_size"]}|{clip["resolution"]}"
        if(pattern.endswith("p")):
            # If the resolution ends in a p then that p is optional!
            pattern += "?"

        # In search results, clip format string can only be one of the following:
        #   mp4, wmv, mov, mpg, avi, <POSSIBLY MORE>, other
        # On the clip page, the actual correct format will always be available for matching!
        format = clip["format"]
        if(format == "other"):
            # We don't ever want to strip the word "other", so match some other commonish formats instead!
            format = r"(?:m(?:[4k]v|2ts?)|f[l4]v|3g[2p]|rmvb)"

        pattern += f"|\\b{format}\\b"
    else:
        # THIS IS AN AUDIO FILE!!!
        # TODO: Implement me?
        pass

    # Yeet all the matched metadata!
    title = re.sub(pattern, "", clip["title"], re.IGNORECASE)
    # Do config replacements
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