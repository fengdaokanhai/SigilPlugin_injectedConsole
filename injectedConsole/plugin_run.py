#!/usr/bin/env python3
# coding: utf-8

__all__ = ['run']

# TODO: Allow users to set the configuration of `pip`
# TODO: Allow users to create `venv`

import builtins
import json
import sys

from contextlib import contextmanager
from importlib import import_module
from os import path
from typing import Final, Optional, Tuple
from types import MappingProxyType

from plugin_util.run import run_in_process


_IS_MACOS = __import__('platform').system() == 'Darwin'
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


def _import_all(mod_name):
    mod = import_module(mod_name)
    get = mod.__dict__.get
    return {k: get(k) for k in mod.__all__}


'''
@contextmanager
def _ctx_conifg():
    try:
        old_config = json.load(open(CONFIG_JSON_FILE, encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        old_config = {}

    config = deepcopy(old_config)
    yield config

    if old_config != config:
        json.dump(config, open(CONFIG_JSON_FILE, 'w', encoding='utf-8'), ensure_ascii=False)
'''


@contextmanager
def _ctx_conifg(bc):
    config = bc.getPrefs()
    yield config
    bc.savePrefs(config)


def update_config_webui() -> dict:
    raise NotImplementedError


def update_config_tui() -> dict:
    raise NotImplementedError


def update_config_gui_tk(
    # Tips: After closing the `tkinter` GUI in Mac OSX, it will get stuck, 
    # so I specify to run the `tkinter` GUI in a new process.
    config: dict, 
    new_process: bool = _IS_MACOS, 
) -> dict:
    try:
        from plugin_util.xml_tkinter import TkinterXMLConfigParser
    except ImportError:
        __import__('traceback').print_exc(file=sys.stdout)
        print('WARNING:', 'Probably cannot import `tkinter` module, skipping configuration...')
        return {}
    if new_process:
        config_new = run_in_process(update_config_gui_tk, config, False)
        config.clear()
        config.update(config_new)
        return config
    else:
        if 'config' not in config:
            config['config'] = {'shell': 'python', 'errors': 'ignore', 'startup': []}
        if 'configs' not in config:
            config['configs'] = []
        namespace = _import_all('plugin_util.tkinter_extensions')
        namespace.update(config=config, SHELLS=SHELLS)

        tkapp = TkinterXMLConfigParser(
            path.join(MUDULE_DIR, 'plugin_src', 'config.xml'), namespace)
        tkapp.start()
        return config


def update_config_gui_qt(new_process: bool = _IS_MACOS) -> dict:
    raise NotImplementedError


def run(bc) -> Optional[int]:
    with _ctx_conifg(bc) as config:
        config = update_config_gui_tk(config).get('config')

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
    config['path'] = pathes

    setattr(builtins, '_injectedConsole_PATH', MappingProxyType(pathes))
    setattr(builtins, '_injectedConsole_CONFIG', config)

    abortfile    = path.join(outdir, 'abort.exists')
    envfile      = path.join(outdir, 'env.py')
    argsfile     = path.join(outdir, 'args.pkl')
    mainfile     = path.join(this_plugin_dir, 'plugin_main.py')

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
    # Injecting builtins variable: _injectedConsole_CONFIG
    __builtins._injectedConsole_CONFIG = __import__('json').loads({json.dumps(config)!r})

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
    plugin.function._startup(globals())

    # Execution success information
    print("""
    🎉🎉🎉 Environment loaded successfully
    🎆🎆🎆 成功加载环境
""")
    __builtins._injectedConsole_RUNPY = True

del __builtins
''')
    print('WARNING:', 'Created environment initialization script file\n%r\n' %envfile)

    __import__('os').chdir(outdir)

    shell = config.get('shell')
    if shell == 'qtconsole':
        function.start_qtconsole()
    elif shell == 'spyder':
        function.start_spyder()
    else:
        from plugin_util.terminal import start_terminal

        json.dump(config, open(argsfile, 'w'))
        args = [sys.executable, mainfile, '--args', argsfile]
        if shell:
            args.extend(('--shell', shell))
        kwds = {}
        if config.get('terminal'):
            kwds['app'] = config['terminal']
        if config.get('terminal_args'):
            kwds['app_args'] = config['terminal_args']
        kwds['wait'] = config.get('terminal_wait', True)
        start_terminal(args, **kwds)

    # check whether the console is aborted.
    if path.exists(abortfile):
        return 1

    function.load_wrapper()

    return 0

