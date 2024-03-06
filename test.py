import requests

key = "AIzaSyCIqMnn6BbcKJw2Lbn37xqCiHYKtSFR8Cw"
cx = "645b44f25361d4b03"
q = "RAG是什么"
res = requests.get(f"https://www.googleapis.com/customsearch/v1?key={key}&q={q}&cx={cx}&start={10}&num={10}")
print(res.text)


class A:
    name = "A"


class B:
    name = "B"


tmp = A
tmp = B
