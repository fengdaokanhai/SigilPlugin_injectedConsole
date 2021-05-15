#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)

import os, sys

from contextlib import contextmanager
from typing import Optional, Union


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
def temp_sys_path(copy: bool = False):
    'Temporary sys.path'
    original_sys_path: list = sys.path
    sys.path = sys.path.copy() if copy else []
    try:
        yield sys.modules
    finally:
        sys.path = original_sys_path


@contextmanager
def temp_sys_modules(
    mdir: Optional[PathType] = None, 
    copy: bool = False,
    clean_path_by_remove: bool = False,
):
    'Temporary sys.modules'
    original_sys_modules: dict = sys.modules
    sys.modules = sys.modules.copy() if copy else {}
    try:
        if mdir is not None:
            mdir_: str = mdir.decode() if isinstance(mdir, bytes) else str(mdir)
            sys.path.insert(0, mdir_)
        yield sys.modules
    finally:
        sys.modules = original_sys_modules
        if mdir is not None:
            if clean_path_by_remove:
                sys.path.remove(mdir_)
            else:
                del sys.path[0]

