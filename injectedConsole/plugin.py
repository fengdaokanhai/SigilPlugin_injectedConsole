#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 8)
__revision__ = 0
__all__ = ['run']

import builtins
import json
import sys

from contextlib import contextmanager
from os import chdir, path, remove, symlink
from typing import Final, Optional, Tuple
from types import MappingProxyType

from plugin_util.xml_tkinter import TkinterXMLConfigParser


MUDULE_DIR: Final[str] = path.dirname(path.abspath(__file__))
CONFIG_JSON_FILE: Final[str] = path.join(MUDULE_DIR, 'config.json')
SHELLS: Final[Tuple[str, ...]] = (
    'python',
    'ipython',
    'bpython',
    'ptpython',
    'ptipython',
    'nbterm',
    'qtconsole',
    'spyder',
    'jupyter lab',
    'jupyter notebook',
)


def _rm(path) -> bool:
    try:
        remove(path)
        return True
    except FileNotFoundError:
        return True
    except BaseException:
        return False


@contextmanager
def _ctx_conifg():
    try:
        config = json.load(open(CONFIG_JSON_FILE, encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}

    old_config = config.copy()

    yield config

    if old_config != config:
        json.dump(config, open(CONFIG_JSON_FILE, 'w', encoding='utf-8'))


def get_config_webui() -> dict:
    raise NotImplementedError


def get_config_tui() -> dict:
    raise NotImplementedError


def _get_config_gui(pipe=None) -> dict:
    with _ctx_conifg() as config:
        config.setdefault('shell', SHELLS[0])
        config.setdefault('errors', 'ignore')
        config.setdefault('startup', [])

        tkapp = TkinterXMLConfigParser(
            path.join(MUDULE_DIR, 'plugin_src', 'config.xml'), 
            {'config': config, 'SHELLS': SHELLS}
        )
        tkapp.start()

        if pipe:
            pipe.send(config)
        return config


def get_config_gui(new_process: bool = True) -> dict:
    if new_process:
        import multiprocessing

        main_end, sub_end = multiprocessing.Pipe(duplex=False)
        try:
            p = multiprocessing.Process(
                target=_get_config_gui, args=(sub_end,))
            p.start()
            p.join()
            return main_end.recv()
        finally:
            main_end.close()
            sub_end.close()
    else:
        return _get_config_gui()


def run(bc) -> Optional[int]:
    config = get_config_gui()

    laucher_file, ebook_root, outdir, _, target_file = sys.argv
    this_plugin_dir = path.dirname(target_file)
    sigil_package_dir = path.dirname(laucher_file)

    pathes = dict(
        laucher_file      = laucher_file,
        sigil_package_dir = sigil_package_dir,
        this_plugin_dir   = this_plugin_dir,
        plugins_dir       = path.dirname(this_plugin_dir),
        ebook_root        = ebook_root,
        outdir            = outdir,
    )

    abortfile = path.join(outdir, 'abort.exists')
    envfile = path.join(outdir, 'env.py')
    envfile_link = path.expanduser('~/env.py')
    argsfile = path.join(outdir, 'args.pkl')
    mainfile = path.join(this_plugin_dir, 'main.py')

    setattr(builtins, '_injectedConsole_PATH', MappingProxyType(pathes))
    setattr(builtins, '_injectedConsole_STARTUP', tuple(config['startup']))

    from plugin_help import function

    function._WRAPPER = bc._w
    function.dump_wrapper(bc._w)

    open(envfile, 'w', encoding='utf-8').write(
f'''#!/usr/bin/env python3
# coding: utf-8
import builtins as __builtins

if getattr(__builtins, '_injectedConsole_RUNPY', False):
    print("""
    🦶🦶🦶 Environment had been loaded, ignoring
    🏃🏃🏃 环境早已被加载，忽略
""")
else:
    # Injecting builtins variable: _injectedConsole_PATH
    __builtins._injectedConsole_PATH = __import__('types').MappingProxyType({pathes!r})
    # Injecting builtins variable: _injectedConsole_STARTUP
    __builtins._injectedConsole_STARTUP = {tuple(config['startup'])!r}

    # Injecting module pathes
    __sys_path = __import__('sys').path
    __sys_path.insert(0, r'{this_plugin_dir}')
    __sys_path.insert(0, r'{sigil_package_dir}')
    del __sys_path

    __import__('os').chdir(r'{outdir}')

    # Introducing global variables
    import plugin_help as plugin
    w = wrapper = plugin.function._WRAPPER
    container = plugin.get_container(wrapper)
    bc = bk = bookcontainer = container.edit

    # Callback at exit
    __import__('atexit').register(plugin.dump_wrapper)

    # Perform startup scripts
    plugin.function._startup(
        _injectedConsole_STARTUP, 
        globals(), 
        r'{config['errors']}', 
    )

    # Execution success information
    print("""
    🎉🎉🎉 Environment loaded successfully
    🎆🎆🎆 成功加载环境
""")
    __builtins._injectedConsole_RUNPY = True

del __builtins
''')

    _rm(envfile_link)
    symlink(envfile, envfile_link)

    chdir(outdir)

    try:
        shell = config['shell']
        if shell == 'qtconsole':
            function.start_qtconsole()
        elif shell == 'spyder':
            function.start_spyder()
        else:
            from plugin_util.terminal import start_terminal

            __import__('pickle').dump(
                {
                    'path': pathes, 
                    'startup': tuple(config['startup']), 
                    'errors': config['errors'], 
                }, 
                open(argsfile, 'wb'), 
            )
            start_terminal([
                sys.executable, mainfile, 
                '--args', argsfile, 
                '--shell', shell, 
            ])
    finally:
        _rm(envfile_link)

    # check whether the console is aborted.
    if path.exists(abortfile):
        return 1

    function.load_wrapper()

    return 0

