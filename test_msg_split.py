import unittest
from msg_split import split_message

class TestMsgSplit(unittest.TestCase):
    simple_input = """<strong><p>Paragraph<a href="some href">Anchor text <code>this is code 1</code></a> Now some strong text 1</p>
<i>
<a href="some href 2">Anchor text 2 <code> this is code 2</code>more anc</a> And some i text 1
<a href="some href 3">Anchor text 3 <code> this is code 3</code></a> And some i text 2
</i>
</strong>"""
    def test_simple_1(self):
        result = ''
        for s in split_message(TestMsgSplit.simple_input):
            result += s

        self.assertEqual(result, TestMsgSplit.simple_input, "test_simple_1: Input shorter than max_len")

    def test_simple_2(self):
        very_simple_input = """<strong><p>Paragraph<a href="some href">Anchor text <code>this is code 1</code></a> Now</p></strong>"""
        result = ''
        for s in split_message(very_simple_input, 93):
            result += s + '\n'

        self.assertEqual(result, """<strong><p>Paragraph</p></strong>
<strong><p><a href="some href">Anchor text <code>this is code 1</code></a> Now</p></strong>
""", "test_simple_2 Simple input, max_len = 93")
        
    def test_simple_3(self):
        very_simple_input = """<strong><p>Paragraph<a href="some href">Anchor text <code>this is code 1</code></a> Now</p></strong>"""
        result = ''
        try:
            for s in split_message(very_simple_input, 64):
                result += s + '\n'
        except ValueError:
            self.assertTrue(True, "test_simple_3: max_len (64) is too small, must throw")

    def test_simple_4(self):
        very_simple_input = """<strong><p>Paragraph<a href="some href" someattr="checking 123">Anchor text <code>this is code 1</code></a> Now</p></strong>"""
        result = ''
        for s in split_message(very_simple_input, 116):
            result += s + '\n'

        self.assertEqual(result, """<strong><p>Paragraph</p></strong>
<strong><p><a href="some href" someattr="checking 123">Anchor text <code>this is code 1</code></a> Now</p></strong>
""", "test_simple_4 Simple input, max_len = 116")

if __name__ == '__main__':
    unittest.main()