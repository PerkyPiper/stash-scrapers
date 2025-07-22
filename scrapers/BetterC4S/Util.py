import re
import requests

# MISSING_SLUG = r"https:\/\/(?:www\.)clips4sale.com\/studio\/\d+\/\d+"
# VALID_PATTERN = MISSING_SLUG + r"\/[^\/]+\/?"

# def request_slug(url: str):
#     r = requests.get(url)
#     return r.url

# def fix_faulty(url: str):
#     if(re.match(MISSING_SLUG, url)):
#         return request_slug
#     # else:


# def check_url(url: str):
#     if(re.match(VALID_PATTERN, url)):
#         return url
#     else:
#         return fix_faulty(url)

DESIRED_PATTERN = r"https:\/\/(?:www\.)?clips4sale.com\/studio\/\d+\/\d+\/[^\/]+\/?$"

def try_redirect(url: str):
    return requests.get(url).url

def build_link(studio_id: str, clip_id: str, clip_slug: str | None = None):
    url = f"https://www.clips4sale.com/studio/{studio_id}/{clip_id}"

    if(clip_slug):
        return f"/{clip_slug}"
    else:
        return try_redirect(url)

def fix_faulty(url: str):
    r = try_redirect(url)
    if(re.match(DESIRED_PATTERN, r)):
        return r
    
    # https://www.clips4sale.com/work/store/index.php?storeid={storeid}&buy={clipid}&checkout=2
    url = re.sub(r".+\/work.+storeid=(\d+).+buy=(\d+).+", r"https://www.clips4sale.com/studio/\1/\2", url)

    # https://clips4sale.com/list/en/checkout/studio/{studioid}/clip/{clipid}
    url = re.sub(r".+\/list.+checkout\/studio\/(\d+)\/clip\/(\d+).*", r"https://www.clips4sale.com/studio/\1/\2", url)

    return try_redirect(url)

def clean_url(url: str):
    url = url.replace("cidd53a83bfce5aed4137490f7d3a", "")
    if(re.match(DESIRED_PATTERN, url)):
        return url
    else:
        return fix_faulty(url)