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

_PATH = __builtins__._PATH = b64decode_pickle(args.args)

from os import chdir
from sys import path

chdir(_PATH['outdir'])

path.insert(0, _PATH['this_plugin_dir'])
path.insert(0, _PATH['sigil_package_dir'])

try:
    from warnings import warn

    from plugin_util import usepip
    from plugin_util.console import start_specific_python_console
    from plugin_util.terminal import start_terminal
    from plugin_help.function import get_container, load_wrapper, dump_wrapper

    if __import__('platform').system() == 'Windows':
        try:
            # 检查能否引入 pip 模块
            __import__('pip')
        except ImportError:
            warn('can not import pip module', ImportWarning)
            # 如果不能引入，说明可能存在不能安装的原因
            try:
                # USER_BASE 通常是基础模块所在的目录
                # USER_SITE 通常是第三方模块被安装在的 site-packages 目录
                from site import USER_BASE, USER_SITE
            except ImportError:
                warn('''
在 Windows 平台上，请不要使用 Sigil 自带的 Python 运行环境，因为这是有缺陷的。
建议到官网下载并安装最新版 https://www.python.org/downloads/
。然后点开 【Sigil 软件】->【插件】->【插件管理】 界面，去掉【使用捆绑的python】的打勾
，再点击【识别】按钮，就可以自动识别已安装的 Python 运行环境''')

    # remap cssutils to css_parser
    try:
        import css_parser # type: ignore
        __import__('sys').modules['cssutils'] = css_parser
    except ImportError:
        pass

    wrapper = load_wrapper()
    container = get_container(wrapper)

    start_specific_python_console({
            'container': container, 
            'bc': container['edit'], 
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

