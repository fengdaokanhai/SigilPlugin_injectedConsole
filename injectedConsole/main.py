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

from plugin_util.encode_args import b64decode_pickle

_PATH = __import__('builtins')._PATH = b64decode_pickle(args.args)

__import__('os').chdir(_PATH['outdir'])
__import__('sys').path.insert(0, _PATH['sigil_package_dir'])

try:
    from plugin_util import usepip
    from plugin_util.console import start_specific_python_console
    from plugin_util.terminal import start_terminal
    from plugin_help.function import get_container, load_wrapper, dump_wrapper

    # remap cssutils to css_parser
    try:
        __import__('sys').modules['cssutils'] = __import__('css_parser')
    except ImportError:
        pass

    wrapper = load_wrapper()
    container = get_container(wrapper)

    start_specific_python_console(
        {
            'container': container, 
            'bc': container['edit'], 
            'bk': container['edit'], 
            'bookcontainer': container['edit'], 
            'w': wrapper, 
            'wrapper': wrapper, 
            'plugin': __import__('plugin_help'), 
        }, 
        shell=args.shell, 
    )
    dump_wrapper(wrapper)
except BaseException as exc:
    from traceback import print_exc

    from plugin_util.colored import colored
    from plugin_help.function import back_shell

    print(colored('[ERROR]', 'red', attrs=['bold']))
    print_exc()
    back_shell()

