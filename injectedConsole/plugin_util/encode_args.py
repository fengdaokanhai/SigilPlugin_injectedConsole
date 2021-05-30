__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

from base64 import b64encode, b64decode
from json import dumps as json_dumps, loads as json_loads
from pickle import dumps as pickle_dumps, loads as pickle_loads


__all__ = ['b64encode_json', 'b64decode_json', 'b64encode_pickle', 'b64decode_pickle']


def b64encode_json(obj) -> str:
    'serialize a python object to json, and then encode it with base64'
    return b64encode(json_dumps(obj).encode('utf-8')).decode('latin-1')


def b64decode_json(string: str):
    'serialize a python object to json, and then encode it with base64'
    return json_loads(b64decode(string.encode('latin-1')).decode('utf-8'))


def b64encode_pickle(obj) -> str:
    'serialize a python object with pickle, and then encode it with base64'
    return b64encode(pickle_dumps(obj)).decode('latin-1')


def b64decode_pickle(string: str):
    'deserialize a string that is serialized from a python object'
    return pickle_loads(b64decode(string.encode('latin-1')))

