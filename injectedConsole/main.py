#!/usr/bin/env python3
# coding: utf-8

# Reference: 
#   - https://github.com/Sigil-Ebook/Sigil/blob/master/src/Resource_Files/plugin_launchers/python/launcher.py
#   - https://github.com/Sigil-Ebook/Sigil/tree/master/docs

if __name__ != '__main__':
    raise RuntimeError('main.py can only run as a main file')

from argparse import ArgumentParser

ap = ArgumentParser(description='injectedConsole main.py')
ap.add_argument('--args', required=True)
ap.add_argument('--shell', help='shell will start')
ap.add_argument(
    '--prev-shell', help='previous shell, if failed to start [--shell], '
                         'it will return to [--prev-shell]'
)
args = ap.parse_args()

from typing import Final, Mapping

from plugin_util.encode_args import b64decode_pickle
from plugin_util.usepip import ensure_import

import builtins as __builtins
_injectedConsole_PATH: Final[Mapping[str, str]] = b64decode_pickle(args.args)
setattr(__builtins, '_injectedConsole_PATH', _injectedConsole_PATH)

__import__('os').chdir(_injectedConsole_PATH['outdir'])
__import__('sys').path.insert(0, _injectedConsole_PATH['sigil_package_dir'])

from plugin_help import function

shell: str = args.shell
if shell == 'nbterm':
    function.start_nbterm()
elif shell == 'qtconsole':
    function.start_qtconsole()
elif shell == 'spyder':
    function.start_spyder()
elif shell == 'jupyter notebook':
    function.start_jupyter_notebook()
elif shell == 'jupyter lab':
    function.start_jupyter_lab()
else:
    setattr(__builtins, '_injectedConsole_RUNPY', True)
    function.start_python_shell(shell)

