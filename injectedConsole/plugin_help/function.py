#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = [
    'abort', 'exit', 'dump_wrapper', 'load_wrapper', 'get_container', 
    'reload_shell', 'back_shell', 'reload_embeded_shell', 
    'reload_to_shell', 'start_qtconsole', 'start_jupyter_notebook', 
    'start_jupyter_lab', 
]


import subprocess

from contextlib import contextmanager
from os import _exit
from os.path import join as path_join
from pickle import load as pickle_load, dump as pickle_dump
from sys import _getframe, argv, executable
from typing import Final, List, Mapping, Optional

from wrapper import Wrapper # type: ignore
from bookcontainer import BookContainer # type: ignore
from inputcontainer import InputContainer # type: ignore
from outputcontainer import OutputContainer # type: ignore
from validationcontainer import ValidationContainer # type: ignore

from plugin_util.dictattr import DictAttr
from plugin_util.colored import colored
from plugin_util.console import start_specific_python_console
from plugin_util.run import restart_program


_SYSTEM_IS_WINDOWS: Final[bool] = __import__('platform').system() == 'Windows'
_PATH: Final[Mapping] = __import__('builtins')._PATH
_OUTDIR: Final[str] = _PATH['outdir']
_ABORTFILE: Final[str] = path_join(_OUTDIR, 'abort.exists')
_ENVFILE: Final[str] = path_join(_OUTDIR, 'env.py')
_PKLFILE: Final[str] = path_join(_OUTDIR, 'wrapper.pkl')
_WRAPPER: Optional[Wrapper] = None


def abort() -> None:
    'Abort console to discard all changes.'
    open(_ABORTFILE, 'wb').close()
    _exit(1)


def exit() -> None:
    'Exit console for no more operations.'
    dump_wrapper()
    _exit(0)


def dump_wrapper(wrapper: Optional[Wrapper] = None) -> None:
    'Dump wrapper to file.'
    global _WRAPPER
    pickle_dump(wrapper or _WRAPPER, open(_PKLFILE, 'wb'))


def load_wrapper(clear: bool = False) -> Wrapper:
    'Load wrapper from file.'
    global _WRAPPER
    wrapper = pickle_load(open(_PKLFILE, 'rb'))
    if _WRAPPER is None:
        _WRAPPER = wrapper
    else:
        if clear:
            _WRAPPER.__dict__.clear()
        _WRAPPER.__dict__.update(wrapper.__dict__)
    return _WRAPPER


@contextmanager
def _ctx_wrapper():
    dump_wrapper()
    yield _WRAPPER
    load_wrapper()


def get_container(wrapper=None) -> Mapping:
    'Get the sigil containers.'
    if wrapper is None:
        wrapper = load_wrapper()

    # collect the containers
    return DictAttr(
        wrapper    = wrapper,
        edit       = BookContainer(wrapper),
        input      = InputContainer(wrapper),
        validation = ValidationContainer(wrapper),
        output     = OutputContainer(wrapper),
    )


def reload_shell(shell: str) -> None:
    'Restart the program and reload to another shell.'
    are_u_sure = input('reload shell will discrad all local variables'
                       ', are you sure? ([y]/n) ').strip()
    if are_u_sure not in ('', 'y', 'Y'):
        return
    argv_ = argv.copy()
    try:
        idx = argv_.index('--shell')
    except ValueError:
        from plugin_util import console
        prev_shell = getattr(console, '__shell__', None)
        argv_.extend(('--shell', shell))
    else:
        prev_shell = argv_[idx + 1]
        argv_[idx: idx+2] = ['--shell', shell]
    if prev_shell:
        try:
            idx = argv_.index('--prev-shell')
        except ValueError:
            argv_.extend(('--prev-shell', prev_shell))
        else:
            argv_[idx: idx+2] = ['--prev-shell', prev_shell]
    dump_wrapper()
    restart_program(argv_)


def back_shell(argv: List[str] = argv) -> None:
    'back to previous shell (if any)'
    argv_: List[str] = argv.copy()
    try:
        idx: int = argv_.index('--prev-shell')
    except ValueError:
        prev_shell = None
    else:
        prev_shell = argv_[idx + 1]
        del argv_[idx: idx + 2]
    if prev_shell:
        try:
            idx = argv_.index('--shell')
        except ValueError:
            argv_.extend(('--shell', prev_shell))
        else:
            argv_[idx: idx + 2] = ['--shell', prev_shell]
        print(colored('[WARRNING]', 'yellow', attrs=['bold']), 'back to shell:', prev_shell)
        restart_program(argv_)


def reload_embeded_shell(shell, banner='', namespace=None):
    'reload to another embedded shell'
    if namespace is None:
        namespace = _getframe(1).f_locals
    start_specific_python_console(namespace, banner, shell)


reload_to_shell = reload_embeded_shell if _SYSTEM_IS_WINDOWS else reload_shell


def start_qtconsole(
    *args: str, 
    executable: str = executable,
) -> None:
    'Start a qtconsole process, and wait until it is terminated.'
    with _ctx_wrapper():
        subprocess.run([executable, '-m', 'qtconsole', *args], 
                       check=True, shell=_SYSTEM_IS_WINDOWS)


def _prun(args: List[str]) -> None:
    p = subprocess.Popen(args, shell=_SYSTEM_IS_WINDOWS)
    try:
        while True:
            try:
                p.communicate(input=subprocess.PIPE) # type: ignore
                break
            except KeyboardInterrupt:
                pass
    finally:
        p.terminate()


def start_jupyter_notebook(
    *args: str, 
    executable: str = executable,
) -> None:
    'Start a jupyter notebook process, and wait until it is terminated.'
    if not args:
        args = ('--NotebookApp.notebook_dir="."', '--NotebookApp.open_browser=True', '-y')
    with _ctx_wrapper():
        _prun([executable, '-m', 'jupyter', 'notebook', *args])


def start_jupyter_lab(
    *args: str, 
    executable: str = executable,
) -> None:
    'Start a jupyter lab process, and wait until it is terminated.'
    if not args:
        args = ('--notebook-dir="."', '--ServerApp.open_browser=True', '-y')
    with _ctx_wrapper():
        _prun([executable, '-m', 'jupyter', 'lab', *args])

