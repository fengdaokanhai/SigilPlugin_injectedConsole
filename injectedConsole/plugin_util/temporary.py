#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

import os, sys

from contextlib import contextmanager
from typing import Dict, List, Optional, Union
from types import ModuleType


__all__ = ['temp_wdir', 'temp_sys_path', 'temp_sys_modules']


PathType = Union[str, bytes, os.PathLike]


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
    sys_path: List[str] = sys.path
    original_sys_path: List[str] = sys_path.copy()
    try:
        yield sys_path
    finally:
        sys_path[:] = original_sys_path


@contextmanager
def temp_sys_modules(
    mdir: Optional[PathType] = None, 
    clean: bool = True, 
    restore: bool = True, 
):
    'Temporary sys.modules'
    sys_modules: Dict[str, ModuleType] = sys.modules
    original_sys_modules: Dict[str, ModuleType] = sys_modules.copy()
    if clean:
        sys_modules.clear()

    sys_path: List[str]
    with temp_sys_path() as sys_path:
        if mdir is not None:
            mdir_: str = mdir.decode() if isinstance(mdir, bytes) else str(mdir)
            sys_path.insert(0, mdir_)
        try:
            yield sys_modules
        finally:
            if restore:
                if not clean:
                    sys_modules.clear()
                sys_modules.update(original_sys_modules)

