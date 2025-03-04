#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: train_egs_dist_reweight.py
@Time: 2022/4/22 14:04
@Overview:
"""

from __future__ import print_function

import argparse
import itertools

import yaml
import os
import higher
import os.path as osp
import pdb
import random
import shutil
import sys
import time
# Version conflict
import warnings
from collections import OrderedDict

import numpy as np
import torch
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torchvision.transforms as transforms
from hyperpyyaml import load_hyperpyyaml
from kaldi_io import read_mat, read_vec_flt
from kaldiio import load_mat
from tensorboardX import SummaryWriter
from torch.autograd import Variable
from torch.nn.parallel import DistributedDataParallel
from torch.optim import lr_scheduler
from tqdm import tqdm

from Define_Model.Loss.End2End import GE2ELoss, ProtoLoss, AngleProtoLoss
from Define_Model.Loss.LossFunction import CenterLoss, Wasserstein_Loss, MultiCenterLoss, CenterCosLoss, RingLoss, \
    VarianceLoss, DistributeLoss, MMD_Loss
from Define_Model.Loss.SoftmaxLoss import AngleSoftmaxLoss, AngleLinear, AdditiveMarginLinear, AMSoftmaxLoss, \
    ArcSoftmaxLoss, \
    GaussianLoss, MinArcSoftmaxLoss, MinArcSoftmaxLoss_v2
from Process_Data.Datasets.KaldiDataset import KaldiExtractDataset, \
    ScriptVerifyDataset
from Process_Data.Datasets.LmdbDataset import EgsDataset, CrossEgsDataset, CrossMetaEgsDataset, CrossValidEgsDataset
import Process_Data.constants as C
from Process_Data.audio_processing import ConcateVarInput, tolog, ConcateOrgInput, PadCollate
from Process_Data.audio_processing import toMFB, totensor, truncatedinput
from TrainAndTest.common_func import create_optimizer, create_model, verification_test, verification_extract, \
    args_parse, args_model, save_model_args
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
# args = args_parse('PyTorch Speaker Recognition: Classification')

parser = argparse.ArgumentParser(description='PyTorch ( Distributed ) Speaker Recognition: Classification')
parser.add_argument('--local_rank', default=-1, type=int,
                    help='node rank for distributed training')

parser.add_argument('--train-config',
                    default='TrainAndTest/misc/TDNN/vox1_tdnn_reweight.yaml',
                    type=str,
                    help='node rank for distributed training')

parser.add_argument('--seed', type=int, default=12345, help='random seed (default: 0)')

args = parser.parse_args()

# Set the device to use by setting CUDA_VISIBLE_DEVICES env variable in
# order to prevent any memory allocation on unused GPUs
# os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id
# os.environ['MASTER_ADDR'] = '127.0.0.1'
# os.environ['MASTER_PORT'] = '29555'

# args.cuda = not args.no_cuda and torch.cuda.is_available()
# setting seeds
np.random.seed(args.seed)
torch.manual_seed(args.seed)
random.seed(args.seed)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(args.seed)
    cudnn.benchmark = True

torch.distributed.init_process_group(backend='nccl')
torch.cuda.set_device(args.local_rank)

# load train config file
# args.train_config
with open(args.train_config, 'r') as f:
    # config_args = yaml.load(f, Loader=yaml.FullLoader)
    config_args = load_hyperpyyaml(f)

# create logger
# Define visulaize SummaryWriter instance
if torch.distributed.get_rank() == 0:
    writer = SummaryWriter(logdir=config_args['check_path'], filename_suffix='SV')
    sys.stdout = NewLogger(
        os.path.join(config_args['check_path'], 'log.%s.txt' % time.strftime("%Y.%m.%d", time.localtime())))

kwargs = {'num_workers': config_args['nj'], 'pin_memory': False}  # if args.cuda else {}
extract_kwargs = {'num_workers': 4, 'pin_memory': False}  # if args.cuda else {}

if not os.path.exists(config_args['check_path']):
    print('Making checkpath...')
    os.makedirs(config_args['check_path'])

opt_kwargs = {'lr': config_args['lr'],
              'lr_decay': config_args['lr_decay'],
              'weight_decay': config_args['weight_decay'],
              'dampening': config_args['dampening'],
              'momentum': config_args['momentum']}

l2_dist = nn.CosineSimilarity(dim=1, eps=1e-12) if config_args['cos_sim'] else nn.PairwiseDistance(p=2)

transform = transforms.Compose([
    totensor()
])

if config_args['test_input'] == 'var':
    transform_V = transforms.Compose([
        ConcateOrgInput(remove_vad=config_args['remove_vad'], feat_type=config_args['feat_format']),
    ])
elif config_args['test_input'] == 'fix':
    transform_V = transforms.Compose([
        ConcateVarInput(remove_vad=config_args['remove_vad'], num_frames=config_args['chunk_size'],
                        frame_shift=config_args['chunk_size'],
                        feat_type=config_args['feat_format']),
    ])

if config_args['log_scale']:
    transform.transforms.append(tolog())
    transform_V.transforms.append(tolog())

# pdb.set_trace()
if config_args['feat_format'] in ['kaldi', 'wav']:
    file_loader = read_mat
elif config_args['feat_format'] == 'npy':
    file_loader = np.load

# torch.multiprocessing.set_sharing_strategy('file_system')

# train_dir = EgsDataset(dir=config_args['train_dir'], feat_dim=config_args['input_dim'], loader=file_loader,
#                        transform=transform,
#                        batch_size=config_args['batch_size'], random_chunk=config_args['random_chunk'],
#                        verbose=1 if torch.distributed.get_rank() == 0 else 0)
#
# train_extract_dir = KaldiExtractDataset(dir=config_args['train_test_dir'],
#                                         transform=transform_V,
#                                         filer_loader=file_loader,
#                                         trials_file=config_args['train_trials'])
#
# extract_dir = KaldiExtractDataset(dir=config_args['test_dir'], transform=transform_V,
#                                   trials_file=config_args['trials'], filer_loader=file_loader)
#
# valid_dir = EgsDataset(dir=config_args['valid_dir'], feat_dim=config_args['input_dim'], loader=file_loader,
#                        transform=transform,
#                        verbose=1 if torch.distributed.get_rank() == 0 else 0)

train_dir = CrossEgsDataset(dir=config_args['train_dir'], feat_dim=config_args['input_dim'], loader=file_loader,
                            transform=transform, enroll_utt=config_args['enroll_utts'],
                            batch_size=config_args['batch_size'], random_chunk=config_args['random_chunk'],
                            num_meta_spks=config_args['num_meta_spks'],
                            verbose=1 if torch.distributed.get_rank() == 0 else 0)

meta_dir = CrossMetaEgsDataset(dir=config_args['train_dir'], feat_dim=config_args['input_dim'], loader=file_loader,
                               spks=train_dir.meta_spks, enroll_utt=config_args['enroll_utts'],
                               transform=transform, batch_size=config_args['batch_size'],
                               random_chunk=config_args['random_chunk'],
                               verbose=1 if torch.distributed.get_rank() == 0 else 0)

train_extract_dir = KaldiExtractDataset(dir=config_args['train_test_dir'],
                                        transform=transform_V,
                                        filer_loader=file_loader,
                                        trials_file=config_args['train_trials'])

extract_dir = KaldiExtractDataset(dir=config_args['test_dir'], transform=transform_V,
                                  trials_file=config_args['trials'], filer_loader=file_loader)

valid_dir = CrossValidEgsDataset(dir=config_args['valid_dir'], feat_dim=config_args['input_dim'], loader=file_loader,
                                 transform=transform,
                                 enroll_utt=1, batch_size=config_args['batch_size'],
                                 random_chunk=config_args['random_chunk'],
                                 verbose=1 if torch.distributed.get_rank() == 0 else 0)


def train(train_loader, meta_loader, model, ce, optimizer, epoch, scheduler):
    # switch to evaluate mode
    model.train()

    correct = 0.
    total_datasize = 0.
    total_loss = 0.
    orth_err = 0
    other_loss = 0.

    ce_criterion, xe_criterion = ce
    pbar = tqdm(enumerate(train_loader))
    # output_softmax = nn.Softmax(dim=1)
    # lambda_ = (epoch / config_args['epochs']) ** 2

    # start_time = time.time()
    # pdb.set_trace()
    for batch_idx, (data, label) in pbar:
        data = data.transpose(0, 1)

        if torch.cuda.is_available():
            # label = label.cuda(non_blocking=True)
            # data = data.cuda(non_blocking=True)
            label = label.cuda()
            data = data.cuda()

        data_shape = data.shape
        pdb.set_trace()
        with higher.innerloop_ctx(model.module, optimizer) as (meta_model, meta_opt):
            # 1. Update meta model on training data
            _, meta_train_outputs = meta_model(data)
            ce_criterion.criterion.reduction = 'none'
            meta_train_outputs = meta_train_outputs.reshape(int(data_shape[0] / (config_args['enroll_utts'] + 1)),
                                                            config_args['enroll_utts'] + 1, -1)
            meta_train_loss, _ = ce_criterion(meta_train_outputs)
            # print(meta_train_loss)

            eps = torch.zeros(meta_train_loss.size(), requires_grad=True).cuda()
            meta_train_loss = torch.sum(eps * meta_train_loss)
            meta_opt.step(meta_train_loss)

            # 2. Compute grads of eps on meta validation data
            meta_inputs, meta_labels = next(meta_loader)
            meta_inputs = meta_inputs.transpose(0, 1)
            meta_inputs, meta_labels = meta_inputs.cuda(non_blocking=True), meta_labels.cuda(non_blocking=True)

            _, meta_val_outputs = meta_model(meta_inputs)
            ce_criterion.criterion.reduction = 'mean'
            meta_val_loss, _ = ce_criterion(
                meta_val_outputs.reshape(int(meta_inputs.shape[0] / (config_args['enroll_utts'] + 1)),
                                         config_args['enroll_utts'] + 1, -1))
            # print(meta_val_loss)
            # pdb.set_trace()
            eps_grads = torch.autograd.grad(meta_val_loss, eps, allow_unused=True)[0].detach()

        w_tilde = torch.clamp(-eps_grads, min=0)
        l1_norm = torch.sum(w_tilde)
        if l1_norm != 0:
            w = w_tilde / l1_norm
        else:
            w = w_tilde

        classfier, feats = model(data)
        feats = feats.reshape(int(feats.shape[0] / (config_args['enroll_utts'] + 1)), config_args['enroll_utts'] + 1,
                              -1)

        ce_criterion.criterion.reduction = 'none'
        end2end_loss, prec = ce_criterion(feats)
        end2end_loss = torch.sum(w * end2end_loss)

        loss = end2end_loss

        minibatch_acc = float(prec)
        correct += prec * len(feats)

        total_datasize += len(feats)
        total_loss += float(loss.item())

        if torch.distributed.get_rank() == 0:
            writer.add_scalar('Train/All_Loss', float(loss.item()),
                              int((epoch - 1) * len(train_loader) + batch_idx + 1))

        if np.isnan(loss.item()):
            raise ValueError('Loss value is NaN!')

        # compute gradient and update weights
        loss.backward()

        if 'grad_clip' in config_args and config_args['grad_clip'] > 0:
            this_lr = config_args['lr']
            for param_group in optimizer.param_groups:
                this_lr = min(param_group['lr'], this_lr)
            torch.nn.utils.clip_grad_norm_(model.parameters(), config_args['grad_clip'])

        if ((batch_idx + 1) % config_args['accu_steps']) == 0:
            # optimizer the net
            optimizer.step()  # update parameters of net
            optimizer.zero_grad()  # reset gradient

            if config_args['model'] == 'FTDNN' and ((batch_idx + 1) % 4) == 0:
                if isinstance(model, DistributedDataParallel):
                    model.module.step_ftdnn_layers()  # The key method to constrain the first two convolutions, perform after every SGD step
                    orth_err += model.module.get_orth_errors()
                else:
                    model.step_ftdnn_layers()  # The key method to constrain the first two convolutions, perform after every SGD step
                    orth_err += model.get_orth_errors()

        # optimizer.zero_grad()
        # loss.backward()

        if config_args['loss_ratio'] != 0:
            if config_args['loss_type'] in ['center', 'mulcenter', 'gaussian', 'coscenter']:
                for param in xe_criterion.parameters():
                    param.grad.data *= (1. / config_args['loss_ratio'])

        # optimizer.step()
        if config_args['scheduler'] == 'cyclic':
            scheduler.step()

        # if torch.distributed.get_rank() == 0:
        if (batch_idx + 1) % config_args['log_interval'] == 0:
            epoch_str = 'Train Epoch {}: [{:8d}/{:8d} ({:3.0f}%)]'.format(epoch, batch_idx * len(data),
                                                                          len(train_loader.dataset),
                                                                          100. * batch_idx / len(train_loader.dataset))

            if len(args.random_chunk) == 2 and args.random_chunk[0] <= args.random_chunk[1]:
                epoch_str += ' Batch Len: {:>3d}'.format(data.shape[-2])

            if orth_err > 0:
                epoch_str += ' Orth_err: {:>5d}'.format(int(orth_err))

            # if args.loss_type in ['center', 'variance', 'mulcenter', 'gaussian', 'coscenter']:
            #     epoch_str += ' Center Loss: {:.4f}'.format(loss_xent.float())
            # if args.loss_type in ['arcdist']:
            #     epoch_str += ' Dist Loss: {:.4f}'.format(loss_cent.float())

            epoch_str += ' E2E Loss: {:.4f}'.format(end2end_loss.float())

            epoch_str += ' Avg Loss: {:.4f} Batch Accuracy: {:.4f}%'.format(total_loss / (batch_idx + 1),
                                                                            minibatch_acc)
            pbar.set_description(epoch_str)

    this_epoch_str = 'Epoch {:>2d}: \33[91mTrain Accuracy: {:.6f}%, Avg loss: {:6f}'.format(epoch, 100 * float(
        correct) / total_datasize, total_loss / len(train_loader))

    if other_loss != 0:
        this_epoch_str += ' {} Loss: {:6f}'.format(config_args['loss_type'], other_loss / len(train_loader))

    this_epoch_str += '.\33[0m'

    if torch.distributed.get_rank() == 0:
        print(this_epoch_str)
        writer.add_scalar('Train/Accuracy', correct / total_datasize, epoch)
        writer.add_scalar('Train/Loss', total_loss / len(train_loader), epoch)

    torch.cuda.empty_cache()


def valid_class(valid_loader, model, ce, epoch):
    # switch to evaluate mode
    model.eval()

    total_loss = 0.
    other_loss = 0.
    ce_criterion, xe_criterion = ce
    # softmax = nn.Softmax(dim=1)

    correct = 0.
    total_datasize = 0.
    # lambda_ = (epoch / config_args['epochs']) ** 2

    with torch.no_grad():
        for batch_idx, (data, label) in enumerate(valid_loader):
            data = data.transpose(0, 1)
            if torch.cuda.is_available():
                data = data.cuda()
                label = label.cuda()

            data_shape = data.shape
            # compute output
            out, feats = model(data)
            feats = feats.reshape(int(data_shape[0] / 2), 2, -1)

            ce_criterion.criterion.reduction = 'mean'
            loss, prec = ce_criterion(feats)

            total_loss += float(loss.item())
            # pdb.set_trace()

            correct += float(prec * len(feats) / 100)
            total_datasize += len(len(feats))

    total_batch = len(valid_loader)
    all_total_loss = [None for _ in range(torch.distributed.get_world_size())]
    all_correct = [None for _ in range(torch.distributed.get_world_size())]
    all_total_batch = [None for _ in range(torch.distributed.get_world_size())]
    all_total_datasize = [None for _ in range(torch.distributed.get_world_size())]

    torch.distributed.all_gather_object(all_total_loss, total_loss)
    torch.distributed.all_gather_object(all_correct, correct)
    torch.distributed.all_gather_object(all_total_batch, total_batch)
    torch.distributed.all_gather_object(all_total_datasize, total_datasize)

    total_loss = np.sum(all_total_loss)
    correct = np.sum(all_correct)
    total_batch = np.sum(all_total_batch)
    total_datasize = np.sum(all_total_datasize)

    valid_loss = total_loss / total_batch
    valid_accuracy = 100. * correct / total_datasize

    if torch.distributed.get_rank() == 0:
        writer.add_scalar('Train/Valid_Loss', valid_loss, epoch)
        writer.add_scalar('Train/Valid_Accuracy', valid_accuracy, epoch)
        torch.cuda.empty_cache()

        this_epoch_str = '          \33[91mValid Accuracy: {:.6f}%, Avg loss: {:.6f}'.format(valid_accuracy, valid_loss)

        if other_loss != 0:
            this_epoch_str += ' {} Loss: {:6f}'.format(config_args['loss_type'], other_loss / len(valid_loader))

        this_epoch_str += '.\33[0m'
        print(this_epoch_str)

    return valid_loss


def valid_test(train_extract_loader, model, epoch, xvector_dir):
    # switch to evaluate mode
    model.eval()

    this_xvector_dir = "%s/train/epoch_%s" % (xvector_dir, epoch)
    verification_extract(train_extract_loader, model, this_xvector_dir, epoch, test_input=config_args['test_input'])

    verify_dir = ScriptVerifyDataset(dir=config_args['train_test_dir'], trials_file=config_args['train_trials'],
                                     xvectors_dir=this_xvector_dir,
                                     loader=read_vec_flt)
    verify_loader = torch.utils.data.DataLoader(verify_dir, batch_size=128, shuffle=False, **kwargs)
    eer, eer_threshold, mindcf_01, mindcf_001 = verification_test(test_loader=verify_loader,
                                                                  dist_type=('cos' if config_args['cos_sim'] else 'l2'),
                                                                  log_interval=config_args['log_interval'],
                                                                  xvector_dir=this_xvector_dir,
                                                                  epoch=epoch)

    if torch.distributed.get_rank() == 0:
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


def test(extract_loader, model, epoch, xvector_dir):
    this_xvector_dir = "%s/test/epoch_%s" % (xvector_dir, epoch)

    verification_extract(extract_loader, model, this_xvector_dir, epoch, test_input=config_args['test_input'])

    verify_dir = ScriptVerifyDataset(dir=config_args['test_dir'], trials_file=config_args['trials'],
                                     xvectors_dir=this_xvector_dir,
                                     loader=read_vec_flt)

    verify_sampler = torch.utils.data.distributed.DistributedSampler(verify_dir)
    # sampler = verify_sampler,
    verify_loader = torch.utils.data.DataLoader(verify_dir, batch_size=128, shuffle=False,
                                                **extract_kwargs)

    # pdb.set_trace()
    eer, eer_threshold, mindcf_01, mindcf_001 = verification_test(test_loader=verify_loader,
                                                                  dist_type='cos' if config_args[
                                                                      'cos_sim'] else 'l2',
                                                                  log_interval=config_args['log_interval'],
                                                                  xvector_dir=this_xvector_dir,
                                                                  epoch=epoch)

    if torch.distributed.get_rank() == 0:
        print(
            '          \33[91mTest  ERR: {:.4f}%, Threshold: {:.4f}, mindcf-0.01: {:.4f}, mindcf-0.001: {:.4f}.\33[0m\n'.format(
                100. * eer, eer_threshold, mindcf_01, mindcf_001))

        writer.add_scalar('Test/EER', 100. * eer, epoch)
        writer.add_scalar('Test/Threshold', eer_threshold, epoch)
        writer.add_scalar('Test/mindcf-0.01', mindcf_01, epoch)
        writer.add_scalar('Test/mindcf-0.001', mindcf_001, epoch)


def main():
    # Views the training images and displays the distance on anchor-negative and anchor-positive
    # test_display_triplet_distance = False
    # print the experiment configuration
    if torch.distributed.get_rank() == 0:
        print('\nCurrent time is \33[91m{}\33[0m.'.format(str(time.asctime())))
        # opts = vars(config_args)
        # keys = list(config_args.keys())
        # keys.sort()
        # options = ["\'%s\': \'%s\'" % (str(k), str(config_args[k])) for k in keys]
        # print('Parsed options: \n{ %s }' % (', '.join(options)))
        print('Number of Speakers: {}.\n'.format(train_dir.num_spks))

        # instantiate model and initialize weights
        # model_kwargs = args_model(args, train_dir)
        # keys = list(model_kwargs.keys())
        # keys.sort()
        # model_options = ["\'%s\': \'%s\'" % (str(k), str(model_kwargs[k])) for k in keys]
        # print('Model options: \n{ %s }' % (', '.join(model_options)))
        print('Testing with %s distance, ' % ('cos' if config_args['cos_sim'] else 'l2'))
    # model = create_model(config_args['model'], **model_kwargs)
    model = config_args['embedding_model']

    if 'classifier' in config_args:
        model.classifier = config_args['classifier']

    # model_yaml_path = os.path.join(args.check_path, 'model.%s.yaml' % time.strftime("%Y.%m.%d", time.localtime()))
    # save_model_args(model_kwargs, model_yaml_path)
    # exit(0)

    start_epoch = 0
    if 'finetune' not in config_args or not config_args['finetune']:
        check_path = '{}/checkpoint_{}_{}.pth'.format(config_args['check_path'], start_epoch,
                                                      time.strftime('%Y_%b_%d_%H:%M', time.localtime()))
        if not os.path.exists(check_path):
            torch.save({'state_dict': model.state_dict()}, check_path)

    # Load checkpoint
    iteration = 0  # if args.resume else 0
    if 'fintune' in config_args:
        if os.path.isfile(config_args['resume']):
            print('=> loading checkpoint {}'.format(config_args['resume']))
            checkpoint = torch.load(config_args['resume'])
            start_epoch = checkpoint['epoch']

            checkpoint_state_dict = checkpoint['state_dict']
            if isinstance(checkpoint_state_dict, tuple):
                checkpoint_state_dict = checkpoint_state_dict[0]
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
            # model.dropout.p = args.dropout_p
        else:
            print('=> no checkpoint found at {}'.format(config_args['resume']))

    if config_args['loss_type'] == 'e2e':
        ce_criterion = GE2ELoss()
    elif config_args['loss_type'] == 'proto':
        ce_criterion = ProtoLoss()
    elif config_args['loss_type'] in ['angleproto']:
        ce_criterion = AngleProtoLoss()
    xe_criterion = None

    # if config_args['loss_type'] == 'soft':
    #     xe_criterion = None
    # elif config_args['loss_type'] == 'asoft':
    #     ce_criterion = None
    #     xe_criterion = AngleSoftmaxLoss(lambda_min=config_args['lambda_min'], lambda_max=config_args['lambda_max'])
    # elif config_args['loss_type'] == 'center':
    #     xe_criterion = CenterLoss(num_classes=train_dir.num_spks, feat_dim=config_args['embedding_size'])
    # elif config_args['loss_type'] == 'variance':
    #     xe_criterion = VarianceLoss(num_classes=train_dir.num_spks, feat_dim=config_args['embedding_size'])
    # elif config_args['loss_type'] == 'gaussian':
    #     xe_criterion = GaussianLoss(num_classes=train_dir.num_spks, feat_dim=config_args['embedding_size'])
    # elif config_args['loss_type'] == 'coscenter':
    #     xe_criterion = CenterCosLoss(num_classes=train_dir.num_spks, feat_dim=config_args['embedding_size'])
    # elif config_args['loss_type'] == 'mulcenter':
    #     xe_criterion = MultiCenterLoss(num_classes=train_dir.num_spks, feat_dim=config_args['embedding_size'],
    #                                    num_center=config_args['num_center'])
    # elif config_args['loss_type'] == 'amsoft':
    #     ce_criterion = None
    #     xe_criterion = AMSoftmaxLoss(margin=config_args['margin'], s=config_args['s'])
    #
    # elif config_args['loss_type'] in ['arcsoft', 'subarc']:
    #     ce_criterion = None
    #     if 'class_weight' in config_args and config_args['class_weight'] == 'cnc1':
    #         class_weight = torch.tensor(C.CNC1_WEIGHT)
    #         if len(class_weight) != train_dir.num_spks:
    #             class_weight = None
    #     else:
    #         class_weight = None
    #
    #     all_iteraion = 0 if 'all_iteraion' not in config_args else config_args['all_iteraion']
    #     smooth_ratio = 0 if 'smooth_ratio' not in config_args else config_args['smooth_ratio']
    #     xe_criterion = ArcSoftmaxLoss(margin=config_args['margin'], s=config_args['s'], iteraion=iteration,
    #                                   all_iteraion=all_iteraion,
    #                                   smooth_ratio=smooth_ratio,
    #                                   class_weight=class_weight)
    # elif config_args['loss_type'] == 'minarcsoft':
    #     ce_criterion = None
    #     xe_criterion = MinArcSoftmaxLoss(margin=config_args['margin'], s=config_args['s'], iteraion=iteration,
    #                                      all_iteraion=config_args['all_iteraion'])
    # elif config_args['loss_type'] == 'minarcsoft2':
    #     ce_criterion = None
    #     xe_criterion = MinArcSoftmaxLoss_v2(margin=config_args['margin'], s=config_args['s'], iteraion=iteration,
    #                                         all_iteraion=config_args['all_iteraion'])
    # elif config_args['loss_type'] == 'wasse':
    #     xe_criterion = Wasserstein_Loss(source_cls=config_args['source_cls'])
    # elif config_args['loss_type'] == 'mmd':
    #     xe_criterion = MMD_Loss()
    # elif config_args['loss_type'] == 'ring':
    #     xe_criterion = RingLoss(ring=config_args['ring'])
    #     args.alpha = 0.0
    # elif 'arcdist' in config_args['loss_type']:
    #     ce_criterion = DistributeLoss(stat_type=config_args['stat_type'], margin=config_args['m'])
    #     xe_criterion = ArcSoftmaxLoss(margin=config_args['margin'], s=config_args['s'], iteraion=iteration,
    #                                   all_iteraion=config_args['all_iteraion'])

    model_para = [{'params': model.parameters()}]
    if config_args['loss_type'] in ['center', 'variance', 'mulcenter', 'gaussian', 'coscenter', 'ring']:
        assert config_args['lr_ratio'] > 0
        model_para.append({'params': xe_criterion.parameters(), 'lr': config_args['lr'] * config_args['lr_ratio']})

    if 'second_wd' in config_args and config_args['config_args'] > 0:
        # if config_args['loss_type in ['asoft', 'amsoft']:
        classifier_params = list(map(id, model.classifier.parameters()))
        rest_params = filter(lambda p: id(p) not in classifier_params, model.parameters())
        init_lr = config_args['lr'] * config_args['lr_ratio'] if config_args['lr_ratio'] > 0 else config_args['lr']
        init_wd = config_args['second_wd'] if config_args['second_wd'] > 0 else config_args['weight_decay']
        print('Set the lr and weight_decay of classifier to %f and %f' % (init_lr, init_wd))
        model_para = [{'params': rest_params},
                      {'params': model.classifier.parameters(), 'lr': init_lr, 'weight_decay': init_wd}]

    if 'filter' in config_args:
        if config_args['filter'] in ['fDLR', 'fBLayer', 'fLLayer', 'fBPLayer', 'sinc2down']:
            filter_params = list(map(id, model.filter_layer.parameters()))
            rest_params = filter(lambda p: id(p) not in filter_params, model_para[0]['params'])
            init_wd = config_args['filter_wd'] if args.filter_wd > 0 else config_args['weight_decay']
            init_lr = config_args['lr'] * config_args['lr_ratio'] if config_args['lr_ratio'] > 0 else config_args['lr']
            print('Set the lr and weight_decay of filter layer to %f and %f' % (init_lr, init_wd))
            model_para[0]['params'] = rest_params
            model_para.append({'params': model.filter_layer.parameters(), 'lr': init_lr,
                               'weight_decay': init_wd})

    optimizer = create_optimizer(model_para, config_args['optimizer'], **opt_kwargs)

    if 'resume' in config_args:
        if os.path.isfile(config_args['resume']):
            if torch.distributed.get_rank() == 0:
                print('=> loading checkpoint {}'.format(config_args['resume']))
            checkpoint = torch.load(config_args['resume'])
            start_epoch = checkpoint['epoch']

            checkpoint_state_dict = checkpoint['state_dict']
            if isinstance(checkpoint_state_dict, tuple):
                checkpoint_state_dict = checkpoint_state_dict[0]

            filtered = {k: v for k, v in checkpoint_state_dict.items() if 'num_batches_tracked' not in k}

            # filtered = {k: v for k, v in checkpoint['state_dict'].items() if 'num_batches_tracked' not in k}
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
            # model.dropout.p = args.dropout_p
        else:
            if torch.distributed.get_rank() == 0:
                print('=> no checkpoint found at {}'.format(config_args['resume']))

    # Save model config txt
    if torch.distributed.get_rank() == 0:
        with open(os.path.join(config_args['check_path'],
                               'model.%s.conf' % time.strftime("%Y.%m.%d", time.localtime())),
                  'w') as f:
            f.write('model: ' + str(model) + '\n')
            f.write('End2End Loss: ' + str(ce_criterion) + '\n')
            f.write('Other Loss: ' + str(xe_criterion) + '\n')
            f.write('Optimizer: ' + str(optimizer) + '\n')

    milestones = config_args['milestones']
    if config_args['scheduler'] == 'exp':
        gamma = np.power(config_args['base_lr'] / config_args['lr'],
                         1 / config_args['epochs']) if config_args['gamma'] == 0 else config_args['gamma']
        scheduler = lr_scheduler.ExponentialLR(optimizer, gamma=gamma)
    elif config_args['scheduler'] == 'rop':
        scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, patience=config_args['patience'], min_lr=1e-5)
    elif config_args['scheduler'] == 'cyclic':
        cycle_momentum = False if config_args['optimizer'] == 'adam' else True
        scheduler = lr_scheduler.CyclicLR(optimizer, base_lr=config_args['base_lr'],
                                          max_lr=config_args['lr'],
                                          step_size_up=5 * int(np.ceil(len(train_dir) / config_args['batch_size'])),
                                          cycle_momentum=cycle_momentum,
                                          mode='triangular2')
    else:
        scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=milestones, gamma=0.1)

    ce = [ce_criterion, xe_criterion]

    start = 1 + start_epoch
    if torch.distributed.get_rank() == 0:
        print('Start epoch is : ' + str(start))
    # start = 0
    end = start + config_args['epochs']

    if len(config_args['random_chunk']) == 2 and config_args['random_chunk'][0] <= config_args['random_chunk'][1]:
        min_chunk_size = int(config_args['random_chunk'][0])
        max_chunk_size = int(config_args['random_chunk'][1])
        pad_dim = 2 if config_args['feat_format'] == 'kaldi' else 3

        train_sampler = torch.utils.data.distributed.DistributedSampler(train_dir)
        train_loader = torch.utils.data.DataLoader(train_dir, batch_size=1,
                                                   collate_fn=PadCollate(dim=pad_dim,
                                                                         num_batch=int(
                                                                             np.ceil(
                                                                                 len(train_dir) / config_args[
                                                                                     'batch_size'])),
                                                                         min_chunk_size=min_chunk_size,
                                                                         max_chunk_size=max_chunk_size,
                                                                         chisquare=False if 'chisquare' not in config_args else
                                                                         config_args['chisquare'],
                                                                         verbose=1 if torch.distributed.get_rank() == 0 else 0),
                                                   shuffle=config_args['shuffle'], sampler=train_sampler, **kwargs)

        meta_sampler = torch.utils.data.distributed.DistributedSampler(meta_dir)
        meta_loader = torch.utils.data.DataLoader(meta_dir, batch_size=1,
                                                  collate_fn=PadCollate(dim=pad_dim,
                                                                        num_batch=int(
                                                                            np.ceil(len(train_dir) / config_args[
                                                                                'batch_size'])),
                                                                        min_chunk_size=min_chunk_size,
                                                                        max_chunk_size=max_chunk_size,
                                                                        chisquare=False if 'chisquare' not in config_args else
                                                                        config_args['chisquare'],
                                                                        verbose=1 if torch.distributed.get_rank() == 0 else 0),
                                                  shuffle=config_args['shuffle'], sampler=meta_sampler, **kwargs)

        valid_sampler = torch.utils.data.distributed.DistributedSampler(valid_dir)
        valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=int(config_args['batch_size'] / 2),
                                                   collate_fn=PadCollate(dim=pad_dim, fix_len=True,
                                                                         min_chunk_size=min_chunk_size,
                                                                         max_chunk_size=max_chunk_size,
                                                                         verbose=1 if torch.distributed.get_rank() == 0 else 0),
                                                   shuffle=False, sampler=valid_sampler, **kwargs)

        extract_sampler = torch.utils.data.distributed.DistributedSampler(extract_dir)
        # sampler = extract_sampler,
        extract_loader = torch.utils.data.DataLoader(extract_dir, batch_size=1, shuffle=False,
                                                     sampler=extract_sampler, **extract_kwargs)


    else:
        train_loader = torch.utils.data.DataLoader(train_dir, batch_size=config_args['batch_size'],
                                                   shuffle=config_args['shuffle'],
                                                   **kwargs)
        valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=int(config_args['batch_size'] / 2),
                                                   shuffle=False,
                                                   **kwargs)
        extract_loader = torch.utils.data.DataLoader(extract_dir, batch_size=1, shuffle=False,
                                                     **extract_kwargs)

    train_extract_sampler = torch.utils.data.distributed.DistributedSampler(train_extract_dir)
    train_extract_loader = torch.utils.data.DataLoader(train_extract_dir, batch_size=1, shuffle=False,
                                                       sampler=train_extract_sampler, **extract_kwargs)

    meta_loader = itertools.cycle(meta_loader)
    # if config_args['cuda']:
    if len(config_args['gpu_id']) > 1:
        print("Continue with gpu: %s ..." % str(args.local_rank))
        # torch.distributed.init_process_group(backend="nccl",
        #                                      init_method='file:///home/yangwenhao/lstm_speaker_verification/data/sharedfile',
        #                                      rank=0,
        #                                      world_size=1)
        #
        # try:
        #     torch.distributed.init_process_group(backend="nccl", init_method='tcp://localhost:32456', rank=0,
        #                                          world_size=1)
        # except RuntimeError as r:
        #     torch.distributed.init_process_group(backend="nccl", init_method='tcp://localhost:32454', rank=0,
        #                                          world_size=1)
        # if args.gain
        # model = DistributedDataParallel(model.cuda(), find_unused_parameters=True)
        model = DistributedDataParallel(model.cuda(), device_ids=[args.local_rank])


    else:
        model = model.cuda()

    for i in range(len(ce)):
        if ce[i] != None:
            ce[i] = ce[i].cuda()
    try:
        print('Dropout is {}.'.format(model.dropout_p))
    except:
        pass

    xvector_dir = config_args['check_path']
    xvector_dir = xvector_dir.replace('checkpoint', 'xvector')
    start_time = time.time()

    try:
        for epoch in range(start, end):
            # pdb.set_trace()
            if torch.distributed.get_rank() == 0:
                lr_string = '\n\33[1;34m Current \'{}\' learning rate is '.format(config_args['optimizer'])
                for param_group in optimizer.param_groups:
                    lr_string += '{:.10f} '.format(param_group['lr'])
                print('%s \33[0m' % lr_string)

            train(train_loader, meta_loader, model, ce, optimizer, epoch, scheduler)
            valid_loss = valid_class(valid_loader, model, ce, epoch)

            if (epoch == 1 or epoch != (end - 2)) and (
                    epoch % config_args['test_interval'] == 1 or epoch in milestones or epoch == (end - 1)):
                model.eval()
                check_path = '{}/checkpoint_{}.pth'.format(config_args['check_path'], epoch)
                model_state_dict = model.module.state_dict() \
                    if isinstance(model, DistributedDataParallel) else model.state_dict()
                torch.save({'epoch': epoch,
                            'state_dict': model_state_dict,
                            'criterion': ce}, check_path)

                valid_test(train_extract_loader, model, epoch, xvector_dir)
                test(extract_loader, model, epoch, xvector_dir)
                if epoch != (end - 1) and torch.distributed.get_rank() == 0:
                    try:
                        shutil.rmtree("%s/train/epoch_%s" % (xvector_dir, epoch))
                        shutil.rmtree("%s/test/epoch_%s" % (xvector_dir, epoch))
                    except Exception as e:
                        print('rm dir xvectors error:', e)

            if config_args['scheduler'] == 'rop':
                scheduler.step(valid_loss)
            elif config_args['scheduler'] == 'cyclic':
                continue
            else:
                scheduler.step()

    except KeyboardInterrupt:
        end = epoch

    stop_time = time.time()
    t = float(stop_time - start_time)

    if torch.distributed.get_rank() == 0:
        writer.close()
        print("Running %.4f minutes for each epoch.\n" % (t / 60 / (max(end - start, 1))))
    # torch.distributed.des
    exit(0)


if __name__ == '__main__':
    main()
