import sys
sys.path.append("../")

from Parsing import format_html

input = open("./Test.html", "r", encoding="utf-8").read()

# py -m timeit -s "from Test import runTest" "runTest()"
def runTest():
    format_html(input)

with open("./Test.txt", "w", encoding="utf-8") as o:
    o.write(format_html(input))
