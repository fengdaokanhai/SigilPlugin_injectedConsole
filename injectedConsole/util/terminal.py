# Reference:
#   - https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/introduction/ASLR_intro.html
#   - https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/
#   - https://en.wikibooks.org/wiki/AppleScript_Programming
#   - https://linux.die.net/man/1/xdg-open

import os
import platform
import re

from enum import Enum
from subprocess import run as sprun, CompletedProcess
from tempfile import NamedTemporaryFile
from typing import cast, Dict, Iterable, Optional, Tuple, Union

try:
    from shlex import join as shlex_join # type: ignore
except ImportError:
    from shlex import quote

    def shlex_join(split_command):
        """Return a shell-escaped string from *split_command*."""
        return ' '.join(quote(arg) for arg in split_command)


__all__ = ['start_terminal', 'start_windows_terminal', 'start_linux_terminal', 
           'AppleScriptWaitEvent', 'start_macosx_terminal', 'open_macosx_terminal']


def start_terminal(cmd, **kwargs) -> CompletedProcess:
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


def _win_quote(part, _cre=re.compile(r'\s')):
    if '"' in part:
        part = part.replace('"', '\\"')
    if _cre.search(part):
        part = '"%s"' % part
    return part


def start_windows_terminal(
    cmd: Union[str, Iterable[str]], 
    app: Optional[str] = 'powershell',
    wait: bool = True,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.cmd',
    app_args: Union[None, Tuple[str]] = None,
) -> CompletedProcess:
    start_cmd = ['start']
    if wait:
        start_cmd.append('/wait')
    if app:
        start_cmd.append(app)
        if app_args is None:
            if app in ('cmd', 'cmd.exe'):
                start_cmd.append('/c')
        else:
            start_cmd.extend(app_args)
    if with_tempfile:
        # In Windows, file is occupied when is opening, until it is closed.
        # Like lock, anyone cannot open the file while it is occupied.
        # So we should close it first, then give it to any other, and finally delete it.
        f = NamedTemporaryFile(suffix=tempfile_suffix, mode='w', delete=False)
        try:
            with f:
                if not isinstance(cmd, str):
                    cmd = ' '.join(map(_win_quote, cmd))
                    cmd = cast(str, cmd)
                f.write(cmd)
            start_cmd.append(f.name)
            return sprun(start_cmd, check=True, shell=True)
        finally:
            # TODO: We may need to wait until the file is no longer occupied before deleting it.
            os.remove(f.name)
    else:
        if isinstance(cmd, str):
            if app in ('powershell', 'powershell.exe'):
                # [The call operator &](https://ss64.com/ps/call.html)
                start_cmd.append("& " + cmd)
        else:
            start_cmd.extend(cmd)
        return sprun(start_cmd, check=True, shell=True)


def start_linux_terminal(
    cmd: Union[str, Iterable[str]], 
    app: Optional[str] = 'xterm', 
    wait: bool = True,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.sh',
    shebang: str = '#!/bin/sh',
) -> CompletedProcess:
    # TODO: to implement terminal app auto-checking
    # TODO: use xdg-open
    raise NotImplementedError("start terminal of 'Linux' is unavailable")


AppleScriptWaitEvent = Enum('AppleScriptWaitEvent', ('exists', 'busy'))


def _get_wait_for_str(
    event: Union[int, str, AppleScriptWaitEvent],
    _wait_for_str: Dict[AppleScriptWaitEvent, str] = {
        AppleScriptWaitEvent.busy: 'is busy',
        AppleScriptWaitEvent.exists: 'exists',
    },
) -> str:
    if isinstance(event, str):
        event = AppleScriptWaitEvent[event]
    else:
        event = AppleScriptWaitEvent(event)
    event = cast(AppleScriptWaitEvent, event)
    return _wait_for_str[event]


def start_macosx_terminal(
    cmd: Union[str, Iterable[str]], 
    app: str = 'Terminal.app',
    wait: bool = True,
    wait_event: Union[int, str, AppleScriptWaitEvent] = AppleScriptWaitEvent.exists,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.command',
    shebang: str = '#!/bin/sh',
) -> CompletedProcess:
    if not isinstance(cmd, str):
        cmd = shlex_join(cmd)
        cmd = cast(str, cmd)
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
    cmd: Union[str, Iterable[str]], 
    app: Optional[str] = 'Terminal.app',
    wait: bool = True,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.command',
    shebang: str = '#!/bin/sh',
) -> CompletedProcess:
    open_cmd = ['open']
    if wait:
        open_cmd.append('-W')
    if app:
        open_cmd.extend(('-a', app))
    if with_tempfile:
        with NamedTemporaryFile(suffix=tempfile_suffix, mode='w') as f:
            sprun(['chmod', '+x', f.name], check=True)
            if not isinstance(cmd, str):
                cmd = shlex_join(cmd)
                cmd = cast(str, cmd)
            f.write('%s\n%s\n' % (shebang, cmd))
            f.flush()
            open_cmd.append(f.name)
            return sprun(open_cmd, check=True)
    else:
        if isinstance(cmd, str):
            open_cmd.append(cmd)
        else:
            open_cmd.extend(cmd)
        return sprun(open_cmd, check=True)

