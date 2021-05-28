#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 4)
__all__ = [
    'abort', 'exit', 'dump_wrapper', 'load_wrapper', 'get_container', 
    'reload_shell', 'back_shell', 'reload_embeded_shell', 'reload_to_shell', 
    'run_env', 'run_plugin', 'start_nbterm', 'start_qtconsole', 'start_spyder', 
    'start_jupyter_notebook', 'start_jupyter_lab', 'start_python_shell', 
]


import subprocess
import sys

from contextlib import contextmanager
from copy import deepcopy
from os import _exit, path as _path
from pickle import load as pickle_load, dump as pickle_dump
from tempfile import NamedTemporaryFile
from traceback import print_exc
from typing import cast, Any, Final, List, Mapping, Optional
from xml.etree.ElementTree import parse as parse_xml_file

from wrapper import Wrapper # type: ignore
from bookcontainer import BookContainer # type: ignore
from inputcontainer import InputContainer # type: ignore
from outputcontainer import OutputContainer # type: ignore
from validationcontainer import ValidationContainer # type: ignore

from plugin_util.colored import colored
from plugin_util.console import start_specific_python_console
from plugin_util.dictattr import DictAttr
from plugin_util.run import ctx_load, run_file, prun_module, restart_program
from plugin_util.temporary import temp_list
from plugin_util.usepip import ensure_import


_SYSTEM_IS_WINDOWS: Final[bool] = __import__('platform').system() == 'Windows'
_injectedConsole_PATH: Final[Mapping] = __import__('builtins')._injectedConsole_PATH
_OUTDIR: Final[str] = _injectedConsole_PATH['outdir']
_ABORTFILE: Final[str] = _path.join(_OUTDIR, 'abort.exists')
_ENVFILE: Final[str] = _path.join(_OUTDIR, 'env.py')
_PKLFILE: Final[str] = _path.join(_OUTDIR, 'wrapper.pkl')
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
    if wrapper is None:
        wrapper = _WRAPPER
    pickle_dump(wrapper, open(_PKLFILE, 'wb'))


def load_wrapper() -> Wrapper:
    'Load wrapper from file.'
    global _WRAPPER
    wrapper = pickle_load(open(_PKLFILE, 'rb'))
    if _WRAPPER is None:
        _WRAPPER = wrapper
    else:
        _WRAPPER.__dict__.clear()
        _WRAPPER.__dict__.update(wrapper.__dict__)
    return _WRAPPER

try:
    load_wrapper()
except FileNotFoundError:
    pass


@contextmanager
def _ctx_wrapper():
    dump_wrapper()
    yield _WRAPPER
    load_wrapper()


def get_container(wrapper=None) -> Mapping:
    'Get the sigil containers.'
    if wrapper is None:
        wrapper = _WRAPPER

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
    are_u_sure = input(
        colored('[ASK]', 'red', attrs=['bold']) + ' Reload shell will discrad all '
        'local variables, are you sure ([y]/n)? '
    ).strip()
    if are_u_sure not in ('', 'y', 'Y'):
        return
    argv_ = sys.argv.copy()
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


def back_shell(argv: List[str] = sys.argv) -> None:
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
        namespace = sys._getframe(1).f_locals
    start_specific_python_console(namespace, banner, shell)


reload_to_shell = reload_embeded_shell if _SYSTEM_IS_WINDOWS else reload_shell


def run_env(forcible_execution: bool = False, /) -> None:
    'Run env.py, to inject some configuration and global variables'
    if forcible_execution:
        __import__('builtins')._injectedConsole_RUNPY = False
    run_file(_ENVFILE, sys._getframe(1).f_globals)


def _run_plugin(
    file_or_dir: str, 
    bc: Optional[BookContainer] = None,
):
    if bc is None:
        try:
            bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])
        except KeyError:
            bc = cast(BookContainer, get_container()['edit'])

    container = get_container(deepcopy(bc._w))

    target_dir: str
    target_file: str
    if _path.isdir(file_or_dir):
        target_dir = file_or_dir
        target_file = _path.join(file_or_dir, 'plugin.py')
    else:
        target_file = file_or_dir
        target_dir = _path.dirname(target_file)

    try:
        et = parse_xml_file(_path.join(target_dir, 'plugin.xml'))
    except FileNotFoundError:
        plugin_type = 'edit'
    else:
        plugin_type = et.findtext('type', 'edit')

    if plugin_type not in ('edit', 'input', 'validation', 'output'):
        raise ValueError('Invalid plugin type %r' % plugin_type) from NotImplementedError

    with ctx_load(
            target_file, 
            wdir=target_dir, 
            prefixes_not_clean=(
                *set(__import__('site').PREFIXES), 
                _injectedConsole_PATH['sigil_package_dir'], 
            ), 
        ) as mod, \
        temp_list(sys.argv) as av, \
        _ctx_wrapper() \
    :
        sys.modules['__main__'] = __import__('launcher')
        sys.modules[getattr(mod, '__name__')] = mod
        av[:] = [_injectedConsole_PATH['laucher_file'], 
                 _injectedConsole_PATH['ebook_root'], 
                 _injectedConsole_PATH['outdir'], 
                 plugin_type, target_file]

        bk = container[plugin_type]
        try:
            ret = getattr(mod, 'run')(bk)
            if ret == 0 or type(ret) is not int:
                dump_wrapper(bk._w)
            else:
                # Restore to unmodified (no guarantee of right result)
                dump_wrapper(bc._w)
        except BaseException:
            # Restore to unmodified (no guarantee of right result)
            dump_wrapper(bc._w)
            raise
        return ret


def run_plugin(
    file_or_dir: str, 
    bc: Optional[BookContainer] = None,
    run_in_process: bool = False,
    executable: str = sys.executable,
):
    '''Running a Sigil plug-in

    :param file_or_dir: Path of Sigil plug-in folder or script file.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param run_in_process: Determine whether to run the program in a child process.

    :return: If `run_in_process` is True, return `subprocess.CompletedProcess`, else 
             return the return value of the plugin function.
    '''
    if not _path.exists(file_or_dir):
        raise FileNotFoundError('No such file or directory: %r' % file_or_dir)

    file_or_dir = _path.abspath(file_or_dir)

    if run_in_process:
        with NamedTemporaryFile(suffix='.py', mode='w', encoding='utf-8') as f, _ctx_wrapper():
            f.write(
f'''#!/usr/bin/env python3
# coding: utf-8

exec(open(r'{_ENVFILE}', encoding='utf-8').read(), globals())

try:
    retcode = __import__('plugin_help').function._run_plugin(r'{file_or_dir}', bc)
    print("plugin %r \\n\\t |_ return ➜ %r" % (r'{file_or_dir}', retcode))
    if type(retcode) is not int:
        retcode = 0
except BaseException:
    retcode = -1

if retcode != 0:
    __import__('atexit').unregister(plugin.dump_wrapper)
    __import__('os')._exit(retcode)
''')
            f.flush()
            return subprocess.run(
                [executable, f.name], 
                check=True, shell=_SYSTEM_IS_WINDOWS)
    else:
        return _run_plugin(file_or_dir, bc)


def _run_env_tips(shell=None):
    if shell:
        print('[TIPS] %s' % shell)
    print('Please run the following command first in interactive shell:\n\n\t%run env\n')
    print('在交互式命令行中，请先运行以下命令：\n\n\t%run env\n')


def start_nbterm(
    *args: str, 
    executable: str = sys.executable,
) -> subprocess.CompletedProcess:
    'Start a qtconsole process, and wait until it is terminated.'
    ensure_import('nbterm')
    if not args:
        args = ('RUN FIRST ➜ %run env',)
    with _ctx_wrapper():
        _run_env_tips('nbterm')
        return subprocess.run(
            [executable, '-m', 'nbterm.nbterm', *args], 
            check=True, shell=_SYSTEM_IS_WINDOWS)


def _ensure_pyqt5():
    ensure_import('PyQt5.pyrcc', 'PyQt5')
    ensure_import('PyQt5.sip', 'PyQt5-sip')
    ensure_import('PyQt5.Qt5', 'PyQt5-Qt5')
    ensure_import('PyQt5.QtWebEngine', ('PyQtWebEngine', 'PyQtWebEngine-Qt5'))


def start_qtconsole(
    *args: str, 
    executable: str = sys.executable,
) -> subprocess.CompletedProcess:
    'Start a qtconsole process, and wait until it is terminated.'
    ensure_import('qtconsole')
    _ensure_pyqt5()
    if not args:
        args = ('--FrontendWidget.banner=⏰ RUN COMMAND FIRST\n\t%s\n\n' 
                % colored('%run env', 'red', attrs=['bold', 'blink']),)
    with _ctx_wrapper():
        _run_env_tips('qtconsole')
        return subprocess.run(
            [executable, '-m', 'qtconsole', *args], 
            check=True, shell=_SYSTEM_IS_WINDOWS)


def start_spyder(
    *args: str, 
    executable: str = sys.executable,
) -> subprocess.CompletedProcess:
    'Start a spyder IDE process, and wait until it is terminated.'
    ensure_import('spyder')
    _ensure_pyqt5()
    if not args:
        args = ('-w', _OUTDIR, '--window-title', 'RUN FIRST ➜ %run env')
    with _ctx_wrapper():
        _run_env_tips('spyder')
        return subprocess.run(
            [executable, '-m', 'spyder.app.start', *args], 
            shell=_SYSTEM_IS_WINDOWS)


def start_jupyter_notebook(
    *args: str, 
    executable: str = sys.executable,
) -> subprocess.CompletedProcess:
    'Start a jupyter notebook process, and wait until it is terminated.'
    ensure_import('jupyter')
    if not args:
        args = ('--NotebookApp.notebook_dir="."', '--NotebookApp.open_browser=True', '-y')
    with _ctx_wrapper():
        _run_env_tips('jupyter notebook')
        return prun_module('jupyter', 'notebook', *args)


def start_jupyter_lab(
    *args: str, 
    executable: str = sys.executable,
) -> subprocess.CompletedProcess:
    'Start a jupyter lab process, and wait until it is terminated.'
    ensure_import('jupyterlab')
    if not args:
        args = ('--notebook-dir="."', '--ServerApp.open_browser=True', '-y')
    with _ctx_wrapper():
        _run_env_tips('jupyter lab')
        return prun_module('jupyter', 'lab', *args)


def start_python_shell(shell: str = 'python'):
    'Start a jupyter lab process, and wait until it is terminated.'
    try:
        container = get_container()

        start_specific_python_console(
            {
                'container': container, 
                'bc': container['edit'], 
                'bk': container['edit'], 
                'bookcontainer': container['edit'], 
                'w': _WRAPPER, 
                'wrapper': _WRAPPER, 
                'plugin': __import__('plugin_help'), 
            }, 
            shell=shell, 
        )
        dump_wrapper()
    except BaseException:
        print(colored('[ERROR]', 'red', attrs=['bold']))
        print_exc()
        back_shell()

