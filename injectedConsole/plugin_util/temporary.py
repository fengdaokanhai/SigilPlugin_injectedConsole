#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 3)

import os, sys

from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Union
from types import ModuleType


__all__ = ['temp_dict', 'temp_list', 'temp_set', 'temp_wdir', 
           'temp_sys_path', 'temp_sys_modules']


PathType = Union[str, bytes, os.PathLike]


@contextmanager
def temp_dict(container: dict, /):
    original = container.copy()
    try:
        yield container
    finally:
        container.clear()
        container.update(original)


@contextmanager
def temp_list(container: list, /):
    original = container.copy()
    try:
        yield container
    finally:
        container[:] = original


@contextmanager
def temp_set(container: set, /):
    original = container.copy()
    try:
        yield container
    finally:
        container.clear()
        container.update(original)


@contextmanager
def temp_wdir(wdir: PathType):
    'Temporary working directory'
    original_wdir: PathType = os.getcwd()
    try:
        os.chdir(wdir)
        yield
    finally:
        os.chdir(original_wdir)


@contextmanager
def temp_sys_path():
    'Temporary sys.path'
    yield from temp_list.__wrapped__(sys.path)


@contextmanager
def temp_sys_modules(
    mdir: Optional[PathType] = None, 
    clean: bool = True, 
    restore: bool = True, 
    prefixes_not_clean: Tuple[str, ...] = tuple(set(__import__('site').PREFIXES)),
):
    'Temporary sys.modules'
    sys_modules: Dict[str, ModuleType] = sys.modules
    original_sys_modules: Dict[str, ModuleType] = sys_modules.copy()
    if clean:
        # Only retaining built-in modules and standard libraries and site-packages modules 
        # (`prefixes_not_clean` as the path prefix), 
        # but ignoring namespace packages (the documentation is as follows)
        # [Packaging namespace packages](https://packaging.python.org/guides/packaging-namespace-packages/)
        sys_modules.clear()
        sys_modules.update(
            (k, m) for k, m in original_sys_modules.items() 
            if not hasattr(m, '__file__') # It means a built-in module
                or m.__file__ is not None # It means not a namespace package
                and m.__file__.startswith(prefixes_not_clean) # It means a standard library or site-packages module
        )

    sys_path: List[str]
    with temp_sys_path() as sys_path:
        if mdir is not None:
            mdir_: str = mdir.decode() if isinstance(mdir, bytes) else str(mdir)
            sys_path.insert(0, mdir_)
        try:
            yield sys_modules
        finally:
            if restore:
                sys_modules.clear()
                sys_modules.update(original_sys_modules)

