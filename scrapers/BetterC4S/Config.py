import json
import pathlib

from typing import TypedDict, TypeAlias
from py_common.config import get_config
from py_common import log

BANNED_WORDS: set[str] = set()
with open(f"{pathlib.Path(__file__).parent}/banned_words.txt", "r") as wordFile:
    for word in wordFile:
        if(not word.startswith("#")):
            BANNED_WORDS.add(word.strip())

class SchemaField[T](TypedDict):
    default: T = None
    comment: str
    multi = False
    ini_only = True
    is_list = False

Replacer: TypeAlias = list[str, str]

class Scraper_Extra(TypedDict):
    title_regex: list[Replacer]
    desc_regex: list[Replacer]
    use_gif_for_thumb: bool
    user_agent: str

class Scraper_Conf(Scraper_Extra):
    # banned_words: list[str]
    skip_default_title_replacer: bool
    join_search_results: bool
    do_extra_sort: bool
    include_duration: bool
    multi_page: bool
    use_proxy: bool
    
CONFIG_SCHEMA: dict[str, SchemaField] = {}
CONFIG_SCHEMA["skip_default_title_replacer"] = SchemaField[bool](
    default=False,
    comment="""# The default title replacer does the following (in order):
               # - Strips HTML tags
               # - Removes references to the clip's file extension or resolution
               # - Removes empty bracket pairs ([], (), {}, <>) that may be leftover from the previous step
               # - Replaces sequences of multiple spaces with just one
               # Generally speaking, you shouldn't need to disable it! Custom title_replacers are run immediately after the default!"""
)
CONFIG_SCHEMA["join_search_results"] = SchemaField[bool](
    default=True,
    comment="# After running title replacements, clips with the same name will be merged into one to reduce search results! All merged urls are included in the final result!"
)
CONFIG_SCHEMA["do_extra_sort"] = SchemaField[bool](
    default=True, ini_only=False,
    comment="# Attempts to help make the order of search results more relevant!"
)
CONFIG_SCHEMA["title_regex"] = SchemaField[Replacer](
    default=[], ini_only=False, is_list=True, multi=True,
    comment="""# This is a list of regex replacements for titles, format is [["REGEX_HERE", "OPTIONAL_REPLACEMENT_HERE"]]
               # NOTE: Escaped sequences (\\d, \\1, etc.) will require a double backslash (\\\\d, \\\\1, etc.)"""
)
CONFIG_SCHEMA["desc_regex"] = SchemaField[Replacer](
    default=[], ini_only=False, is_list=True, multi=True,
    comment="# Same as above, but for the video description!"
)
CONFIG_SCHEMA["include_duration"] = SchemaField[bool](
    default=True, comment="# Includes the clip duration in the search results' titles!"
)
CONFIG_SCHEMA["use_gif_for_thumb"] = SchemaField[bool](
    default=False, comment="""# If the clip has a custom gif preview, use it as the cover image instead of the default static preview!
                              # NOTE: having a lot of these can negatively impact stash browsing performance!""", ini_only=False
)
CONFIG_SCHEMA["multi_page"] = SchemaField[bool](
    default=False, comment="""# By default, you will only ever get one page of results back, this is usually, but not always enough!
                              # If you enable this, clicking the search button multiple times will load 1 more page worth of results each time.
                              # Pagination is reset after 10 minutes when the cache expires! Extra sorting is highly recommended!"""
)
CONFIG_SCHEMA["user_agent"] = SchemaField[str](
    default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    comment="# The user-agent string to use when scraping! You probably don't have to change this!", ini_only=False
)
CONFIG_SCHEMA["use_proxy"] = SchemaField[bool](
    default=True, comment="# Sacrifice a little speed to make your scraping ways a little less obvious!"
)

conf_string = ""
for v in CONFIG_SCHEMA:
    conf_string +=f"""
                        {CONFIG_SCHEMA[v]["comment"]}
                        {v} = {json.dumps(CONFIG_SCHEMA[v]['default'])}
                   """

CONF = get_config(conf_string)
CONFIG_DICT: Scraper_Conf = CONF.config_dict

for k,v in CONFIG_DICT.items():
    if(isinstance(v, str)):
        try:
            CONFIG_DICT[k] = json.loads(v)
        except json.JSONDecodeError:
            CONFIG_DICT[k] = v
        

def parse_extra_value(key: str, val):
    if(not CONFIG_SCHEMA[key].get("ini_only")):
        if(isinstance(val, str)):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                pass
                # log.debug(f"{val} not converting from json, reason: {e}")

            if(CONFIG_SCHEMA[key].get("is_list") and not isinstance(val, list)):
                val = [val]

            if(CONFIG_SCHEMA[key].get("multi")):
                val = [val]
        return val
    else:
        log.warning(f"The {key} field can only be used in the config.ini file!")

def set_conf(conf: Scraper_Extra):
    for i,v in conf.items():
        if i in CONFIG_SCHEMA:
            multi = CONFIG_SCHEMA[i].get("multi")

            if(i in CONFIG_DICT and CONFIG_DICT[i] != None):
                if(multi):
                    CONFIG_DICT[i] += v
                else:
                    CONFIG_DICT[i] = v
                    # log.warning(f"Attempted to set {i}, but it's already been set and doesn't allow multiple values!")
            else:
                CONFIG_DICT[i] = [v] if multi else v
        else:
            CONFIG_DICT[i] = v
    return CONFIG_DICT
        

def conf_from_extra(extra: list[str]):
    retVal: Scraper_Extra = {}
    for v in extra:
        v = v.split("::")
        val = True

        if(len(v) > 1):
            val = v[1]
            if(v[0] in CONFIG_SCHEMA):
                val = parse_extra_value(v[0], val)

        retVal[v[0]] = val
    return retVal