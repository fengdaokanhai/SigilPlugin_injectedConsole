#!/usr/bin/env python3
# coding=utf-8

# Reference:
# https://docs.python.org/3/installing/index.html
# https://packaging.python.org/tutorials/installing-packages/

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

import platform
import subprocess
import warnings

from os import path
from sys import executable
from tempfile import NamedTemporaryFile
from typing import Iterable, Optional, Union
from urllib.parse import urlsplit
from urllib.request import urlopen


__all__ = ['INDEX_URL', 'TRUSTED_HOST', 'install_pip_by_ensurepip', 'install_pip_by_getpip', 
           'install_pip', 'execute_pip', 'install', 'uninstall']


# When using subprocess.run on Windows, you should specify shell=True
_PLATFORM_IS_WINDOWS = platform.system() == 'Windows'
_INSTALL_PIP_SCRIPT_PATH = path.join(path.dirname(__file__), 'get-pip.py')
## The following two may be redundant
# INDEX_URL: Base URL of the Python Package Index (default
#     https://pypi.org/simple). This should point to a
#     repository compliant with PEP 503 (the simple
#     repository API) or a local directory laid out in
#     the same format.
INDEX_URL = 'https://mirrors.aliyun.com/pypi/simple/'
# TRUSTED_HOST: Mark this host or host:port pair as trusted,
#     even though it does not have valid or any HTTPS.
TRUSTED_HOST = 'mirrors.aliyun.com'


def install_pip_by_ensurepip(
    *args: str, 
    check: bool = False,
    executable: str = executable,
) -> subprocess.CompletedProcess:
    ''
    return subprocess.run([executable, '-m', 'ensurepip', *args], 
                        check=check, shell=_PLATFORM_IS_WINDOWS)


def install_pip_by_getpip(
    *args: str, 
    check: bool = False,
    use_local_file: bool = True,
    executable: str = executable,
) -> subprocess.CompletedProcess:
    ''
    if use_local_file:
        return subprocess.run([executable, _INSTALL_PIP_SCRIPT_PATH, *args], 
                              check=check, shell=_PLATFORM_IS_WINDOWS)
    else:
        with NamedTemporaryFile(mode='wb', suffix='.py') as f:
            response = urlopen(
                'https://bootstrap.pypa.io/get-pip.py',
                context=__import__('ssl')._create_unverified_context()
            )
            f.write(response.read())
            f.flush()
            return subprocess.run([executable, f.name, *args], 
                                  check=check, shell=_PLATFORM_IS_WINDOWS)


def install_pip(getpip_first: bool = False) -> None:
    'install pip for execution environment'
    def use_getpip():
        args = []
        index_url = globals().get('INDEX_URL')
        trusted_host = globals().get('TRUSTED_HOST')
        if index_url:
            args.extend(('-i', index_url))
            if not trusted_host:
                trusted_host = urlsplit(index_url).netloc
            args.extend(('--trusted-host', trusted_host))

        install_pip_by_getpip(*args, check=True)

    def use_ensurepip():
        try:
            import ensurepip
        except ImportError:
            warnings.warn('can not import module: ensurepip', ImportWarning)
            raise
        else:
            install_pip_by_ensurepip('--default-pip', check=True)

    if getpip_first:
        try:
            use_getpip()
        except:
            use_ensurepip()
    else:
        try:
            use_ensurepip()
        except:
            use_getpip()


try:
    __import__('pip')
except ImportError:
    if input('There is no pip installed, want you to try to '
             'install pip? [y]/n').strip() in ('', 'y', 'Y'):
        try:
            install_pip()
        except:
            print('Failed to install pip module')

try:
    __import__('pip')
except ImportError:
    def execute_pip(
        args: Union[str, Iterable[str]],
        check: bool = True,
        executable: str = executable,
    ) -> subprocess.CompletedProcess:
        'execute pip in child process'
        raise NotImplementedError('No pip installed')
else:
    def execute_pip(
        args: Union[str, Iterable[str]],
        check: bool = True,
        executable: str = executable,
    ) -> subprocess.CompletedProcess:
        'execute pip in child process'
        command: Union[str, list]
        if isinstance(args, str):
            command = '"%s" -m pip %s' % (executable, args)
            return subprocess.run(command, shell=True)
        else:
            command = [executable, '-m', 'pip', *args]
            return subprocess.run(command, shell=_PLATFORM_IS_WINDOWS)


def install(
    package: str, 
    *other_packages: str,
    upgrade: bool = False,
    index_url: Optional[str] = None,
    trusted_host: Optional[str] = None,
    other_args: Iterable[str] = (),
) -> None:
    'install package with pip'
    cmd = ['install']
    if not index_url:
        index_url = globals().get('INDEX_URL')
        trusted_host = globals().get('TRUSTED_HOST')
    if index_url:
        cmd.extend(('-i', index_url))
        if not trusted_host:
            trusted_host = urlsplit(index_url).netloc
        cmd.extend(('--trusted-host', trusted_host))
    if upgrade:
        cmd.append('--upgrade')
    cmd.extend(other_args)
    cmd.append(package)
    if other_packages:
        cmd.extend(other_packages)
    execute_pip(cmd)


def uninstall(
    package: str, 
    *other_packages: str,
    other_args: Iterable[str] = (),
) -> None:
    'uninstall package with pip'
    execute_pip(['uninstall', *other_args, package, *other_packages])


if __name__ == '__main__':
    execute_pip(__import__('sys').argv[1:])

