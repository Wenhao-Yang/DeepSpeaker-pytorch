#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: train_egs_multi.py
@Time: 2020/10/23 17:00
@Overview:
"""

from __future__ import print_function

import argparse
import os
import os.path as osp
import sys
import time
# Version conflict
import warnings

import numpy as np
import torch
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torchvision.transforms as transforms
from kaldi_io import read_mat, read_vec_flt
from tensorboardX import SummaryWriter
from torch.autograd import Variable
from torch.nn.parallel import DistributedDataParallel
from torch.optim import lr_scheduler
from tqdm import tqdm

from Define_Model.LossFunction import CenterLoss, Wasserstein_Loss, MultiCenterLoss, CenterCosLoss
from Define_Model.SoftmaxLoss import AngleSoftmaxLoss, AngleLinear, AdditiveMarginLinear, AMSoftmaxLoss, ArcSoftmaxLoss, \
    GaussianLoss
from Process_Data import constants as c
from Process_Data.Datasets.KaldiDataset import KaldiExtractDataset, \
    ScriptVerifyDataset
from Process_Data.Datasets.LmdbDataset import EgsDataset
from Process_Data.audio_processing import concateinputfromMFB, ConcateVarInput, tolog
from Process_Data.audio_processing import toMFB, totensor, truncatedinput, read_audio
from TrainAndTest.common_func import create_optimizer, create_model, verification_test, verification_extract
from logger import NewLogger

warnings.filterwarnings("ignore")

import torch._utils

try:
    torch._utils._rebuild_tensor_v2
except AttributeError:
    def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks):
        tensor = torch._utils._rebuild_tensor(storage, storage_offset, size, stride)
        tensor.requires_grad = requires_grad
        tensor._backward_hooks = backward_hooks
        return tensor


    torch._utils._rebuild_tensor_v2 = _rebuild_tensor_v2

# Training settings
parser = argparse.ArgumentParser(description='PyTorch Speaker Recognition')
# Data options
parser.add_argument('--train-dir-a', type=str, help='path to dataset')
parser.add_argument('--train-dir-b', type=str, help='path to dataset')
parser.add_argument('--train-test-dir', type=str, help='path to dataset')

parser.add_argument('--valid-dir-a', type=str, help='path to dataset')
parser.add_argument('--valid-dir-b', type=str, help='path to dataset')
parser.add_argument('--test-dir', type=str,
                    default='/home/work2020/yangwenhao/project/lstm_speaker_verification/data/vox1/spect/test_power',
                    help='path to voxceleb1 test dataset')
parser.add_argument('--log-scale', action='store_true', default=False, help='log power spectogram')

parser.add_argument('--train-trials', type=str, default='trials', help='path to voxceleb1 test dataset')
parser.add_argument('--trials', type=str, default='trials', help='path to voxceleb1 test dataset')
parser.add_argument('--sitw-dir', type=str,
                    default='/home/yangwenhao/local/project/lstm_speaker_verification/data/sitw',
                    help='path to voxceleb1 test dataset')
parser.add_argument('--remove-vad', action='store_true', default=False, help='using Cosine similarity')
parser.add_argument('--extract', action='store_true', default=True, help='need to make mfb file')

parser.add_argument('--nj', default=10, type=int, metavar='NJOB', help='num of job')
parser.add_argument('--feat-format', type=str, default='kaldi', choices=['kaldi', 'npy'],
                    help='number of jobs to make feats (default: 10)')

parser.add_argument('--check-path', default='Data/checkpoint/GradResNet8/vox1/spect_egs/soft_dp25',
                    help='folder to output model checkpoints')
parser.add_argument('--save-init', action='store_true', default=True, help='need to make mfb file')
parser.add_argument('--resume', type=str, metavar='PATH', help='path to latest checkpoint (default: none)')

parser.add_argument('--start-epoch', default=1, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('--epochs', type=int, default=20, metavar='E',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--scheduler', default='multi', type=str,
                    metavar='SCH', help='The optimizer to use (default: Adagrad)')
parser.add_argument('--patience', default=4, type=int,
                    metavar='PAT', help='patience for scheduler (default: 4)')
parser.add_argument('--gamma', default=0.75, type=float,
                    metavar='GAMMA', help='The optimizer to use (default: Adagrad)')
parser.add_argument('--milestones', default='10,15', type=str,
                    metavar='MIL', help='The optimizer to use (default: Adagrad)')
parser.add_argument('--min-softmax-epoch', type=int, default=40, metavar='MINEPOCH',
                    help='minimum epoch for initial parameter using softmax (default: 2')
parser.add_argument('--veri-pairs', type=int, default=20000, metavar='VP',
                    help='number of epochs to train (default: 10)')

# Training options
# Model options
parser.add_argument('--model', type=str, help='path to voxceleb1 test dataset')
parser.add_argument('--resnet-size', default=8, type=int,
                    metavar='RES', help='The channels of convs layers)')
parser.add_argument('--filter', type=str, default='None', help='replace batchnorm with instance norm')
parser.add_argument('--mask-layer', type=str, default='None', help='time or freq masking layers')
parser.add_argument('--mask-len', type=int, default=20, help='maximum length of time or freq masking layers')
parser.add_argument('--block-type', type=str, default='None', help='resnet block type')
parser.add_argument('--transform', type=str, default='None', help='add a transform layer after embedding layer')

parser.add_argument('--vad', action='store_true', default=False, help='vad layers')
parser.add_argument('--inception', action='store_true', default=False, help='multi size conv layer')
parser.add_argument('--inst-norm', action='store_true', default=False, help='batchnorm with instance norm')
parser.add_argument('--input-norm', type=str, default='Mean', help='batchnorm with instance norm')
parser.add_argument('--encoder-type', type=str, default='SAP', help='path to voxceleb1 test dataset')
parser.add_argument('--channels', default='64,128,256', type=str,
                    metavar='CHA', help='The channels of convs layers)')
parser.add_argument('--feat-dim', default=64, type=int, metavar='N', help='acoustic feature dimension')
parser.add_argument('--input-dim', default=257, type=int, metavar='N', help='acoustic feature dimension')
parser.add_argument('--input-len', default=300, type=int, metavar='N', help='acoustic feature dimension')

parser.add_argument('--accu-steps', default=1, type=int, metavar='N', help='manual epoch number (useful on restarts)')

parser.add_argument('--alpha', default=12, type=float, metavar='FEAT', help='acoustic feature dimension')
parser.add_argument('--ring', default=12, type=float, metavar='FEAT', help='acoustic feature dimension')
parser.add_argument('--kernel-size', default='5,5', type=str, metavar='KE', help='kernel size of conv filters')
parser.add_argument('--padding', default='', type=str, metavar='KE', help='padding size of conv filters')
parser.add_argument('--stride', default='2', type=str, metavar='ST', help='stride size of conv filters')
parser.add_argument('--fast', action='store_true', default=False, help='max pooling for fast')

parser.add_argument('--cos-sim', action='store_true', default=False, help='using Cosine similarity')
parser.add_argument('--avg-size', type=int, default=4, metavar='ES', help='Dimensionality of the embedding')
parser.add_argument('--time-dim', default=2, type=int, metavar='FEAT', help='acoustic feature dimension')
parser.add_argument('--embedding-size', type=int, default=128, metavar='ES',
                    help='Dimensionality of the embedding')
parser.add_argument('--batch-size', type=int, default=128, metavar='BS',
                    help='input batch size for training (default: 128)')
parser.add_argument('--input-per-spks', type=int, default=224, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--num-valid', type=int, default=5, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--test-input-per-file', type=int, default=4, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--test-batch-size', type=int, default=4, metavar='BST',
                    help='input batch size for testing (default: 64)')
parser.add_argument('--dropout-p', type=float, default=0.25, metavar='BST',
                    help='input batch size for testing (default: 64)')

# loss configure
parser.add_argument('--loss-type', type=str, default='soft', help='path to voxceleb1 test dataset')
parser.add_argument('--num-center', type=int, default=2, help='the num of source classes')
parser.add_argument('--source-cls', type=int, default=1951,
                    help='the num of source classes')

parser.add_argument('--finetune', action='store_true', default=False,
                    help='using Cosine similarity')
parser.add_argument('--set-ratio', type=float, default=0.6, metavar='LOSSRATIO',
                    help='the ratio softmax loss - triplet loss (default: 2.0')
parser.add_argument('--loss-ratio', type=float, default=0.1, metavar='LOSSRATIO',
                    help='the ratio softmax loss - triplet loss (default: 2.0')

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
parser.add_argument('--lambda-max', type=float, default=1000, metavar='S',
                    help='random seed (default: 0)')

parser.add_argument('--lr', type=float, default=0.1, metavar='LR', help='learning rate (default: 0.125)')
parser.add_argument('--lr-decay', default=0, type=float, metavar='LRD',
                    help='learning rate decay ratio (default: 1e-4')
parser.add_argument('--weight-decay', default=5e-4, type=float,
                    metavar='WEI', help='weight decay (default: 0.0)')
parser.add_argument('--momentum', default=0.9, type=float,
                    metavar='MOM', help='momentum for sgd (default: 0.9)')
parser.add_argument('--dampening', default=0, type=float,
                    metavar='DAM', help='dampening for sgd (default: 0.0)')
parser.add_argument('--optimizer', default='sgd', type=str,
                    metavar='OPT', help='The optimizer to use (default: Adagrad)')
parser.add_argument('--grad-clip', default=10., type=float,
                    help='momentum for sgd (default: 0.9)')
# Device options
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='enables CUDA training')
parser.add_argument('--gpu-id', default='0', type=str,
                    help='id(s) for CUDA_VISIBLE_DEVICES')
parser.add_argument('--seed', type=int, default=123456, metavar='S',
                    help='random seed (default: 0)')
parser.add_argument('--log-interval', type=int, default=10, metavar='LI',
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
np.random.seed(args.seed)
torch.manual_seed(args.seed)
# torch.multiprocessing.set_sharing_strategy('file_system')

if args.cuda:
    torch.cuda.manual_seed_all(args.seed)
    cudnn.benchmark = True

# create logger
# Define visulaize SummaryWriter instance
writer = SummaryWriter(logdir=args.check_path, filename_suffix='_first')

sys.stdout = NewLogger(osp.join(args.check_path, 'log.%s.txt' % time.strftime("%Y.%m.%d", time.localtime())))

kwargs = {'num_workers': args.nj, 'pin_memory': False} if args.cuda else {}
if not os.path.exists(args.check_path):
    os.makedirs(args.check_path)

opt_kwargs = {'lr': args.lr, 'lr_decay': args.lr_decay, 'weight_decay': args.weight_decay, 'dampening': args.dampening,
              'momentum': args.momentum}

l2_dist = nn.CosineSimilarity(dim=1, eps=1e-12) if args.cos_sim else nn.PairwiseDistance(p=2)

if args.acoustic_feature == 'fbank':
    transform = transforms.Compose([
        totensor()
    ])
    transform_T = transforms.Compose([
        concateinputfromMFB(num_frames=c.NUM_FRAMES_SPECT, input_per_file=args.test_input_per_file,
                            remove_vad=args.remove_vad),
    ])
    transform_V = transforms.Compose([
        ConcateVarInput(remove_vad=args.remove_vad),
        # varLengthFeat(remove_vad=args.remove_vad),
        # concateinputfromMFB(num_frames=c.NUM_FRAMES_SPECT, input_per_file=args.test_input_per_file,
        #                     remove_vad=args.remove_vad),
    ])

else:
    transform = transforms.Compose([
        truncatedinput(),
        toMFB(),
        totensor(),
        # tonormal()
    ])
    file_loader = read_audio

if args.log_scale:
    transform.transforms.append(tolog())
    transform_T.transforms.append(tolog())
    transform_V.transforms.append(tolog())

# pdb.set_trace()
if args.feat_format == 'kaldi':
    file_loader = read_mat
elif args.feat_format == 'npy':
    file_loader = np.load
torch.multiprocessing.set_sharing_strategy('file_system')

train_dir_a = EgsDataset(dir=args.train_dir_a, feat_dim=args.feat_dim, loader=file_loader, transform=transform)
train_dir_b = EgsDataset(dir=args.train_dir_b, feat_dim=args.feat_dim, loader=file_loader, transform=transform)

train_extract_dir = KaldiExtractDataset(dir=args.train_test_dir,
                                        transform=transform_V,
                                        filer_loader=file_loader,
                                        trials_file=args.train_trials)
extract_dir = KaldiExtractDataset(dir=args.test_dir, transform=transform_V, filer_loader=file_loader)
# test_dir = ScriptTestDataset(dir=args.test_dir, loader=file_loader, transform=transform_T)

# if len(test_dir) < args.veri_pairs:
#     args.veri_pairs = len(test_dir)
#     print('There are %d verification pairs.' % len(test_dir))
# else:
#     test_dir.partition(args.veri_pairs)

valid_dir_a = EgsDataset(dir=args.valid_dir_a, feat_dim=args.feat_dim, loader=file_loader, transform=transform)
valid_dir_b = EgsDataset(dir=args.valid_dir_b, feat_dim=args.feat_dim, loader=file_loader, transform=transform)



def main():
    # Views the training images and displays the distance on anchor-negative and anchor-positive
    # test_display_triplet_distance = False
    # print the experiment configuration
    print('\nCurrent time is \33[91m{}\33[0m.'.format(str(time.asctime())))
    opts = vars(args)
    keys = list(opts.keys())
    keys.sort()

    options = []
    for k in keys:
        options.append("\'%s\': \'%s\'" % (str(k), str(opts[k])))

    print('Parsed options: \n{ %s }' % (', '.join(options)))
    print('Number of Speakers for set A: {}.'.format(train_dir_a.num_spks))
    print('Number of Speakers for set B: {}.\n'.format(train_dir_b.num_spks))

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
                    'resnet_size': args.resnet_size, 'num_classes_a': train_dir_a.num_spks,
                    'num_classes_b': train_dir_b.num_spks, 'input_len': args.input_len,
                    'channels': channels, 'alpha': args.alpha, 'dropout_p': args.dropout_p}

    print('Model options: {}'.format(model_kwargs))
    model = create_model(args.model, **model_kwargs)

    start_epoch = 0
    if args.save_init and not args.finetune:
        check_path = '{}/checkpoint_{}.pth'.format(args.check_path, start_epoch)
        torch.save(model, check_path)

    if args.resume:
        if os.path.isfile(args.resume):
            print('=> loading checkpoint {}'.format(args.resume))
            checkpoint = torch.load(args.resume)
            start_epoch = checkpoint['epoch']

            # filtered = {k: v for k, v in checkpoint['state_dict'].items() if 'num_batches_tracked' not in k}
            # filtered = {k: v for k, v in checkpoint['state_dict'] if 'num_batches_tracked' not in k}
            checkpoint_state_dict = checkpoint['state_dict']
            if isinstance(checkpoint_state_dict, tuple):
                checkpoint_state_dict = checkpoint_state_dict[0]
            filtered = {k: v for k, v in checkpoint_state_dict.items() if 'num_batches_tracked' not in k}
            model_dict = model.state_dict()
            model_dict.update(filtered)
            model.load_state_dict(model_dict)
            # model.dropout.p = args.dropout_p
        else:
            print('=> no checkpoint found at {}'.format(args.resume))

    ce_criterion = nn.CrossEntropyLoss()
    if args.loss_type == 'soft':
        xe_criterion = None
    elif args.loss_type == 'asoft':
        ce_criterion = None
        model.classifier_a = AngleLinear(in_features=args.embedding_size, out_features=train_dir_a.num_spks, m=args.m)
        model.classifier_b = AngleLinear(in_features=args.embedding_size, out_features=train_dir_b.num_spks, m=args.m)
        xe_criterion = AngleSoftmaxLoss(lambda_min=args.lambda_min, lambda_max=args.lambda_max)

    elif args.loss_type == 'center':
        xe_criterion = CenterLoss(num_classes=int(train_dir_a.num_spks + train_dir_b.num_spks),
                                  feat_dim=args.embedding_size)
        if args.resume:
            try:
                criterion = checkpoint['criterion']
                xe_criterion.load_state_dict(criterion[1].state_dict())
            except:
                pass

    elif args.loss_type == 'gaussian':
        xe_criterion = GaussianLoss(num_classes=int(train_dir_a.num_spks + train_dir_b.num_spks),
                                    feat_dim=args.embedding_size)
    elif args.loss_type == 'coscenter':
        xe_criterion = CenterCosLoss(num_classes=int(train_dir_a.num_spks + train_dir_b.num_spks),
                                     feat_dim=args.embedding_size)
        if args.resume:
            try:
                criterion = checkpoint['criterion']
                xe_criterion.load_state_dict(criterion[1].state_dict())
            except:
                pass

    elif args.loss_type == 'mulcenter':
        xe_criterion = MultiCenterLoss(num_classes=int(train_dir_a.num_spks + train_dir_b.num_spks),
                                       feat_dim=args.embedding_size,
                                       num_center=args.num_center)
    elif args.loss_type == 'amsoft':
        ce_criterion = None
        model.classifier_a = AdditiveMarginLinear(feat_dim=args.embedding_size, n_classes=train_dir_a.num_spks)
        model.classifier_b = AdditiveMarginLinear(feat_dim=args.embedding_size, n_classes=train_dir_b.num_spks)
        xe_criterion = AMSoftmaxLoss(margin=args.margin, s=args.s)

    elif args.loss_type == 'arcsoft':
        ce_criterion = None
        model.classifier_a = AdditiveMarginLinear(feat_dim=args.embedding_size, n_classes=train_dir_a.num_spks)
        model.classifier_b = AdditiveMarginLinear(feat_dim=args.embedding_size, n_classes=train_dir_b.num_spks)
        xe_criterion = ArcSoftmaxLoss(margin=args.margin, s=args.s)
    elif args.loss_type == 'wasse':
        xe_criterion = Wasserstein_Loss(source_cls=args.source_cls)

    optimizer = create_optimizer(model.parameters(), args.optimizer, **opt_kwargs)
    if args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
        optimizer = torch.optim.SGD([{'params': xe_criterion.parameters(), 'lr': args.lr * 5},
                                     {'params': model.parameters()}],
                                    lr=args.lr, weight_decay=args.weight_decay,
                                    momentum=args.momentum)

    if args.filter == 'fDLR':
        filter_params = list(map(id, model.filter_layer.parameters()))
        rest_params = filter(lambda p: id(p) not in filter_params, model.parameters())
        optimizer = torch.optim.SGD([{'params': model.filter_layer.parameters(), 'lr': args.lr * 0.05},
                                     {'params': rest_params}],
                                    lr=args.lr, weight_decay=args.weight_decay,
                                    momentum=args.momentum)

    # Save model config txt
    with open(osp.join(args.check_path, 'model.%s.cfg' % time.strftime("%Y.%m.%d", time.localtime())), 'w') as f:
        f.write('model: ' + str(model) + '\n')
        f.write('CrossEntropy: ' + str(ce_criterion) + '\n')
        f.write('Other Loss: ' + str(xe_criterion) + '\n')
        f.write('Optimizer: ' + str(optimizer) + '\n')

    milestones = args.milestones.split(',')
    milestones = [int(x) for x in milestones]
    milestones.sort()
    if args.scheduler == 'exp':
        scheduler = lr_scheduler.ExponentialLR(optimizer, gamma=args.gamma, verbose=True)
    elif args.scheduler == 'rop':
        scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, patience=args.patience, min_lr=1e-5, verbose=True)
    else:
        scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=milestones, gamma=0.1, verbose=True)

    ce = [ce_criterion, xe_criterion]

    start = args.start_epoch + start_epoch
    print('Start epoch is : ' + str(start))
    # start = 0
    end = start + args.epochs

    batch_size_a = int(args.batch_size * len(train_dir_a) / (len(train_dir_a) + len(train_dir_b)))
    train_loader_a = torch.utils.data.DataLoader(train_dir_a, batch_size=batch_size_a, shuffle=False, **kwargs)

    # num_iteration = np.floor(len(train_dir_a) / args.batch_size)
    batch_size_b = args.batch_size - batch_size_a
    train_loader_b = torch.utils.data.DataLoader(train_dir_b, batch_size=batch_size_b, shuffle=False, **kwargs)
    train_loader = [train_loader_a, train_loader_b]

    train_extract_loader = torch.utils.data.DataLoader(train_extract_dir, batch_size=1, shuffle=False, **kwargs)

    print('Batch_size is {} for A, and {} for B.'.format(batch_size_a, batch_size_b))

    batch_size_a = int(args.batch_size / 8)
    valid_loader_a = torch.utils.data.DataLoader(valid_dir_a, batch_size=batch_size_a, shuffle=False,
                                                 **kwargs)

    batch_size_b = int(len(valid_dir_b) / len(valid_dir_a) * batch_size_a)
    valid_loader_b = torch.utils.data.DataLoader(valid_dir_b, batch_size=batch_size_b, shuffle=False,
                                                 **kwargs)
    valid_loader = valid_loader_a, valid_loader_b

    # test_loader = torch.utils.data.DataLoader(test_dir, batch_size=int(args.batch_size / 16), shuffle=False, **kwargs)
    # sitw_test_loader = torch.utils.data.DataLoader(sitw_test_dir, batch_size=args.test_batch_size,
    #                                                shuffle=False, **kwargs)
    # sitw_dev_loader = torch.utils.data.DataLoader(sitw_dev_part, batch_size=args.test_batch_size, shuffle=False,
    #                                               **kwargs)
    # print('Batcch_size is {} for A, and {} for B.'.format(batch_size_a, batch_size_b))
    if args.cuda:
        if len(args.gpu_id) > 1:
            print("Continue with gpu: %s ..." % str(args.gpu_id))
            torch.distributed.init_process_group(backend="nccl",
                                                 # init_method='tcp://localhost:23456',
                                                 init_method='file:///home/work2020/yangwenhao/project/lstm_speaker_verification/data/sharedfile',
                                                 rank=0,
                                                 world_size=1)
            model = model.cuda()
            model = DistributedDataParallel(model, find_unused_parameters=True)

        else:
            model = model.cuda()

        for i in range(len(ce)):
            if ce[i] != None:
                ce[i] = ce[i].cuda()
        try:
            print('Dropout is {}.'.format(model.dropout_p))
        except:
            pass

    xvector_dir = args.check_path
    xvector_dir = xvector_dir.replace('checkpoint', 'xvector')

    start_time = time.time()
    for epoch in range(start, end):
        # pdb.set_trace()
        print('\n\33[1;34m Current \'{}\' learning rate is '.format(args.optimizer), end='')
        for param_group in optimizer.param_groups:
            print('{:.5f} '.format(param_group['lr']), end='')
        print(' \33[0m')
        # pdb.set_trace()
        train(train_loader, model, ce, optimizer, epoch)
        valid_loss = valid_class(valid_loader, model, ce, epoch)

        if epoch % 4 == 1 or epoch == (end - 1) or epoch in milestones:
            check_path = '{}/checkpoint_{}.pth'.format(args.check_path, epoch)
            model_state_dict = model.module.state_dict() \
                                   if isinstance(model, DistributedDataParallel) else model.state_dict(),

            torch.save({'epoch': epoch, 'state_dict': model_state_dict, 'criterion': ce},
                       check_path)

        if epoch % 2 == 1 or epoch == (end - 1):
            valid_test(train_extract_loader, model, epoch, xvector_dir)

        if epoch != (end - 2) and (epoch % 4 == 1 or epoch in milestones or epoch == (end - 1)):
            test(model, epoch, writer, xvector_dir)

        if args.scheduler == 'rop':
            scheduler.step(valid_loss)
        else:
            scheduler.step()

        # exit(1)
    writer.close()
    stop_time = time.time()
    t = float(start_time - stop_time)
    print("Running %.4f minutes for each epoch.\n" % (t / 60 / (end - start)))


def train(train_loader, model, ce, optimizer, epoch):
    # switch to evaluate mode
    model.train()

    correct_a = 0.
    correct_b = 0.

    total_datasize_a = 0.
    total_datasize_b = 0.

    total_loss = 0.

    ce_criterion, xe_criterion = ce
    train_loader_a, train_loader_b = train_loader
    pbar = tqdm(enumerate(zip(train_loader_a, train_loader_b)))
    output_softmax = nn.Softmax(dim=1)
    # start_time = time.time()
    for batch_idx, ((data_a, label_a), (data_b, label_b)) in pbar:

        # data = torch.cat((data_a, data_b), dim=0)
        if args.cuda:
            # data = data.cuda(non_blocking=True)
            data_a = data_a.cuda(non_blocking=True)
            data_b = data_b.cuda(non_blocking=True)
            label_a = label_a.cuda(non_blocking=True)
            label_b = label_b.cuda(non_blocking=True)

        data_a, data_b = Variable(data_a), Variable(data_b)
        data = (data_a, data_b)

        label_a, label_b = Variable(label_a), Variable(label_b)

        classifier, feats = model(data)
        classfier_a, classfier_b = classifier
        feats = torch.cat(feats, dim=0)
        # feat_a, feat_b = feat
        # _, feats = model(data)
        # if isinstance(model, DistributedDataParallel):
        #     classfier_a, classfier_b = model.module.cls_forward(feats[:len(data_a)], feats[len(data_a):])
        # else:
        #     classfier_a, classfier_b = model.cls_forward(feats[:len(data_a)], feats[len(data_a):])

        # feats_b = model.pre_forward(data_b)
        # cos_theta, phi_theta = classfier
        classfier_label_a = classfier_a
        classfier_label_b = classfier_b

        if args.loss_ratio > 0.3:
            loss_ratio = args.loss_ratio * min(epoch / 5, 1.0)
        elif args.loss_ratio > 0:
            loss_ratio = args.loss_ratio
        else:
            loss_ratio = 0

        if args.loss_type == 'soft':
            loss_a = ce_criterion(classfier_a, label_a)
            loss_b = ce_criterion(classfier_b, label_b)
            loss = loss_a + args.set_ratio * loss_b

        elif args.loss_type == 'asoft':
            classfier_label_a, _ = classfier_a
            loss_a = xe_criterion(classfier_a, label_a)
            classfier_label_b, _ = classfier_a
            loss_b = xe_criterion(classfier_a, label_a)

            loss = loss_a + args.set_ratio * loss_b

        elif args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
            label_b_plus = label_b + train_dir_a.num_spks
            label = torch.cat((label_a, label_b_plus))

            loss_a = ce_criterion(classfier_a, label_a)
            loss_b = ce_criterion(classfier_b, label_b)
            loss_cent = loss_a + args.set_ratio * loss_b

            # loss_xent = xe_criterion(torch.cat((feat_a, feat_b), dim=0), label)
            loss_xent = xe_criterion(feats, label)
            loss = loss_ratio * loss_xent + loss_cent

        elif args.loss_type in ['amsoft', 'arcsoft']:
            loss_a = xe_criterion(classfier_a, label_a)
            loss_b = xe_criterion(classfier_b, label_b)
            loss = loss_a + args.set_ratio * loss_b
            # loss = xe_criterion(classfier, label)

        predicted_labels = output_softmax(classfier_label_a)
        predicted_one_labels = torch.max(predicted_labels, dim=1)[1]
        minibatch_correct = float((predicted_one_labels.cuda() == label_a).sum().item())
        minibatch_a = minibatch_correct / len(predicted_one_labels)
        correct_a += minibatch_correct
        total_datasize_a += len(predicted_one_labels)

        predicted_labels = output_softmax(classfier_label_b)
        predicted_one_labels = torch.max(predicted_labels, dim=1)[1]
        minibatch_correct = float((predicted_one_labels.cuda() == label_b).sum().item())
        minibatch_b = minibatch_correct / len(predicted_one_labels)
        correct_b += minibatch_correct
        total_datasize_b += len(predicted_one_labels)

        total_loss += float(loss.item())

        if np.isnan(loss.item()):
            print(classfier_a, classfier_b)
            raise ValueError('Loss value is NaN!')

        # compute gradient and update weights
        optimizer.zero_grad()
        loss.backward()

        if args.loss_ratio != 0:
            if args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
                for param in xe_criterion.parameters():
                    param.grad.data *= (1. / args.loss_ratio)

        if args.grad_clip > 0:
            this_lr = args.lr
            for param_group in optimizer.param_groups:
                this_lr = min(param_group['lr'], this_lr)
            torch.nn.utils.clip_grad_norm_(model.parameters(), this_lr * args.grad_clip)

        optimizer.step()

        if batch_idx % args.log_interval == 0:
            if args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
                pbar.set_description(
                    'Train Epoch {} ({:3.0f}%): Center Loss: {:.4f} Avg Loss: {:.4f} Accuracy_A: {:.4f}%  Accuracy_B: {:.4f}%'.format(
                        epoch,
                        100. * batch_idx / len(train_loader_a),
                        loss_xent.float(),
                        total_loss / (batch_idx + 1),
                        100. * minibatch_a,
                        100. * minibatch_b))
            else:
                pbar.set_description(
                    'Train Epoch {} ({:3.0f}%): Avg Loss: {:.4f} Accuracy_A: {:.4f}%  Accuracy_B: {:.4f}%'.format(
                        epoch,
                        100. * batch_idx / len(train_loader_a),
                        total_loss / (batch_idx + 1),
                        100. * minibatch_a,
                        100. * minibatch_b))
            # break

    print('\nEpoch {:>2d}: \33[91mTrain A_Accuracy:{:.4f}%, B_Accuracy:{:.4f}%, Avg_loss: {:.6f}.\33[0m'.format(epoch, 100 * float(
                                                                                          correct_a) / total_datasize_a,
                                                                                          100 * float(
                                                                                          correct_b) / total_datasize_b,
                                                                                          total_loss / len(train_loader_a)))
    writer.add_scalar('Train/Accuracy_A', correct_a / total_datasize_a, epoch)
    writer.add_scalar('Train/Accuracy_B', correct_b / total_datasize_b, epoch)
    writer.add_scalar('Train/Loss', total_loss / len(train_loader_a), epoch)

    torch.cuda.empty_cache()


def valid_class(valid_loader, model, ce, epoch):
    # switch to evaluate mode
    model.eval()

    valid_loader_a, valid_loader_b = valid_loader
    # valid_pbar = tqdm(enumerate(zip(valid_loader_a, valid_loader_b)))
    correct_a = 0.
    correct_b = 0.

    total_loss_a = 0.
    total_loss_b = 0.

    total_datasize_a = 0.
    total_datasize_b = 0.

    ce_criterion, xe_criterion = ce
    softmax = nn.Softmax(dim=1)
    with torch.no_grad():
        for batch_idx, ((data_a, label_a), (data_b, label_b)) in enumerate(zip(valid_loader_a, valid_loader_b)):

            if args.cuda:
                # data = data.cuda(non_blocking=True)
                data_a = data_a.cuda()
                data_b = data_b.cuda()
                label_a = label_a.cuda()
                label_b = label_b.cuda()

            data = (data_a, data_b)

            classifier, feats = model(data)
            classfier_a, classfier_b = classifier

            if args.loss_type == 'soft':
                loss_a = ce_criterion(classfier_a, label_a)
                loss_b = ce_criterion(classfier_b, label_b)
            elif args.loss_type == 'arcsoft':
                loss_a = xe_criterion(classfier_a, label_a)
                loss_b = xe_criterion(classfier_b, label_b)

            total_loss_a += float(loss_a.item())
            total_loss_b += float(loss_b.item())

            # pdb.set_trace()
            predicted_labels = softmax(classfier_a)
            predicted_one_labels = torch.max(predicted_labels, dim=1)[1]
            minibatch_correct = float((predicted_one_labels.cuda() == label_a).sum().item())
            correct_a += minibatch_correct
            total_datasize_a += len(predicted_one_labels)

            predicted_labels = softmax(classfier_b)
            predicted_one_labels = torch.max(predicted_labels, dim=1)[1]
            minibatch_correct = float((predicted_one_labels.cuda() == label_b).sum().item())
            correct_b += minibatch_correct
            total_datasize_b += len(predicted_one_labels)

    valid_accuracy_a = 100. * correct_a / total_datasize_a
    valid_accuracy_b = 100. * correct_b / total_datasize_b
    valid_loss_a = total_loss_a / len(valid_loader_a)
    valid_loss_b = total_loss_b / len(valid_loader_b)

    valid_loss = valid_loss_a + args.set_ratio * valid_loss_b

    writer.add_scalar('Train/Valid_Accuracy_A', valid_accuracy_a, epoch)
    writer.add_scalar('Train/Valid_Accuracy_B', valid_accuracy_b, epoch)
    writer.add_scalar('Train/Valid_Loss_A', valid_loss_a, epoch)
    writer.add_scalar('Train/Valid_Loss_B', valid_loss_b, epoch)
    writer.add_scalar('Train/Valid_Loss', valid_loss, epoch)

    torch.cuda.empty_cache()
    print('          \33[91mValid Accuracy, A: %.4f %%; B: %.4f %%. Avg Loss, A: %.5f; B: %.5f\33[0m' %
          (valid_accuracy_a, valid_accuracy_b, valid_loss_a, valid_loss_b))

    return valid_loss


def valid_test(train_extract_loader, model, epoch, xvector_dir):
    # switch to evaluate mode
    model.eval()

    this_xvector_dir = "%s/train/epoch_%s" % (xvector_dir, epoch)
    verification_extract(train_extract_loader, model, this_xvector_dir, epoch)

    verify_dir = ScriptVerifyDataset(dir=args.train_test_dir, trials_file=args.train_trials,
                                     xvectors_dir=this_xvector_dir,
                                     loader=read_vec_flt)
    verify_loader = torch.utils.data.DataLoader(verify_dir, batch_size=128, shuffle=False, **kwargs)
    eer, eer_threshold, mindcf_01, mindcf_001 = verification_test(test_loader=verify_loader,
                                                                  dist_type=('cos' if args.cos_sim else 'l2'),
                                                                  log_interval=args.log_interval,
                                                                  xvector_dir=this_xvector_dir,
                                                                  epoch=epoch)

    print('Test  Epoch {}:\n\33[91mTrain EER: {:.4f}%, Threshold: {:.4f}, ' \
          'mindcf-0.01: {:.4f}, mindcf-0.001: {:.4f}.'.format(epoch,
                                                              100. * eer,
                                                              eer_threshold,
                                                              mindcf_01,
                                                              mindcf_001))

    writer.add_scalar('Train/EER', 100. * eer, epoch)
    writer.add_scalar('Train/Threshold', eer_threshold, epoch)
    writer.add_scalar('Train/mindcf-0.01', mindcf_01, epoch)
    writer.add_scalar('Train/mindcf-0.001', mindcf_001, epoch)

    torch.cuda.empty_cache()


def test(model, epoch, writer, xvector_dir):
    this_xvector_dir = "%s/test/epoch_%s" % (xvector_dir, epoch)

    extract_loader = torch.utils.data.DataLoader(extract_dir, batch_size=1, shuffle=False, **kwargs)
    verification_extract(extract_loader, model, this_xvector_dir, epoch)

    verify_dir = ScriptVerifyDataset(dir=args.test_dir, trials_file=args.trials, xvectors_dir=this_xvector_dir,
                                     loader=read_vec_flt)
    verify_loader = torch.utils.data.DataLoader(verify_dir, batch_size=128, shuffle=False, **kwargs)
    eer, eer_threshold, mindcf_01, mindcf_001 = verification_test(test_loader=verify_loader,
                                                                  dist_type=('cos' if args.cos_sim else 'l2'),
                                                                  log_interval=args.log_interval,
                                                                  xvector_dir=this_xvector_dir,
                                                                  epoch=epoch)
    print('\33[91mTest  ERR: {:.4f}%, Threshold: {:.4f}, mindcf-0.01: {:.4f}, mindcf-0.001: {:.4f}.\33[0m\n'.format(
        100. * eer, eer_threshold, mindcf_01, mindcf_001))

    writer.add_scalar('Test/EER', 100. * eer, epoch)
    writer.add_scalar('Test/Threshold', eer_threshold, epoch)
    writer.add_scalar('Test/mindcf-0.01', mindcf_01, epoch)
    writer.add_scalar('Test/mindcf-0.001', mindcf_001, epoch)

# python TrainAndTest/Spectrogram/train_surescnn10_kaldi.py > Log/SuResCNN10/spect_161/

if __name__ == '__main__':
    main()
