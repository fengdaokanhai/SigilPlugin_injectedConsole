#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 6)
__stage__ = 'rev6'

from os import chdir, path
from pickle import dump as pickle_dump, load as pickle_load
from sys import argv, executable

from plugin_util.encode_args import b64encode_pickle
from plugin_util.terminal import start_terminal


def run(bc):
    laucher_file, ebook_root, outdir, _, target_file = argv
    this_plugin_dir = path.dirname(target_file)

    pathes = dict(
        sigil_package_dir = path.dirname(laucher_file),
        this_plugin_dir   = this_plugin_dir,
        plugins_dir       = path.dirname(this_plugin_dir),
        ebook_root        = ebook_root,
        outdir            = outdir,
    )

    abortfile = path.join(outdir, 'abort.exists')
    envfile = path.join(outdir, 'env.py')
    mainfile = path.join(this_plugin_dir, 'main.py')
    pklfile = path.join(outdir, 'wrapper.pkl')

    pickle_dump(bc._w, open(pklfile, 'wb'))

    open(envfile, 'w').write(
f'''# Injecting builtins variable: _PATH
__import__('builtins')._PATH = {pathes!r}

# Injecting module pathes
__sys_path = __import__('sys').path
__sys_path.insert(0, '{pathes['this_plugin_dir']}')
__sys_path.insert(0, '{pathes['sigil_package_dir']}')
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
    cmd = [executable, mainfile, '--args', b64encode_pickle(pathes)]
    # TODO: tui, gui, webui
    start_terminal(cmd)

    # check whether the console is aborted.
    if path.exists(abortfile):
        return 1
    bc._w = pickle_load(open(pklfile, 'rb'))
    return 0

