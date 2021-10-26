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
ap.add_argument('--shell', default=None, help='shell will start')
ap.add_argument(
    '--prev-shell', help='previous shell, if failed to start [--shell], '
                         'it will return to [--prev-shell]'
)
args = ap.parse_args()

if __import__('platform').system() == 'Linux':
    from plugin_util.terminal import _send_pid_to_server
    _send_pid_to_server()

import builtins, os, sys

from typing import Final, Mapping
from types import MappingProxyType


_config: Final[dict] = __import__('json').load(open(args.args))
_injectedConsole_CONFIG: Final[Mapping] = MappingProxyType(_config['config'])
_injectedConsole_PATH: Final[Mapping[str, str]] = MappingProxyType(_config['path'])
setattr(builtins, '_injectedConsole_CONFIG', _injectedConsole_CONFIG)
setattr(builtins, '_injectedConsole_PATH', _injectedConsole_PATH)

sys.path.insert(0, _injectedConsole_PATH['sigil_package_dir'])
os.chdir(_injectedConsole_PATH['outdir'])

from plugin_help import function

os.environ['env'] = function._ENVFILE

from plugin_util import usepip
usepip._update_index_url(_injectedConsole_CONFIG['pip_index_url'])
usepip._update_trusted_host(_injectedConsole_CONFIG['pip_trusted_host'])

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
    function.start_python_shell(shell)

