#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['restart_program', 'run', 'load', 'prun']


import re
import subprocess
import sys

from os import execl, getcwd, path as _path
from sys import argv, executable
from typing import Any, Dict, Optional, Tuple, Type, Union
from types import CodeType, ModuleType
from urllib.parse import unquote
from urllib.request import urlopen

from .temporary import temp_wdir, temp_sys_modules


def _startswith_protocol(
    path: Union[bytes, str], 
    _cre=re.compile('^[_a-zA-Z][_a-zA-Z0-9]+://'),
    _creb=re.compile(b'^[_a-zA-Z][_a-zA-Z0-9]+://'),
) -> bool:
    if isinstance(path, bytes):
        return _creb.match(path) is not None
    else:
        return _cre.match(path) is not None


def restart_program(argv=argv):
    'restart the program'
    execl(executable, executable, *argv)


def run(
    path: str, 
    namespace: Optional[dict] = None, 
    wdir: Optional[str] = None, 
    mainfile: Union[str, Tuple[str, ...]] = ('__main__.py', 'main.py', '__init__.py'),
) -> Dict[str, Any]:
    '''Run a [file] / [mainfile in directory], from a [file] | [url] | [directory].

    :param path: The path of file or directory of the python script.
    :param namespace: Execute the given source in the context of namespace.
                      If it is None (the default), will create a new dict().
    :param wdir: Temporay working directory, if it is None (the default), 
                 then use the current working directory.
    :param mainfile: If the `path` is a directory, according to this parameter, 
                     an existing main file will be used.

    :return: Dictionary of script execution results.
    '''
    # If you want to run as main module, set namespace['__name__'] = '__main__'
    # TODO: run a .zip or .egg file
    if wdir is None:
        wdir = getcwd()
    else:
        wdir = _path.abspath(wdir)

    if _startswith_protocol(path):
        file_ = path = unquote(path)
        mdir = None
        module_name = _path.splitext(_path.basename(path))[0]
        package_name = ''
        source = urlopen(path).read().decode('utf-8')
    else:
        file_ = path = _path.abspath(path)
        if _path.isdir(path):
            mdir = path
            module_name = package_name = _path.basename(path)
            if isinstance(mainfile, str):
                file_ = _path.join(path, mainfile)
            else:
                notfound_files = []
                for mainfile_ in mainfile:
                    file_ = _path.join(path, mainfile_)
                    if _path.exists(file_):
                        break
                    notfound_files.append(file_)
                else:
                    raise FileNotFoundError(notfound_files)
        else:
            mdir = _path.dirname(path)
            module_name = _path.splitext(_path.basename(path))[0]
            package_name = ''

        source = open(file_).read()

    if namespace is None:
        namespace = {'__name__': module_name}
    elif not namespace.get('__name__'):
        namespace['__name__'] = module_name

    namespace['__file__'] = file_
    namespace['__package__'] = package_name

    with temp_sys_modules(mdir):
        code: CodeType = compile(source, path, 'exec')
        if wdir == getcwd():
            exec(code, namespace)
        else:
            with temp_wdir(wdir):
                exec(code, namespace)

    return dict(path=path, code=code, namespace=namespace)


def load(
    path: str, 
    wdir: Optional[str] = None,
    mainfile: Union[str, Tuple[str, ...]] = '__init__.py',
    as_sys_module: bool = False,
) -> ModuleType:
    '''Load a [module] | [package], from a [file] | [directory] | [url].

    :param path: The path of file or directory of the python script.
    :param wdir: Temporay working directory, if it is None (the default), 
                 then use the current working directory.
    :param mainfile: If the `path` is a directory, according to this parameter, 
                     an existing main file will be used.
    :param as_sys_module: If True, module will be set to sys.modules.

    :return: A new module.
    '''
    # TODO: load a .zip or .egg file
    mod: ModuleType = ModuleType('')
    info: Dict[str, Any] = run(path, mod.__dict__, wdir=wdir, mainfile=mainfile)

    if as_sys_module:
        sys.modules[info['path']] = mod

    return mod


def prun(
    *popenargs,
    input: Optional[bytes] = None, 
    capture_output: bool = False, 
    timeout: Union[None, int, float] = None, 
    check: bool = False, 
    continue_with_exceptions: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = (),
    **kwargs,
) -> subprocess.CompletedProcess:
    """
    Run command with arguments and return a CompletedProcess instance.
    # Fork from: subprocess.run

    The returned instance will have attributes args, returncode, stdout and
    stderr. By default, stdout and stderr are not captured, and those attributes
    will be None. Pass stdout=PIPE and/or stderr=PIPE in order to capture them.

    When a exception occurs, if type of the exception is contained in `continue_with_exceptions`, 
    the program will ignore the exception and continue to execute.

    If check is True and the exit code was non-zero, it raises a
    CalledProcessError. The CalledProcessError object will have the return code
    in the returncode attribute, and output & stderr attributes if those streams
    were captured.

    If timeout is given, and the process takes too long, a TimeoutExpired
    exception will be raised.

    There is an optional argument "input", allowing you to
    pass bytes or a string to the subprocess's stdin.  If you use this argument
    you may not also use the Popen constructor's "stdin" argument, as
    it will be used internally.

    By default, all communication is in bytes, and therefore any "input" should
    be bytes, and the stdout and stderr will be bytes. If in text mode, any
    "input" should be a string, and stdout and stderr will be strings decoded
    according to locale encoding, or by "encoding" if set. Text mode is
    triggered by setting any of text, encoding, errors or universal_newlines.

    The other arguments are the same as for the Popen constructor.
    """
    if input is not None:
        if kwargs.get('stdin') is not None:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = subprocess.PIPE

    if capture_output:
        if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
            raise ValueError('stdout and stderr arguments may not be used '
                             'with capture_output.')
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE

    with subprocess.Popen(*popenargs, **kwargs) as process:
        while True:
            try:
                stdout, stderr = process.communicate(input, timeout=timeout)
                break
            except continue_with_exceptions:
                continue
            except subprocess.TimeoutExpired as exc:
                process.kill()
                if subprocess._mswindows: # type: ignore
                    # Windows accumulates the output in a single blocking
                    # read() call run on child threads, with the timeout
                    # being done in a join() on those threads.  communicate()
                    # _after_ kill() is required to collect that and add it
                    # to the exception.
                    exc.stdout, exc.stderr = process.communicate()
                else:
                    # POSIX _communicate already populated the output so
                    # far into the TimeoutExpired exception.
                    process.wait()
                raise
            except:  # Including KeyboardInterrupt, communicate handled that.
                process.kill()
                # We don't call process.wait() as .__exit__ does that for us.
                raise
        retcode = process.poll()
        if check and retcode:
            raise subprocess.CalledProcessError(
                retcode, process.args, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(process.args, retcode, stdout, stderr) # type: ignore

