#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: prob_extract.py
@Time: 2021/9/8 21:48 PM
@Overview:
"""
from __future__ import print_function

import argparse
import json
import os
import pickle
import random
import time
from collections import OrderedDict

import numpy as np
import torch
import torch._utils
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torchvision.transforms as transforms
from kaldi_io import read_mat
from torch.autograd import Variable
from torch.utils.data import DataLoader
from tqdm import tqdm

from Define_Model.SoftmaxLoss import AngleLinear, AdditiveMarginLinear
from Define_Model.model import PairwiseDistance
from Process_Data.Datasets.KaldiDataset import ScriptTrainDataset, \
    ScriptTestDataset, ScriptValidDataset
from Process_Data.audio_processing import ConcateOrgInput, mvnormal, ConcateVarInput
from TrainAndTest.common_func import create_model

# Version conflict

try:
    torch._utils._rebuild_tensor_v2
except AttributeError:
    def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks):
        tensor = torch._utils._rebuild_tensor(storage, storage_offset, size, stride)
        tensor.requires_grad = requires_grad
        tensor._backward_hooks = backward_hooks
        return tensor


    torch._utils._rebuild_tensor_v2 = _rebuild_tensor_v2
import warnings

warnings.filterwarnings("ignore")

# Training settings
parser = argparse.ArgumentParser(description='PyTorch Speaker Recognition')
# Data options
parser.add_argument('--train-dir', type=str, help='path to dataset')
parser.add_argument('--test-dir', type=str, help='path to voxceleb1 test dataset')
parser.add_argument('--train-set-name', type=str, required=True, help='path to voxceleb1 test dataset')
parser.add_argument('--test-set-name', type=str, required=True, help='path to voxceleb1 test dataset')

parser.add_argument('--sample-utt', type=int, default=0, metavar='SU', help='Dimensionality of the embedding')
parser.add_argument('--test-only', action='store_true', default=False, help='using Cosine similarity')
parser.add_argument('--check-path', help='folder to output model checkpoints')
parser.add_argument('--extract-path', help='folder to output model grads, etc')

parser.add_argument('--start-epochs', type=int, default=36, metavar='E', help='number of epochs to train (default: 10)')
parser.add_argument('--epochs', type=int, default=36, metavar='E', help='number of epochs to train (default: 10)')

# Data options
parser.add_argument('--feat-dim', default=64, type=int, metavar='N', help='acoustic feature dimension')
parser.add_argument('--input-dim', default=257, type=int, metavar='N', help='acoustic feature dimension')

parser.add_argument('--revert', action='store_true', default=False, help='using Cosine similarity')
parser.add_argument('--input-length', choices=['var', 'fix'], default='var',
                    help='choose the acoustic features type.')
parser.add_argument('--remove-vad', action='store_true', default=False, help='using Cosine similarity')
parser.add_argument('--mvnorm', action='store_true', default=False,
                    help='using Cosine similarity')
# Model options
parser.add_argument('--model', type=str, help='path to voxceleb1 test dataset')
parser.add_argument('--resnet-size', default=8, type=int, metavar='RES', help='The channels of convs layers)')

parser.add_argument('--filter', type=str, default='None', help='replace batchnorm with instance norm')
parser.add_argument('--input-norm', type=str, default='Mean', help='batchnorm with instance norm')
parser.add_argument('--vad', action='store_true', default=False, help='vad layers')
parser.add_argument('--inception', action='store_true', default=False, help='multi size conv layer')
parser.add_argument('--inst-norm', action='store_true', default=False, help='batchnorm with instance norm')

parser.add_argument('--mask-layer', type=str, default='None', help='time or freq masking layers')
parser.add_argument('--mask-len', type=int, default=20, help='maximum length of time or freq masking layers')
parser.add_argument('--block-type', type=str, default='None', help='replace batchnorm with instance norm')
parser.add_argument('--relu-type', type=str, default='relu', help='replace batchnorm with instance norm')
parser.add_argument('--encoder-type', type=str, help='path to voxceleb1 test dataset')
parser.add_argument('--transform', type=str, default="None", help='add a transform layer after embedding layer')

parser.add_argument('--channels', default='64,128,256', type=str,
                    metavar='CHA', help='The channels of convs layers)')
parser.add_argument('--fast', type=str, default='None', help='max pooling for fast')

parser.add_argument('--kernel-size', default='5,5', type=str, metavar='KE',
                    help='kernel size of conv filters')
parser.add_argument('--padding', default='', type=str, metavar='KE', help='padding size of conv filters')
parser.add_argument('--stride', default='2', type=str, metavar='ST', help='stride size of conv filters')
parser.add_argument('--time-dim', default=1, type=int, metavar='FEAT', help='acoustic feature dimension')
parser.add_argument('--avg-size', type=int, default=4, metavar='ES', help='Dimensionality of the embedding')

parser.add_argument('--loss-type', type=str, default='soft', help='path to voxceleb1 test dataset')
parser.add_argument('--dropout-p', type=float, default=0., metavar='BST',
                    help='input batch size for testing (default: 64)')

# args for additive margin-softmax
parser.add_argument('--margin', type=float, default=0.3, metavar='MARGIN',
                    help='the margin value for the angualr softmax loss function (default: 3.0')
parser.add_argument('--s', type=float, default=15, metavar='S',
                    help='the margin value for the angualr softmax loss function (default: 3.0')
# args for a-softmax
parser.add_argument('--m', type=int, default=3, metavar='M',
                    help='the margin value for the angualr softmax loss function (default: 3.0')
parser.add_argument('--lambda-min', type=int, default=5, metavar='S',
                    help='random seed (default: 0)')
parser.add_argument('--lambda-max', type=float, default=0.05, metavar='S',
                    help='random seed (default: 0)')

parser.add_argument('--alpha', default=0, type=float,
                    metavar='l2 length', help='acoustic feature dimension')
parser.add_argument('--cos-sim', action='store_true', default=True, help='using Cosine similarity')
parser.add_argument('--embedding-size', type=int, metavar='ES', help='Dimensionality of the embedding')

parser.add_argument('--nj', default=12, type=int, metavar='NJOB', help='num of job')
parser.add_argument('--batch-size', type=int, default=1, metavar='BS',
                    help='input batch size for training (default: 128)')
parser.add_argument('--test-batch-size', type=int, default=1, metavar='BST',
                    help='input batch size for testing (default: 64)')
parser.add_argument('--input-per-spks', type=int, default=192, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--test-input-per-file', type=int, default=1, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')

# Device options
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='enables CUDA training')
parser.add_argument('--gpu-id', default='1', type=str,
                    help='id(s) for CUDA_VISIBLE_DEVICES')
parser.add_argument('--seed', type=int, default=123456, metavar='S',
                    help='random seed (default: 0)')
parser.add_argument('--log-interval', type=int, default=1, metavar='LI',
                    help='how many batches to wait before logging training status')

parser.add_argument('--acoustic-feature', choices=['fbank', 'spectrogram', 'mfcc'], default='fbank',
                    help='choose the acoustic features type.')
parser.add_argument('--makemfb', action='store_true', default=False,
                    help='need to make mfb file')
parser.add_argument('--makespec', action='store_true', default=False,
                    help='need to make spectrograms file')

args = parser.parse_args()

# Set the device to use by setting CUDA_VISIBLE_DEVICES env variable in
# order to prevent any memory allocation on unused GPUs
os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id

args.cuda = not args.no_cuda and torch.cuda.is_available()
random.seed(args.seed)
np.random.seed(args.seed)
torch.manual_seed(args.seed)
torch.multiprocessing.set_sharing_strategy('file_system')

if args.cuda:
    cudnn.benchmark = True

# Define visulaize SummaryWriter instance
kwargs = {'num_workers': args.nj, 'pin_memory': False} if args.cuda else {}
l2_dist = nn.CosineSimilarity(dim=1, eps=1e-6) if args.cos_sim else PairwiseDistance(2)

if args.input_length == 'var':
    transform = transforms.Compose([
        ConcateOrgInput(remove_vad=args.remove_vad),
    ])
    transform_T = transforms.Compose([
        ConcateOrgInput(remove_vad=args.remove_vad),
    ])
elif args.input_length == 'fix':
    transform = transforms.Compose([
        ConcateVarInput(remove_vad=args.remove_vad),
    ])
    transform_T = transforms.Compose([
        ConcateVarInput(remove_vad=args.remove_vad),
    ])

if args.mvnorm:
    transform.transforms.append(mvnormal())
    transform_T.transforms.append(mvnormal())

file_loader = read_mat

train_dir = ScriptTrainDataset(dir=args.train_dir, samples_per_speaker=args.input_per_spks,
                               loader=file_loader, transform=transform, return_uid=True)
indices = list(range(len(train_dir)))
random.shuffle(indices)
indices = indices[:args.sample_utt]
train_part = torch.utils.data.Subset(train_dir, indices)

valid_dir = ScriptValidDataset(valid_set=train_dir.valid_set, spk_to_idx=train_dir.spk_to_idx,
                               valid_uid2feat=train_dir.valid_uid2feat, valid_utt2spk_dict=train_dir.valid_utt2spk_dict,
                               loader=file_loader, transform=transform, return_uid=True)
indices = list(range(len(valid_dir)))
random.shuffle(indices)
indices = indices[:args.sample_utt]
valid_part = torch.utils.data.Subset(valid_dir, indices)

def train_extract(train_loader, model, file_dir, set_name, save_per_num=25000):
    # switch to evaluate mode
    model.eval()

    input_grads = []
    pbar = tqdm(enumerate(train_loader))

    for batch_idx, (data, label, uid) in pbar:

        # orig = data.detach().numpy().squeeze().astype(np.float32)
        with torch.no_grad():
            data = data.cuda()
            logits, _ = model(data)
            label = label.numpy()
            logits = logits.numpy()

            input_grads.append([uid, label, logits])

        if batch_idx % args.log_interval == 0:
            pbar.set_description('Saving {} : [{:8d}/{:8d} ({:3.0f}%)] '.format(
                uid,
                batch_idx + 1,
                len(train_loader.dataset),
                100. * batch_idx / len(train_loader)))

        if (batch_idx + 1) % save_per_num == 0 or (batch_idx + 1) == len(train_loader.dataset):
            num = batch_idx // save_per_num if batch_idx + 1 % save_per_num == 0 else batch_idx // save_per_num + 1
            # checkpoint_dir / extract / < dataset > / < set >.*.bin

            filename = file_dir + '/%s.%d.bin' % (set_name, num)
            with open(filename, 'wb') as f:
                pickle.dump(input_grads, f)

            input_grads = []

    print('Saving pairs in %s.\n' % file_dir)
    torch.cuda.empty_cache()

if __name__ == '__main__':

    print('\nNumber of Speakers: {}.'.format(train_dir.num_spks))
    # print the experiment configuration
    print('Current time is \33[91m{}\33[0m.'.format(str(time.asctime())))
    print('Parsed options: {}'.format(vars(args)))

    # instantiate model and initialize weights
    kernel_size = args.kernel_size.split(',')
    kernel_size = [int(x) for x in kernel_size]
    if args.padding == '':
        padding = [int((x - 1) / 2) for x in kernel_size]
    else:
        padding = args.padding.split(',')
        padding = [int(x) for x in padding]

    kernel_size = tuple(kernel_size)
    padding = tuple(padding)
    stride = args.stride.split(',')
    stride = [int(x) for x in stride]

    channels = args.channels.split(',')
    channels = [int(x) for x in channels]

    model_kwargs = {'input_dim': args.input_dim, 'feat_dim': args.feat_dim, 'kernel_size': kernel_size,
                    'mask': args.mask_layer, 'mask_len': args.mask_len, 'block_type': args.block_type,
                    'filter': args.filter, 'inst_norm': args.inst_norm, 'input_norm': args.input_norm,
                    'stride': stride, 'fast': args.fast, 'avg_size': args.avg_size, 'time_dim': args.time_dim,
                    'padding': padding, 'encoder_type': args.encoder_type, 'vad': args.vad,
                    'transform': args.transform, 'embedding_size': args.embedding_size, 'ince': args.inception,
                    'resnet_size': args.resnet_size, 'num_classes': train_dir.num_spks,
                    'channels': channels, 'alpha': args.alpha, 'dropout_p': args.dropout_p,
                    'loss_type': args.loss_type, 'm': args.m, 'margin': args.margin, 's': args.s,}

    print('Model options: {}'.format(model_kwargs))

    model = create_model(args.model, **model_kwargs)

    train_loader = DataLoader(train_part, batch_size=args.batch_size, shuffle=False, **kwargs)
    valid_loader = DataLoader(valid_part, batch_size=args.batch_size, shuffle=False, **kwargs)

    resume_path = args.check_path + '/checkpoint_{}.pth'
    print('=> Saving output in {}\n'.format(args.extract_path))
    epochs = np.arange(args.start_epochs, args.epochs + 1)

    for e in epochs:
        # Load model from Checkpoint file
        if os.path.isfile(resume_path.format(e)):
            print('=> loading checkpoint {}'.format(resume_path.format(e)))
            checkpoint = torch.load(resume_path.format(e))
            checkpoint_state_dict = checkpoint['state_dict']
            if isinstance(checkpoint_state_dict, tuple):
                checkpoint_state_dict = checkpoint_state_dict[0]

            # epoch = checkpoint['epoch']
            # if e == 0:
            #     filtered = checkpoint.state_dict()
            # else:
            filtered = {k: v for k, v in checkpoint_state_dict.items() if 'num_batches_tracked' not in k}
            if list(filtered.keys())[0].startswith('module'):
                new_state_dict = OrderedDict()
                for k, v in filtered.items():
                    name = k[7:]  # remove `module.`，表面从第7个key值字符取到最后一个字符，去掉module.
                    new_state_dict[name] = v  # 新字典的key值对应的value为一一对应的值。

                model.load_state_dict(new_state_dict)
            else:
                model_dict = model.state_dict()
                model_dict.update(filtered)
                model.load_state_dict(model_dict)

        else:
            print('=> no checkpoint found at %s' % resume_path.format(e))
            continue
        model.cuda()

        file_dir = args.extract_path + '/epoch_%d' % e
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        train_extract(train_loader, model, file_dir, '%s_train_logits'%args.train_set_name)
        train_extract(valid_loader, model, file_dir, '%s_valid_logits'%args.train_set_name)

