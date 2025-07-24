import html
import sys
import re

sys.path.append("../")

from py_common.deps import ensure_requirements
from py_common import log
from datetime import datetime
# from functools import reduce

ensure_requirements("lxml", "fp:free-proxy")

from fp.fp import FreeProxy
from lxml import html as lhtml
from lxml.html import HtmlElement

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

# These tags, and all of their content (including child elements) will be removed from the output!
IGNORE_TAGS = {"video", "select", "audio", "img", "figure", "form", "map", "textarea", "pre", "input", "button"}
# These tags have a 1 linewidth margin on the top and bottom! This is simulated with a double \n
DOUBLE_BREAK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "blockquote", "dl", "section"}
# These tags are rendered on a seperate line from their closest neighbours! This is simulated with a single \n
SINGLE_BREAK = {"div", "tr", "dt", "dd", "li"}
# These tags render indented! This is simulated with a "	" (TAB)
INDENT_TAGS = {"dd", "li", "blockquote"}

def string_has_text(x: str | None):
    return x != None and x != "" and not x.isspace()

def merge_breaks(x: str, count: int):
    if(count):
        breaks = "\n" * count
        if(string_has_text(x)):
            # Matches 0-<count> instances of linebreaks at the end of the string, then replaces with <count> linebreaks
            # This prevents adding extra linebreaks from being added when they are already present from the previous element!
            return re.sub(r"(?: *\n *){0," + str(count) + r"}$", breaks, x, 1)
        else:
            return breaks
    else:
        return x
    
class FormattingElement(HtmlElement):
    pre_breaks: int | None
    post_breaks: int | None
    list_index: int | None

def set_breaks(element: FormattingElement, count: int):
    # Set our pre_breaks and post_breaks ONLY IF a child hasn't already set them to a value equal/higher
    if(count > element.pre_breaks):
        element.pre_breaks = count
    if(count > element.post_breaks):
        element.post_breaks = count
    
def format_element(element: FormattingElement | HtmlElement, parent: FormattingElement | HtmlElement | None = None):
    try:
        # HTML is case-insensitive, so this could technically be capitalized otherwise!
        tag = element.tag.lower()

        if(tag in IGNORE_TAGS):
            # IGNORED! Yeet this element and don't bother iterating children!
            element.drop_tree()
        else:
            if(tag == "ol"):
                # This is an ordered list! This lets the child list items know!
                element.list_index = 1
            if(element.text == None):
                element.text = ""

            # Defaults to no surrounding breaks!
            element.pre_breaks = element.post_breaks = 0
            for v in element:
                format_element(v, element)

            if(tag != "body"):
                if(tag == "li"):
                    if(hasattr(parent, "list_index")):
                        # Number our ordered lists!
                        element.text = f"{parent.list_index}. {element.text}"
                        parent.list_index += 1
                    else:
                        # Hyphen our unordered lists!
                        # TODO: Allow different characters to be used instead of -?
                        element.text = f"- {element.text}"
                elif(tag == "q"):
                    # Small quotes should have quotation marks!
                    element.text = f'"{element.text}"'
                elif(tag == "br"):
                    # If we just add a \n then it can merge with the breaks of subsequent breaking tags!
                    # That is actually *almost* right, but doesn't match certain HTML scenarios properly!
                    # So we'll use this later to substitute with our desired br behaviour!
                    parent.text += "<br>"

                if(tag in INDENT_TAGS):
                    # Indent tags that should be indented!
                    element.text = f"	{element.text.strip()}"

                # Add breaks if needed!
                if(tag in DOUBLE_BREAK):
                    set_breaks(element, 2)
                elif(tag in SINGLE_BREAK):
                    set_breaks(element, 1)

                if(element.pre_breaks):
                    if(string_has_text(parent.text)):
                        # Add the pre-breaks, optionally replacing ones that already exist!
                        parent.text = merge_breaks(parent.text, element.pre_breaks)
                    else:
                        # Defer pre-breaks to the parent until there is content
                        parent.pre_breaks = element.pre_breaks
                
                if(element.post_breaks):
                    if(string_has_text(element.tail) or element.getnext() != None):
                        # No need to merge anything, as none of the following content has been processed yet!
                        element.tail = "\n" * element.post_breaks + (element.tail if element.tail else "")
                    else:
                        # Defer post-breaks to the parent until there is content
                        parent.post_breaks = element.post_breaks

                # Merge our formatted element.text and element.tail into parent.text!
                # Note that all of the element's children and previous neighbours have already been dropped by the time this one is!
                element.drop_tag()
    except AttributeError:
        # Element is commented out!
        element.drop_tree()
    
def format_html(doc: str):
    """
        A universal HTML to plain-text formatter! Linebreaks and indentation should match what is seen in the browser with default css!
    """
    # Remove all existing linebreaks, html doesn't care about them anyway!
    doc = doc.replace("\n", "")
    doc = doc.replace("\r", "")
    # Turn html escape characters into their unicode equivalent!
    doc = html.unescape(doc)
    # Format the document's body!
    doc: HtmlElement = lhtml.document_fromstring(doc).find("body")
    format_element(doc)

    out: str = doc.text_content()
    # Handle our <br>s from earlier! We merge with an optional following linebreak to ensure parity with actual HMTL rendering!
    out = re.sub(r"<br>(?: *\n *)?", "\n", out)
    # Remove groups of spaces that are either:
    #   - Directly before/after a linebreak
    #   - Directly preceeding another space
    out = re.sub(r" *([\n ]) *", r"\1", out)
    return out.strip()