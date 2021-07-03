#!/usr/bin/env python3
# coding: utf-8

# Reference:
#   - https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/introduction/ASLR_intro.html
#   - https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/
#   - https://en.wikibooks.org/wiki/AppleScript_Programming
#   - https://linux.die.net/man/8/update-alternatives


__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 3)

import json
import platform
import re
import socket

from contextlib import contextmanager
from enum import Enum
from os import getcwd, getpid, remove, path as _path
from shlex import quote as shlex_quote
from subprocess import run as sprun, CompletedProcess
from tempfile import NamedTemporaryFile
from threading import Thread
from typing import (
    cast, Dict, Final, List, Optional, Sequence, Tuple, Union
)

from .cm import ensure_cm
from .shell_util import exists_execfile
from .run import wait_for_pid

try:
    from shlex import join as shlex_join # type: ignore
except ImportError:
    def shlex_join(split_command: Sequence[str]) -> str: # type: ignore
        """Return a shell-escaped string from *split_command*."""
        return ' '.join(map(shlex_quote, split_command))


__all__ = ['start_terminal', 'shlex_quote', 'shlex_join', 'winsh_quote', 'winsh_join', 
           'start_windows_terminal', 'start_linux_terminal', 'AppleScriptWaitEvent', 
           'start_macosx_terminal', 'open_macosx_terminal']


_CURDIR: Final[str] = getcwd()
_ENV_WAIT_PID_FILE = _path.join(_CURDIR, 'env_wait_pid.json')


def winsh_quote(part, _cre=re.compile(r'\s')):
    'Return a shell-escaped string.'
    part = part.strip().replace(r'"', r'\"')
    if _cre.search(part) is not None:
        part = r'"%s"' % part
    return part


def winsh_join(split_command: Sequence[str]) -> str:
    'Return a shell-escaped string from *split_command*.'
    return ' '.join(map(winsh_quote, split_command))


def start_terminal(cmd, **kwargs) -> CompletedProcess:
    'Start a terminal emulator in current OS platform.'
    sys = platform.system()
    if sys == 'Windows':
        return start_windows_terminal(cmd, **kwargs)
    elif sys == 'Darwin':
        return start_macosx_terminal(cmd, **kwargs)
    elif sys == 'Linux':
        return start_linux_terminal(cmd, **kwargs)
    else:
        raise NotImplementedError(
            'start terminal of other system %r is unavailable' % sys)


def start_windows_terminal(
    cmd: Union[str, Sequence[str]], 
    app: Optional[str] = 'powershell',
    app_args: Union[None, Sequence[str]] = None,
    wait: bool = True,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.cmd',
) -> CompletedProcess:
    'Start a terminal emulator in Windows.'
    split_command: List[str] = ['start']
    if wait:
        split_command.append('/wait')
    if app:
        split_command.append(app)
        if app_args is None:
            if app in ('cmd', 'cmd.exe'):
                split_command.append('/c')
        else:
            split_command.extend(app_args)
    if with_tempfile:
        # In Windows, file is occupied when is opening, until it is closed.
        # Like lock, anyone cannot open the file while it is occupied.
        # So we should close it first, then give it to any other, and finally delete it.
        f = NamedTemporaryFile(suffix=tempfile_suffix, mode='w', delete=False)
        try:
            with f:
                if not isinstance(cmd, str):
                    cmd = cast(str, winsh_join(cmd))
                f.write(cmd)
            if app in ('powershell', 'powershell.exe'):
                # Reference::
                # [The call operator &](https://ss64.com/ps/call.html)
                split_command.append('&' + winsh_quote(f.name))
            else:
                split_command.append(winsh_quote(f.name))
            return sprun(split_command, check=True, shell=True)
        finally:
            # TODO: We may need to wait until the file is no longer 
            #       occupied before deleting it.
            try:
                remove(f.name)
            except FileNotFoundError:
                pass
    if isinstance(cmd, str):
        if app in ('powershell', 'powershell.exe') and cmd.strip():
            split_command.append('&')
        return sprun(
            winsh_join(split_command) + ' ' + cmd, 
            check=True, shell=True)
    else:
        if cmd:
            if app in ('powershell', 'powershell.exe'):
                split_command.append('& ' + winsh_quote(cmd[0]))
                split_command.extend(cmd[1:])
            else:
                split_command.extend(cmd)
        return sprun(split_command, check=True, shell=True)


@contextmanager
def _wait_for_client(timeout=10):
    def wait():
        pid: int = 0
        try:
            try:
                server.listen(1)
                client, _ = server.accept()
                try:
                    pid = int(client.recv(1024) or 0)
                finally:
                    client.close()
            except socket.timeout:
                pass
            finally:
                server.close()
        finally:
            try:
                remove(_ENV_WAIT_PID_FILE)
            except FileNotFoundError:
                pass

        if pid:
            wait_for_pid(pid)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for port in range(10000, 65536):
        try:
            server.bind(('localhost', port))
            break
        except OSError:
            pass
    else:
        raise OSError('cannot bind port 10000-65535')

    server.settimeout(timeout)

    json.dump({'port': port}, open(_ENV_WAIT_PID_FILE, 'w'))

    t = Thread(target=wait, daemon=True)
    t.start()

    yield port

    t.join()


def _send_pid_to_server():
    try:
        env = json.load(open(_ENV_WAIT_PID_FILE))
    except FileNotFoundError:
        return

    port = env['port']

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(('localhost', port))
    except:
        return
    try:
        client.send(str(getpid()).encode('ascii'))
    finally:
        client.close()


def start_linux_terminal(
    cmd: Union[str, Sequence[str]], 
    app: Optional[str] = None, 
    app_args: Union[None, Sequence[str]] = None, 
    wait: bool = True, 
    with_tempfile: bool = False, 
    tempfile_suffix: str = '.sh', 
    shebang: str = '#!/bin/sh', 
) -> CompletedProcess:
    'Start a terminal emulator in Linux.'
    terminal_apps: Tuple[str, ...] = (
        'gnome-terminal',      # GNOME
        'konsole',             # KDE
        'xfce4-terminal',      # XFCE
        'lxterminal',          # LXDE
        # Other popular terminal emulators
        'terminator', 'rxvt', 'xterm', 
    )

    terminal_app_execute_args: Dict[str, List[str]] = {
        # https://linuxcommandlibrary.com/man/gnome-terminal
        'gnome-terminal': ['--'], 
        # https://linuxcommandlibrary.com/man/konsole
        'konsole': ['-e'], 
        # https://linuxcommandlibrary.com/man/xfce4-terminal
        'xfce4-terminal': ['-x'], 
        # https://linuxcommandlibrary.com/man/lxterminal
        'lxterminal': ['-e'], 
        # https://linux.die.net/man/1/terminator
        'terminator': ['-x'], 
        # https://linux.die.net/man/1/rxvt
        'rxvt': ['-e'], 
        # https://linux.die.net/man/1/xterm
        'xterm': ['-e']
    }

    if app is None:
        # Debian Series
        # https://helpmanual.io/man1/x-terminal-emulator/
        if exists_execfile('x-terminal-emulator'):
            from .shell_util import get_debian_default_app
            app = get_debian_default_app('x-terminal-emulator')
        else:
            for app in terminal_apps:
                if exists_execfile(app):
                    break
            else:
                raise NotImplementedError('Failed to detect the terminal app, '
                                          'please specify one')
        app = cast(str, app)
    split_command: List[str] = [app]
    if app_args is None:
        app_name = app.rsplit('/', 1)[-1]
        app_args = cast(List[str], terminal_app_execute_args.get(app_name, []))
    split_command.extend(app_args)
    with ensure_cm(_wait_for_client() if wait else None) as port:
        if with_tempfile:
            with NamedTemporaryFile(suffix=tempfile_suffix, mode='w') as f:
                sprun(['chmod', '+x', f.name], check=True)
                if not isinstance(cmd, str):
                    cmd = cast(str, shlex_join(cmd))
                f.write('%s\n%s\n' % (shebang, cmd))
                f.flush()
                split_command.append(f.name)
                return sprun(split_command, check=True)
        if isinstance(cmd, str):
            return sprun(shlex_join(split_command) + ' ' + cmd, 
                         check=True, shell=True)
        else:
            split_command.extend(cmd)
            return sprun(split_command, check=True)


AppleScriptWaitEvent = Enum('AppleScriptWaitEvent', ('exists', 'busy'))


def _get_wait_for_str(
    event: Union[int, str, AppleScriptWaitEvent],
    _wait_for_str: Dict[AppleScriptWaitEvent, str] = {
        AppleScriptWaitEvent.busy: 'is busy',
        AppleScriptWaitEvent.exists: 'exists',
    },
) -> str:
    ''
    if isinstance(event, str):
        event = AppleScriptWaitEvent[event]
    else:
        event = AppleScriptWaitEvent(event)
    event = cast(AppleScriptWaitEvent, event)
    return _wait_for_str[event]


def start_macosx_terminal(
    cmd: Union[str, Sequence[str]], 
    app: str = 'Terminal.app',
    wait: bool = True,
    wait_event: Union[int, str, AppleScriptWaitEvent] = AppleScriptWaitEvent.exists,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.command',
    shebang: str = '#!/bin/sh',
) -> CompletedProcess:
    'Start a terminal emulator in MacOSX.'
    if not isinstance(cmd, str):
        cmd = cast(str, shlex_join(cmd))
    if wait:
        tpl_command = '''
tell application "{app}"
    activate
    set w to do script "{script}"
    repeat while w %s
        delay 0.1
    end repeat
end tell''' % _get_wait_for_str(wait_event)
    else:
        tpl_command = 'tell application "{app}" to do script "{script}"'
    if with_tempfile:
        with NamedTemporaryFile(suffix=tempfile_suffix, mode='w') as f:
            sprun(['chmod', '+x', f.name], check=True)
            f.write('%s\n%s\n' % (shebang, cmd))
            f.flush()
            command = tpl_command.format(app=app, script=f.name)
            return sprun(['osascript', '-e', command], check=True)
    else:
        command = tpl_command.format(app=app, script=cmd.replace('"', '\\"'))
        return sprun(['osascript', '-e', command], check=True)


def open_macosx_terminal(
    cmd: Union[str, Sequence[str]], 
    app: Optional[str] = 'Terminal.app',
    app_args: Union[None, Sequence[str]] = None,
    wait: bool = True,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.command',
    shebang: str = '#!/bin/sh',
) -> CompletedProcess:
    'Start a terminal emulator in MacOSX.'
    split_command: List[str] = ['open']
    if wait:
        split_command.append('-W')
    if app:
        split_command.extend(('-a', app))
    if app_args:
         split_command.extend(app_args)
    if with_tempfile:
        with NamedTemporaryFile(suffix=tempfile_suffix, mode='w') as f:
            sprun(['chmod', '+x', f.name], check=True)
            if not isinstance(cmd, str):
                cmd = cast(str, shlex_join(cmd))
            f.write('%s\n%s\n' % (shebang, cmd))
            f.flush()
            split_command.append(f.name)
            return sprun(split_command, check=True)
    else:
        if isinstance(cmd, str):
            return sprun(shlex_join(split_command) + ' ' + cmd, 
                         check=True, shell=True)
        else:
            split_command.extend(cmd)
            return sprun(split_command, check=True)


if __name__ == '__main__':
    from sys import executable, argv
    argv = argv[1:]
    if argv:
        start_terminal(argv)
    else:
        start_terminal(executable)

