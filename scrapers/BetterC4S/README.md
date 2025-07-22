# Piper's Better Clips4Sale Scraper
The aim for this scraper is to provide a number of features that make the experience of scraping from clips4sale less of a chore!

## Features:
- Uses REST API routes to access the clip JSON directly, rather than scraping the DOM!
- Automatically removes banned search terms from queries
- Merges clips with multiple resolutions/formats in search results!
  - All of the merged URLs are added to the resulting scene!
- Allows for per-studio scraping behaviour through dependant scrapers (See below)
- Includes clip duration in search result titles, allowing for much faster identification!
- Most major features are toggleable in the config file!

## Customizing Behaviour
You can configure the scraping behaviour of BetterC4S by editing the provided fields in the config.ini (if it doesn't exist, run the scraper once then check again)!

You can also specify per-studio behaviour, which allows you to use the studio's specific search page, rather than the main clips4sale one!

Here's how you do it:
### YAML
```
# requires: BetterC4S
name: "<Your scraper name>"

<SCRAPER_ACTION>: # sceneByName, sceneByQueryFragment, etc.
  action: script
  script:
      - python
      - ./BetterC4S/BetterC4S.py                              # Path may need to be altered based on location
      - studio_link::/studio/<STUDIO_ID>/<STUDIO_SLUG>/       # The studio store link, minus the https://clips4sale.com part USED FOR STUDIO SEARCH!
      - title_regex::<REGEX_TO_DELETE>                        # Replace this match with nothing!
      - title_regex::<ANOTHER_TO_DELETE>                      # You can put as many of these as you want, they will each run in order!
      - title_regex::["<REGEX_TO_REPLACE>", "<REPLACEMENT>"]  # Replace <REGEX_TO_REPLACE> with <REPLACEMENT>
      - desc_regex::<REGEX_TO_DELETE>                         # Same as title_regex, but for the description!
      - <SCRAPER_OPERATION>                                   # scene-by-name, scene-by-query-fragment, etc.
```

### Python
```
from BetterC4S.BetterC4S import do_scrape

<<SCRIPT ENTRY LOGIC>>
result = do_scrape(
        <SCRAPER_OPERATION>, # scene-by-name, scene-by-query-fragment, etc.
        args, # Arguments object, dependant on operation
        {
            "studio_link": <STUDIO_LINK>,
            "title_regex": [[r"<REGEX_TO_DELETE>"], [r"<ANOTHER_TO_DELETE>"], [r"<REGEX_TO_REPLACE>", r"<REPLACEMENT>"]],
            "desc_regex": [[r"REGEX_TO_DELETE"]]
        })
```

## Installing
Refer to https://github.com/PerkyPiper/stash-scrapers/blob/main/README.md
