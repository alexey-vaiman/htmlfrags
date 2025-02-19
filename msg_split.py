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

        # TODO проверить несколько атрибутов, в примерах только один - DONE, test_simple_4
        # добавляем атрибуты в тег через один пробел
        opening_tag_clean_text = functools.reduce(
            lambda x, y: x + ' ' + y[0] + '="' + y[1] + '"', 
            attrs, 
            opening_tag_clean_text)

        # закрываем открывающий тег
        opening_tag_clean_text += '>'
        self.cleantext += opening_tag_clean_text

        # добавляем его длину к позиции
        self.pos += len(opening_tag_clean_text)
        if can_fragment:
            self.add_possible_fragment(True)

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
            self.add_possible_fragment(False)

        # если это верхний тег (остался только фейковый пустой корень), то выставляем флаг "я был наверху"
        if len(self.can_fragment_stack) == 1:
            self.i_was_at_the_top = True

    def add_possible_fragment(self, on_open):
        # делаем копию стека тегов
        open_tags = self.tag_stack.copy()[1:]
        # добавляем запись в список возможных фрагментов
        self.possible_fragments.append(Pos(self.pos, 0, open_tags, on_open))
        # обновляем, если изменяется, минимальную длину фрагмента
        # вычисляем расстояние между новым и предыдущим возможным фрагментом
        diff = self.possible_fragments[-1].open_tags_len + self.pos - \
                (self.possible_fragments[-2].pos + self.possible_fragments[-2].width) + \
                self.possible_fragments[-1].close_tags_len
        # если расстояние больше текущего максимума — обновляем максимум
        self.max_unbreakable_text_len = max(diff, self.max_unbreakable_text_len)

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
    
    cur_open_tags_len = 0 # длина текста текущих открывающих тегов, нужна для удобства
    cur_start = 0 # смещение в рафинированном тексте действующего фрагмента
    cur_frag = None # действующий фрагмент — НЕ то же самое, что и frag в цикле, тот просто текущий перебираемый фрагмент
    prev_frag = None # предыдущий перебираемый фрагмент: нужен, когда внезапно оказалось, что с текущим текстом точно не влезет в max_len

    # бежим по найденным возможным фрагментам и набираем максимальные куски, не превышающие max_len
    for frag in fragParser.possible_fragments:
        # вычисляем длину текста до текущего фрагмента
        cur_span = frag.pos - cur_start + frag.close_tags_len + cur_open_tags_len
        # если длина текста до текущего фрагмента превышает значение параметра max_len,
        # то сначала обрываем текст по предыдущему фрагменту (он сохранён в prev_frag),
        # а затем пробуем уместить текущий кусок в фрагмент (см. следующий if)
        if cur_span > max_len: # CHECK!!! не может быть первая проверка, иначе исключение (проверкить prev != None)
            # собираем закрывающие теги, чтобы закрыть предыдущий фрагмент
            close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, prev_frag.open_tags, '')

            # если это самый первый фрагмент (а так бывает?)
            first_time = cur_frag == None
            if first_time:
                cur_frag = prev_frag

            # если это не первый фрагмент, то начинаем с открывающих тегов, взятых из текущего фрагмента                
            fragment_text = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '') if not first_time else ''

            # добавляем текст предыдущего фрагмента (т.е. того, что был обработан на предыдущем шаге), плюс закрывающие теги
            fragment_text += fragParser.cleantext[cur_start:prev_frag.pos + prev_frag.width] + close_tags
            if len(fragment_text) > max_len:
                raise ValueError(f"Unable to fit fragment into specified length (max_len = {max_len}): start position {cur_start} \"{fragParser.cleantext[cur_start:cur_start + min(ERROR_CITATION_LENGTH, max_len)]}…\"")

            yield fragment_text

            # вычисляем начало следующего фрагмента, длину открывающих тегов (для учёта длины набираемого фрагмента), длину набранного следующего фрагмента 
            cur_start = prev_frag.pos + prev_frag.width
            cur_open_tags_len = prev_frag.open_tags_len
            cur_span = frag.pos - (prev_frag.pos + prev_frag.width) + frag.close_tags_len + prev_frag.open_tags_len
            # сдвигаем фрагмент
            cur_frag = prev_frag
        # если набранный фрагмент умещается в max_len, а со всем текущим текстом разбиения — не умещается, то
        # бьём по max_len набранный фрагмент и начинаем считать следующий, с остатка текста текущего фрагмента
        if cur_span <= max_len and cur_span + frag.width > max_len:
            # собираем открывающие теги текущего фрагмента (если это не первый фрагмент, потому что в первом они уже есть в тексте)
            open_tags = ''
            if cur_frag != None:
                open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '')
            # собираем закрывающие теги — всегда, кроме последнего фрагмента (это выполняется уже за текущим циклом)
            close_tags = functools.reduce(lambda x, y: '</' + y + '>' + x, frag.open_tags, '')

            # вычисляем количество символов, которые надо взять из текста текущего фрагмента для заполнения до max_len
            extra = max_len - cur_span
            
            # собираме текст фрагмента = открывающие теги (если есть) + кусок чистого текста (с возможными тегами) + закрывающие теги
            fragment_text = open_tags + fragParser.cleantext[cur_start:frag.pos + extra] + close_tags

            if len(fragment_text) > max_len:
                raise ValueError(f"Unable to fit fragment into specified length (max_len = {max_len}): start position {cur_start} \"{fragParser.cleantext[cur_start:cur_start + min(ERROR_CITATION_LENGTH, max_len)]}…\"")
            yield fragment_text

            # переставляем переменные — текущий фрагмент, старт текущего фрагмента, сдвинутый на уже использованный в предыдущем фрагменте текст,
            # и переменную, в которой хранится длина повторённых открывающих тегов (используется в начале цикла для вычисления длины следующего фрагмента)
            cur_frag = frag
            cur_start = frag.pos + extra
            cur_open_tags_len = frag.open_tags_len
        # переставляем переменную, храняющую предыдущий фрагмент
        prev_frag = frag

    # набираем открывающие теги (если уже был хотя бы один фрагмент)
    open_tags = functools.reduce(lambda x, y: x + '<' + y + '>', cur_frag.open_tags, '') if cur_frag != None else ''
    # набираем текст фрагмента = открывающие теги, кусок текста до конца (с последнего фрагмента) — а последние закрывающие теги уже есть в рафинированной строке
    fragment_text = open_tags + fragParser.cleantext[cur_start:]

    if len(fragment_text) > max_len:
        raise ValueError(f"Unable to fit fragment into specified length (max_len = {max_len}): start position {cur_start} \"{fragParser.cleantext[cur_start:cur_start + min(ERROR_CITATION_LENGTH, max_len)]}…\"")
    yield fragment_text
