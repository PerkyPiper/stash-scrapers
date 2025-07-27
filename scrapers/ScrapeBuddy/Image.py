import requests
import base64

from io import BytesIO
from py_common.deps import ensure_requirements
from py_common import log

ensure_requirements("PIL:pillow")
from PIL import Image, ImageFile

def get_img(src: str | requests.Response | ImageFile.ImageFile, proxy: dict | None = None):
    if(isinstance(src, ImageFile.ImageFile)):
        return src
    elif(isinstance(src, str)):
        src = requests.get(src, proxies=proxy)
    
    try:
        return Image.open(BytesIO(src.content))
    except Image.UnidentifiedImageError as e:
        log.warning(f"Failed to find image at {src.url}! Error: {e}")

def img_data_url(img: str | requests.Response | ImageFile.ImageFile, format: str | None = None, proxy: dict | None = None):
    """ 
        Stash can accept data-urls for image fields! This is useful if you can't or don't want to let stash scrape the target URL!\n
        The main case where this is desirable is when you are scraping with a proxy, and want to keep using the proxy for getting the images!
    """
    img = get_img(img, proxy)

    if(img):
        with BytesIO() as buffer:
            if(format == None and img.format != None):
                format = img.format
            
            img.save(buffer, format, save_all=True if format.lower() == "gif" else None)
            data = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            mimetype = img.get_format_mimetype()
            if(mimetype == None):
                mimetype = f"image/{format}"
            
            return f"data:{mimetype};base64,{data}"
    else:
        return img