import platform
import subprocess
import warnings

from os import path
from sys import executable
from tempfile import NamedTemporaryFile
from typing import Iterable, Optional, Union
from urllib.parse import urlsplit
from urllib.request import urlopen


__all__ = ['install_pip', 'execute_pip', 'install', 'uninstall']


# When using subprocess.run on Windows, you should specify shell=True
PLATFORM_IS_WINDOWS = platform.system() == 'Windows'

_INSTALL_PIP_SCRIPT_PATH = path.join(path.dirname(__file__), 'get-pip.py')
INDEX_URL = 'https://mirrors.aliyun.com/pypi/simple/'
TRUSTED_HOST = 'mirrors.aliyun.com'


def install_pip(
    executable: str = executable,
    prefix: Optional[str] = None,
    use_local_file: bool = True,
) -> None:
    'install PIP for execution environment'
    # Reference:
    # https://docs.python.org/3/installing/index.html
    # https://packaging.python.org/tutorials/installing-packages/
    try:
        import ensurepip
    except ImportError:
        warnings.warn('can not import module: ensurepip', ImportWarning)
    else:
        result = subprocess.run([executable, '-m', 'ensurepip', '--default-pip'], 
                                shell=PLATFORM_IS_WINDOWS)
        if result.returncode == 0:
            return None
    prefix = '' if prefix is None else '--prefix=%s' % prefix
    if use_local_file:
        subprocess.run([executable, _INSTALL_PIP_SCRIPT_PATH, prefix], 
                       check=True, shell=PLATFORM_IS_WINDOWS)
    else:
        with NamedTemporaryFile(mode='wb', suffix='.py') as f:
            response = urlopen(
                'https://bootstrap.pypa.io/get-pip.py',
                context=__import__('ssl')._create_unverified_context()
            )
            f.write(response.read())
            f.flush()
            subprocess.run([executable, f.name, prefix], 
                           check=True, shell=PLATFORM_IS_WINDOWS)


try:
    __import__('pip')
except ImportError:
    if input('There is no pip installed, want you to try to '
             'install pip [y]/n? ').strip().lower() in ('', 'y'):
        try:
            install_pip()
        except subprocess.CalledProcessError:
            print('Failed to install pip module')

try:
    __import__('pip')
except ImportError:
    def execute_pip(
        args: Union[str, Iterable[str]],
        check: bool = True,
        executable: str = executable,
    ) -> subprocess.CompletedProcess:
        'execute PIP in child process'
        raise NotImplementedError('No pip installed')
else:
    def execute_pip(
        args: Union[str, Iterable[str]],
        check: bool = True,
        executable: str = executable,
    ) -> subprocess.CompletedProcess:
        'execute PIP in child process'
        command: Union[str, list]
        if isinstance(args, str):
            command = '"%s" -m pip %s' % (executable, args)
            return subprocess.run(command, check=check, shell=True)
        else:
            command = [executable, '-m', 'pip', *args]
            return subprocess.run(command, check=check, shell=PLATFORM_IS_WINDOWS)


def install(
    package: str, 
    *other_packages: str,
    upgrade: bool = False,
    index_url: Optional[str] = None,
    trusted_host: Optional[str] = None,
    other_args: Iterable[str] = (),
) -> subprocess.CompletedProcess:
    'install package with PIP'
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
    return execute_pip(cmd)


def uninstall(
    package: str, 
    *other_packages: str,
    other_args: Iterable[str] = (),
) -> subprocess.CompletedProcess:
    'uninstall package with PIP'
    return execute_pip(['uninstall', *other_args, package, *other_packages])


if __name__ == '__main__':
    execute_pip(__import__('sys').argv[1:])

