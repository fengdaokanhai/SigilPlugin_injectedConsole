#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['exists_execfile', 'get_debian_default_app', 'set_debian_default_app']


from subprocess import run as sprun, CompletedProcess, DEVNULL, PIPE
from typing import Optional, Union


def exists_execfile(file: str) -> bool:
    'Check whether the executable file exists in a directory in $PATH.'
    return sprun(['which', file], stdout=DEVNULL, stderr=DEVNULL).returncode == 0


def get_debian_default_app(field: Union[bytes, str]) -> Optional[str]:
    'Use the update-alternatives command to get the default app'
    if isinstance(field, str):
        field = field.encode('utf-8')
    rt = sprun(
        'update-alternatives --get-selections', 
        check=True, shell=True, stdout=PIPE)
    return next((
        row.rsplit(maxsplit=1)[-1].decode('utf-8') 
        for row in rt.stdout.split(b'\n') 
        if row.startswith(b'%s '%field)
    ), None)


def set_debian_default_app(field: str) -> CompletedProcess:
    'Use the update-alternatives command to set the default app'
    return sprun(['update-alternatives', '--config', field])

