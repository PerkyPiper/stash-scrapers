import requests
import base64

from typing import overload
from py_common.deps import ensure_requirements
from py_common import log
from py_common.cache import cache_to_disk

ensure_requirements("fp:free-proxy")
from fp.fp import FreeProxy

_current_proxy: dict | None = None
@cache_to_disk(300)
def get_proxy():
    """ Returns the proxy for this scrape! Assigns one if not already assigned! """
    global _current_proxy
    if(_current_proxy == None):
        log.info("Selecting proxy...")
        proxy = FreeProxy(rand=True).get()
        log.info(f"Selected proxy: {proxy}")
        _current_proxy = {'https': proxy} if "https" in proxy else {'http': proxy}
    return _current_proxy

@overload
def get_data_url(src: requests.Response) -> str: ...
@overload
def get_data_url(src: str) -> str: ...
@overload
def get_data_url(src: str, ses: requests.Session) -> str: ...
def get_data_url(src: str | requests.Response, ses: requests.Session | None = None) -> str:
    """
        Get a base64 data url from a url or response! If a url src and no session are provided, a proxy will be requested and used!\n
        This is used in tandem with proxied scraping to request images through the proxy, rather than letting stash request them without one!
    """
    if(isinstance(src, str)):
        if(ses):
            src = ses.get(src)
        else:
            src = requests.get(src, proxies=get_proxy())
    encoded = base64.b64encode(src.content).decode("utf-8")
    return f"data:{src.headers.get("content-type")};base64,{encoded}"