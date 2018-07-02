#!/usr/bin/env python

import ROOT
import os
import glob
import argparse
from progressbar import progressbar


@progressbar(pause=0.1)
def checkZombie():
    parser = argparse.ArgumentParser(description="Check if ROOT file is a zombie.",
                                     conflict_handler="resolve")
    parser.add_argument("--dir", help="path to ntuple directory")
    args = parser.parse_args()

    rfiles = glob.glob("{}/*.root".format(args.dir))

    for filename in rfiles:
        _file = ROOT.TFile(filename)
        if _file.IsZombie():
            print filename, "\033[91mis a frickin' zombie!\033[0m"
            continue


if __name__ == "__main__":
    checkZombie()
