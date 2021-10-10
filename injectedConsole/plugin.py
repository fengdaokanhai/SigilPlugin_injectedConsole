#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 8)
__revision__ = 8

import sys
if sys.version_info < (3, 8):
    raise RuntimeError('Python version at least 3.8, got\n%s' % sys.version)

from plugin_run import run

