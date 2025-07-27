import json

from typing import TypedDict, Callable, Any, TypeAlias
from py_common import log
from py_common.config import get_config

ConfigParser: TypeAlias = Callable[[Any, Any | None, bool], bool]
_configParsers: dict[str, ConfigParser] = {}
_confString = ""
def _addConfigField(name: str, default, comment: str, /, ini_only = True, multi_value = False, is_list = False, custom_parser: ConfigParser | None = None):
    global _confString
    _confString += f"""
                        {comment if comment.startswith("#") else "# " + comment}
                        {name} = {json.dumps(default)}
                    """
    
    # if(custom_parser):
    #     _parsers[name] = custom_parser
    # else:
    def fieldParser(val, existing: Any | None, from_ini: bool):
        nonlocal name, ini_only, multi_value, is_list, custom_parser

        if(ini_only and not from_ini):
            log.warning(f"Setting config field '{name}' is not allowed outside of the config.ini!")
            return existing
        else:
            if(isinstance(val, str)):
                try:
                    val = json.loads(val)
                except json.JSONDecodeError:
                    pass

            if(custom_parser):
                val = custom_parser(val, existing, from_ini)

            if(is_list and not isinstance(val, list)):
                val = [val]

            if(multi_value and not from_ini):
                val = [val]

            if(existing == None):
                return val
            elif(multi_value):
                return existing + val
    _configParsers[name] = fieldParser

class ScraperConfigParams(TypedDict):
    title_regex: list[str]
    desc_regex: list[str]
    studio_link: str

class ScraperConfig(ScraperConfigParams):
    use_proxy: bool
    multi_page: bool
    include_duration: bool
    do_extra_sort: bool
    join_results: bool
    remove_banned_words: bool
    use_gif_thumbs: bool
    user_agent: str

_addConfigField("title_regex", [], """# A JSON encoded list of regex replacements to apply to clip titles!
                # This should be used to remove metadata from titles so identical clips can be merged!
                # Example: [["Replace me", "With me"], ["Delete me!"]]
                # Use a double \\ instead of just one for escape sequences! Example: ["\\\\d+", "This used to be a number!"]""",  ini_only=False, is_list=True, multi_value=True)
_addConfigField("desc_regex", [], "# Same as title_regex, but for the description! This DOES NOT affect clip merging!", ini_only=False, is_list=True, multi_value=True)
# _addConfigField("studio_link", None, "# Technically you can use this, but it's meant for dependant scrapers, not the config file!", ini_only=False)

_addConfigField("use_proxy", True, "# Sacrifice a bit of speed in order to hide your scraping ways!")
# _addConfigField("multi_page", False, "# Scrapes an additional page each time you search with the same prompt (until the cache expires in 10 minutes)")
_addConfigField("include_duration", True, "# When true, the clip duration will be included in search result titles (not the final scene)!")
_addConfigField("do_extra_sort", True, "# Sorts the search results again after getting them! *May* help make results more relevant!")
_addConfigField("join_results", True, "# Joins search results with matching names (after replacements)! All URLs are included in final scene!")
_addConfigField("remove_banned_words", True, "# Removes banned words (see banned_words.txt) from search queries automatically! If you turn this off, queries with banned words will just error out!")
_addConfigField("use_gif_thumbs", False, """# If true, gif previews will be used as the thumbnail instead of still images!
                                            # WARNING: This will slow down the scraper! Stash browsing performance also takes a hit with gif thumbnails!""")
_addConfigField("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "# This is the user-agent string to use while scraping! You probably don't need to change this!")

BC4S_CONFIG = get_config(_confString)
CONFIG_DICT: ScraperConfig = BC4S_CONFIG.config_dict

# for k,v in CONFIG_DICT.items():
#     if(k in _configParsers):
#         CONFIG_DICT[k] = _configParsers[k](v, None, True)

def _applyConf(params: ScraperConfigParams, from_ini):
    for k,v in params.items():
        if(k in _configParsers):
            CONFIG_DICT[k] = _configParsers[k](v, None if from_ini else CONFIG_DICT.get(k), from_ini)
        else:
            CONFIG_DICT[k] = v
_applyConf(CONFIG_DICT, True)

def _extraToDict(extra: list[str]):
    retVal = {}
    for v in extra:
        v = v.split("::")
        key = v[0]
        val = True

        if(len(v) > 1):
            val = v[1]
        retVal[key] = val
    return retVal

def apply_params(params: ScraperConfigParams | list[str]):
    if(isinstance(params, list)):
        params = _extraToDict(params)
    _applyConf(params, False)