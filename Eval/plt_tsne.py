#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: plt_tsne.py
@Time: 2020/10/20 15:25
@Overview:
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np
from kaldiio import ReadHelper
from sklearn.manifold import TSNE

# Training settings
from Process_Data.constants import cValue_1

parser = argparse.ArgumentParser(description='PyTorch Speaker Recognition')
# Data options
parser.add_argument('--scp-file', type=str, default='Data/xvector/LoResNet8/vox1/spect_egs/arcsoft_dp25/xvectors.scp',
                    help='path to scp file for xvectors')
parser.add_argument('--sid-length', default=7, type=int,
                    help='num of speakers to plot (default: 10)')
parser.add_argument('--num-spk', default=7, type=int,
                    help='num of speakers to plot (default: 10)')
parser.add_argument('--out-pdf', default='', type=str, help='num of speakers to plot (default: 10)')

args = parser.parse_args()

if __name__ == '__main__':

    vects = {}
    with ReadHelper('scp:%s'% args.scp_file) as reader:
        for key, numpy_array in reader:
            vects[key] = numpy_array

    spks = []
    for key in vects:
        s = key[:args.sid_length]
        if s not in spks:
            spks.append(s)

    spks.sort()
    spks_this = spks[:args.num_spk] if len(spks) > args.num_spk else spks
    spk2vec = {}
    for s in spks_this:
        spk2vec[s] = []
    for key in vects:
        if key[:args.sid_length] in spks_this:
            this_vec = vects[key]
            vec_len = len(this_vec)
            spk2vec[key[:args.sid_length]].append(this_vec.reshape(1, vec_len))

    all_vectors = []
    all_len = [0]
    for spk in spk2vec:
        spk_con = np.concatenate(spk2vec[spk])
        all_len.append(len(spk_con))
        all_vectors.append(spk_con)

    all_vectors = np.concatenate(all_vectors, axis=0)
    S_embedded = TSNE(n_components=2).fit_transform(all_vectors)

    emb_group = []
    for i in range(len(all_len) - 1):
        start = np.sum(all_len[:(i + 1)]).astype(np.int32)
        stop = np.sum(all_len[:(i + 2)]).astype(np.int32)
        this_points = S_embedded[start:stop]
        assert len(this_points) > 0, 'start:stop is %s:%s' % (start, stop)
        emb_group.append(this_points)

    plt.figure(figsize=(8, 8))
    leng = []
    for idx, group in enumerate(emb_group):
        if len(group) > 0:
            c = cValue_1[idx]
            leng.append(spks_this[idx])
            plt.scatter(group[:, 0], group[:, 1], color=c, s=10)

    plt.legend(leng, loc="best", fontsize=18)
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)
    if args.out_pdf.endswith('pdf'):
        plt.savefig(args.out_pdf, format="pdf")

    plt.show()

    within_vars = []
    spk2num_utt = []
    for spk in spk2vec:
        within_vars.append(np.var(spk2vec[spk], axis=0).sum())
        spk2num_utt.append(len(spk2vec[spk]))

    within_var = np.array(within_vars) * np.array(spk2num_utt)
    within_var = np.sum(within_var) / np.sum(spk2num_utt)

    # between_var = np.var(all_vectors, axis=0).sum() - within_var
    overall_mean = np.mean(all_vectors, axis=0)
    between_var = 0
    for spk in spk2vec:
        between_var += np.sum((np.mean(spk2vec[spk], axis=0) - overall_mean) ** 2) * len(spk2vec[spk])
    between_var /= np.sum(spk2num_utt)

    print("Variance Within-Class Between-Class\n", '         {:>7.4f}    {:>7.4f}'.format(within_var, between_var))
