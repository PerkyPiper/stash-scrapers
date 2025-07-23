from ScrapeBuddy import format_html

with open("./test.html", "r", encoding="utf-8") as f:
    doc = f.read()

    with open("./test.txt", "w", encoding="utf-8") as y:
        y.write(format_html(doc))