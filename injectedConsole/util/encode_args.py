__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)

from base64 import b64encode, b64decode
from pickle import loads as pickle_loads, dumps as pickle_dumps


__all__ = ['b64encode_pickle', 'b64decode_pickle']


def b64encode_pickle(obj) -> str:
    'serialize a python object with pickle, and then encode it with base64'
    return b64encode(pickle_dumps(obj)).decode()


def b64decode_pickle(string: str):
    'deserialize a string that is serialized from a python object'
    return pickle_loads(b64decode(string.encode()))

