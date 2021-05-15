#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['restart_program', 'run', 'load']


import re
import sys

from os import execl, getcwd, path as _path
from sys import argv, executable
from typing import Any, Dict, Optional, Tuple, Union
from types import CodeType, ModuleType
from urllib.parse import unquote
from urllib.request import urlopen

from .temporary import temp_wdir, temp_sys_modules


def _startswith_protocol(
    path: Union[bytes, str], 
    _cre=re.compile('^[_a-zA-Z][_a-zA-Z0-9]+://'),
    _creb=re.compile(b'^[_a-zA-Z][_a-zA-Z0-9]+://'),
) -> bool:
    if isinstance(path, bytes):
        return _creb.match(path) is not None
    else:
        return _cre.match(path) is not None


def restart_program(argv=argv):
    'restart the program'
    execl(executable, executable, *argv)


def run(
    path: str, 
    namespace: Optional[dict] = None, 
    wdir: Optional[str] = None, 
    mainfile: Union[str, Tuple[str, ...]] = ('__main__.py', 'main.py', '__init__.py'),
) -> Dict[str, Any]:
    '''Run a [file] / [mainfile in directory], from a [file] | [url] | [directory].

    :param path: The path of file or directory of the python script.
    :param namespace: Execute the given source in the context of namespace.
                      If it is None (the default), will create a new dict().
    :param wdir: Temporay working directory, if it is None (the default), 
                 then use the current working directory.
    :param mainfile: If the `path` is a directory, according to this parameter, 
                     an existing main file will be used.

    :return: Dictionary of script execution results.
    '''
    # If you want to run as main module, set namespace['__name__'] = '__main__'
    if wdir is None:
        wdir = getcwd()
    else:
        wdir = _path.abspath(wdir)

    if _startswith_protocol(path):
        path = unquote(path)
        mdir = None
        mname = _path.splitext(_path.basename(path))[0]
        pname = ''
        source = urlopen(path).read().decode('utf-8')
    else:
        path = _path.abspath(path)
        if _path.isdir(path):
            mdir = path
            mname = pname = _path.basename(path)
            if isinstance(mainfile, str):
                path_ = _path.join(path, mainfile)
            else:
                notfound_files = []
                for mainfile_ in mainfile:
                    path_ = _path.join(path, mainfile_)
                    if _path.exists(path_):
                        break
                    notfound_files.append(path_)
                else:
                    raise FileNotFoundError(notfound_files)
            source = open(path_).read()
        else:
            mdir = _path.dirname(path)
            mname = _path.splitext(_path.basename(path))[0]
            pname = ''
            source = open(path).read()

    if namespace is None:
        namespace = {'__name__': mname}
    elif not namespace.get('__name__'):
        namespace['__name__'] = mname

    with temp_sys_modules(mdir):
        code: CodeType = compile(source, path, 'exec')
        if wdir == getcwd():
            exec(code, namespace)
        else:
            with temp_wdir(wdir):
                exec(code, namespace)

    return dict(
        code=code, 
        namespace=namespace, 
        wdir=wdir, 
        mdir=mdir, 
        path=path,
        module_name=mname, 
        package_name=pname, 
        mainfile=path, 
    )


def load(
    path: str, 
    wdir: Optional[str] = None,
    mainfile: Union[str, Tuple[str, ...]] = '__init__.py',
    as_sys_module: bool = False,
) -> ModuleType:
    '''Load a [module] | [package], from a [file] | [directory] | [url].

    :param path: The path of file or directory of the python script.
    :param wdir: Temporay working directory, if it is None (the default), 
                 then use the current working directory.
    :param mainfile: If the `path` is a directory, according to this parameter, 
                     an existing main file will be used.
    :param as_sys_module: If True, module will be set to sys.modules.

    :return: A new module.
    '''
    mod: ModuleType = ModuleType('')
    info: Dict[str, Any] = run(path, mod.__dict__, wdir=wdir, mainfile=mainfile)
    mod.__file__ = info['mainfile']
    mod.__name__ = info['module_name']
    mod.__package__ = info['package_name']

    if as_sys_module:
        sys.modules[info['path']] = mod

    return mod

