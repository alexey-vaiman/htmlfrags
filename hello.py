from msg_split import split_message

input = """<strong><p>Paragraph<a href="some href">Anchor text <code>this is code 1</code></a> Now some strong text 1</p>
<i>
<a href="some href 2">Anchor text 2 <code> this is code 2</code>more anc</a> And some i text 1
<a href="some href 3">Anchor text 3 <code> this is code 3</code></a> And some i text 2
</i>
</strong>"""

file = open('tstpages\source.html','r')
content = file.read()

frag_cnt = 0
# for s in split_message(content, 4396):
for s in split_message(content, 4296):
    frag_cnt += 1
    print(f"-- fragment #{frag_cnt}: {len(s)} chars --")
    print(s)
