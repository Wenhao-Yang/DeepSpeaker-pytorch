#!/usr/bin/env python3
#
# Copyright 2015   David Snyder
# Apache 2.0.
#
# Copied from egs/sre10/v1/local/prepare_for_eer.py (commit 9cb4c4c2fb0223ee90c38d98af11305074eb7ef8)
#
# Given a trials and scores file, this script
# prepares input for the binary compute-eer.
import sys
trials = open(sys.argv[1], 'r').readlines()
scores = open(sys.argv[2], 'r').readlines()
spkrutt2target = {}
for line in trials:
  spkr, utt, target = line.strip().split()
  if target == '1':
    target = 'target'
  elif target == '0':
    target = 'nontarget'
  spkrutt2target[spkr + utt] = target
for line in scores:
  spkr, utt, score = line.strip().split()
  print("{} {}".format(score, spkrutt2target[spkr+utt]))
