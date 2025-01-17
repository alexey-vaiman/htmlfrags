from html.parser import HTMLParser
from dataclasses import dataclass, field
from typing import List
import functools
from typing import Generator

@dataclass
class Pos:
    pos: int # позиция в cleantxt
    width: int # возможная вариация — текстовую часть ноды можно бить в любом месте
    open_tags: List[str]
    on_open: bool
    open_tags_len: int = field(init=False)
    close_tags_len: int = field(init=False)
    def __post_init__(self):
        self.open_tags_len = \
            functools.reduce(lambda x, y: x + len(y) + 2, self.open_tags, 0) if len(self.open_tags) > 0 else 0
        self.close_tags_len = \
            functools.reduce(lambda x, y: x + len(y) + 1 + 2, self.open_tags, 0) if len(self.open_tags) > 0 else 0

class FragParser(HTMLParser):
    acc: List[Pos]
    cleantxt: str # пересобираем сюда весь текст сюда только из тегов, атрибутов и текста (тогда, например, лишние пробелы в теге уйдут)
    stack: List[str] # стек тегов, нужен, чтобы знать, где мы находимся
    pos: int # текущая позиция в cleantxt
    can_fragment: List[bool]

    def __init__(self):
        super().__init__()
        self.blockElements = ["p", "b", "strong", "i", "ul", "ol", "div", "span"]
        self.pos = 0
        self.can_fragment = [True]
        self.stack = ['']
        self.stacklen = 0
        self.acc = [Pos(0, 0, self.stack.copy(), True)]
        self.veryfirsttag = ''
        self.cleantxt = ''
        self.i_was_at_top = False
        self.has_no_root = False
        self.max_unbreakable_data_len = -1
        self.reset()
 
    #Defining what the methods should output when called by HTMLParser.
    def handle_starttag(self, tag, attrs):
        # print("Start tag: ", tag)

        # if not self.has_no_root and self.i_was_at_top:
        #     self.has_no_root = True
        self.has_no_root = self.has_no_root or self.i_was_at_top

        if self.veryfirsttag == '':
            self.veryfirsttag = tag

        can_fragment = tag in self.blockElements and \
            (len(self.can_fragment) == 0 or self.can_fragment[-1])
        
        self.stack.append(tag) # добавляем тег к стеку тегов

        # заполняем чистый текст
        taglen = len(tag)
        cleantxt = '<' + tag
        self.stacklen += taglen
        totlen = taglen + 2 # учитываем скобки
        for a in attrs:
            # print("Attributes of the tag: ", a)
            totlen += 1 + len(a[0]) + 1 + 1 + len(a[1]) + 1 # !!! учесть енкоднутые символы
            #         _   attrname    =   "   attrval     "
            # пробел перед атрибутом, кавычки имени атрибута, имя атрибута, знак равно, кавычки значения атрибута, значение атрибута
            cleantxt += ' ' + a[0] + '="' + a[1] + '"'
        cleantxt += '>'
        self.cleantxt += cleantxt
        self.pos += totlen
        if can_fragment:
            open_tags = self.stack.copy()[1:]
            self.acc.append(Pos( self.pos, 0, open_tags, True))
            # print("added position: ", str(self.pos) + " {" + self.cleantxt + "}")
            # self.acc.append(Pos( self.pos, 0, self.stack.copy()[1:] ))
            # open_tags_len = \
            #     functools.reduce(lambda x, y: x + len(y), open_tags, len(open_tags[0])) if len(open_tags) > 0 else 0
            # close_tags_len = functools.reduce(lambda x, y: x + len(y) + 1, open_tags, len(open_tags[0]) + 1)
            diff = self.acc[-1].open_tags_len + self.pos - (self.acc[-2].pos + self.acc[-2].width) + self.acc[-1].close_tags_len
            if self.max_unbreakable_data_len < diff:
                self.max_unbreakable_data_len = diff
        self.can_fragment.append(can_fragment)
 
    def handle_data(self, data):
        # print("Data: '" + data + "'")
        self.pos += len(data)
        self.cleantxt += data
        if len(self.can_fragment) == 0 or self.can_fragment[-1]: # если можно разбивать, то весь этот текст надо учесть в последней записи разбиения
            self.acc[-1].width = len(data)
 
    def handle_endtag(self, tag):
        # print("End tag: ", tag)
        endtag = self.stack.pop()
        self.cleantxt += "</" + tag + ">"
        taglen = len(tag)
        totlen = taglen + 2 + 1 # учитываем скобки и косую черту
        self.pos += totlen
        # if len(self.stack) == 0 and endtag != self.veryfirsttag:
        #     print("NO TOP TAG!!!")

        could_fragment = self.can_fragment.pop()
        can_fragment = len(self.can_fragment) == 0 or self.can_fragment[-1]
        # if not could_fragment and can_fragment: # если нельзя было и опять стало можно, то добавим точку разбиения
        if can_fragment: # если нельзя было и опять стало можно, то добавим точку разбиения
            open_tags = self.stack.copy()[1:]
            self.acc.append(Pos( self.pos, 0, open_tags, False))
            # print("added position: ", str(self.pos) + " {" + self.cleantxt + "}")
            # print("added position: ", ">>" + self.cleantxt + "<<")
            # open_tags_len = \
            #     functools.reduce(lambda x, y: x + len(y), open_tags, len(open_tags[0])) if len(open_tags) > 0 else 0
            # close_tags_len = functools.reduce(lambda x, y: x + len(y) + 1, open_tags, len(open_tags[0]) + 1)
            # diff = self.acc[-1].open_tags_len + self.pos - (self.acc[-2].pos + self.acc[-2].width)
            diff = self.acc[-1].open_tags_len + self.pos - (self.acc[-2].pos + self.acc[-2].width) + self.acc[-1].close_tags_len
            if self.max_unbreakable_data_len < diff:
                self.max_unbreakable_data_len = diff

        if len(self.can_fragment) == 1:
            self.i_was_at_top = True

MAX_LEN = 4096

def split_message(source: str, max_len=MAX_LEN) -> Generator[str]:
    """Splits the original message (`source`) into fragments of the specified length(`max_len`)."""
    fragParser = FragParser()
    fragParser.feed(source)
    
    cur_len = 0
    cur_pos = 0
    cur_start = 0
    prev_frag = None
    frag_cnt = 0
    cur_frag = None
    # print('clean text:')
    # print(fragParser.cleantxt)

    # print('\nfragments:')
    # первый 
    for frag in fragParser.acc:
        cur_span = frag.pos - cur_start + frag.close_tags_len + cur_len
        if cur_span > max_len: # CHECK!!! не может быть первая проверка, иначе исключение (проверкить prev != None)
            # print('frag: ', fragParser.cleantxt[cur_start:prev.pos + 1], prev.close_tags_len)
            # print('open: ', prev.open_tags_len)
            frag_cnt += 1
            close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, prev_frag.open_tags, '')

            open_tags = ''
            # if cur_frag != None: # CHECK!!! вообще-то он тут обязан быть
            if cur_frag == None:
                cur_frag = prev_frag
                
            open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '')
            
            yield f"-- fragment #{frag_cnt}: {prev_frag.pos + prev_frag.width - cur_start + len(close_tags) + len(open_tags)} chars --"
            # print()

            # if cur_frag != None: # CHECK!!! вообще-то он тут обязан быть
            fragment_text = open_tags
            # print(open_tags, end='')

            # print(fragParser.cleantxt[cur_start:prev_frag.pos + prev_frag.width] + close_tags)
            fragment_text += fragParser.cleantxt[cur_start:prev_frag.pos + prev_frag.width] + close_tags
            yield fragment_text
            # print('open: ', functools.reduce(lambda x, y: x + '<' + y + '>', prev.open_tags, ''))
            cur_start = prev_frag.pos + prev_frag.width
            cur_len = prev_frag.open_tags_len
            cur_span = frag.pos - (prev_frag.pos + prev_frag.width) + frag.close_tags_len + prev_frag.open_tags_len
            cur_frag = prev_frag
            # cur_span = prev.pos - cur_start + prev.close_tags_len + cur_len
            # CHECK!!! добавить проверку на следующее условие, если нет, то исключение
        if cur_span <= max_len and cur_span + frag.width > max_len:
            frag_cnt += 1
            open_tags = ''
            if cur_frag != None:
                open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '')
            close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, frag.open_tags, '')

            extra = max_len - cur_span 
            yield f"-- fragment #{frag_cnt}: {frag.pos + extra - cur_start + len(close_tags) + len(open_tags)} chars --"
            
            fragment_text = ''
            if cur_frag != None:
                # print(open_tags, end='')
                fragment_text = open_tags

            fragment_text += fragParser.cleantxt[cur_start:frag.pos + extra] + close_tags
            yield fragment_text

            cur_frag = frag
            # print('open: ', functools.reduce(lambda x, y: x + '<' + y + '>', frag.open_tags, ''))
            cur_start = frag.pos + extra
            cur_len = frag.open_tags_len
        # print("'" + fragParser.cleantxt[frag.pos - 5:frag.pos + 5] + "'")
        prev_frag = frag

    frag_cnt += 1
    # frag = fragParser.acc[-1]
    open_tags = ''
    if cur_frag != None:
        open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '')
    close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, cur_frag.open_tags, '')

    # extra = max_len - cur_span 

    # yield f"-- fragment #{frag_cnt}: {frag.pos - cur_start + len(close_tags) + len(open_tags)} chars --"

    fragment_text = ''
    if cur_frag != None:
        fragment_text += open_tags

    fragment_text += fragParser.cleantxt[cur_start:] + close_tags
        # + functools.reduce(lambda x, y: '</' + y + '>' + x, frag.open_tags, '')
    yield f"-- fragment #{frag_cnt}: {len(fragment_text)} chars --"
    yield fragment_text
