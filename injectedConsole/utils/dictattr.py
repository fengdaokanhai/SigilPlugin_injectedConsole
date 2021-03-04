__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)

from collections.abc import MutableMapping


__all__ = ['DictAttr']


class DictAttr(MutableMapping):
    """Implements the MutableMapping protocol 
    for modifying objects's __dict__."""
    def __init__(self, *args, **kwargs):
        self.__dict__ = dict(*args, **kwargs)

    def __repr__(self):
        return '%s(%r)' % (type(self).__qualname__, self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __getattr__(self, attr):
        return getattr(self.__dict__, attr)

