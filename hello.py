from msg_split import split_message

the_input = """<strong><p>Paragraph<a href="some href">Anchor text <code>this is code 1</code></a> Now some strong text 1</p>
<i>
<a href="some href 2">Anchor text 2 <code> this is code 2</code>more anc</a> And some i text 1
<a href="some href 3">Anchor text 3 <code> this is code 3</code></a> And some i text 2
</i>
</strong>"""

very_simple_input = """<strong><p>Paragraph<a href="some href">Anchor text <code>this is code 1</code></a> Now</p></strong>"""

input_70 = """<strong><p>Paragraph more padding padding padding more 12</p><i><a href="hrefhrefhref">here is anchor text</a></i></strong>"""

file = open('tstpages\\source.html','r')
content = file.read()

def test_split_message(input, max_len):
    frag_cnt = 0
    result = ''
    print(input)
    print('-----------------------------')
    for s in split_message(input, max_len):
        frag_cnt += 1
        print(f"-- fragment #{frag_cnt}: {len(s)} chars --")
        print(s)
        result += s + '\n'
    print('-----------------------------')
    print(result)

# test_split_message(content, 4396)
test_split_message(content, 4296)
# test_split_message(input, 100)
# test_split_message(very_simple_input, 64)
# test_split_message(very_simple_input, 90)
# test_split_message(very_simple_input, 64)
# test_split_message(input_70, 70)
# test_split_message(input_70, 120)
# test_split_message(input_70, 69)