#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 7)
__revision__ = 3
__all__ = ['run']


import json

from contextlib import contextmanager
from os import chdir, path
from pickle import dump as pickle_dump, load as pickle_load
from sys import argv, executable
from typing import Final, Optional, Tuple

from plugin_util.encode_args import b64encode_pickle
from plugin_util.terminal import start_terminal


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
    'jupyter lab',
    'jupyter notebook',
)


def get_config_webui() -> dict:
    raise NotImplementedError


def get_config_tui() -> dict:
    raise NotImplementedError


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


def _get_config_gui(pipe=None) -> dict:
    import tkinter
    from tkinter import ttk

    def set_shell(*args):
        nonlocal shell
        shell = comboxlist.get()

    with _ctx_conifg() as old_config:
        try:
            shell = old_config['shell']
            shell_idx = SHELLS.index(shell)
        except (KeyError, ValueError):
            shell = 'python'
            shell_idx = 0

        app = tkinter.Tk()
        app.title('Select a shell')
        comvalue = tkinter.StringVar()
        comboxlist = ttk.Combobox(
            app, textvariable=comvalue, state='readonly')
        comboxlist["values"] = SHELLS
        comboxlist.current(shell_idx)
        comboxlist.bind("<<ComboboxSelected>>", set_shell)
        comboxlist.bind("<Return>", lambda *args: app.quit())
        comboxlist.pack()
        app.mainloop()

        config = {'shell': shell}
        old_config.update(config)

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
    laucher_file, ebook_root, outdir, _, target_file = argv
    this_plugin_dir = path.dirname(target_file)

    pathes = dict(
        sigil_package_dir = path.dirname(laucher_file),
        this_plugin_dir   = this_plugin_dir,
        plugins_dir       = path.dirname(this_plugin_dir),
        ebook_root        = ebook_root,
        outdir            = outdir,
    )
    __import__('builtins')._PATH = pathes

    abortfile = path.join(outdir, 'abort.exists')
    envfile = path.join(outdir, 'env.py')
    mainfile = path.join(this_plugin_dir, 'main.py')
    pklfile = path.join(outdir, 'wrapper.pkl')

    pickle_dump(bc._w, open(pklfile, 'wb'))

    open(envfile, 'w', encoding='utf-8').write(
f'''# Injecting builtins variable: _PATH
__import__('builtins')._PATH = {pathes!r}

# Injecting module pathes
__sys_path = __import__('sys').path
__sys_path.insert(0, {pathes['this_plugin_dir']!r})
__sys_path.insert(0, {pathes['sigil_package_dir']!r})
del __sys_path

# Introducing global variables
import plugin_help as plugin
w = wrapper = plugin.load_wrapper()
container = plugin.get_container(wrapper)
bc = bk = bookcontainer = container.edit

# Callback at exit
__import__('atexit').register(plugin.dump_wrapper)

# Execution success information
print(
"""🎉🎉🎉 Environment loaded successfully
🎆🎆🎆 成功加载环境""")
''')

    chdir(outdir)

    config = get_config_gui()
    shell = config['shell']

    if shell == 'qtconsole':
        from plugin_help.function import start_qtconsole
        from plugin_util.usepip import ensure_import

        ensure_import('qtconsole')
        ensure_import('PyQt5.pyrcc', 'PyQt5')
        start_qtconsole()
    else:
        start_terminal([executable, mainfile, '--args', 
                        b64encode_pickle(pathes), '--shell', shell])

    # check whether the console is aborted.
    if path.exists(abortfile):
        return 1
    bc._w = pickle_load(open(pklfile, 'rb'))
    return 0

