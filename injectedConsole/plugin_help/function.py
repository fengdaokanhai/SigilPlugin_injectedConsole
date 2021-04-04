from os import _exit, execl
from pickle import load as pickle_load, dump as pickle_dump
from sys import _getframe, argv, executable
from subprocess import run as sprun
from typing import Any, Mapping

from bookcontainer import BookContainer # type: ignore
from inputcontainer import InputContainer # type: ignore
from outputcontainer import OutputContainer # type: ignore
from validationcontainer import ValidationContainer # type: ignore

from plugin_util.dictattr import DictAttr
from plugin_util.colored import colored
from plugin_util.console import get_current_shell, list_shells, start_specific_python_console
from plugin_util.usepip import install, uninstall, execute_pip


__all__ = [
    'install', 'uninstall', 'execute_pip', 'restart_program', 'abort', 'exit', 
    'dump_wrapper', 'load_wrapper', 'get_container', 'get_current_shell', 
    'list_shells', 'reload_shell', 'reload_embeded_shell', 'reload_to_shell', 
    'start_qtconsole', 'start_jupyter_notebook', 'start_jupyter_lab',
]


WRAPPER: Any = None
_SYSTEM_IS_WINDOWS: bool = __import__('platform').system() == 'Windows'


def restart_program(argv=argv):
    'restart the program'
    execl(executable, executable, *argv)


def abort():
    'Abort console to discard all changes.'
    open('abort.exists', 'wb').close()
    _exit(1)


def exit():
    'Exit console for no more operations.'
    dump_wrapper()
    _exit(0)


def _create_env_py(name='env'):
    open(name + '.py', 'w').write(f'''
# Injecting module pathes
__sys_path = __import__('sys').path
__sys_path.insert(0, '{_PATH['this_plugin_dir']}')
__sys_path.insert(0, '{_PATH['sigil_package_dir']}')
del __sys_path

# Introducing global variables
import plugin_help as plugin
w = wrapper = plugin.load_wrapper()
container = plugin.get_container(wrapper)
bc = bookcontainer = container.edit

__import__('atexit').register(plugin.dump_wrapper)
''')


def dump_wrapper(wrapper=None):
    'Dump wrapper to file.'
    if wrapper is None:
        wrapper = WRAPPER
    return pickle_dump(wrapper, open('wrapper.pkl', 'wb'))


def load_wrapper():
    'Load wrapper from file.'
    global WRAPPER
    WRAPPER = pickle_load(open('wrapper.pkl', 'rb'))
    return WRAPPER


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


def start_qtconsole(executable=executable):
    # TODO: Support for qtconsole: {executable} -m qtconsole arg1 arg2 ...
    _create_env_py()
    return sprun([executable, '-m', 'qtconsole'], 
                 check=True, shell=_SYSTEM_IS_WINDOWS)


# TODO: Implement the following functions
def start_jupyter_notebook(executable=executable):
    # TODO: Support for jupyter notebook: {executable} -m python -m jupyter notebook arg1 arg2 ...
    raise NotImplementedError

def start_jupyter_lab(executable=executable):
    # TODO: Support for jupyter lab: {executable} -m python -m jupyter lab arg1 arg2 ...
    raise NotImplementedError

def runfile(path):
    raise NotImplementedError

def load_file(path):
    raise NotImplementedError

def load_package(path, main_module_name='__init__.py'):
    raise NotImplementedError

def load_zipped_package(path, main_module_name='__init__.py'):
    raise NotImplementedError

