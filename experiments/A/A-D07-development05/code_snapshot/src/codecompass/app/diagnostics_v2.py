"""Independent parallel concept snippets. Never contains final-task answer keys."""
from .diagnostic_items import ITEMS as ORIGINAL

ITEMS=dict(ORIGINAL)
for tid,concept,code,choices,answer in [
 ('task_003','python.hash_set','print(len(set([4, 4, 7])))',['2','3','1'],0),
 ('task_004','python.sentinel_default','sentinel = object()\nfound = None\nprint(found is sentinel)',['True','False','None'],1),
 ('task_005','python.regex_boundary',"import re\nprint(re.sub(r'(?<=[a-z])(?=[A-Z])', '_', 'redBlue'))",['redBlue','red_Blue','red_blue'],1),
 ('task_006','python.bytes_text',"print(type('hello'.encode('ascii')).__name__)",['str','list','bytes'],2),
 ('task_007','python.string_index',"print('cat'[-1])",['c','a','t'],2),
 ('task_008','python.bytes_text',"print(b'hi'.decode('utf-8'))",['hi',"b'hi'",'[104, 105]'],0),
 ('task_009','python.compression_roundtrip',"import zlib\npayload = b'xyz'\nprint(zlib.decompress(zlib.compress(payload)) == payload)",['True','False','None'],0),
 ('task_010','python.regex_group',"import re\nprint(re.split(r'(,)', 'a,b'))",["['a', 'b']","['a', ',', 'b']","['a,b']"],1),
 ('task_011','python.range_closed','print(list(range(2, 5)))',['[2, 3, 4, 5]','[2, 3, 4]','[3, 4, 5]'],1),
 ('task_012','python.prefix_slice',"print('blueprint'[:4])",['blue','print','bluep'],0),
]:
    ITEMS[tid]=dict(item_id='B06-parallel-'+tid+'-v2',concept_id=concept,prompt='独立概念短测：程序打印什么？',
        code=code,choices=choices,answer=answer,basis='Independently executable Python semantics; distinct inputs from final task; engineering-reviewed, not human-calibrated')


def public_item(tid):return {k:ITEMS[tid][k] for k in ('item_id','prompt','code','choices')}


def score(tid,choice):
    q=ITEMS[tid]
    if type(choice) is not int or not 0<=choice<len(q['choices']):raise ValueError('请选择一个答案')
    return 'pass' if choice==q['answer'] else 'fail'
