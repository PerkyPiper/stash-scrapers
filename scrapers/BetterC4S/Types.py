from typing import TypedDict
from enum import Enum

class C4S_Keyword(TypedDict):
    keyword: str
    link: str

class C4S_Performer(TypedDict):
    id: int
    stage_name: str
    created_at: None | str

class C4S_Studio(TypedDict):
    id: int
    name: str
    slug: str
    avatar: str
    link: str

class C4S_Json(TypedDict):
    """ NOTE: These types are far from exhaustive!!! """
    clipId: str
    title: str
    duration: int
    """ Duration in MINUTES """
    previewLink: str
    """ Static .jpg thumbnail, seems to default to extra large size! """
    studioTitle: str
    studioLink: str
    """ Relative to c4s site root """
    dateDisplay: str
    """ M/D/Y h:mm PM/AM """
    link: str
    """ Relative to c4s site root """
    format: str
    category_name: str
    keyword_links: list[C4S_Keyword]
    """ Clips4Sale's tag equivalent! """
    performers: None | list[C4S_Performer]
    """ 
        Contrary to comments in the existing Clips4Sale.yml, the site DOES actually have a dedicated performers field!\n
        It seems to mostly only show up in search results for some reason, but some clip pages do actually have it too!
    """
    description: str
    """ The description html, exactly how it was written by the creator! HTML formatting mistakes and all! """
    description_sanitized: str
    """ 
        The description html after it was sanitized by c4s. Unclear what all this involves, but this much is clear:\n
        - Removes most tags (<p>, <br> remain)
        - Replaces \\n with <br>
        - (Suspected, but not confirmed) Replaces sequences of multiple line breaks with just one
    """
    gifPreviewUrl: str
    resolution: str
    size: int
    """ File size in MB! """
    studio: C4S_Studio
    # urls: list[str] | None = None
    # """ IMPORTANT: This fields is just here for clip merging! It doesn't exist in the c4s schema! """