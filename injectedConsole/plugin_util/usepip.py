#!/usr/bin/env python3
# coding: utf-8

# Reference:
# https://docs.python.org/3/installing/index.html
# https://packaging.python.org/tutorials/installing-packages/
# https://pip.pypa.io/en/stable/

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 3)

import platform
import subprocess

from os import path
from sys import executable
from tempfile import NamedTemporaryFile
from typing import Final, Iterable, List, Optional, Union
from types import ModuleType
from urllib.parse import urlsplit
from urllib.request import urlopen


__all__ = ['check_pip', 'install_pip_by_ensurepip', 'install_pip_by_getpip', 
           'install_pip', 'execute_pip', 'install', 'uninstall', 'ensure_import']


# When using subprocess.run on Windows, you should specify shell=True
_PLATFORM_IS_WINDOWS: Final[bool] = platform.system() == 'Windows'
## The following two may be redundant
# INDEX_URL: Base URL of the Python Package Index (default https://pypi.org/simple). 
#     This should point to a repository compliant with PEP 503 (the simple repository API)
#     or a local directory laid out in the same format.
INDEX_URL: str = 'https://mirrors.aliyun.com/pypi/simple/'
# TRUSTED_HOST: Mark this host or host:port pair as trusted,
#     even though it does not have valid or any HTTPS.
TRUSTED_HOST: str = 'mirrors.aliyun.com'


def check_pip() -> bool:
    'Check if the `pip` package is installed.'
    try:
        # Check whether the `pip` package can be imported
        import pip
    except ImportError:
        # If the `pip` package can't be imported, there may be reasons why it can't be installed
        try:
            ## Check configurations for `site-packages` 
            # USER_BASE: Path to the base directory for the user site-packages.
            # [site.USER_BASE](https://docs.python.org/3/library/site.html#site.USER_BASE)
            # USER_SITE: Path to the user site-packages for the running Python.
            # [site.USER_SITE](https://docs.python.org/3/library/site.html#site.USER_SITE)
            from site import USER_BASE, USER_SITE
        except ImportError:
            print('''Defective Python executable detected.
Please replace a Python executable with `pip` package, 
or it can install `pip` package (the `site` module defines available `USER_BASE` and `USER_SITE`).

Python official download address: https://www.python.org/downloads/

Tips: If you installed Python from source, with an installer from python.org, 
you should already have `pip`. If you installed using your OS package manager, 
`pip` may have been installed, or you can install separately by the same package manager.''')
            return False
        else:
            if input('There is no pip installed, do you want to try to '
                     'install pip? [y]/n ').strip() in ('', 'y', 'Y'):
                try:
                    install_pip()
                except:
                    print('Failed to install pip module')
                    return False
            else:
                return False
    return True


def install_pip_by_ensurepip(
    *args: str, 
    check: bool = False,
    executable: str = executable,
) -> subprocess.CompletedProcess:
    '''Install `pip` package using `ensurepip` package.
    Reference:
        - https://docs.python.org/3/library/ensurepip.html
        - https://packaging.python.org/tutorials/installing-packages/#ensure-you-can-run-pip-from-the-command-line
    '''
    return subprocess.run([executable, '-m', 'ensurepip', *args], 
                          check=check, shell=_PLATFORM_IS_WINDOWS)


def install_pip_by_getpip(
    *args: str, 
    check: bool = False,
    executable: str = executable,
) -> subprocess.CompletedProcess:
    '''Install `pip` package using bootstrapping script.
    Reference:
        - https://bootstrap.pypa.io/get-pip.py
        - https://packaging.python.org/tutorials/installing-packages/#ensure-you-can-run-pip-from-the-command-line
    '''
    with NamedTemporaryFile(mode='wb', suffix='.py') as f:
        response = urlopen(
            'https://bootstrap.pypa.io/get-pip.py',
            context=__import__('ssl')._create_unverified_context()
        )
        f.write(response.read())
        f.flush()
        return subprocess.run([executable, f.name, *args], 
                              check=check, shell=_PLATFORM_IS_WINDOWS)


def install_pip(executable: str = executable) -> None:
    'Install `pip` package.'
    try:
        # https://docs.python.org/3/installing/index.html#pip-not-installed
        install_pip_by_ensurepip('--default-pip', check=True, executable=executable)
    except:
        args: List[str] = []
        index_url = globals().get('INDEX_URL')
        trusted_host = globals().get('TRUSTED_HOST')
        if index_url:
            args.extend(('-i', index_url))
            if not trusted_host:
                trusted_host = urlsplit(index_url).netloc
            args.extend(('--trusted-host', trusted_host))

        install_pip_by_getpip(*args, check=True, executable=executable)


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
    /, 
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
    /, 
    *other_packages: str,
    other_args: Iterable[str] = (),
) -> None:
    'uninstall package with pip'
    execute_pip(['uninstall', *other_args, package, *other_packages])


def ensure_import(
    module: str, 
    depencies: Union[None, str, Iterable[str]]= None,
) -> ModuleType:
    '''Import the `module`, if it does not exist, try to install the `depencies`, 
    and then import it again.'''
    try:
        return __import__(module)
    except ModuleNotFoundError:
        if depencies is None:
            depencies = module,
        elif isinstance(depencies, str):
            depencies = depencies,
        install(*depencies)
        return __import__(module)


check_pip()

if __name__ == '__main__':
    execute_pip(__import__('sys').argv[1:])

