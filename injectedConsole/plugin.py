#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 9)
__revision__ = 0

import sys
if sys.version_info < (3, 8):
    msg = f'''Python version at least 3.8, got
 * executable: 
{sys.executable!r}

 * version:
{sys.version}

* version_info:
{sys.version_info}'''
    raise RuntimeError(msg)

from plugin_run import run

