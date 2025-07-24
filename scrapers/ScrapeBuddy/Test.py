from ScrapeBuddy import format_html

input = open("./Test.html", "r", encoding="utf-8").read()

def runTest():
    format_html(input)

with open("./Test.txt", "w", encoding="utf-8") as o:
    o.write(format_html(input))
