import os
import subprocess

from contextlib import contextmanager
from os import execl, path
from pickle import load as pickle_load, dump as pickle_dump
from sys import _getframe, argv, executable
from typing import Any, Mapping, Optional

from wrapper import Wrapper
from bookcontainer import BookContainer # type: ignore
from inputcontainer import InputContainer # type: ignore
from outputcontainer import OutputContainer # type: ignore
from validationcontainer import ValidationContainer # type: ignore

from plugin_util.dictattr import DictAttr
from plugin_util.colored import colored
from plugin_util.console import get_current_shell, list_shells, start_specific_python_console
from plugin_util.usepip import install, uninstall, execute_pip


__all__ = [
    'install', 'uninstall', 'execute_pip', 'restart_program', 'run', 'load', 
    'run_env', 'abort', 'exit', 'dump_wrapper', 'load_wrapper', 'get_container', 
    'get_current_shell', 'list_shells', 'reload_shell', 'back_shell', 
    'reload_embeded_shell', 'reload_to_shell', 'start_qtconsole', 
    'start_jupyter_notebook', 'start_jupyter_lab', 
]


_SYSTEM_IS_WINDOWS: bool = __import__('platform').system() == 'Windows'
_PATH = __import__('builtins')._PATH
_OUTDIR = _PATH['outdir']
_ABORTFILE = path.join(_OUTDIR, 'abort.exists')
_ENVFILE = path.join(_OUTDIR, 'env.py')
_PKLFILE = path.join(_OUTDIR, 'wrapper.pkl')
_WRAPPER: Optional[Wrapper] = None


def restart_program(argv=argv):
    'restart the program'
    execl(executable, executable, *argv)


def run(path, main_file='main.py'):
    '''Run a [file] | [program with directory structure], 
    from a [file] | [directory] | [zipped file] | [...].'''
    raise NotImplementedError


def load(path, module_file='__init__.py'):
    'Load a [module] | [package], from a [file] | [directory] | [zipped file] | [...].'
    raise NotImplementedError


def run_env():
    'Run the env file "./env.py", to initialize environment.'
    run(_ENVFILE)


def abort():
    'Abort console to discard all changes.'
    open(_ABORTFILE, 'wb').close()
    os._exit(1)


def exit():
    'Exit console for no more operations.'
    dump_wrapper()
    os._exit(0)


def dump_wrapper(wrapper: Optional[Wrapper] = None):
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


def reload_shell(shell):
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


def back_shell(argv=argv):
    'back to previous shell (if any)'
    argv_ = argv.copy()
    try:
        idx = argv_.index('--prev-shell')
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


def start_qtconsole(*args, executable=executable):
    'start a qtconsole process, and wait until it is terminated'
    with _ctx_wrapper():
        subprocess.run([executable, '-m', 'qtconsole', *args], 
                       check=True, shell=_SYSTEM_IS_WINDOWS)


def start_jupyter_notebook(*args, executable=executable):
    if not args:
        args = ('--NotebookApp.notebook_dir="."', '--NotebookApp.open_browser=True', '-y')
    with _ctx_wrapper():
        p = subprocess.Popen(
            [executable, '-m', 'jupyter', 'notebook', *args], 
            shell=_SYSTEM_IS_WINDOWS, 
        )
        try:
            while True:
                try:
                    p.communicate(subprocess.PIPE)
                    break
                except KeyboardInterrupt:
                    pass
        finally:
            p.terminate()


def start_jupyter_lab(*args, executable=executable):
    if not args:
        args = ('--notebook-dir="."', '--ServerApp.open_browser=True', '-y')
    with _ctx_wrapper():
        p = subprocess.Popen(
            [executable, '-m', 'jupyter', 'lab', *args], 
            shell=_SYSTEM_IS_WINDOWS, 
        )
        try:
            while True:
                try:
                    p.communicate(subprocess.PIPE)
                    break
                except KeyboardInterrupt:
                    pass
        finally:
            p.terminate()

