#!/usr/bin/env python3
# coding=utf-8

# Reference:
#   - https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/introduction/ASLR_intro.html
#   - https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/
#   - https://en.wikibooks.org/wiki/AppleScript_Programming
#   - https://linux.die.net/man/8/update-alternatives


__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

import platform
import re

from enum import Enum
from os import remove
from shlex import quote as shlex_quote
from subprocess import run as sprun, CalledProcessError, CompletedProcess, PIPE
from tempfile import NamedTemporaryFile
from typing import cast, Dict, List, Optional, Sequence, Union

try:
    from shlex import join as shlex_join # type: ignore
except ImportError:
    def shlex_join(split_command: Sequence[str]) -> str:
        """Return a shell-escaped string from *split_command*."""
        return ' '.join(map(shlex_quote, split_command))


__all__ = ['start_terminal', 'shlex_quote', 'shlex_join', 'winsh_quote', 'winsh_join', 
           'get_debian_default_app', 'set_debian_default_app', 'start_windows_terminal', 
           'start_linux_terminal', 'AppleScriptWaitEvent', 'start_macosx_terminal', 
           'open_macosx_terminal']


def winsh_quote(part, _cre=re.compile(r'\s')):
    ''
    part = part.strip().replace(r'"', r'\"')
    if _cre.search(part) is not None:
        part = r'"%s"' % part
    return part


def winsh_join(split_command: Sequence[str]) -> str:
    """Return a shell-escaped string from *split_command*."""
    return ' '.join(map(winsh_quote, split_command))


def get_debian_default_app(field: Union[bytes, str]) -> Optional[str]:
    ''
    if isinstance(field, str):
        field = field.encode('utf-8')
    rt = sprun(
        'update-alternatives --get-selections', 
        check=True, shell=True, stdout=PIPE)
    return next((
        row.rsplit(maxsplit=1)[-1].decode('utf-8') 
        for row in rt.stdout.split(b'\n') 
        if row.startswith(b'%s '%field)
    ), None)


def set_debian_default_app(field: str) -> CompletedProcess:
    ''
    return sprun(['update-alternatives', '--config', field])


def start_terminal(cmd, **kwargs) -> CompletedProcess:
    ''
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
    ''
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
            remove(f.name)
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


def start_linux_terminal(
    cmd: Union[str, Sequence[str]], 
    app: Optional[str] = None, 
    app_args: Union[None, Sequence[str]] = None,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.sh',
    shebang: str = '#!/bin/sh',
) -> CompletedProcess:
    ''
    if app is None:
        try:
            app = get_debian_default_app('x-terminal-emulator')
        except CalledProcessError:
            # TIPS: So far, automatically detect terminal is only for Debian series
            raise NotImplementedError('Failed to detect the terminal app, '
                                      'please specify one')
    if app is None:
        raise RuntimeError('There is no default terminal app')
    split_command: List[str] = [app]
    if app_args is None:
        # SUPPOSE: All apps except xterm have the -x(--execute) parameter 
        #          to execute the command.
        if not app.endswith('xterm'):
            split_command.append('-x')
    else:
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
    ''
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
    ''
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

