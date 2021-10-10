#!/usr/bin/env python3
# coding: utf-8

# Fork From: https://github.com/dabeaz/python-cookbook/blob/master/src/10/loading_modules_from_a_remote_machine_using_import_hooks/urlimport.py
# Reference:
#    - https://python3-cookbook.readthedocs.io/zh_CN/latest/c10/p11_load_modules_from_remote_machine_by_hooks.html
#    - https://github.com/dabeaz/python-cookbook/blob/master/src/10/loading_modules_from_a_remote_machine_using_import_hooks/
#    - https://www.python.org/dev/peps/pep-0302/
#    - https://www.python.org/dev/peps/pep-0369/
#    - https://docs.python.org/zh-cn/3/library/importlib.html
#    - https://docs.python.org/zh-cn/3/library/modules.html
#    - https://docs.python.org/3/tutorial/modules.html
# TODO: Refer to the source code of zipimport, implements importing remote .pyc and .zip files.
#>   - https://docs.python.org/3/library/zipimport.html
#>   - https://github.com/python/cpython/blob/main/Lib/zipimport.py

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['UrlMetaFinder', 'UrlModuleLoader', 'UrlPackageLoader', 'install_url_meta', 
           'remove_url_meta', 'UrlPathFinder', 'install_path_hook', 'remove_path_hook']

import logging
import sys

from html.parser import HTMLParser
from importlib.abc import Loader, MetaPathFinder, PathEntryFinder, SourceLoader
from types import CodeType, ModuleType
from typing import Callable, Collection, Dict, Final, List, Optional, Set
from urllib.request import urlopen
from urllib.error import HTTPError, URLError


# Debugging
_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def _get_links(url: str) -> Set[str]:
    'Get links from a given URL'
    class LinkParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                attrs = dict(attrs)
                links.add(attrs.get('href').rstrip('/'))
    links: Set[str] = set()
    try:
        _LOGGER.debug('Getting links from %s' % url)
        u = urlopen(url)
        parser = LinkParser()
        parser.feed(u.read().decode('utf-8'))
    except Exception as e:
        _LOGGER.debug('Could not get links. %s', e)
    _LOGGER.debug('links: %r', links)
    return links


class UrlMetaFinder(MetaPathFinder):

    def __init__(
        self, 
        baseurl: str, 
        get_links: Callable[[str], Collection[str]] = _get_links,
    ):
        self._baseurl: str = baseurl
        self._links: Dict[str, Collection[str]] = { }
        self._loaders: Dict[str, Loader] = { baseurl : UrlModuleLoader(baseurl) }
        self._get_links: Callable[[str], Collection[str]] = get_links

    def find_module(self, fullname, path):
        _LOGGER.debug('find_module: fullname=%r, path=%r', fullname, path)
        if path is None:
            baseurl = self._baseurl
        else:
            if not path[0].startswith(self._baseurl):
                return None
            baseurl = path[0]

        parts = fullname.split('.')
        basename = parts[-1]
        _LOGGER.debug('find_module: baseurl=%r, basename=%r', baseurl, basename)

        # Check link cache
        if basename not in self._links:
            self._links[baseurl] = self._get_links(baseurl)

        # Check if it's a package
        if basename in self._links[baseurl]:
            _LOGGER.debug('find_module: trying package %r', fullname)
            fullurl = self._baseurl + '/' + basename
            # Attempt to load the package (which accesses __init__.py)
            loader = UrlPackageLoader(fullurl)
            try:
                loader.load_module(fullname)
                self._links[fullurl] = self._get_links(fullurl)
                self._loaders[fullurl] = UrlModuleLoader(fullurl)
                _LOGGER.debug('find_module: package %r loaded', fullname)
            except ImportError as e:
                _LOGGER.debug('find_module: package failed. %s', e)
                loader = None
            return loader

        # A normal module
        filename = basename + '.py'
        if filename in self._links[baseurl]:
            _LOGGER.debug('find_module: module %r found', fullname)
            return self._loaders[baseurl]
        else:
            _LOGGER.debug('find_module: module %r not found', fullname)
            return None

    def invalidate_caches(self) -> None:
        _LOGGER.debug('invalidating link cache')
        self._links.clear()


# Module Loader for a URL
class UrlModuleLoader(SourceLoader):

    def __init__(self, baseurl: str) -> None:
        self._baseurl: str = baseurl
        self._source_cache: Dict[str, str] = {}

    def module_repr(self, module: ModuleType) -> str:
        return '<urlmodule %r from %r>' % (module.__name__, module.__file__)

    def load_module(self, fullname: str) -> ModuleType:
        code: CodeType = self.get_code(fullname)
        mod: ModuleType = sys.modules.setdefault(fullname, ModuleType(fullname))
        mod.__file__ = self.get_filename(fullname)
        mod.__loader__ = self
        mod.__package__ = fullname.rpartition('.')[0]
        exec(code, mod.__dict__)
        return mod

    # Optional extensions
    def get_code(self, fullname: str) -> CodeType:
        src = self.get_source(fullname)
        return compile(src, self.get_filename(fullname), 'exec')

    def get_data(self, path):
        pass

    def get_filename(self, fullname: str) -> str:
        return self._baseurl + '/' + fullname.split('.')[-1] + '.py'

    def get_source(self, fullname: str) -> str:
        filename = self.get_filename(fullname)
        _LOGGER.debug('loader: reading %r', filename)
        if filename in self._source_cache:
            _LOGGER.debug('loader: cached %r', filename)
            return self._source_cache[filename]
        try:
            u = urlopen(filename)
            source = u.read().decode('utf-8')
            _LOGGER.debug('loader: %r loaded', filename)
            self._source_cache[filename] = source
            return source
        except (HTTPError, URLError) as e:
            _LOGGER.debug('loader: %r failed.  %s', filename, e)
            raise ImportError("Can't load %s" % filename)

    def is_package(self, fullname: str) -> bool:
        return False


# Package loader for a URL
class UrlPackageLoader(UrlModuleLoader):

    def load_module(self, fullname: str) -> ModuleType:
        mod: ModuleType = super().load_module(fullname)
        mod.__path__: List[str] = [ self._baseurl ] # type: ignore
        mod.__package__ = fullname
        return mod

    def get_filename(self, fullname: str) -> str:
        return self._baseurl + '/' + '__init__.py'

    def is_package(self, fullname: str) -> bool:
        return True


# Utility functions for installing/uninstalling the loader
_installed_url_meta_cache = { }


def install_url_meta(
    address: str, 
    get_links: Callable[[str], Collection[str]] = _get_links, 
) -> None:
    if address not in _installed_url_meta_cache:
        finder = UrlMetaFinder(address, get_links)
        _installed_url_meta_cache[address] = finder
        sys.meta_path.append(finder)
        _LOGGER.debug('%r installed on sys.meta_path', finder)


def remove_url_meta(address: str) -> None:
    if address in _installed_url_meta_cache:
        finder = _installed_url_meta_cache.pop(address)
        sys.meta_path.remove(finder)
        _LOGGER.debug('%r removed from sys.meta_path', finder)


# Path finder class for a URL
class UrlPathFinder(PathEntryFinder):

    def __init__(
        self, 
        baseurl: str, 
        get_links: Callable[[str], Collection[str]] = _get_links, 
    ):
        self._links: Optional[Collection[str]] = None
        self._loader: Loader = UrlModuleLoader(baseurl)
        self._baseurl: str = baseurl
        self._get_links: Callable[[str], Collection[str]] = get_links

    def find_loader(self, fullname):
        _LOGGER.debug('find_loader: %r', fullname)
        parts = fullname.split('.')
        basename = parts[-1]
        # Check link cache
        if self._links is None:
            # The following fragment of code ensures that the finder doesn’t respond to any 
            # import requests while it’s in the processs of getting the initial set of links.
            self._links = []
            self._links = self._get_links(self._baseurl)

        # Check if it's a package
        if basename in self._links:
            _LOGGER.debug('find_loader: trying package %r', fullname)
            fullurl = self._baseurl + '/' + basename
            # Attempt to load the package (which accesses __init__.py)
            loader = UrlPackageLoader(fullurl)
            try:
                loader.load_module(fullname)
                _LOGGER.debug('find_loader: package %r loaded', fullname)
            except ImportError:
                _LOGGER.debug('find_loader: %r is a namespace package', fullname)
                loader = None
            return (loader, [fullurl])

        # A normal module
        filename = basename + '.py'
        if filename in self._links:
            _LOGGER.debug('find_loader: module %r found', fullname)
            return (self._loader, [])
        else:
            _LOGGER.debug('find_loader: module %r not found', fullname)
            return (None, [])

    def invalidate_caches(self) -> None:
        _LOGGER.debug('invalidating link cache')
        self._links = None


# Check path to see if it looks like a URL
def _handle_url(
    url: str, 
    _url_path_cache: dict = {},
) -> None:
    if url.startswith(('http://', 'https://')):
        _LOGGER.debug('Handle url? %s. [Yes]', url)
        if url not in _url_path_cache:
            _url_path_cache[url] = UrlPathFinder(url)
        return _url_path_cache[url]
    else:
        _LOGGER.debug('Handle url? %s. [No]', url)


def install_path_hook(path_hook: Callable = _handle_url) -> None:
    _LOGGER.debug('Installing %r' % path_hook)
    sys.path_hooks.append(path_hook)
    sys.path_importer_cache.clear()


def remove_path_hook(path_hook: Callable = _handle_url) -> None:
    _LOGGER.debug('Removing %r' % path_hook)
    sys.path_hooks.remove(path_hook)
    sys.path_importer_cache.clear()

