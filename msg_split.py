from html.parser import HTMLParser
from dataclasses import dataclass, field
from typing import List
import functools
from typing import Generator

ERROR_CITATION_LENGTH = 25 # количество символов входной строки, выводимых при цитировании в тексте ошибки

@dataclass
class Pos:
    pos: int # позиция в cleantxt
    width: int # возможная вариация — текстовую часть ноды можно бить в любом месте по этой ширине
    open_tags: List[str]
    on_open: bool = True
    open_tags_len: int = field(init=False)
    close_tags_len: int = field(init=False)
    def __post_init__(self):
        self.open_tags_len = \
            functools.reduce(lambda x, y: x + len(y) + 2, self.open_tags, 0) if len(self.open_tags) > 0 else 0
        self.close_tags_len = \
            functools.reduce(lambda x, y: x + len(y) + 1 + 2, self.open_tags, 0) if len(self.open_tags) > 0 else 0

class FragParser(HTMLParser):
    blockElements = ["p", "b", "strong", "i", "ul", "ol", "div", "span"] # статический список блочных элементов — их можно разбивать

    def __init__(self):
        super().__init__()
        self.cleantext = '' # рафинированный текст: пересобираем сюда весь текст только из тегов, атрибутов и текста (тогда например, лишние пробелы между атрибутами пропадут)
        self.pos = 0 # текущая позиция внутри рафинированного текста
        self.can_fragment_stack = [True] # стек флагов нахождения в блочном теге – если парсер заедет внутрь неблочного тега, то все вложенные в него теги можно не обрабатывать — их всё равно нельзя разбивать
        self.tag_stack = [''] # стек тегов — чтобы знать, где мы находимся по ходу парсинга; изначально вставляем туда пустой тег — просто для того, чтобы не проверять всё время наличие корневого тега
        self.possible_fragments = [Pos(0, 0, self.tag_stack.copy(), True)] # список возможных мест, где можно разбить входной текст, pos считается по рафинированному тексту (cleantext); изначально вставляется пустой элемент, чтобы не проверять каждый раз на пустоту, элемент соответствует псевдокорню, добавленному в предудущей строке
        self.i_was_at_the_top = False # выставляется в True, когда возвращается из самого верхнего тега, нужен для вычисления следующего флага
        self.no_root = False # выставляется в True, если окажется, что мы уже были на самом верху — это означает, что у входного хтмл-я нет корневого тега (вдруг пригодится)
        self.max_unbreakable_text_len = -1 # пытаемся посчитать минимальный размер max_len
        self.reset() # понятия не имею, что это — оно было в учёбнике; скорее всего ресетится родительский парсер
 
    #Defining what the methods should output when called by HTMLParser.
    def handle_starttag(self, tag, attrs):
        # если пришли в новый тег, а перед этим были в самом верхнем — значит кусок хтмл без корневого тега; нигде не используется, возможно пригодится 
        self.no_root = self.no_root or self.i_was_at_the_top

        # флаг, можно ли втыкать фрагмент сразу за этим тегом — можно, если этот тег блочный И родительский тег тоже можно было бить
        # CHECK проверить, по-моему на пустость проверять не надо уже
        can_fragment = tag in FragParser.blockElements and \
            (len(self.can_fragment_stack) == 0 or self.can_fragment_stack[-1])
        
        self.tag_stack.append(tag) # push тег в стек тегов

        # рафинируем тег
        opening_tag_clean_text = '<' + tag
        # набираем длину рафинированного открывающего тега (можно было не выпендриваться, а просто по тексту посчитать)
        totlen = len(tag) + 2 # учитываем скобки тега
        # добавляем атрибуты в тег через один пробел
        # TODO переделать на reduce
        for a in attrs:
            # print("Attributes of the tag: ", a)
            totlen += 1  +   len(a[0]) + 1 + 1 + len(a[1]) + 1 # TODO посмотреть, как парсер работает с енкоднутыми символами типа &gt; или &nbsp;
            #         ↑      ↑           ↑   ↑   ↑           ↑
            #         пробел attrname    =   "   attrval     "
            # пробел перед атрибутом, имя атрибута, знак равно, кавычки значения атрибута, значение атрибута
            opening_tag_clean_text += ' ' + a[0] + '="' + a[1] + '"'
        opening_tag_clean_text += '>'
        self.cleantext += opening_tag_clean_text
        self.pos += totlen
        if can_fragment:
            open_tags = self.tag_stack.copy()[1:]
            self.possible_fragments.append(Pos(self.pos, 0, open_tags, True))
            # вычисляем расстояние между новым и предыдущим возможным фрагментом:
            diff = self.possible_fragments[-1].open_tags_len + self.pos - \
                (self.possible_fragments[-2].pos + self.possible_fragments[-2].width) + \
                self.possible_fragments[-1].close_tags_len
            if self.max_unbreakable_text_len < diff:
                self.max_unbreakable_text_len = diff

        self.can_fragment_stack.append(can_fragment)
 
    def handle_data(self, data):
        self.pos += len(data)
        self.cleantext += data
        # важно: если мы находимся в теге, который можно разбивать (то есть он находится на верхушке стека возможных фрагментов), то весь этот текст (data) надо учесть в этой верхушке (в последней записи возможного фрагмента)
        # CHECK по-моему, можно выкинуть проверку на пустой стек
        if len(self.can_fragment_stack) == 0 or self.can_fragment_stack[-1]: 
            self.possible_fragments[-1].width = len(data)
 
    def handle_endtag(self, tag):
        # print("End tag: ", tag)
        self.tag_stack.pop()
        # добавляем к рафинированному тексту закрывающий тег
        self.cleantext += "</" + tag + ">"
        self.pos += len(tag) + 2 + 1 # учитываем скобки и косую черту
        self.can_fragment_stack.pop()
        # CHECK по-моему, можно не проверять на пустой стек
        can_fragment = len(self.can_fragment_stack) == 0 or self.can_fragment_stack[-1]
        # если можно бить, то после закрывающего тега добавим точку разбиения
        if can_fragment: 
            # делаем копию стека тегов
            open_tags = self.tag_stack.copy()[1:]
            self.possible_fragments.append(Pos( self.pos, 0, open_tags, False))
            diff = self.possible_fragments[-1].open_tags_len + self.pos - (self.possible_fragments[-2].pos + self.possible_fragments[-2].width) + self.possible_fragments[-1].close_tags_len
            if self.max_unbreakable_text_len < diff:
                self.max_unbreakable_text_len = diff

        # если это верхний тег (остался только фейковый пустой корень), то выставляем флаг "я был наверху"
        if len(self.can_fragment_stack) == 1:
            self.i_was_at_the_top = True

MAX_LEN = 4096

def split_message(source: str, max_len=MAX_LEN) -> Generator[str]:
    """Splits the original message (`source`) into fragments of the specified length(`max_len`)."""

    if source == None:
        return
    
    if len(source) <= max_len:
        yield source
        return
    
    fragParser = FragParser()
    fragParser.feed(source)
    
    cur_len = 0
    cur_start = 0
    prev_frag = None
    cur_frag = None

    for frag in fragParser.possible_fragments:
        cur_span = frag.pos - cur_start + frag.close_tags_len + cur_len
        must_frag_next = False
        if cur_span > max_len: # CHECK!!! не может быть первая проверка, иначе исключение (проверкить prev != None)
            # print('frag: ', fragParser.cleantxt[cur_start:prev.pos + 1], prev.close_tags_len)
            # print('open: ', prev.open_tags_len)
            close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, prev_frag.open_tags, '')

            # open_tags = ''
            first_time = cur_frag == None
            # if cur_frag != None: # CHECK!!! вообще-то он тут обязан быть
            if first_time:
                cur_frag = prev_frag
                
            # open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '')
            
            # if cur_frag != None: # CHECK!!! вообще-то он тут обязан быть
            fragment_text = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '') if not first_time else ''
            # print(open_tags, end='')

            # print(fragParser.cleantxt[cur_start:prev_frag.pos + prev_frag.width] + close_tags)
            fragment_text += fragParser.cleantext[cur_start:prev_frag.pos + prev_frag.width] + close_tags
            if len(fragment_text) > max_len:
                raise ValueError(f"Unable to fit fragment into specified length (max_len = {max_len}): start position {cur_start} \"{fragParser.cleantext[cur_start:cur_start + min(ERROR_CITATION_LENGTH, max_len)]}…\"")

            yield fragment_text
            # print('open: ', functools.reduce(lambda x, y: x + '<' + y + '>', prev.open_tags, ''))
            cur_start = prev_frag.pos + prev_frag.width
            cur_len = prev_frag.open_tags_len
            cur_span = frag.pos - (prev_frag.pos + prev_frag.width) + frag.close_tags_len + prev_frag.open_tags_len
            cur_frag = prev_frag
            # cur_span = prev.pos - cur_start + prev.close_tags_len + cur_len
            must_frag_next = True
            # CHECK!!! добавить проверку на следующее условие, если нет, то исключение
        if cur_span <= max_len and cur_span + frag.width > max_len:
            open_tags = ''
            if cur_frag != None:
                open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '')
            close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, frag.open_tags, '')

            extra = max_len - cur_span 
            
            fragment_text = ''
            if cur_frag != None:
                # print(open_tags, end='')
                fragment_text = open_tags

            fragment_text += fragParser.cleantext[cur_start:frag.pos + extra] + close_tags
            if len(fragment_text) > max_len:
                raise ValueError(f"Unable to fit fragment into specified length (max_len = {max_len}): start position {cur_start} \"{fragParser.cleantext[cur_start:cur_start + min(ERROR_CITATION_LENGTH, max_len)]}…\"")
            yield fragment_text

            cur_frag = frag
            # print('open: ', functools.reduce(lambda x, y: x + '<' + y + '>', frag.open_tags, ''))
            cur_start = frag.pos + extra
            cur_len = frag.open_tags_len
        # elif must_frag_next:
        #     raise ValueError(f"Unable to fit fragment into specified length (max_len = {max_len})")
        prev_frag = frag

    # frag = fragParser.acc[-1]
    open_tags = ''
    if cur_frag != None:
        open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '')
    # close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, cur_frag.open_tags, '')

    # extra = max_len - cur_span 

    fragment_text = ''
    if cur_frag != None:
        fragment_text += open_tags

    fragment_text += fragParser.cleantext[cur_start:] # + close_tags
        # + functools.reduce(lambda x, y: '</' + y + '>' + x, frag.open_tags, '')
    if len(fragment_text) > max_len:
        raise ValueError(f"Unable to fit fragment into specified length (max_len = {max_len}): start position {cur_start} \"{fragParser.cleantext[cur_start:cur_start + min(ERROR_CITATION_LENGTH, max_len)]}…\"")
    yield fragment_text
