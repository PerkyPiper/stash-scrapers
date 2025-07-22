# Piper's Better Clips4Sale Scraper
This is intended to be a much more capable version of the Clips4Sale scraper!

## Improvements:
- Gets results faster by using REST JSON routes instead of scraping the DOM!
- Automatically removes banned search terms from queries
- Automatically trims metadata from clip titles
    - Merges results that have the same name (after trimming), so that the url for each version of a clip can be included in the resulting fragment!
- Allows for per-studio scraping behaviour through dependant scrapers (See below)

## Customizing Behaviour
You can configure the scraping behaviour of BetterC4S by editing the provided fields in the config.ini (if it doesn't exist, run the scraper once then check again)!

You can also specify per-studio behaviour by creating a dependant scraper, like so:

### YAML
```
# requires: BetterC4S
name: "<Your scraper name>"

<SCRAPER_ACTION>: # sceneByName, sceneByQueryFragment, etc.
  action: script
  script:
      - python
      - ./BetterC4S/BetterC4S.py                              # Path may need to be altered based on location
      - studio_link::/studio/<STUDIO_ID>/<STUDIO_SLUG>/       # The studio store link, minus the https://clips4sale.com part
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
