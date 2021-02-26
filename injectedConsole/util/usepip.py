import platform
import subprocess
import warnings

from os import path
from sys import executable
from tempfile import NamedTemporaryFile
from typing import Optional, Tuple, Union
from urllib.parse import urlsplit
from urllib.request import urlopen


__all__ = ['install_pip', 'execute_pip', 'install', 'uninstall']


# When using subprocess.run on Windows, you should specify shell=True
PLATFORM_IS_WINDOWS = platform.system() == 'Windows'

_INSTALL_PIP_SCRIPT_PATH = path.join(path.dirname(__file__), 'get-pip.py')
INDEX_URL = 'https://mirrors.aliyun.com/pypi/simple/'
TRUSTED_HOST = 'mirrors.aliyun.com'


def install_pip(
    use_local_file: bool = True,
    executable: str = executable,
) -> None:
    'install PIP for execution environment'
    if use_local_file:
        subprocess.run([executable, _INSTALL_PIP_SCRIPT_PATH], check=True, shell=PLATFORM_IS_WINDOWS)
    else:
        with NamedTemporaryFile(mode='wb', suffix='.py') as f:
            response = urlopen(
                'https://bootstrap.pypa.io/get-pip.py',
                context=__import__('ssl')._create_unverified_context()
            )
            f.write(response.read())
            f.flush()
            subprocess.run([executable, f.name], check=True, shell=PLATFORM_IS_WINDOWS)


def execute_pip(
    args: Union[str, tuple, list],
    executable: str = executable,
) -> None:
    'execute PIP in child process'
    command: Union[str, list]
    if isinstance(args, str):
        command = '"%s" -m pip %s' % (executable, args)
    else:
        command = [executable, '-m', 'pip', *args]
    subprocess.run(command, check=True, shell=PLATFORM_IS_WINDOWS)


def install(
    package: str, *other_packages: str,
    index_url: Optional[str] = None,
    trusted_host: Optional[str] = None,
    upgrade: bool = False,
    executable: str = executable,
) -> None:
    'install package with PIP'
    if not index_url:
        index_url = INDEX_URL
        trusted_host = TRUSTED_HOST
    cmd = ['install']
    if index_url:
        cmd.extend(('-i', index_url))
        if not trusted_host:
            trusted_host = urlsplit(index_url).netloc
    if trusted_host:
        cmd.extend(('--trusted-host', trusted_host))
    if upgrade:
        cmd.append('--upgrade')
    cmd.append(package)
    if other_packages:
        cmd.extend(other_packages)
    execute_pip(cmd)


def uninstall(
    package: str, *other_packages: str,
    executable: str = executable,
) -> None:
    'uninstall package with PIP'
    execute_pip(['uninstall', package, *other_packages])


try:
    __import__('pip')
except ImportError:
    warnings.warn('An error occurred while importing the '
                  'module pip, try installing it')
    install_pip()


if __name__ == '__main__':
    execute_pip(__import__('sys').argv[1:])

