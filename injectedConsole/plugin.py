# Reference: 
#   - https://github.com/Sigil-Ebook/Sigil/blob/master/src/Resource_Files/plugin_launchers/python/launcher.py
#   - https://github.com/Sigil-Ebook/Sigil/tree/master/docs

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 5)

import base64
import os
import pickle
import platform
import sys
import traceback
import warnings

from collections import namedtuple
from tempfile import NamedTemporaryFile
from typing import Any, Mapping, Iterable, MutableMapping, Optional, Union

from utils.colored import colored
from utils.console import get_current_shell, list_shells, start_specific_python_console
from utils.dictattr import DictAttr
from utils.terminal import start_terminal


PLATFORM_IS_WINDOWS: bool = platform.system() == 'Windows'

wrapper: Any


def abort():
    'abort console to discard all changes'
    open('abort.exists', 'wb').close()
    os._exit(1)


def exit(status=0):
    '''exit with status, this may lose all modifications,
    please use the exit method (It could be 'exit', 'quit', or Ctrl-D, etc.) 
    provided by the environment
    '''
    os._exit(status)


def check_abort() -> bool:
    'check whether the console is aborted'
    return os.path.exists('abort.exists')


def restart_program(argv=None):
    'restart the program'
    if argv is None:
        argv = sys.argv
    os.execl(sys.executable, sys.executable, *argv)


def reload_to_shell(shell):
    'Restart the program and reload to another shell'
    are_u_sure = input('reload shell will discrad all local variables'
                       ', are you sure? ([y]/n) ').strip()
    if are_u_sure and not are_u_sure.startswith(('y', 'Y')):
        return
    argv = sys.argv.copy()
    try:
        idx = argv.index('--shell')
    except ValueError:
        from utils import console
        prev_shell = getattr(console, '__shell__', None)
        argv.extend(('--shell', shell))
    else:
        prev_shell = argv[idx + 1]
        argv[idx: idx+2] = ['--shell', shell]
    if prev_shell:
        try:
            idx = argv.index('--prev-shell')
        except ValueError:
            argv.extend(('--prev-shell', prev_shell))
        else:
            argv[idx: idx+2] = ['--prev-shell', prev_shell]
    dump_wrapper()
    restart_program(argv)


def reload_to_embeded_shell(shell, namespace=None):
    'reload to another embedded shell'
    if namespace is None:
        namespace = sys._getframe(1).f_locals
    start_specific_python_console(namespace, '', shell)


def back():
    'back to previous shell (if any)'
    argv = sys.argv.copy()
    try:
        idx = argv.index('--prev-shell')
    except ValueError:
        prev_shell = None
    else:
        prev_shell = argv[idx + 1]
        del argv[idx: idx + 2]
    if prev_shell:
        try:
            idx = argv.index('--shell')
        except ValueError:
            argv.extend(('--shell', prev_shell))
        else:
            argv[idx: idx + 2] = ['--shell', prev_shell]
        print(colored('[WARRNING]', 'yellow', attrs=['bold']), 'back to shell:', prev_shell)
        restart_program(argv)


def dump_wrapper(wrapper=None):
    'dump wrapper to file'
    global WRAPPER
    path = os.path.join(PATH.outdir, '_w.pkl')
    if wrapper is None:
        wrapper = WRAPPER
    return pickle.dump(wrapper, open(path, 'wb'))


def load_wrapper():
    'load wrapper from file'
    global WRAPPER
    path = os.path.join(PATH.outdir, '_w.pkl')
    WRAPPER = pickle.load(open(path, 'rb'))
    return WRAPPER


def b64_serialize(obj) -> str:
    'serialize a python object with pickle, and then encode it with base64'
    return base64.b64encode(pickle.dumps(obj)).decode()


def b64_deserialize(string: str):
    'deserialize a string that is serialized from a python object'
    return pickle.loads(base64.b64decode(string.encode()))


def insert_path(path, index=None) -> bool:
    if path not in sys.path:
        if index is None:
            sys.path.append(path)
        else:
            sys.path.insert(index, path)
        return True
    return False


def _get_container() -> Mapping:
    'get the sigil containers'
    from bookcontainer import BookContainer # type: ignore
    from inputcontainer import InputContainer # type: ignore
    from outputcontainer import OutputContainer # type: ignore
    from validationcontainer import ValidationContainer # type: ignore

    global wrapper

    wrapper = load_wrapper()

    # collect the containers
    return DictAttr(
        wrapper    = wrapper,
        edit       = BookContainer(wrapper),
        input      = InputContainer(wrapper),
        validation = ValidationContainer(wrapper),
        output     = OutputContainer(wrapper),
    )


def main(args):
    from utils import usepip

    if PLATFORM_IS_WINDOWS:
        try:
            # 检查能否引入 pip 模块
            __import__('pip')
        except ImportError:
            warnings.warn('can not import pip module', ImportWarning)
            # 如果不能引入，说明可能存在不能安装的原因
            try:
                # USER_BASE 通常是基础模块所在的目录
                # USER_SITE 通常是第三方模块被安装在的 site-packages 目录
                from site import USER_BASE, USER_SITE
            except ImportError:
                warnings.warn('''
在 Windows 平台上，请不要使用 Sigil 自带的 Python 运行环境，因为这是有缺陷的。
建议到官网下载并安装最新版 https://www.python.org/downloads/
。然后点开 【Sigil 软件】->【插件】->【插件管理】 界面，去掉【使用捆绑的python】的打勾
，再点击【识别】按钮，就可以自动识别已安装的 Python 运行环境''')

    global PATH

    os.chdir(PATH.outdir)

    insert_path(PATH['sigil_python_module_path'], 0)
    insert_path(PATH['this_plugin_dir'])
    insert_path(PATH['plugins_dir'])

    # remap cssutils to css_parser
    try:
        import css_parser # type: ignore
        sys.modules['cssutils'] = css_parser
    except ImportError:
        pass

    container = _get_container()

    start_specific_python_console(
        {
            'w': container.wrapper, 
            'wrapper': container.wrapper, 
            'bc': container.edit, 
            'bookcontainer': container.edit, 
            'container': container, 
            'path': PATH, 
            'func': DictAttr(
                abort=abort,
                exit=exit,
                get_current_shell=get_current_shell,
                list_shells=list_shells,
                reload_to_shell=reload_to_embeded_shell 
                                if PLATFORM_IS_WINDOWS
                                else reload_to_shell,
                install=usepip.install,
                uninstall=usepip.uninstall,
                execute_pip=usepip.execute_pip,
            ),
        }, shell=args.shell)
    dump_wrapper(container.wrapper)


def run(bc):
    global PATH

    laucher_file, ebook_root, outdir, _, target_file = sys.argv
    PATH = DictAttr(
        sigil_python_module_path=os.path.dirname(laucher_file),
        ebook_root=ebook_root,
        outdir=outdir,
        this_plugin_file=target_file,
        this_plugin_dir=os.path.dirname(target_file),
        plugins_dir=os.path.dirname(os.path.dirname(target_file)),
    )

    os.chdir(outdir)

    cmd = [sys.executable, sys.argv[4], '--args', b64_serialize(PATH)]
    dump_wrapper(bc._w)
    start_terminal(cmd)
    if check_abort():
        return 1
    bc._w = load_wrapper()
    return 0


if __name__ == '__main__':
    from argparse import ArgumentParser

    ap = ArgumentParser()
    ap.add_argument('--args', required=True)
    ap.add_argument('--shell', help='shell will start')
    ap.add_argument(
        '--prev-shell', help='previous shell, if failed to start [--shell], '
                             'it will return to [--prev-shell]'
    )
    args = ap.parse_args()
    PATH = b64_deserialize(args.args)
    try:
        main(args)
    except BaseException as exc:
        print(colored('[ERROR]', 'red', attrs=['bold']))
        traceback.print_exc()
        back()

