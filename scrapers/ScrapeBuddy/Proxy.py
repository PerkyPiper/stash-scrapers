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