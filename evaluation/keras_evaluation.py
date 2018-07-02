#!/usr/bin/env python

import ROOT
# disable ROOT internal argument parser
ROOT.PyConfig.IgnoreCommandLineOptions = True

import argparse
from array import array
import yaml
import pickle
import numpy as np
import os
import sys

from keras.models import load_model

base = os.path.normpath(os.path.join(os.path.abspath(__file__), "../.."))
sys.path.append(base)

from utils.treetools import *
from utils.model import Config


def keras_evaluation():
    parser = argparse.ArgumentParser(description="Application of keras model.",
                                     fromfile_prefix_chars="@", conflict_handler="resolve")
    parser.add_argument("--files", nargs='+', help="Path to ROOT files.")
    parser.add_argument("--tree", default="latino", help="Name of the tree.")

    args = parser.parse_args()

    config = Config()

    # Load keras model and preprocessing

    classifiers = []
    preprocessing = []
    for c, p in zip(config.load["classifiers"], config.load["preprocessing"]):
        classifiers.append(load_model(c))
        preprocessing.append(pickle.load(open(p, "rb")))

    for _file in args.files:

        print "Currently processing {}".format(_file)

        path = _file + "/" + args.tree

        with TreeExtender(path) as extender:

            values = []
            for feature in config.load["features"]:
                values.append(array("f", [-999]))
                extender.tree.SetBranchAddress(feature, values[-1])

            event_branch = config.load["event_branch"]

            # Add branches with TreeExtender method
            extender.addBranch("ml_max_score", nLeaves=1, unpackBranches=None)
            extender.addBranch("ml_max_index", nLeaves=1, unpackBranches=None)

            extender.addBranch("ml_sig_score", nLeaves=1, unpackBranches=None)
            extender.addBranch("mTi_scaled", nLeaves=1,
                               unpackBranches=["mTi"])

            # mTi_scaled_v1 = mTi * ml_sig_score**2
            extender.addBranch("mTi_scaled_v1", nLeaves=1,
                               unpackBranches=["mTi"])
            # mTi_scaled_v2 = mTi * ml_sig_score**3
            extender.addBranch("mTi_scaled_v2", nLeaves=1,
                               unpackBranches=["mTi"])
            # mTi_scaled_v3 = mTi * ml_sig_score**0.5
            extender.addBranch("mTi_scaled_v3", nLeaves=1,
                               unpackBranches=["mTi"])
            # mTi_scaled_v4 = mTi * 1./(abs(ln(ml_sig_score)))
            # extender.addBranch("mTi_scaled_v4", nLeaves=1,
            #                    unpackBranches=["mTi"])
            for entry in extender:

                # Initiate ml_sig_score with 0
                entry.ml_sig_score[0] = 0

                # Get event number and calculate method's response
                event = int(getattr(extender.tree, event_branch))

                values_stacked = np.hstack(values).reshape(1, len(values))

                # Preprocessing
                values_preprocessed = preprocessing[event % 2].transform(
                    values_stacked)

                # Get DNN response
                response = classifiers[event % 2].predict(values_preprocessed)
                response = np.squeeze(response)

                # Find max score and index
                for i, r in enumerate(response):

                    # i = 0..5 are the signal classes
                    if i < 6:
                        entry.ml_sig_score[0] += r

                    # Get class with highest probability and probability itself
                    if r > entry.ml_max_score[0]:
                        entry.ml_max_score[0] = r
                        entry.ml_max_index[0] = i

                # Scale mTi with DNN probability sum of signal classes
                entry.mTi_scaled[0] = entry.ml_sig_score[0] * entry.mTi[0]
                entry.mTi_scaled_v1[0] = entry.mTi[0] * \
                    entry.ml_sig_score[0]**2
                entry.mTi_scaled_v2[0] = entry.mTi[0] * \
                    entry.ml_sig_score[0]**3
                entry.mTi_scaled_v3[0] = entry.mTi[0] * \
                    np.sqrt(entry.ml_sig_score[0])
                # entry.mTi_scaled_v4[0] = entry.mTi[0] * \
                #     1. / (abs(np.log(entry.ml_sig_score[0])))


if __name__ == "__main__":
    keras_evaluation()
