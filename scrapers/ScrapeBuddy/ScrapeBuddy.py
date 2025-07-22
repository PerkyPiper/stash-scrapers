import html
import sys

sys.path.append("../")

from py_common.deps import ensure_requirements
from py_common import log
from datetime import datetime
from typing import TypedDict
# from functools import reduce

ensure_requirements("lxml", "regex", "fp:free-proxy")

from fp.fp import FreeProxy
from lxml import html as lhtml
import regex as re


IGNORE_TAGS = {"video", "select", "audio", "img", "figure", "form", "map", "textarea", "pre", "input", "button"}
DOUBLE_BREAK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "blockquote", "dl", "section"}
SINGLE_BREAK = {"div", "tr", "dt", "dd", "li"}
INDENT_TAGS = {"dd", "li", "blockquote"}

def string_has_text(x: str | None):
    return x != None and x != "" and not x.isspace()

def regex_breaks(x: str | None, count: int, end: bool = False):
    breaks = "\n" * count

    if(x):
        regex = r"(?: *\n *){0," + str(count) + r"}"
        return re.sub(f"{regex}$" if end else f"^{regex}", "\n" * count, x, 1)
    else:
        return breaks

def add_breaks(element: lhtml.HtmlElement, count: int):
    for v in element.iterancestors():
        if(string_has_text(v.text)):
            v.text = regex_breaks(v.text, count, True)
            break

    t = element
    while(not string_has_text(t.tail) and t.getnext() == None and t.tag != "body"):
        t = t.getparent()
    t.tail = regex_breaks(t.tail, count)

def format_element(element: lhtml.HtmlElement):
    tag = ""
    try:
        tag = element.tag.lower()
    except:
        pass
    if(tag in IGNORE_TAGS):
        element.drop_tree()
    else:
        parent: lhtml.HtmlElement = element.getparent()
        if(not element.text):
            element.text = ""

        for v in element.iterchildren():
            format_element(v)

        if(element.tag != "body"):
            # Add numbers to ordered lists and hyphens to unordered lists
            if(tag == "li"):
                if(parent.tag == "ol"):
                    item_num = int(parent.get("item_num")) + 1 if parent.get("item_num") else 1
                    element.text = f"{item_num}. {element.text}"
                    parent.set("item_num", str(item_num))
                else:
                    element.text = f"- {element.text}"
            # Indent certain tags
            if(tag in INDENT_TAGS):
                element.text = f"	{element.text.strip(" ")}"

            if(tag == "q"):
                element.text = f'"{element.text}"'

            # NOTE: Re-implement later, with a config option?
            # if(tag == "h1"):
            #     element.text += "\n" + ("=" * len(element.text.strip()))
            # elif(tag == "h2"):
            #     element.text += "\n" + ("-" * len(element.text.strip()))
            
            # Handle tags like <p> and <h#> that add 1 full line between them and their neighbours (with default styling)
            if(tag in DOUBLE_BREAK and string_has_text(element.text)):
                add_breaks(element, 2)
            # Handle tags like <div> and <li> which 
            elif(tag in SINGLE_BREAK and string_has_text(element.text)):
                add_breaks(element, 1)
            elif(tag == "br"):
                parent.text += "<br>"

            element.drop_tag()
        
def format_html(doc: str):
    doc = re.sub(r"[\r\n]", "", doc)
    doc = html.unescape(doc)
    doc: lhtml.HtmlElement = lhtml.document_fromstring(doc).xpath("//body")[0]
    format_element(doc)
    doc = re.sub(r"<br>(?: *\n *)?", "\n", doc.text_content())
    doc = re.sub(r"(?<=\n|^) +| +(?=\n|$)", "", doc)
    return re.sub(r" {2,}", " ", doc)


def parse_date(date_string: str, format: str = "%m/%d/%y %I:%M %p") -> str:
    try:
        return datetime.strftime(datetime.strptime(date_string, format), "%Y-%m-%d")
    except Exception as e:
        log.error(e)
        return date_string

def get_proxies() -> dict:
    proxy = FreeProxy(rand=True).get()
    log.debug("proxy: %s" % proxy)
    return { 'http': proxy } if proxy.startswith('http:') else { 'https': proxy }