#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: input_compare.py
@Time: 2020/3/25 5:30 PM
@Overview:
"""
import argparse
import os.path
import pathlib
import pdb
import pickle
import random

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from python_speech_features import mel2hz
from scipy import interpolate
from tqdm import tqdm

parser = argparse.ArgumentParser(description='PyTorch Speaker Recognition')
# Model options
parser.add_argument('--extract-path', help='folder to output model checkpoints')
# Training options
parser.add_argument('--feat-dim', type=int, default=161, metavar='ES', help='Dimensionality of the features')
parser.add_argument('--samples', type=int, default=0, metavar='ES', help='Dimensionality of the features')
parser.add_argument('--acoustic-feature', choices=['fbank', 'spectrogram', 'mfcc'], default='spectrogram',
                    help='choose the acoustic features type.')
parser.add_argument('--grad-weight', choices=['max', 'mean'], default='mean',
                    help='choose the acoustic features type.')
parser.add_argument('--grad-clip', choices=['abs', 'relu'], default='abs',
                    help='choose the acoustic features type.')
parser.add_argument('--seed', type=int, default=123456, metavar='S', help='random seed (default: 0)')

args = parser.parse_args()

random.seed(args.seed)
np.random.seed(args.seed)


def relu(x):
    return np.clip(x, a_min=0, a_max=None)


def main():
    # subsets = ['orignal', 'babble', 'noise', 'music', 'reverb']

    # load selected input uids
    dir_path = pathlib.Path(args.extract_path)
    print('Path is %s' % str(dir_path))

    # inputs [train/valid/test]
    # if args.grad_weight == 'max':
    vis_path = args.extract_path + '/' + args.grad_clip + '_' + args.grad_weight
    if not os.path.exists(vis_path):
        os.makedirs(vis_path)

    grad_clip = np.abs if args.grad_clip == 'abs' else relu
    time_squeeze = np.mean if args.grad_weight == 'mean' else np.max

    # if os.path.exists(vis_path + '/freq.data.pickle') and os.path.exists(vis_path + '/time.data.pickle'):
    #     with open(vis_path + '/freq.data.pickle', 'rb') as f:
    #         freq_data = pickle.load(f)  # avg on time axis
    #     with open(vis_path + '/time.data.pickle', 'rb') as f:
    #         time_data = pickle.load(f)  # avg on freq axis
    # else:
    train_lst = list(dir_path.glob('*train*bin'))
    veri_lst = list(dir_path.glob('*ver*bin'))
    valid_lst = list(dir_path.glob('*valid*bin'))
    test_lst = list(dir_path.glob('*test*bin'))

    print(' Train set extracting:')
    time_data = []

    num_utt = 0
    for t in train_lst:
        p = str(t)
        with open(p, 'rb') as f:
            sets = pickle.load(f)
            # for (data, grad, uid) in tqdm(sets):
            for (data, grad) in tqdm(sets, ncols=100):
                time_data.append((data, grad))
                num_utt += 1
                if args.samples > 0 and num_utt >= args.samples:
                    break
    # with open(vis_path + '/time.data.pickle', 'wb') as f:
    #     pickle.dump(time_data, f, protocol=pickle.HIGHEST_PROTOCOL)

    freq_data = {}
    train_data_mean = np.zeros((args.feat_dim))  # [data.mean/grad.abssum/grad.var]
    train_time_mean = np.zeros((args.feat_dim))  # [data.mean/grad.abssum/grad.var]
    train_time_var = np.zeros((args.feat_dim))

    num_utt = 0
    for t in train_lst:
        p = str(t)
        with open(p, 'rb') as f:
            sets = pickle.load(f)
            # for (data, grad, uid) in tqdm(sets):
            for (data, grad) in tqdm(sets, ncols=100):
                try:
                    train_time_mean += time_squeeze(grad_clip(grad), axis=0)
                    train_time_var += np.var(grad, axis=0)
                    train_data_mean += np.mean(data, axis=0)
                    num_utt += 1
                except Exception as e:
                    print(e)
                    pdb.set_trace()

    train_time_mean /= num_utt
    train_time_var /= num_utt
    train_data_mean /= num_utt

    freq_data['train.time.mean'] = train_time_mean
    freq_data['train.time.var'] = train_time_var
    freq_data['train.data.mean'] = train_data_mean

    print(' Valid set extracting:')
    valid_data_mean = np.zeros((args.feat_dim))  # [data.mean/grad.abssum/grad.var]
    valid_time_mean = np.zeros((args.feat_dim))  # [data.mean/grad.abssum/grad.var]
    valid_time_var = np.zeros((args.feat_dim))

    valid_data = np.zeros((3, args.feat_dim))  # [data/grad]
    num_utt = 0
    for t in valid_lst:
        p = str(t)
        with open(p, 'rb') as f:
            sets = pickle.load(f)
            # for (data, grad, uid) in tqdm(sets):
            for (data, grad) in tqdm(sets, ncols=100):
                valid_data_mean += np.mean(data, axis=0)
                valid_time_mean += time_squeeze(grad_clip(grad), axis=0)
                valid_time_var += np.var(grad, axis=0)

                num_utt += 1
    if num_utt > 0:
        valid_time_mean = valid_time_mean / num_utt
        valid_time_var = valid_time_var / num_utt
        valid_data_mean = valid_data_mean / num_utt

    freq_data['valid.time.mean'] = valid_time_mean
    freq_data['valid.time.var'] = valid_time_var
    freq_data['valid.data.mean'] = valid_data_mean

    print(' Train verification set extracting:')
    veri_data = np.zeros((3, 2, args.feat_dim))  # [data/grad, utt_a, utt_b]
    train_veri_data = np.zeros((args.feat_dim))
    train_veri_mean = np.zeros((args.feat_dim))
    train_veri_var = np.zeros((args.feat_dim))
    train_veri_relu = np.zeros((args.feat_dim))

    num_utt = 0
    for t in veri_lst:
        p = str(t)
        with open(p, 'rb') as f:
            sets = pickle.load(f)
            for (label, grad_a, grad_b, data_a, data_b) in tqdm(sets, ncols=100):
                train_veri_data += (np.mean(data_a, axis=0) + np.mean(data_b, axis=0)) / 2
                train_veri_mean += (time_squeeze(grad_clip(grad_a), axis=0) + time_squeeze(grad_clip(grad_b),
                                                                                           axis=0)) / 2
                train_veri_relu += (np.mean(np.where(grad_a > 0, grad_a, 0), axis=0) +
                                    np.mean(np.where(grad_b > 0, grad_b, 0), axis=0)) / 2

                train_veri_var += (np.var(grad_a, axis=0) + np.var(grad_b, axis=0)) / 2

                num_utt += 1

    if num_utt > 0:
        train_veri_data /= num_utt
        train_veri_mean /= num_utt
        train_veri_var /= num_utt
        train_veri_relu /= num_utt

    freq_data['train.veri.time.mean'] = train_veri_mean
    freq_data['train.veri.time.var'] = train_veri_var
    freq_data['train.veri.data.mean'] = train_veri_data
    freq_data['train.veri.time.relu'] = train_veri_relu

    print(' Test set extracting:')
    # test_data = np.zeros((3, 2, args.feat_dim))  # [data/grad, utt_a, utt_b]
    test_veri_data = np.zeros((args.feat_dim))
    test_veri_mean = np.zeros((args.feat_dim))
    test_veri_var = np.zeros((args.feat_dim))
    test_veri_relu = np.zeros((args.feat_dim))

    num_utt = 0
    for t in test_lst:
        p = str(t)
        with open(p, 'rb') as f:
            sets = pickle.load(f)
            for (label, grad_a, grad_b, data_a, data_b) in tqdm(sets, ncols=100):
                test_veri_data += (np.mean(data_a, axis=0) + np.mean(data_b, axis=0)) / 2
                test_veri_mean += (time_squeeze(grad_clip(grad_a), axis=0) + time_squeeze(grad_clip(grad_b),
                                                                                          axis=0)) / 2
                test_veri_relu += (np.mean(np.where(grad_a > 0, grad_a, 0), axis=0) + np.mean(
                    np.where(grad_b > 0, grad_b, 0), axis=0)) / 2

                test_veri_var += (np.var(grad_a, axis=0) + np.var(grad_b, axis=0)) / 2

                num_utt += 1
    if num_utt > 0:
        test_veri_data /= num_utt
        test_veri_mean /= num_utt
        test_veri_var /= num_utt
        test_veri_relu /= num_utt

    freq_data['test.veri.time.mean'] = test_veri_mean
    freq_data['test.veri.time.var'] = test_veri_var
    freq_data['test.veri.data.mean'] = test_veri_data
    freq_data['test.veri.time.relu'] = test_veri_relu

    print('Saving inputs in %s' % vis_path)

    with open(vis_path + '/freq.data.pickle', 'wb') as f:
        pickle.dump(freq_data, f, protocol=pickle.HIGHEST_PROTOCOL)

    # all_data [5, 2, 120, 161]
    # plotting filters distributions

    # train_data [numofutt, feats[N, 161]]
    train_input = freq_data['train.data.mean']
    valid_input = freq_data['valid.data.mean']
    test_input = freq_data['test.veri.data.mean']

    train_grad = freq_data['train.time.mean']
    valid_grad = freq_data['valid.time.mean']
    veri_grad = freq_data['train.veri.time.mean']
    veri_grad_relu = freq_data['train.veri.time.relu']

    test_grad = freq_data['test.veri.time.mean']
    test_grad_relu = freq_data['test.veri.time.relu']

    np.save(vis_path + '/train.grad.npy', train_grad)

    x = np.arange(args.feat_dim) * 8000 / (args.feat_dim - 1)  # [0-8000]
    if args.acoustic_feature == 'fbank':
        m = np.linspace(0, 2840.0230467083188, args.feat_dim)
        x = mel2hz(m)

    # y = np.sum(all_data, axis=2)  # [5, 2, 162]
    # pdf = PdfPages(vis_path + '/grad.veri.time.mean.pdf')
    # plt.rc('font', family='Times New Roman')

    plt.figure(figsize=(12, 16))
    # plt.title('Gradient Distributions', fontsize=22)

    plt.subplot(3, 1, 1)
    plt.xlabel('Frequency (Hz)')
    # plt.xticks(fontsize=22)
    plt.ylabel('Weight')
    # plt.yticks(fontsize=22)

    m = np.arange(0, 2840.0230467083188)
    m = 700 * (10 ** (m / 2595.0) - 1)
    n = np.array([m[i] - m[i - 1] for i in range(1, len(m))])
    n = 1 / n

    f = interpolate.interp1d(m[1:], n)
    xnew = np.arange(np.min(m[1:]), np.max(m[1:]), (np.max(m[1:]) - np.min(m[1:])) / 161)
    ynew = f(xnew)
    ynew = ynew / ynew.sum()
    plt.plot(xnew, ynew)
    # print(np.sum(ynew))

    plot_index = []
    for i, s in enumerate([train_grad, valid_grad, veri_grad, veri_grad_relu, test_grad]):
        # for s in test_a_set_grad, test_b_set_grad:
        f = interpolate.interp1d(x, s)
        xnew = np.linspace(np.min(x), np.max(x), 161)
        ynew = f(xnew)
        if ynew.sum() != 0:
            plot_index.append(i)
            ynew = ynew / ynew.sum()
            plt.plot(xnew, ynew)
        # pdb.set_trace
    # if not os.path.exists(args.extract_path + '/grad.npy'):
    # ynew = veri_grad
    # ynew = train_grad
    # # ynew = ynew / ynew.sum()

    # plt.legend(['Mel-scale', 'Train', 'Valid', 'Test_a', 'Test_b'], loc='upper right', fontsize=18)
    all_sets = np.array(['Mel', 'Train', 'Valid', 'Train Verify', 'Train Verify Relu', 'Test'])
    plt.legend(all_sets[plot_index], loc='upper right')
    plt.grid(linestyle='--', axis='both', alpha=0.2, linewidth=1.5)

    # plt.legend(['Mel-scale', 'Train', 'Valid', 'Train Verify', 'Test'], loc='upper right', fontsize=24)
    # plt.savefig(vis_path + "/freq.sets.png")
    # plt.show()
    # pdf.savefig()
    # pdf.close()

    # plt.savefig(args.extract_path + "/grads.png")
    # plt.show()

    # plt.figure(figsize=(8, 6))
    plt.subplot(3, 1, 2)
    plt.title('Data distributions')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Log Power (-)')
    # 插值平滑 ？？？
    plot_index = []
    for i, s in enumerate([train_input, valid_input, test_input]):
        # for s in test_a_set_grad, test_b_set_grad:
        f = interpolate.interp1d(x, s)
        xnew = np.linspace(np.min(x), np.max(x), 161)
        ynew = f(xnew)
        if ynew.sum() != 0:
            plot_index.append(i)
            plt.plot(xnew, ynew)

    all_sets = np.array(['Train', 'Valid', 'Test'])
    plt.legend(all_sets[plot_index], loc='upper right')
    # plt.savefig(vis_path + "/inputs.freq.png")
    # plt.show()

    plt.subplot(6, 1, 5)
    # plt.figure(figsize=(16, 8))
    plt.title('Data distributions in Time Axis')
    plt.xlabel('Time')
    plt.ylabel('Magnetitude')
    # 插值平滑 ？？？
    # for i, (data, grad) in enumerate(time_data):
    # for s in test_a_set_grad, test_b_set_grad:
    data = time_data[0][0]
    grad = time_data[0][1]
    norm = matplotlib.colors.Normalize(vmin=0., vmax=1.)
    # data_mean = data.mean(axis=10
    # ax = plt.subplot(2, 1, 1)

    # data = (data - data.min()) / (data.max() - data.min())
    # im = ax.imshow(np.log(data.transpose()), cmap='viridis', aspect='auto')
    im = plt.imshow(data.transpose(), cmap='viridis', aspect='auto')
    # print(data.min(), data.max())
    plt.colorbar(im)  # 显示颜色标尺
    # ax.plot(data_mean)

    # ax = plt.subplot(2, 1, 2)
    plt.subplot(6, 1, 6)
    grad = np.abs(grad)
    grad_mean = grad
    # grad_mean = (grad - grad.min()) / (grad.max() - grad.min())
    # im = ax.imshow(1/np.log(grad_mean.transpose()), norm=norm, cmap='viridis', aspect='auto')
    im = plt.imshow(grad_mean.transpose(), cmap='viridis', aspect='auto')
    # ax.plot(np.log(grad_mean))
    plt.xlim(0, len(grad_mean))

    # plt.legend(['Train', 'Valid', 'Test'], loc='upper right', fontsize=16)
    plt.colorbar(im)  # 显示颜色标尺
    plt.tight_layout()

    plt.savefig(vis_path + "/inputs.time.png")
    plt.show()

    print('Completed!\n')

if __name__ == '__main__':
    main()
