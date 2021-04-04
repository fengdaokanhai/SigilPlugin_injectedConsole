#!/usr/bin/env python3
# coding: utf-8


__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 6)

from os import chdir, path
from pickle import dump as pickle_dump, load as pickle_load
from sys import argv, executable

from util.encode_args import b64encode_pickle
from util.terminal import start_terminal


def run(bc):
    laucher_file, ebook_root, outdir, _, target_file = argv
    this_plugin_dir = path.dirname(target_file)

    args = b64encode_pickle(dict(
        sigil_package_dir = path.dirname(laucher_file),
        this_plugin_dir   = this_plugin_dir,
        plugins_dir       = path.dirname(this_plugin_dir),
        ebook_root        = ebook_root,
        outdir            = outdir,
    ))

    pklfile = path.join(outdir, 'wrapper.pkl')
    mainfile = path.join(this_plugin_dir, 'main.py')

    pickle_dump(bc._w, open(pklfile, 'wb'))

    chdir(outdir)
    cmd = [executable, mainfile, '--args', args]
    start_terminal(cmd)

    # check whether the console is aborted.
    if path.exists('abort.exists'):
        return 1
    bc._w = pickle_load(open(pklfile, 'rb'))
    return 0

