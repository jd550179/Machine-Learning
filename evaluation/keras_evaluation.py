#!/usr/bin/env python

import ROOT
# disable ROOT internal argument parser
ROOT.PyConfig.IgnoreCommandLineOptions = True

import argparse
from array import array
import yaml
import pickle
import numpy as np

from keras.models import load_model


def keras_evaluation(args_from_script=None):
    parser = argparse.ArgumentParser(description="Evaluate the training on new data.",
                                     fromfile_prefix_chars="@", conflict_handler="resolve")
    parser.add_argument("config", help="Path to config")
    parser.add_argument("--tree", help="Name of tree.")
    args = parser.parse_args()

    # Load keras model and preprocessing
    classifiers = []
    for c in config["classifiers"]:
        classifiers.append(load_model(c))

    # inverted hierarchy
    FOLD = 0
    input_files = config["trainingssets"]
    # Open input file and register branches with input and output variables
    file_ = ROOT.TFile(input_files[0 if FOLD == 1 else 1], "UPDATE")
    if file_ == None:
        raise Exception(
            "File is not existent: {}".format(config["input_file"]))

    tree = file_.Get(args.tree)
    if tree == None:
        raise Exception("Tree {} is not existent in file: {}".format(
            args.tree, config["input_file"]))

    features = []
    for feature in config["features"]:
        features.append(array("f", [-999]))
        tree.SetBranchAddress(feature, values[-1])

    response_branches = []
    response_single_scores = []
    prefix = config["branch_prefix"]
    for class_ in config["classes"]:
        response_single_scores.append(array("f", [-999]))
        response_branches.append(
            tree.Branch("{}{}".format(prefix, class_),
                        response_single_scores[-1], "{}{}/F".format(
                            prefix, class_)))

    response_max_score = array("f", [-999])
    response_branches.append(
        tree.Branch("{}max_score".format(prefix), response_max_score,
                    "{}max_score/F".format(prefix)))

    response_max_index = array("f", [-999])
    response_branches.append(
        tree.Branch("{}max_index".format(prefix), response_max_index,
                    "{}max_index/F".format(prefix)))

    # Loop over events and add method's response to tree
    for i_event in range(tree.GetEntries()):
        # Get current event
        tree.GetEntry(i_event)

        # Get event number and calculate method's response
        event = int(getattr(tree, config["event_branch"]))
        values_stacked = np.hstack(values).reshape(1, len(values))

        # preprocessing
        from sklearn import preprocessing
        scaler = preprocessing.StandardScaler().fit(values_stacked)
        values_preprocessed = scaler.transform(values_stacked)

        response = classifiers[event % 2].predict(values_preprocessed)
        response = np.squeeze(response)

        # Find max score and index
        response_max_score[0] = -999.0
        for i, r in enumerate(response):
            response_single_scores[i][0] = r
            if r > response_max_score[0]:
                response_max_score[0] = r
                response_max_index[0] = i

        # Fill branches
        for branch in response_branches:
            branch.Fill()

    # Write new branches to input file
    file_.Write()
    file_.Close()


if __name__ == "__main__":
    keras_evaluation()
