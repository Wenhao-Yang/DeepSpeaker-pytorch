#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: test_accuracy.py
@Time: 19-8-6 下午1:29
@Overview: Train the resnet 10 with asoftmax.
"""
from __future__ import print_function
# import torch._utils
import pickle
import random
import argparse
import os
import pdb
import sys
import time
# Version conflict
import warnings
from collections import OrderedDict
from hyperpyyaml import load_hyperpyyaml

import kaldiio
import numpy as np
import psutil
import torch
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torchvision.transforms as transforms
from kaldi_io import read_mat, read_vec_flt
from torch.autograd import Variable
from tqdm import tqdm

# from Define_Model.Loss.SoftmaxLoss import AngleLinear, AdditiveMarginLinear
# import Define_Model
from Define_Model.FilterLayer import FreqMaskIndexLayer
from Define_Model.ParallelBlocks import Adapter
from Define_Model.TDNN.Slimmable import FLAGS
from Eval.eval_metrics import evaluate_kaldi_eer, evaluate_kaldi_mindcf
from Process_Data.Datasets.KaldiDataset import ScriptTrainDataset, ScriptValidDataset, KaldiExtractDataset, \
    ScriptVerifyDataset
from Process_Data.audio_processing import ConcateOrgInput, ConcateVarInput, mvnormal, read_WaveFloat, read_WaveInt
from TrainAndTest.common_func import verification_extract, args_parse
from Define_Model.model import create_classifier, create_model, load_model_args
from logger import NewLogger

warnings.filterwarnings("ignore")


# try:
#     torch._utils._rebuild_tensor_v2
# except AttributeError:
#     def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks):
#         tensor = torch._utils._rebuild_tensor(
#             storage, storage_offset, size, stride)
#         tensor.requires_grad = requires_grad
#         tensor._backward_hooks = backward_hooks
#         return tensor

#     torch._utils._rebuild_tensor_v2 = _rebuild_tensor_v2

# Training settings
# parser = argparse.ArgumentParser(description='PyTorch Speaker Recognition TEST')
# # Data options
# parser.add_argument('--train-dir', type=str, required=True, help='path to dataset')
# parser.add_argument('--train-extract-dir', type=str, default='', help='path to dataset')
# parser.add_argument('--train-test-dir', type=str, help='path to dataset')
# parser.add_argument('--valid-dir', type=str, help='path to dataset')
# parser.add_argument('--test-dir', type=str, required=True, help='path to voxceleb1 test dataset')
# parser.add_argument('--exp', action='store_true', default=False, help='exp power spectogram')
#
# parser.add_argument('--log-scale', action='store_true', default=False, help='log power spectogram')
#
# parser.add_argument('--trials', type=str, default='trials', help='path to voxceleb1 test dataset')
# parser.add_argument('--extract-trials', action='store_false', default=True, help='log power spectogram')
#
# parser.add_argument('--train-trials', type=str, default='trials', help='path to voxceleb1 test dataset')
# parser.add_argument('--score-suffix', type=str, default='', help='path to voxceleb1 test dataset')
#
# parser.add_argument('--test-input', type=str, default='fix', help='path to voxceleb1 test dataset')
# parser.add_argument('--remove-vad', action='store_true', default=False, help='using Cosine similarity')
# parser.add_argument('--vad-select', action='store_true', default=False, help='using Cosine similarity')
# parser.add_argument('--xvector', action='store_true', default=False, help='need to make mfb file')
#
# parser.add_argument('--extract', action='store_false', default=True, help='need to make mfb file')
# parser.add_argument('--test', action='store_false', default=True, help='need to make mfb file')
# parser.add_argument('--cluster', default='mean', type=str, help='The optimizer to use (default: Adagrad)')
#
# parser.add_argument('--num-frames', default=300, type=int, metavar='N', help='acoustic feature dimension')
# parser.add_argument('--frame-shift', default=300, type=int, metavar='N', help='acoustic feature dimension')
#
# parser.add_argument('--nj', default=10, type=int, metavar='NJOB', help='num of job')
# parser.add_argument('--feat-format', type=str, default='kaldi', choices=['kaldi', 'npy'],
#                     help='number of jobs to make feats (default: 10)')
#
# parser.add_argument('--check-path', help='folder to output model checkpoints')
# parser.add_argument('--save-init', action='store_true', default=True, help='need to make mfb file')
# parser.add_argument('--resume', type=str, metavar='PATH', help='path to latest checkpoint (default: none)')
# parser.add_argument('--model-yaml', default='', type=str, help='path to yaml of model for the latest checkpoint (default: none)')
#
# parser.add_argument('--start-epoch', default=1, type=int, metavar='N',
#                     help='manual epoch number (useful on restarts)')
# parser.add_argument('--epochs', type=int, default=20, metavar='E',
#                     help='number of epochs to train (default: 10)')
# parser.add_argument('--xvector-dir', type=str, help='The dir for extracting xvectors')
#
# parser.add_argument('--scheduler', default='multi', type=str,
#                     metavar='SCH', help='The optimizer to use (default: Adagrad)')
# parser.add_argument('--patience', default=2, type=int,
#                     metavar='PAT', help='patience for scheduler (default: 4)')
# parser.add_argument('--gamma', default=0.75, type=float,
#                     metavar='GAMMA', help='The optimizer to use (default: Adagrad)')
# parser.add_argument('--milestones', default='10,15', type=str,
#                     metavar='MIL', help='The optimizer to use (default: Adagrad)')
# parser.add_argument('--min-softmax-epoch', type=int, default=40, metavar='MINEPOCH',
#                     help='minimum epoch for initial parameter using softmax (default: 2')
# parser.add_argument('--veri-pairs', type=int, default=20000, metavar='VP',
#                     help='number of epochs to train (default: 10)')
#
# # Training options
# # Model options
# parser.add_argument('--model', type=str, help='path to voxceleb1 test dataset')
# parser.add_argument('--resnet-size', default=8, type=int, metavar='RES', help='The channels of convs layers)')
#
# parser.add_argument('--filter', type=str, default='None', help='replace batchnorm with instance norm')
# parser.add_argument('--filter-fix', action='store_true', default=False, help='replace batchnorm with instance norm')
# parser.add_argument('--activation', type=str, default='relu', help='activation functions')
#
# parser.add_argument('--mask-layer', type=str, default='None', help='replace batchnorm with instance norm')
# parser.add_argument('--power-weight', type=str, default='none', help='replace batchnorm with instance norm')
# parser.add_argument('--init-weight', type=str, default='mel', help='replace batchnorm with instance norm')
# parser.add_argument('--weight-norm', type=str, default='max', help='replace batchnorm with instance norm')
# parser.add_argument('--weight-p', default=0.1, type=float, help='replace batchnorm with instance norm')
# parser.add_argument('--scale', default=0.2, type=float, metavar='FEAT', help='acoustic feature dimension')
#
# parser.add_argument('--mask-len', type=str, default='5,5', help='maximum length of time or freq masking layers')
# parser.add_argument('--first-2d', action='store_true', default=False, help='replace first tdnn layer with conv2d layers')
# parser.add_argument('--dilation', default='1,1,1,1', type=str, metavar='CHA', help='The dilation of convs layers)')
# parser.add_argument('--block-type', type=str, default='None', help='replace batchnorm with instance norm')
# parser.add_argument('--red-ratio', default=8, type=int, metavar='N', help='acoustic feature dimension')
#
# parser.add_argument('--relu-type', type=str, default='relu', help='replace batchnorm with instance norm')
# parser.add_argument('--transform', type=str, default="None", help='add a transform layer after embedding layer')
#
# parser.add_argument('--vad', action='store_true', default=False, help='vad layers')
# parser.add_argument('--inception', action='store_true', default=False, help='multi size conv layer')
# parser.add_argument('--inst-norm', action='store_true', default=False, help='batchnorm with instance norm')
# parser.add_argument('--input-norm', type=str, default='Mean', help='batchnorm with instance norm')
# parser.add_argument('--encoder-type', type=str, default='None', help='path to voxceleb1 test dataset')
# parser.add_argument('--downsample', type=str, default='None', help='replace batchnorm with instance norm')
# parser.add_argument('--expansion', default=1, type=int, metavar='N', help='acoustic feature dimension')
#
# parser.add_argument('--channels', default='64,128,256', type=str,
#                     metavar='CHA', help='The channels of convs layers)')
# parser.add_argument('--width-mult-list', default='1', type=str, metavar='WIDTH',
#                     help='The channels of convs layers)')
# parser.add_argument('--context', default='5,3,3,5', type=str, metavar='KE', help='kernel size of conv filters')
#
# parser.add_argument('--feat-dim', default=64, type=int, metavar='N', help='acoustic feature dimension')
# parser.add_argument('--input-dim', default=257, type=int, metavar='N', help='acoustic feature dimension')
# parser.add_argument('--input-length', type=str, help='batchnorm with instance norm')
#
# parser.add_argument('--accu-steps', default=1, type=int, metavar='N', help='manual epoch number (useful on restarts)')
#
# parser.add_argument('--alpha', default=0, type=float, metavar='FEAT', help='acoustic feature dimension')
# parser.add_argument('--kernel-size', default='5,5', type=str, metavar='KE', help='kernel size of conv filters')
# parser.add_argument('--padding', default='', type=str, metavar='KE', help='padding size of conv filters')
# parser.add_argument('--stride', default='2', type=str, metavar='ST', help='stride size of conv filters')
# parser.add_argument('--fast', type=str, default='None', help='max pooling for fast')
#
# parser.add_argument('--cos-sim', action='store_true', default=False, help='using Cosine similarity')
# parser.add_argument('--avg-size', type=int, default=4, metavar='ES', help='Dimensionality of the embedding')
# parser.add_argument('--time-dim', default=1, type=int, metavar='FEAT', help='acoustic feature dimension')
# parser.add_argument('--embedding-size', type=int, default=128, metavar='ES',
#                     help='Dimensionality of the embedding')
# parser.add_argument('--batch-size', type=int, default=1, metavar='BS',
#                     help='input batch size for training (default: 128)')
# parser.add_argument('--input-per-spks', type=int, default=224, metavar='IPFT',
#                     help='input sample per file for testing (default: 8)')
# parser.add_argument('--num-valid', type=int, default=5, metavar='IPFT',
#                     help='input sample per file for testing (default: 8)')
# parser.add_argument('--test-input-per-file', type=int, default=4, metavar='IPFT',
#                     help='input sample per file for testing (default: 8)')
# parser.add_argument('--test-batch-size', type=int, default=1, metavar='BST',
#                     help='input batch size for testing (default: 64)')
# parser.add_argument('--dropout-p', type=float, default=0., metavar='BST',
#                     help='input batch size for testing (default: 64)')
#
# # loss configure
# parser.add_argument('--loss-type', type=str, default='soft',
#                     help='path to voxceleb1 test dataset')
# parser.add_argument('--num-center', type=int, default=2, help='the num of source classes')
# parser.add_argument('--source-cls', type=int, default=1951,
#                     help='the num of source classes')
# parser.add_argument('--finetune', action='store_true', default=False,
#                     help='using Cosine similarity')
# parser.add_argument('--loss-ratio', type=float, default=0.1, metavar='LOSSRATIO',
#                     help='the ratio softmax loss - triplet loss (default: 2.0')
#
# # args for additive margin-softmax
# parser.add_argument('--margin', type=float, default=0.3, metavar='MARGIN',
#                     help='the margin value for the angualr softmax loss function (default: 3.0')
# parser.add_argument('--s', type=float, default=15, metavar='S',
#                     help='the margin value for the angualr softmax loss function (default: 3.0')
#
# # args for a-softmax
# parser.add_argument('--m', type=int, default=3, metavar='M',
#                     help='the margin value for the angualr softmax loss function (default: 3.0')
# parser.add_argument('--all-iteraion', type=int, default=0, metavar='M',
#                     help='the margin value for the angualr softmax loss function (default: 3.0')
# parser.add_argument('--lambda-min', type=int, default=5, metavar='S',
#                     help='random seed (default: 0)')
# parser.add_argument('--lambda-max', type=float, default=1000, metavar='S',
#                     help='random seed (default: 0)')
#
# parser.add_argument('--lr', type=float, default=0.1, metavar='LR', help='learning rate (default: 0.125)')
# parser.add_argument('--lr-decay', default=0, type=float, metavar='LRD',
#                     help='learning rate decay ratio (default: 1e-4')
# parser.add_argument('--weight-decay', default=5e-4, type=float,
#                     metavar='WEI', help='weight decay (default: 0.0)')
# parser.add_argument('--momentum', default=0.9, type=float,
#                     metavar='MOM', help='momentum for sgd (default: 0.9)')
# parser.add_argument('--dampening', default=0, type=float,
#                     metavar='DAM', help='dampening for sgd (default: 0.0)')
# parser.add_argument('--optimizer', default='sgd', type=str,
#                     metavar='OPT', help='The optimizer to use (default: Adagrad)')
# parser.add_argument('--grad-clip', default=0., type=float,
#                     help='momentum for sgd (default: 0.9)')
# # Device options
# parser.add_argument('--no-cuda', action='store_true', default=False,
#                     help='enables CUDA training')
# parser.add_argument('--gpu-id', default='0', type=str,
#                     help='id(s) for CUDA_VISIBLE_DEVICES')
# parser.add_argument('--seed', type=int, default=123456, metavar='S',
#                     help='random seed (default: 0)')
# parser.add_argument('--log-interval', type=int, default=10, metavar='LI',
#                     help='how many batches to wait before logging training status')
#
# parser.add_argument('--acoustic-feature', choices=['fbank', 'spectrogram', 'mfcc'], default='fbank',
#                     help='choose the acoustic features type.')
# parser.add_argument('--makemfb', action='store_true', default=False,
#                     help='need to make mfb file')
# parser.add_argument('--makespec', action='store_true', default=False,
#                     help='need to make spectrograms file')
# parser.add_argument('--mvnorm', action='store_true', default=False,
#                     help='need to make spectrograms file')
# parser.add_argument('--valid', action='store_true', default=False,
#                     help='need to make spectrograms file')
# parser.add_argument('--verbose', type=int, default=0, choices=[0, 1, 2],
#                     help='how many batches to wait before logging training status')
# parser.add_argument('--normalize', action='store_false', default=True,
#                     help='normalize vectors in final layer')
# parser.add_argument('--mean-vector', action='store_false', default=True, help='mean for embeddings while extracting')
# parser.add_argument('--score-norm', type=str, default='', help='score normalization')
#
# parser.add_argument('--test-mask', action='store_true', default=False, help='need to make spectrograms file')
# parser.add_argument('--mask-sub', type=str, default='0,1', help='mask input start index')
# # parser.add_argument('--mask-lenght', type=int, default=1, help='mask input start index')
#
# parser.add_argument('--n-train-snts', type=int, default=100000,
#                     help='how many batches to wait before logging training status')
# parser.add_argument('--cohort-size', type=int, default=50000,
#                     help='how many imposters to include in cohort')
#
# args = parser.parse_args()

args = args_parse('PyTorch Speaker Recognition: Extraction, Test')

# Set the device to use by setting CUDA_VISIBLE_DEVICES env variable in
# order to prevent any memory allocation on unused GPUs
os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id

args.cuda = not args.no_cuda and torch.cuda.is_available()
np.random.seed(args.seed)
torch.manual_seed(args.seed)
torch.multiprocessing.set_sharing_strategy('file_system')

if args.cuda:
    torch.cuda.manual_seed_all(args.seed)
    cudnn.benchmark = True

# create logger
# Define visulaize SummaryWriter instance
assert os.path.exists(args.resume), print(
    '=> no checkpoint found at {}'.format(args.resume))

kwargs = {'num_workers': args.nj, 'pin_memory': False} if args.cuda else {}
sys.stdout = NewLogger(os.path.join(os.path.dirname(args.resume), 'test.log'))

l2_dist = nn.CosineSimilarity(dim=-1, eps=1e-6) if args.cos_sim else nn.PairwiseDistance(p=2)

# pdb.set_trace()
feat_type = 'kaldi'
if args.feat_format == 'kaldi':
    # file_loader = read_mat
    file_loader = kaldiio.load_mat
    torch.multiprocessing.set_sharing_strategy('file_system')
elif args.feat_format == 'npy':
    file_loader = np.load
elif args.feat_format == 'wav':
    file_loader = read_WaveInt
    feat_type = 'wav'

    if args.chunk_size // 16000 <= 0:
        args.chunk_size = args.chunk_size * 160

    if args.frame_shift // 16000 <= 0:
        args.frame_shift = args.frame_shift * 160


if not args.valid:
    args.num_valid = 0

if args.test_input == 'var':
    # transform = transforms.Compose([
    #     ConcateOrgInput(remove_vad=args.remove_vad),
    # ])

    # transform for train extracting
    transform = transforms.Compose([
        ConcateVarInput(num_frames=args.chunk_size,
                        frame_shift=args.frame_shift, remove_vad=args.remove_vad,
                        feat_type=feat_type),
    ])

    transform_T = transforms.Compose([
        ConcateOrgInput(remove_vad=args.remove_vad),
    ])

elif args.test_input == 'fix':
    transform = transforms.Compose([
        ConcateVarInput(num_frames=args.chunk_size,
                        frame_shift=args.frame_shift,
                        remove_vad=args.remove_vad,
                        feat_type=feat_type),
    ])
    transform_T = transforms.Compose([
        ConcateVarInput(num_frames=args.chunk_size,
                        frame_shift=args.frame_shift,
                        remove_vad=args.remove_vad,
                        feat_type=feat_type),
    ])
else:
    raise ValueError('input length must be var or fix.')

if args.mvnorm:
    transform.transforms.append(mvnormal())
    transform_T.transforms.append(mvnormal())

def valid(valid_loader, model):
    model.eval()

    valid_pbar = tqdm(enumerate(valid_loader))
    softmax = nn.Softmax(dim=1)

    correct = 0.
    total_datasize = 0.

    for batch_idx, (data, label) in valid_pbar:
        data = Variable(data.cuda())
        # print(model.conv1.weight)
        # print(data)
        # pdb.set_trace()

        # compute output
        out, _ = model(data)
        if args.loss_type == 'asoft':
            predicted_labels, _ = out
        else:
            predicted_labels = out

        true_labels = Variable(label.cuda())

        # pdb.set_trace()
        predicted_one_labels = softmax(predicted_labels)
        predicted_one_labels = torch.max(predicted_one_labels, dim=1)[1]

        batch_correct = (predicted_one_labels.cuda() ==
                         true_labels.cuda()).sum().item()
        minibatch_acc = float(batch_correct / len(predicted_one_labels))
        correct += batch_correct
        total_datasize += len(predicted_one_labels)

        if batch_idx % args.log_interval == 0:
            valid_pbar.set_description('Valid: [{:8d}/{:8d} ({:3.0f}%)] Batch Accuracy: {:.4f}%'.format(
                batch_idx * len(data),
                len(valid_loader.dataset),
                100. * batch_idx / len(valid_loader),
                100. * minibatch_acc
            ))

    valid_accuracy = 100. * correct / total_datasize
    print('  \33[91mValid Accuracy is %.4f %%.\33[0m' % valid_accuracy)
    torch.cuda.empty_cache()


def test(test_loader, xvector_dir, test_cohort_scores=None):
    # switch to evaluate mode
    labels, distances = [], []
    l_batch = []
    d_batch = []
    pbar = tqdm(enumerate(test_loader)
                ) if args.verbose > 0 else enumerate(test_loader)
    for batch_idx, this_batch in pbar:
        if test_cohort_scores != None:

            data_a, data_p, label, uid_a, uid_b = this_batch
        else:
            data_a, data_p, label = this_batch

        # .cuda()  # .view(-1, 4, embedding_size)
        data_a = torch.tensor(data_a).cuda()
        data_p = torch.tensor(data_p).cuda()  # .cuda()  # .view(-

        # if out_p.shape[-1] != args.embedding_size:
        #     out_p = out_p.reshape(-1, args.embedding_size)

        # if args.cluster == 'mean':
        #     out_a = out_a.mean(dim=0, keepdim=True)
        #     out_p = out_p.mean(dim=0, keepdim=True)
        #
        # elif args.cluster == 'cross':
        #     out_a_first = out_a.shape[0]
        #     out_a = out_a.repeat(out_p.shape[0], 1)
        #     out_p = out_p.reshape(out_a_first, 1)
        if len(data_a.shape) == 3:
            data_a_dim1 = data_a.shape[1]
            data_a = data_a.repeat_interleave(data_p.shape[1], dim=1)
            data_p = data_p.repeat_interleave(data_a_dim1, dim=1)
        #
        # else:
        # dists = (data_a[:, :, None] - data_p[:]).norm(p=2, dim=-1)

        # print(dists.shape)
        # pdb.set_trace()
        dists = l2_dist(data_a, data_p)

        if len(dists.shape) == 3:
            dists = dists.mean(dim=-1).mean(dim=-1)
        elif len(dists.shape) == 2:
            dists = dists.mean(dim=-1)

        dists = dists.cpu().numpy()
        label = label.cpu().numpy()

        if test_cohort_scores != None:
            enroll_mean_std = np.array(
                [test_cohort_scores[uid] for uid in uid_a])

            mean_e_c = enroll_mean_std[:, 0]
            std_e_c = enroll_mean_std[:, 1]

            test_mean_std = np.array(
                [test_cohort_scores[uid] for uid in uid_b])

            mean_t_c = test_mean_std[:, 0]
            std_t_c = test_mean_std[:, 1]
            # [test_cohort_scores[uid] for uid in uid_b]

            if args.score_norm == "z-norm":
                dists = (dists - mean_e_c) / std_e_c
            elif args.score_norm == "t-norm":
                dists = (dists - mean_t_c) / std_t_c
            elif args.score_norm in ["s-norm", "as-norm"]:
                score_e = (dists - mean_e_c) / std_e_c
                score_t = (dists - mean_t_c) / std_t_c
                dists = 0.5 * (score_e + score_t)

        if len(dists) == 1:
            d_batch.append(float(dists[0]))
            l_batch.append(label[0])

            if len(l_batch) >= 128 or len(test_loader.dataset) == (batch_idx + 1):
                distances.append(d_batch)
                labels.append(l_batch)

                l_batch = []
                d_batch = []
        else:
            distances.append(dists)
            labels.append(label)

        if args.verbose > 0 and batch_idx % args.log_interval == 0:
            pbar.set_description('Test: [{}/{} ({:.0f}%)]'.format(
                batch_idx * len(data_a), len(test_loader.dataset), 100. * batch_idx / len(test_loader)))

        del data_a, data_p

    labels    = np.array([sublabel for label in labels for sublabel in label])
    distances = np.array([subdist for dist in distances for subdist in dist])

    time_stamp = time.strftime("%Y.%m.%d.%X", time.localtime(
    )) if args.score_suffix == '' else args.score_suffix

    score_file = os.path.join(xvector_dir, 'score.' + time_stamp)
    with open(score_file, 'w') as f:
        for l in zip(labels, distances):
            f.write(" ".join([str(i) for i in l]) + '\n')

    # pdb.set_trace()
    eer, eer_threshold, accuracy = evaluate_kaldi_eer(
        distances, labels, cos=args.cos_sim, re_thre=True)
    mindcf_01, mindcf_001 = evaluate_kaldi_mindcf(distances, labels)

    dist_type = 'cos' if args.cos_sim else 'l2'
    test_directorys = args.test_dir.split('/')
    test_set_name = '-'
    for i, dir in enumerate(test_directorys):
        if dir == 'data':
            # try:
            #     test_subset = test_directorys[i + 3].split('_')[0]
            # except Exception as e:
            #     test_subset = test_directorys[i + 2].split('_')[0]
            test_set_name = "-".join(test_directorys[(i+1):])
            test_set_name = test_set_name.replace('_', '-')

            # test_set_name = "-".join((test_directorys[i + 1], test_subset))
    if args.score_suffix != '':
        test_set_name = '-'.join((test_set_name, args.score_suffix))

    if args.score_norm in ["z-norm", "t-norm", "s-norm", "as-norm"]:
        test_set_name = '-'.join((test_set_name, args.score_norm))

    result_str = ''
    if args.verbose > 0:
        result_str += 'For %s_distance, %d pairs:\n' % (dist_type, len(labels))
    result_str += '\33[91m'
    tab_line = '+------------------------------------------+------------+------------+--------------+---------------+---------------------+\n'
    if args.verbose > 0:
        result_str +=  tab_line

        result_str += '| {: <40s} |  {: >8s}  | {: >8s}  | {: >8s}  | {: >8s}  | {: >19s} |\n'.format('Test Set',
                                                                                         'EER (%)',
                                                                                         'Threshold',
                                                                                         'MinDCF-0.01',
                                                                                         'MinDCF-0.001',
                                                                                         'Date')
    if args.verbose > 0:
        result_str += tab_line

    eer = '{:.4f}'.format(eer * 100.)
    threshold = '{:.4f}'.format(eer_threshold)
    mindcf_01 = '{:.4f}'.format(mindcf_01)
    mindcf_001 = '{:.4f}'.format(mindcf_001)
    date = time.strftime("%Y%m%d %H:%M:%S", time.localtime())

    result_str += '| {: <40s} |  {: >8s}  | {: >8s}  | {: >8s}  | {: >8s}  | {: >19s} |'.format(test_set_name,
                                                                                   eer,
                                                                                   threshold,
                                                                                   mindcf_01,
                                                                                   mindcf_001,
                                                                                   date)
    if args.verbose > 0:
        result_str += '\n' + tab_line
    result_str += '\33[0m'

    print(result_str)

    result_file = os.path.join(xvector_dir, '%sresult.' %
                               args.score_norm + time_stamp)
    with open(result_file, 'w') as f:
        f.write(result_str)


def cohort(train_xvectors_dir, test_xvectors_dir):
    train_xvectors_scp = os.path.join(train_xvectors_dir, 'xvectors.scp')
    test_xvectors_scp = os.path.join(test_xvectors_dir, 'xvectors.scp')

    assert os.path.exists(train_xvectors_scp), print(train_xvectors_scp)
    assert os.path.exists(test_xvectors_scp), print(test_xvectors_scp)

    train_stats = {}

    train_vectors = []
    train_scps = []
    with open(train_xvectors_scp, 'r') as f:
        for l in f.readlines():
            uid, vpath = l.split()
            train_scps.append((uid, vpath))

    random.shuffle(train_scps)

    if args.n_train_snts < len(train_scps):
        train_scps = train_scps[:args.n_train_snts]

    for (uid, vpath) in train_scps:
        train_vectors.append(file_loader(vpath))

    train_vectors = torch.tensor(train_vectors).cuda()
    if args.cos_sim:
        train_vectors = train_vectors / \
            train_vectors.norm(p=2, dim=1).unsqueeze(1)

    with open(test_xvectors_scp, 'r') as f:
        pbar = tqdm(f.readlines(),
                    ncols=100) if args.verbose > 0 else f.readlines()

        for l in pbar:
            uid, vpath = l.split()

            test_vector = torch.tensor(file_loader(vpath))
            # pdb.set_trace()
            if args.cos_sim:
                test_vector = test_vector.cuda()
                scores = torch.matmul(
                    train_vectors, test_vector / test_vector.norm(p=2))

                if args.score_norm == "as-norm":
                    scores = torch.topk(scores, k=args.cohort_size, dim=0)[0]
            else:
                test_vector = test_vector.repeat(
                    train_vectors.shape[0], 1).cuda()
                scores = l2_dist(test_vector, train_vectors)

                if args.score_norm == "as-norm":
                    scores = -torch.topk(-scores, k=args.cohort_size, dim=0)[0]

            mean_t_c = torch.mean(scores, dim=0).cpu()
            std_t_c = torch.std(scores, dim=0).cpu()

            train_stats[uid] = [mean_t_c, std_t_c]

    with open(test_xvectors_dir + '/cohort_%d_%d.pickle' % (args.n_train_snts, args.cohort_size), 'wb') as f:
        pickle.dump(train_stats, f, protocol=pickle.HIGHEST_PROTOCOL)

    # pickle.dump(train_stats, test_xvectors_dir)

    return train_stats

def xvector_exists(test_xvectors_dir, verfify_dir):
    test_uids = verfify_dir.uids

    test_xvectors_scp = os.path.join(test_xvectors_dir, 'xvectors.scp')
    if not os.path.exists(test_xvectors_scp):
        return False
        #print(test_xvectors_scp)

    exists_uids = set([])
    with open(test_xvectors_scp, 'r') as f:
        for l in f.readlines():
            uid, offset = l.split()
            exists_uids.add(uid)

    for uid in test_uids:
        if uid not in exists_uids:
            return False
        
    return True


if __name__ == '__main__':

    # Views the training images and displays the distance on anchor-negative and anchor-positive
    # test_display_triplet_distance = False
    # print the experiment configuration
    if args.verbose > 0:
        print('\nCurrent time is \33[91m{}\33[0m.'.format(str(time.asctime())))
    opts = vars(args)
    keys = list(opts.keys())
    keys.sort()
    options = []
    for k in keys:
        options.append("\'%s\': \'%s\'" % (str(k), str(opts[k])))
    if args.verbose > 1:
        print('Parsed options: \n{ %s }' % (', '.join(options)))
        # print('Number of Speakers: {}.\n'.format(train_dir.num_spks))
    if args.verbose > 1:
        # print('Model options: {}'.format(model_kwargs))
        dist_type = 'cos' if args.cos_sim else 'l2'
        print('Testing with %s distance, ' % dist_type)

    start_time = time.time()
    test_xvector_dir  = os.path.join(args.xvector_dir, 'test')
    if args.train_xvector_dir == '':
        train_xvector_dir = os.path.join(args.xvector_dir, 'train')
    else:
        train_xvector_dir = args.train_xvector_dir

    if args.valid or args.extract:
        train_dir = ScriptTrainDataset(dir=args.train_dir, samples_per_speaker=args.input_per_spks, loader=file_loader,
                               feat_type=feat_type,
                               transform=transform, num_valid=args.num_valid, verbose=args.verbose)

        if args.score_norm != '' and os.path.isdir(args.train_extract_dir):
            train_extract_dir = KaldiExtractDataset(dir=args.train_extract_dir, transform=transform, 
                                                    filer_loader=file_loader, feat_type=feat_type,
                                                    verbose=args.verbose, trials_file='')

        if args.valid:
            valid_dir = ScriptValidDataset(valid_set=train_dir.valid_set, loader=file_loader,
                                        spk_to_idx=train_dir.spk_to_idx,
                                        valid_uid2feat=train_dir.valid_uid2feat,
                                        valid_utt2spk_dict=train_dir.valid_utt2spk_dict,
                                        transform=transform, verbose=args.verbose)

        with open(args.check_yaml, 'r') as f:
            config_args = load_hyperpyyaml(f)

        if 'embedding_model' in config_args:
            model = config_args['embedding_model']

        if 'classifier' in config_args:
            model.classifier = config_args['classifier']
        else:
            create_classifier(model, **config_args)
        # model = create_model(args.model, **model_kwargs)

        if 'domain_classifier' in config_args:
            model.domain_classifier = config_args['domain_classifier']

        if 'adapter_type' in config_args:
            adapter_rate = config_args['adapter_rate'] if 'adapter_rate' in config_args else 0
            model = Adapter(model, scale=config_args['scale'],
                    layers=config_args['layers'], adapter_rate=adapter_rate,
                    adapter_steps=0,
                    adapter_type=config_args['adapter_type'])

        if args.verbose > 0:
            print('=> loading checkpoint {}'.format(args.resume))
        checkpoint = torch.load(args.resume)
        # start_epoch = checkpoint['epoch']

        checkpoint_state_dict = checkpoint['state_dict']
        start = checkpoint['epoch'] if 'epoch' in checkpoint else args.start_epoch
        if args.verbose > 0:
            print('Epoch is : ' + str(start))

        if isinstance(checkpoint_state_dict, tuple):
            checkpoint_state_dict = checkpoint_state_dict[0]
        filtered = {k: v for k, v in checkpoint_state_dict.items()
                    if 'num_batches_tracked' not in k}

        # filtered = {k: v for k, v in checkpoint['state_dict'].items() if 'num_batches_tracked' not in k}
        if list(filtered.keys())[0].startswith('module'):
            new_state_dict = OrderedDict()
            for k, v in filtered.items():
                name = k[7:]  # remove `module.`，表面从第7个key值字符取到最后一个字符，去掉module.
                new_state_dict[name] = v  # 新字典的key值对应的value为一一对应的值。
            filtered = new_state_dict

        if 'fc1.1.weight' in filtered:
            model.fc1 = nn.Sequential(
                nn.Linear(model.encoder_output, model.embedding_size),
                nn.BatchNorm1d(model.embedding_size)
            )

        model_dict = model.state_dict()
        if 'classifier.W' in filtered and 'classifier.W' not in model_dict:
            model.classifier = None
            create_classifier(model, **config_args)
            model_dict = model.state_dict()

        model_dict.update(filtered)

        model.load_state_dict(model_dict)
        # model.dropout.p = args.dropout_p

        if args.test_mask:
            mask_str = args.mask_sub
            # print(mask_str)
            mask_str = mask_str.split(',')
            start = int(mask_str[0])
            end = int(mask_str[1])
            # transform.transforms.append(FreqMaskIndexLayer(start=start, mask_len=end))
            # transform_T.transforms.append(
                # FreqMaskIndexLayer(start=start, mask_len=end))
            trans = model.input_mask
            model.input_mask.add_module(str(len(trans)), 
                                        FreqMaskIndexLayer(start=start, mask_len=end))
            if args.verbose > 0:
                print('Mean set values in frequecy from %d to %d.' % (start, end))

                if args.verbose > 1:
                    print("==> input-mask: \n", model.input_mask)

        # print(model)
        if args.cuda:
            model.cuda()
        # train_loader = torch.utils.data.DataLoader(train_dir, batch_size=args.batch_size, shuffle=True, **kwargs)
        if args.valid:
            valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=args.test_batch_size, shuffle=False,
                                                       **kwargs)
            valid(valid_loader, model)

        del train_dir  # , valid_dir
        if args.verbose > 0:
            print('Memery Usage: %.4f GB' % (psutil.Process(
                os.getpid()).memory_info().rss / 1024 / 1024 / 1024))

        if args.extract:
            if args.score_norm != '' and not os.path.exists(train_xvector_dir + '/xvectors.scp'):
                train_verify_loader = torch.utils.data.DataLoader(train_extract_dir,
                                                                  batch_size=args.test_batch_size,
                                                                  shuffle=False, **kwargs)
                train_test_input = 'fix' if args.batch_size > 1 else 'var'
                verification_extract(train_verify_loader, model, xvector_dir=train_xvector_dir, epoch=start,
                                     test_input=train_test_input, ark_num=50000, gpu=True, verbose=args.verbose,
                                     mean_vector=args.mean_vector,
                                     xvector=args.xvector, input_mean=args.input_mean)
            verfify_dir = KaldiExtractDataset(dir=args.test_dir, transform=transform_T, filer_loader=file_loader,
                                  feat_type=feat_type, trials_file=args.trials,
                                  verbose=args.verbose)
            verify_loader = torch.utils.data.DataLoader(verfify_dir, batch_size=args.test_batch_size, shuffle=False,
                                                        **kwargs)
            if not xvector_exists(test_xvector_dir, verfify_dir):
                verification_extract(verify_loader, model, xvector_dir=test_xvector_dir, epoch=start,
                                    test_input=args.test_input, ark_num=50000, gpu=True, verbose=args.verbose,
                                    mean_vector=args.mean_vector,
                                    xvector=args.xvector, input_mean=args.input_mean)

    if args.test:
        file_loader = kaldiio.load_mat
        # file_loader = read_vec_flt
        return_uid = True if args.score_norm != '' else False
        test_dir = ScriptVerifyDataset(dir=args.test_dir, trials_file=args.trials,
                                         xvectors_dir=test_xvector_dir,
                                       loader=file_loader, return_uid=return_uid,
                                       verbose=args.verbose)

        test_loader = torch.utils.data.DataLoader(test_dir,
                                                  batch_size=1 if not args.mean_vector else args.test_batch_size * 128,
                                                  shuffle=False, **kwargs)

        train_stats_pickle = os.path.join(test_xvector_dir,
                                          'cohort_%d_%d.pickle' % (args.n_train_snts, args.cohort_size))

        if args.score_norm == '':
            train_stats = None
        elif os.path.isfile(train_stats_pickle):
            with open(train_stats_pickle, 'rb') as f:
                train_stats = pickle.load(f)
        else:
            train_stats = cohort(train_xvector_dir, test_xvector_dir)

        test(test_loader, xvector_dir=args.xvector_dir, test_cohort_scores=train_stats)

    stop_time = time.time()
    t = float(stop_time - start_time)
    if args.verbose > 0:
        print("Running %.4f minutes for testing.\n" % (t / 60))

