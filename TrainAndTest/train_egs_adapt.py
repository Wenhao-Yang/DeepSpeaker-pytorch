#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: train_egs_adapt.py
@Time: 2022/4/7 13:27
@Overview:
"""
from __future__ import print_function

import argparse
import os
import os.path as osp
import pdb
import shutil
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
from torch.utils.tensorboard import SummaryWriter
from torch.autograd import Variable
from torch.nn.parallel.distributed import DistributedDataParallel
from torch.optim.lr_scheduler import MultiStepLR, ExponentialLR
from tqdm import tqdm

from Define_Model.Loss.LossFunction import CenterLoss, MMD_Loss
from Define_Model.Loss.SoftmaxLoss import ArcSoftmaxLoss
from Define_Model.ResNet import DomainNet
from Define_Model.SoftmaxLoss import AngleSoftmaxLoss, AngleLinear, AdditiveMarginLinear, AMSoftmaxLoss
from Define_Model.model import PairwiseDistance
from Define_Model.FilterLayer import RevGradLayer
from Process_Data import constants as c
from Process_Data.Datasets.KaldiDataset import ScriptTestDataset, KaldiExtractDataset, \
    ScriptVerifyDataset
from Process_Data.Datasets.LmdbDataset import EgsDataset
from Process_Data.audio_processing import concateinputfromMFB, to2tensor, ConcateVarInput, ConcateOrgInput, PadCollate3d
from Process_Data.audio_processing import toMFB, totensor, truncatedinput, read_audio
from TrainAndTest.common_func import create_optimizer, create_model, verification_test, verification_extract
from Eval.eval_metrics import evaluate_kaldi_eer, evaluate_kaldi_mindcf
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
parser.add_argument('--train-dir', type=str, required=True, help='path to dataset')
parser.add_argument('--train-test-dir', type=str, required=True, help='path to dataset')
parser.add_argument('--valid-dir', type=str, required=True, help='path to dataset')
parser.add_argument('--test-dir', type=str, required=True, help='path to voxceleb1 test dataset')
parser.add_argument('--log-scale', action='store_true', default=False, help='log power spectogram')
parser.add_argument('--exp', action='store_true', default=False, help='exp power spectogram')
parser.add_argument('--trials', type=str, default='trials', help='path to voxceleb1 test dataset')
parser.add_argument('--train-trials', type=str, default='trials', help='path to voxceleb1 test dataset')

parser.add_argument('--domain', action='store_true', default=False, help='set domain in dataset')
parser.add_argument('--domain-steps', default=5, type=int, help='set domain in dataset')
parser.add_argument('--speech-dom', default='4,7,9,10', type=str, help='set domain in dataset')
parser.add_argument('--random-chunk', nargs='+', type=int, default=[], metavar='MINCHUNK')
parser.add_argument('--chunk-size', type=int, default=300, metavar='CHUNK')
parser.add_argument('--shuffle', action='store_false', default=True, help='need to shuffle egs')

parser.add_argument('--nj', default=12, type=int, metavar='NJOB', help='num of job')
parser.add_argument('--feat-format', type=str, default='kaldi', choices=['kaldi', 'npy'],
                    help='number of jobs to make feats (default: 10)')

parser.add_argument('--check-path', help='folder to output model checkpoints')
parser.add_argument('--save-init', action='store_true', default=True, help='need to make mfb file')
parser.add_argument('--resume', type=str, metavar='PATH', help='path to latest checkpoint (default: none)')

parser.add_argument('--start-epoch', default=1, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('--epochs', type=int, default=20, metavar='E',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--scheduler', default='multi', type=str,
                    metavar='SCH', help='The optimizer to use (default: Adagrad)')
parser.add_argument('--gamma', default=0.75, type=float,
                    metavar='GAMMA', help='The optimizer to use (default: Adagrad)')
parser.add_argument('--milestones', default='10,15', type=str,
                    metavar='MIL', help='The optimizer to use (default: Adagrad)')
parser.add_argument('--min-softmax-epoch', type=int, default=40, metavar='MINEPOCH',
                    help='minimum epoch for initial parameter using softmax (default: 2')
parser.add_argument('--veri-pairs', type=int, default=12800, metavar='VP',
                    help='number of epochs to train (default: 10)')

# Training options
# Model options
parser.add_argument('--filter', type=str, default='None', help='replace batchnorm with instance norm')
parser.add_argument('--filter-fix', action='store_true', default=False, help='replace batchnorm with instance norm')

parser.add_argument('--model', type=str, help='path to voxceleb1 test dataset')
parser.add_argument('--resnet-size', default=8, type=int,
                    metavar='RES', help='The channels of convs layers)')
parser.add_argument('--inst-norm', action='store_true', default=False,
                    help='replace batchnorm with instance norm')
parser.add_argument('--vad', action='store_true', default=False, help='vad layers')
parser.add_argument('--inception', action='store_true', default=False, help='multi size conv layer')

parser.add_argument('--input-norm', type=str, default='Mean', help='batchnorm with instance norm')
parser.add_argument('--fast', type=str, default='None', help='max pooling for fast')

parser.add_argument('--input-dim', default=257, type=int, metavar='N', help='acoustic feature dimension')
parser.add_argument('--mask-layer', type=str, default='None', help='time or freq masking layers')
parser.add_argument('--mask-len', type=int, default=20, help='maximum length of time or freq masking layers')
parser.add_argument('--block-type', type=str, default='basic', help='replace batchnorm with instance norm')
parser.add_argument('--relu-type', type=str, default='relu', help='replace batchnorm with instance norm')
parser.add_argument('--transform', type=str, default="None", help='add a transform layer after embedding layer')

parser.add_argument('--channels', default='64,128,256', type=str,
                    metavar='CHA', help='The channels of convs layers)')
parser.add_argument('--downsample', type=str, default='None', help='replace batchnorm with instance norm')

parser.add_argument('--first-2d', action='store_true', default=False,
                    help='replace first tdnn layer with conv2d layers')
parser.add_argument('--kernel-size', default='5,5', type=str, metavar='KE',
                    help='kernel size of conv filters')
parser.add_argument('--stride', default='2', type=str, metavar='ST', help='stride size of conv filters')

parser.add_argument('--dilation', default='1,1,1,1', type=str, metavar='CHA', help='The dilation of convs layers)')
parser.add_argument('--context', default='5,3,3,5', type=str, metavar='KE', help='kernel size of conv filters')
parser.add_argument('--padding', default='', type=str, metavar='KE', help='padding size of conv filters')

parser.add_argument('--feat-dim', default=161, type=int, metavar='FEAT',
                    help='acoustic feature dimension')
parser.add_argument('--remove-vad', action='store_true', default=False,
                    help='using Cosine similarity')
parser.add_argument('--extract', action='store_true', default=True, help='need to make mfb file')

parser.add_argument('--alpha', default=12, type=float, metavar='FEAT',
                    help='acoustic feature dimension')
parser.add_argument('--cos-sim', action='store_true', default=True,
                    help='using Cosine similarity')
parser.add_argument('--avg-size', type=int, default=4, metavar='ES',
                    help='Dimensionality of the embedding')
parser.add_argument('--time-dim', default=1, type=int, metavar='FEAT', help='acoustic feature dimension')

parser.add_argument('--encoder-type', type=str, default='None', help='path to voxceleb1 test dataset')

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
parser.add_argument('--test-batch-size', type=int, default=1, metavar='BST',
                    help='input batch size for testing (default: 64)')
parser.add_argument('--dropout-p', type=float, default=0., metavar='BST',
                    help='input batch size for testing (default: 64)')
parser.add_argument('--test-input', type=str, default='fix', choices=['var', 'fix'],
                    help='batchnorm with instance norm')
# loss configure
parser.add_argument('--loss-type', type=str, default='soft', choices=['soft', 'asoft', 'center', 'amsoft', 'arcsoft'],
                    help='path to voxceleb1 test dataset')
parser.add_argument('--submean', action='store_true', default=False,
                    help='substract center for speaker embeddings')
parser.add_argument('--finetune', action='store_true', default=False,
                    help='using Cosine similarity')
parser.add_argument('--loss-ratio', type=float, default=0.1, metavar='LOSSRATIO',
                    help='the ratio softmax loss - triplet loss (default: 2.0')
parser.add_argument('--dom-ratio', type=float, default=0.1, metavar='DOMAINLOSSRATIO',
                    help='the ratio softmax loss - triplet loss (default: 2.0')
parser.add_argument('--sim-ratio', type=float, default=0.1, metavar='DOMAINLOSSRATIO',
                    help='the ratio softmax loss - triplet loss (default: 2.0')
# args for additive margin-softmax
parser.add_argument('--margin', type=float, default=0.3, metavar='MARGIN',
                    help='the margin value for the angualr softmax loss function (default: 3.0')
parser.add_argument('--s', type=float, default=15, metavar='S',
                    help='the margin value for the angualr softmax loss function (default: 3.0')

# args for a-softmax
parser.add_argument('--all-iteraion', type=int, default=0, metavar='M',
                    help='the margin value for the angualr softmax loss function (default: 3.0')
parser.add_argument('--m', type=int, default=3, metavar='M',
                    help='the margin value for the angualr softmax loss function (default: 3.0')
parser.add_argument('--lambda-min', type=int, default=5, metavar='S',
                    help='random seed (default: 0)')
parser.add_argument('--lambda-max', type=float, default=1000, metavar='S',
                    help='random seed (default: 0)')

parser.add_argument('--lr', type=float, default=0.1, metavar='LR', help='learning rate (default: 0.125)')
parser.add_argument('--base-lr', type=float, default=1e-8, metavar='LR', help='learning rate (default: 0.125)')
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
np.random.seed(args.seed)
torch.manual_seed(args.seed)
# torch.multiprocessing.set_sharing_strategy('file_system')

if args.cuda:
    torch.cuda.manual_seed_all(args.seed)
    cudnn.benchmark = True

# create logger Define visulaize SummaryWriter instance
writer = SummaryWriter(log_dir=args.check_path, filename_suffix='_first')

sys.stdout = NewLogger(osp.join(args.check_path, 'log.txt'))

kwargs = {'num_workers': args.nj, 'pin_memory': False} if args.cuda else {}
extract_kwargs = {'num_workers': args.nj, 'pin_memory': False} if args.cuda else {}

if not os.path.exists(args.check_path):
    os.makedirs(args.check_path)

opt_kwargs = {'lr': args.lr, 'lr_decay': args.lr_decay, 'weight_decay': args.weight_decay,
              'dampening': args.dampening,
              'momentum': args.momentum}

l2_dist = nn.CosineSimilarity(dim=1, eps=1e-6) if args.cos_sim else PairwiseDistance(2)

if args.acoustic_feature == 'fbank':
    transform = transforms.Compose([
        totensor()
    ])
else:
    transform = transforms.Compose([
        truncatedinput(),
        toMFB(),
        totensor(),
        # tonormal()
    ])

if args.test_input == 'var':
    transform_V = transforms.Compose([
        ConcateOrgInput(remove_vad=args.remove_vad),
    ])
elif args.test_input == 'fix':
    transform_V = transforms.Compose([
        ConcateVarInput(num_frames=args.chunk_size, remove_vad=args.remove_vad),
    ])

# pdb.set_trace()
# torch.multiprocessing.set_sharing_strategy('file_system')

if args.feat_format == 'kaldi':
    file_loader = read_mat
elif args.feat_format == 'npy':
    file_loader = np.load

train_dir = EgsDataset(dir=args.train_dir, feat_dim=args.feat_dim, loader=file_loader, transform=transform,
                       domain=args.domain)
# test_dir = ScriptTestDataset(dir=args.test_dir, loader=file_loader, transform=transform_V)


valid_dir = EgsDataset(dir=args.valid_dir, feat_dim=args.feat_dim, loader=file_loader, transform=transform,
                       domain=args.domain)

train_extract_dir = KaldiExtractDataset(dir=args.train_test_dir,
                                        transform=transform_V,
                                        filer_loader=file_loader,
                                        trials_file=args.train_trials)

extract_dir = KaldiExtractDataset(dir=args.test_dir, transform=transform_V, filer_loader=file_loader)

# easy domain index
speech_dom = args.speech_dom.split(',')
speech_dom = [int(x) for x in speech_dom]


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
    print('Number of Speakers: {}.\n'.format(train_dir.num_spks))

    # instantiate model and initialize weights
    kernel_size = args.kernel_size.split(',')
    kernel_size = [int(x) for x in kernel_size]

    context = args.context.split(',')
    context = [int(x) for x in context]
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

    dilation = args.dilation.split(',')
    dilation = [int(x) for x in dilation]

    xvector_kwargs = {'input_dim': args.input_dim, 'feat_dim': args.feat_dim, 'kernel_size': kernel_size,
                      'context': context, 'filter_fix': args.filter_fix, 'dilation': dilation,
                      'mask': args.mask_layer, 'mask_len': args.mask_len, 'block_type': args.block_type,
                      'filter': args.filter, 'exp': args.exp, 'inst_norm': args.inst_norm,
                      'input_norm': args.input_norm, 'first_2d': args.first_2d,
                      'stride': stride, 'fast': args.fast, 'avg_size': args.avg_size, 'time_dim': args.time_dim,
                      'padding': padding, 'encoder_type': args.encoder_type, 'vad': args.vad,
                      'transform': args.transform, 'embedding_size': args.embedding_size, 'ince': args.inception,
                      'resnet_size': args.resnet_size, 'num_classes': 0,
                      'num_classes_b': train_dir.num_doms,
                      'channels': channels, 'alpha': args.alpha, 'dropout_p': args.dropout_p,
                      'loss_type': args.loss_type, 'm': args.m, 'margin': args.margin, 's': args.s,
                      'iteraion': 0, 'all_iteraion': args.all_iteraion}

    print('Model options: {}'.format(xvector_kwargs))
    xvector_model = create_model(args.model, **xvector_kwargs)
    xvector_model.classifier = None

    if args.loss_type == 'soft':
        classifier_spk = nn.Linear(args.embedding_size, train_dir.num_spks)
    elif args.loss_type in ['arcsoft', 'amsoft']:
        classifier_spk = AdditiveMarginLinear(feat_dim=args.embedding_size, num_classes=train_dir.num_spks)

    start_epoch = 0
    if args.save_init and not args.finetune:
        check_path = '{}/checkpoint_{}.pth'.format(args.check_path, start_epoch)
        torch.save({"xvector": xvector_model.state_dict(),
                    "spk_classifier": classifier_spk.state_dict()}, check_path)

    if args.resume:
        if os.path.isfile(args.resume):
            print('=> loading checkpoint {}'.format(args.resume))
            checkpoint = torch.load(args.resume)
            start_epoch = checkpoint['epoch']

            filtered = {k: v for k, v in checkpoint['state_dict'][0].items() if 'num_batches_tracked' not in k}
            model_dict = xvector_model.state_dict()
            model_dict.update(filtered)
            xvector_model.load_state_dict(model_dict)

            classifier_spk = checkpoint['spk_classifier']
            classifier_dom = checkpoint['spk_classifier']
            # model.dropout.p = args.dropout_p
        else:
            print('=> no checkpoint found at {}'.format(args.resume))

    ce_criterion = nn.CrossEntropyLoss()
    if args.loss_type == 'soft':
        xe_criterion = None
    elif args.loss_type == 'asoft':
        ce_criterion = AngleSoftmaxLoss(lambda_min=args.lambda_min, lambda_max=args.lambda_max)
    elif args.loss_type == 'center':
        ce_criterion = CenterLoss(num_classes=train_dir.num_spks, feat_dim=args.embedding_size)
    elif args.loss_type == 'amsoft':
        ce_criterion = AMSoftmaxLoss(margin=args.margin, s=args.s)
    elif args.loss_type == 'arcsoft':
        ce_criterion = ArcSoftmaxLoss(margin=args.margin, s=args.s)

    xe_criterion = MMD_Loss()
    # nn.CrossEntropyLoss()
    # xe_criterion = nn.CrossEntropyLoss(weight=torch.tensor([0.94, 0.06]))  # label weight for speech & other domain
    # dom_params = list(map(id, model.classifier_dom.parameters()))
    # rest_params = list(map(id, model.xvectors.parameters()))
    # rest_params = filter(lambda p: id(p) not in dom_params, model.parameters())

    spk_optimizer = create_optimizer([{'params': xvector_model.parameters()},
                                      {'params': classifier_spk.parameters()}], args.optimizer, **opt_kwargs)
    # dom_optimizer = create_optimizer(classifier_dom.parameters(), args.optimizer, **opt_kwargs)

    # if args.loss_type == 'center':
    #     optimizer = torch.optim.SGD([{'params': xe_criterion.parameters(), 'lr': args.lr * 5},
    #                                  {'params': model.parameters()}],
    #                                 lr=args.lr, weight_decay=args.weight_decay,
    #                                 momentum=args.momentum)
    # if args.finetune:
    #     if args.loss_type == 'asoft' or args.loss_type == 'amsoft':
    #         classifier_params = list(map(id, model.classifier.parameters()))
    #         rest_params = filter(lambda p: id(p) not in classifier_params, model.parameters())
    #         optimizer = torch.optim.SGD([{'params': model.classifier.parameters(), 'lr': args.lr * 5},
    #                                      {'params': rest_params}],
    #                                     lr=args.lr, weight_decay=args.weight_decay,
    #                                     momentum=args.momentum)

    if args.scheduler == 'exp':
        spk_scheduler = ExponentialLR(spk_optimizer, gamma=args.gamma)
        # dom_scheduler = ExponentialLR(dom_optimizer, gamma=args.gamma)
    else:
        milestones = args.milestones.split(',')
        milestones = [int(x) for x in milestones]
        milestones.sort()

        spk_scheduler = MultiStepLR(spk_optimizer, milestones=milestones, gamma=0.1)
        # dom_scheduler = MultiStepLR(dom_optimizer, milestones=milestones, gamma=0.1)

    start = args.start_epoch + start_epoch
    print('Start epoch is : ' + str(start))
    end = start + args.epochs
    if len(args.random_chunk) == 2 and args.random_chunk[0] < args.random_chunk[1]:
        min_chunk_size = int(args.random_chunk[0])
        max_chunk_size = int(args.random_chunk[1])
        pad_dim = 2 if args.feat_format == 'kaldi' else 3

        train_loader = torch.utils.data.DataLoader(train_dir, batch_size=args.batch_size,
                                                   collate_fn=PadCollate3d(dim=pad_dim,
                                                                           num_batch=int(
                                                                               np.ceil(
                                                                                   len(train_dir) / args.batch_size)),
                                                                           min_chunk_size=min_chunk_size,
                                                                           max_chunk_size=max_chunk_size),
                                                   shuffle=args.shuffle, **kwargs)
        valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=int(args.batch_size / 2),
                                                   collate_fn=PadCollate3d(dim=pad_dim, fix_len=True,
                                                                           min_chunk_size=args.chunk_size,
                                                                           max_chunk_size=args.chunk_size + 1),
                                                   shuffle=False, **kwargs)
    else:
        train_loader = torch.utils.data.DataLoader(train_dir, batch_size=args.batch_size, shuffle=args.shuffle,
                                                   **kwargs)
        valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=int(args.batch_size / 2), shuffle=False,
                                                   **kwargs)
    ce = [ce_criterion, xe_criterion]
    # valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=int(args.batch_size / 2), shuffle=False, **kwargs)
    train_extract_loader = torch.utils.data.DataLoader(train_extract_dir, batch_size=1, shuffle=False, **extract_kwargs)

    if args.cuda:
        if len(args.gpu_id) > 1:
            print("Continue with gpu: %s ..." % str(args.gpu_id))
            try:
                torch.distributed.init_process_group(backend="nccl", init_method='tcp://localhost:32466', rank=0,
                                                     world_size=1)
            except RuntimeError as r:
                torch.distributed.init_process_group(backend="nccl", init_method='tcp://localhost:32464', rank=0,
                                                     world_size=1)
            # if args.gain
            # model = DistributedDataParallel(model.cuda(), find_unused_parameters=True)
            # model = DistributedDataParallel(model.cuda())
            xvector_model = DistributedDataParallel(xvector_model.cuda(), find_unused_parameters=True)
            classifier_spk = DistributedDataParallel(classifier_spk.cuda(), find_unused_parameters=True)
            # classifier_dom = DistributedDataParallel(classifier_dom.cuda(), find_unused_parameters=True)

        else:
            xvector_model = xvector_model.cuda()
            classifier_spk = classifier_spk.cuda()
            # classifier_dom = classifier_dom.cuda()

        for i in range(len(ce)):
            if ce[i] != None:
                ce[i] = ce[i].cuda()
        try:
            print('Dropout is {}.'.format(xvector_model.dropout_p))
        except:
            pass

    model = (xvector_model, classifier_spk, classifier_dom)
    xvector_dir = args.check_path
    xvector_dir = xvector_dir.replace('checkpoint', 'xvector')
    start_time = time.time()
    steps = args.domain_steps

    for epoch in range(start, end):
        spk_lr_string = '\n\33[1;34m Spk \'{}\' learning rate is '.format(args.optimizer)
        for param_group in spk_optimizer.param_groups:
            spk_lr_string += '{:.8f} '.format(param_group['lr'])

        # dom_lr_string = 'Domain \'{}\' learning rate is '.format(args.optimizer)
        # for param_group in dom_optimizer.param_groups:
        #     dom_lr_string += '{:.8f} '.format(param_group['lr'])
        print('%s \33[0m' % (spk_lr_string))
        optimizer = spk_optimizer
        scheduler = spk_scheduler

        train(train_loader, model, ce, optimizer, epoch, scheduler, steps)
        valid_loss = valid_class(valid_loader, model, ce, epoch)

        if (epoch == 1 or epoch != (end - 2)) and (epoch % 4 == 1 or epoch in milestones or epoch == (end - 1)):
            xvector_model, classifier_spk, classifier_dom = model
            xvector_model.eval()
            classifier_spk.eval()
            # classifier_dom.eval()
            check_path = '{}/checkpoint_{}.pth'.format(args.check_path, epoch)
            model_state_dict = xvector_model.module.state_dict() \
                if isinstance(xvector_model, DistributedDataParallel) else xvector_model.state_dict()
            classifier_spk_dict = classifier_spk.module.state_dict() \
                if isinstance(classifier_spk, DistributedDataParallel) else classifier_spk.state_dict()
            # classifier_dom_dict = classifier_dom.module.state_dict() \
            #     if isinstance(classifier_dom, DistributedDataParallel) else classifier_dom.state_dict()

            torch.save({'epoch': epoch,
                        'state_dict': model_state_dict,
                        'spk_classifier': classifier_spk_dict,
                        'criterion': ce},
                       check_path)

            valid_test(train_extract_loader, model, epoch, xvector_dir)
            test(model, epoch, writer, xvector_dir)
            if epoch != (end - 1):
                try:
                    shutil.rmtree("%s/train/epoch_%s" % (xvector_dir, epoch))
                    shutil.rmtree("%s/test/epoch_%s" % (xvector_dir, epoch))
                except Exception as e:
                    print('rm dir xvectors error:', e)

        # if args.scheduler == 'rop':
        #     spkscheduler.step(valid_loss)
        # elif args.scheduler == 'cyclic':
        #     continue
        # else:
        #     scheduler.step()
        spk_scheduler.step()

        # exit(1)

    stop_time = time.time()
    t = float(stop_time - start_time)
    print("Running %.4f minutes for each epoch.\n" % (t / 60 / (max(end - start, 1))))
    exit(0)


def train(train_loader, model, ce, optimizer, epoch, scheduler, steps):
    # switch to evaluate mode
    xvector_model, classifier_spk, classifier_dom = model

    xvector_model.train()
    classifier_spk.train()
    classifier_dom.train()

    spk_optimizer, dom_optimizer = optimizer
    # spk_scheduler, dom_scheduler = scheduler
    # lambda_ = min(2. / (1 + np.exp(-10. * (epoch-2) / args.epochs)) - 1., 0)
    lambda_ = 2. / (1 + np.exp(-10. * epoch / args.epochs)) - 1
    # model.grl.set_lambda(lambda_)

    correct_a = 0.
    correct_b = 0.

    total_datasize = 0.
    total_loss_a = 0.
    total_loss_b = 0.
    total_loss_c = 0.

    total_loss = 0.
    # for param_group in optimizer.param_groups:
    #     print('\33[1;34m Optimizer \'{}\' learning rate is {}.\33[0m'.format(args.optimizer, param_group['lr']))
    ce_criterion, xe_criterion = ce
    pbar = tqdm(enumerate(train_loader))
    output_softmax = nn.Softmax(dim=1)

    for batch_idx, (data, label_a, label_b) in pbar:

        if args.cuda:
            data = data.cuda()

        data, label_a = Variable(data), Variable(label_a)

        if len(speech_dom) == 1:
            label_b = torch.where(label_b == speech_dom[0], torch.tensor([0]), torch.tensor([1])).long()
        else:
            multi_b = torch.ones_like(label_b)
            for s in speech_dom:
                multi_b = multi_b * torch.where(label_b == s, torch.tensor([0]), torch.tensor([1])).long()

            label_b = multi_b

        label_b = Variable(label_b)
        true_labels_a = label_a.cuda()
        true_labels_b = label_b.cuda()

        _, spk_embeddings = xvector_model(data)

        spk_logits = classifier_spk(spk_embeddings)
        loss = ce_criterion(spk_logits, true_labels_a)  # if xe_criterion == None else xe_criterion(spk_logits,
        # true_labels_a)

        source_spk_idx = torch.where(true_labels_b == 0)
        target_spk_idx = torch.where(true_labels_b == 1)

        if len(source_spk_idx) > 1 and len(target_spk_idx) > 1:
            source_spk_embeddings = spk_embeddings[source_spk_idx]
            target_spk_embeddings = spk_embeddings[target_spk_idx]
            mmd_loss = args.dom_ratio * xe_criterion(source_spk_embeddings, target_spk_embeddings) * lambda_
            loss = loss + mmd_loss

        loss.backward()

        spk_optimizer.step()
        spk_optimizer.zero_grad()
        # dom_optimizer.zero_grad()

        # speech_labels_b = torch.LongTensor(torch.ones_like(label_b) * args.speech_dom)
        # speech_labels_b = speech_labels_b.cuda()

        # elif args.loss_type == 'asoft':
        #     spk_label, _ = spk_label
        #     spk_loss = xe_criterion(logits_spk, true_labels_a)
        # elif args.loss_type == 'center':
        #     loss_cent = ce_criterion(logits_spk, true_labels_a)
        #     loss_xent = xe_criterion(feat_spk, true_labels_a)
        #     spk_loss = args.loss_ratio * loss_xent + loss_cent
        # elif args.loss_type == 'amsoft':
        #     spk_loss = xe_criterion(logits_spk, true_labels_a)

        # if args.sim_ratio:
        #     spk_dom_sim_loss = torch.cosine_similarity(feat_spk, feat_dom, dim=1).pow(2).mean()
        #     spk_dom_sim_loss = args.sim_ratio * spk_dom_sim_loss
        #     loss += spk_dom_sim_loss

        predicted_labels_a = output_softmax(spk_logits)

        predicted_one_labels_a = torch.max(predicted_labels_a, dim=1)[1]
        minibatch_correct_a = float((predicted_one_labels_a.cuda() == true_labels_a.cuda()).sum().item())
        minibatch_acc_a = minibatch_correct_a / len(predicted_one_labels_a)
        correct_a += minibatch_correct_a

        total_datasize += len(predicted_one_labels_a)
        total_loss_a += float(spk_loss.item())
        # total_loss_c += float(spk_dom_sim_loss.item()) if args.sim_ratio else 0.
        total_loss += float(loss.item())

        # compute gradient and update weights
        # optimizer.zero_grad()
        # loss.backward()

        if args.loss_type == 'center' and args.loss_ratio != 0:
            for param in xe_criterion.parameters():
                param.grad.data *= (1. / args.loss_ratio)

        # optimizer.step()
        # if args.scheduler == 'cyclic':
        #     scheduler.step()

        if batch_idx % args.log_interval == 0:
            print_desc = 'Train Epoch {:2d}: [{:4d}/{:4d}({:3.0f}%)]'.format(epoch,
                                                                             batch_idx,
                                                                             len(train_loader),
                                                                             100. * batch_idx / len(train_loader))

            print_desc += ' Loss[ Gen: {:.4f} Spk: {:.4f} MMD: {:.4f}]'.format(total_loss / (batch_idx + 1),
                                                                               total_loss_a / (batch_idx + 1),
                                                                               total_loss_b / (batch_idx + 1))
            # print_desc += 'SimLoss: {:.4f}'.format(total_loss_c / (batch_idx + 1))
            print_desc += ' Accuracy[ Spk: {: >8.4f}%]'.format(100. * minibatch_acc_a)
            pbar.set_description(print_desc)

    print('\nEpoch {:>2d}: \33[91mTrain loss: {:.4f} Spk: {:.4f} MMD: {:.4f}, '.format(epoch,
                                                                                       total_loss / len(
                                                                                           train_loader),
                                                                                       total_loss_a / len(
                                                                                           train_loader),
                                                                                       total_loss_b / len(
                                                                                           train_loader)),
          end='')

    print('Accuracy Spk: {:.4f}%.\33[0m'.format(100 * correct_a / total_datasize))

    writer.add_scalar('Train/Spk_Accuracy', correct_a / total_datasize, epoch)
    writer.add_scalar('Train/Loss', total_loss / len(train_loader), epoch)

    torch.cuda.empty_cache()


def valid_class(valid_loader, model, ce, epoch):
    # switch to evaluate mode
    xvector_model, classifier_spk, classifier_dom = model
    xvector_model.eval()
    classifier_spk.eval()
    classifier_dom.eval()

    spk_loss = 0.
    dis_loss = 0.
    ce_criterion, xe_criterion = ce
    softmax = nn.Softmax(dim=1)

    correct_a = 0.
    correct_b = 0.

    total_datasize = 0.

    with torch.no_grad():
        for batch_idx, (data, label_a, label_b) in enumerate(valid_loader):
            data = data.cuda()

            if len(speech_dom) == 1:
                label_b = torch.where(label_b == speech_dom[0], torch.tensor([0]), torch.tensor([1])).long()
            else:
                multi_b = torch.ones_like(label_b)
                for s in speech_dom:
                    multi_b = multi_b * torch.where(label_b == s, torch.tensor([0]), torch.tensor([1])).long()

                label_b = multi_b
            # label_b = torch.where(label_b == args.speech_dom, torch.tensor([0]), torch.tensor([1])).long()

            _, embeddings = xvector_model(data)

            if args.submean:
                domain_embeddings = embeddings - classifier_spk.module.W.transpose(0, 1)[label_a]
            else:
                domain_embeddings = embeddings

            out_a = classifier_spk(embeddings)
            # out_b = classifier_dom(domain_embeddings)

            predicted_labels_a = out_a
            # predicted_labels_b = out_b

            true_labels_a = label_a.cuda()
            true_labels_b = label_b.cuda()

            loss_a = ce_criterion(out_a, true_labels_a)

            source_spk_idx = torch.where(true_labels_b == 0)
            target_spk_idx = torch.where(true_labels_b == 1)
            source_spk_embeddings = embeddings[source_spk_idx]
            target_spk_embeddings = embeddings[target_spk_idx]

            loss_b = xe_criterion(source_spk_embeddings, target_spk_embeddings)

            # pdb.set_trace()
            predicted_one_labels_a = softmax(predicted_labels_a)
            predicted_one_labels_a = torch.max(predicted_one_labels_a, dim=1)[1]

            batch_correct_a = (predicted_one_labels_a.cuda() == true_labels_a.cuda()).sum().item()
            correct_a += batch_correct_a

            # predicted_one_labels_b = softmax(predicted_labels_b)
            # predicted_one_labels_b = torch.max(predicted_one_labels_b, dim=1)[1]
            # batch_correct_b = (predicted_one_labels_b.cuda() == true_labels_b.cuda()).sum().item()
            # correct_b += batch_correct_b

            total_datasize += len(predicted_one_labels_a)
            spk_loss += float(loss_a.item())
            dis_loss += float(loss_b.item())

    spk_valid_accuracy = 100. * correct_a / total_datasize
    # dom_valid_accuracy = 100. * correct_b / total_datasize

    writer.add_scalar('Train/Spk_Valid_Accuracy', spk_valid_accuracy, epoch)
    # writer.add_scalar('Train/Dom_Valid_Accuracy', dom_valid_accuracy, epoch)

    spk_loss /= len(valid_loader)
    dis_loss /= len(valid_loader)
    valid_loss = spk_loss + args.dom_ratio * dis_loss

    torch.cuda.empty_cache()
    print(
        '          \33[91mValid Loss: {:.4f} Spk: {:.4f} MMD: {:.4f}, Accuracy Spk: {:.4f}% .\33[0m'.format(
            valid_loss, spk_loss, dis_loss,
            spk_valid_accuracy))

    return valid_loss


def valid_test(train_extract_loader, model, epoch, xvector_dir):
    # switch to evaluate mode
    xvector_model, classifier_spk, classifier_dom = model
    xvector_model.eval()

    this_xvector_dir = "%s/train/epoch_%s" % (xvector_dir, epoch)
    verification_extract(train_extract_loader, xvector_model, this_xvector_dir, epoch, test_input=args.test_input)

    verify_dir = ScriptVerifyDataset(dir=args.train_test_dir, trials_file=args.train_trials,
                                     xvectors_dir=this_xvector_dir,
                                     loader=read_vec_flt)
    verify_loader = torch.utils.data.DataLoader(verify_dir, batch_size=128, shuffle=False, **kwargs)
    eer, eer_threshold, mindcf_01, mindcf_001 = verification_test(test_loader=verify_loader,
                                                                  dist_type=('cos' if args.cos_sim else 'l2'),
                                                                  log_interval=args.log_interval,
                                                                  xvector_dir=this_xvector_dir,
                                                                  epoch=epoch)

    print('          \33[91mTrain EER: {:.4f}%, Threshold: {:.4f}, ' \
          'mindcf-0.01: {:.4f}, mindcf-0.001: {:.4f}. \33[0m'.format(100. * eer,
                                                                     eer_threshold,
                                                                     mindcf_01,
                                                                     mindcf_001))

    writer.add_scalar('Train/EER', 100. * eer, epoch)
    writer.add_scalar('Train/Threshold', eer_threshold, epoch)
    writer.add_scalar('Train/mindcf-0.01', mindcf_01, epoch)
    writer.add_scalar('Train/mindcf-0.001', mindcf_001, epoch)

    torch.cuda.empty_cache()


def test(model, epoch, writer, xvector_dir):
    xvector_model, classifier_spk, classifier_dom = model
    xvector_model.eval()
    this_xvector_dir = "%s/test/epoch_%s" % (xvector_dir, epoch)

    extract_loader = torch.utils.data.DataLoader(extract_dir, batch_size=1, shuffle=False, **extract_kwargs)
    verification_extract(extract_loader, xvector_model, this_xvector_dir, epoch, test_input=args.test_input)

    verify_dir = ScriptVerifyDataset(dir=args.test_dir, trials_file=args.trials, xvectors_dir=this_xvector_dir,
                                     loader=read_vec_flt)
    verify_loader = torch.utils.data.DataLoader(verify_dir, batch_size=128, shuffle=False, **kwargs)
    eer, eer_threshold, mindcf_01, mindcf_001 = verification_test(test_loader=verify_loader,
                                                                  dist_type=('cos' if args.cos_sim else 'l2'),
                                                                  log_interval=args.log_interval,
                                                                  xvector_dir=this_xvector_dir,
                                                                  epoch=epoch)
    print(
        '          \33[91mTest  ERR: {:.4f}%, Threshold: {:.4f}, mindcf-0.01: {:.4f}, mindcf-0.001: {:.4f}.\33[0m\n'.format(
            100. * eer, eer_threshold, mindcf_01, mindcf_001))

    writer.add_scalar('Test/EER', 100. * eer, epoch)
    writer.add_scalar('Test/Threshold', eer_threshold, epoch)
    writer.add_scalar('Test/mindcf-0.01', mindcf_01, epoch)
    writer.add_scalar('Test/mindcf-0.001', mindcf_001, epoch)


if __name__ == '__main__':
    main()
