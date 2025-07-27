from py_common import log
from urllib.parse import urljoin

def string_has_text(x: str | None):
    return x != None and x != "" and not x.isspace()

def join_url(*parts: tuple[str]):
    return urljoin(parts[0], "/".join(part.strip("/") for part in parts[1:]))