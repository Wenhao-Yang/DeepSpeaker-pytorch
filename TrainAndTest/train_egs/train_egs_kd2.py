#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: train_egs.py
@Time: 2020/8/21 20:30
@Overview:
"""
from __future__ import print_function

# import argparse
import os
import os.path as osp
# import random
import pdb
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
import torch.nn.functional as F

import torchvision.transforms as transforms
from kaldi_io import read_mat, read_vec_flt
# from kaldiio import load_mat
from tensorboardX import SummaryWriter
from torch.autograd import Variable
from torch.nn.parallel import DistributedDataParallel
from torch.optim import lr_scheduler
from tqdm import tqdm

from Define_Model.Loss.LossFunction import CenterLoss, Wasserstein_Loss, MultiCenterLoss, CenterCosLoss
from Define_Model.Loss.SoftmaxLoss import AngleSoftmaxLoss, AMSoftmaxLoss, \
    ArcSoftmaxLoss, GaussianLoss
from Process_Data.Datasets.KaldiDataset import KaldiExtractDataset, \
    ScriptVerifyDataset
from Process_Data.Datasets.LmdbDataset import EgsDataset
from Process_Data.audio_processing import ConcateVarInput, tolog, ConcateOrgInput, PadCollate3d
from Process_Data.audio_processing import totensor  # , toMFB, truncatedinput
from TrainAndTest.common_func import create_optimizer, create_model, verification_test, verification_extract, \
    args_parse, args_model, load_model_args
from logger import NewLogger

warnings.filterwarnings("ignore")

# import torch._utils
#
# try:
#     torch._utils._rebuild_tensor_v2
# except AttributeError:
#     def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks):
#         tensor = torch._utils._rebuild_tensor(storage, storage_offset, size, stride)
#         tensor.requires_grad = requires_grad
#         tensor._backward_hooks = backward_hooks
#         return tensor
#
#
#     torch._utils._rebuild_tensor_v2 = _rebuild_tensor_v2

args = args_parse('PyTorch Speaker Recognition: Classification, Knowledge Distillation')

# Set the device to use by setting CUDA_VISIBLE_DEVICES env variable in
# order to prevent any memory allocation on unused GPUs
os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id
# os.environ['MASTER_ADDR'] = '127.0.0.1'
# os.environ['MASTER_PORT'] = '29555'

np.random.seed(args.seed)
torch.manual_seed(args.seed)
# torch.multiprocessing.set_sharing_strategy('file_system')

args.cuda = not args.no_cuda and torch.cuda.is_available()
if args.cuda:
    torch.cuda.manual_seed_all(args.seed)
    cudnn.benchmark = True

# create logger
# Define visulaize SummaryWriter instance
writer = SummaryWriter(logdir=args.check_path, filename_suffix='_first')
sys.stdout = NewLogger(osp.join(args.check_path, 'log.%s.txt' % time.strftime("%Y.%m.%d", time.localtime())))

kwargs = {'num_workers': args.nj, 'pin_memory': True} if args.cuda else {}
extract_kwargs = {'num_workers': args.nj, 'pin_memory': False} if args.cuda else {}

if not os.path.exists(args.check_path):
    print('Making checkpath...')
    os.makedirs(args.check_path)

opt_kwargs = {'lr': args.lr, 'lr_decay': args.lr_decay, 'weight_decay': args.weight_decay, 'dampening': args.dampening,
              'momentum': args.momentum}

l2_dist = nn.CosineSimilarity(dim=1, eps=1e-12) if args.cos_sim else nn.PairwiseDistance(p=2)

transform = transforms.Compose([
    totensor()
])

if args.test_input == 'var':
    transform_V = transforms.Compose([
        ConcateOrgInput(remove_vad=args.remove_vad),
    ])
elif args.test_input == 'fix':
    transform_V = transforms.Compose([
        ConcateVarInput(remove_vad=args.remove_vad, num_frames=args.chunk_size, frame_shift=args.chunk_size,
                        feat_type=args.feat_format),
    ])

if args.log_scale:
    transform.transforms.append(tolog())
    transform_V.transforms.append(tolog())

# pdb.set_trace()
if args.feat_format in ['kaldi', 'wav']:
    file_loader = read_mat
elif args.feat_format == 'npy':
    file_loader = np.load

torch.multiprocessing.set_sharing_strategy('file_system')

train_dir = EgsDataset(dir=args.train_dir, feat_dim=args.input_dim, loader=file_loader, transform=transform,
                       batch_size=args.batch_size, random_chunk=args.random_chunk,
                       label_dir=args.label_dir + '/train')

train_extract_dir = KaldiExtractDataset(dir=args.train_test_dir,
                                        transform=transform_V,
                                        filer_loader=file_loader,
                                        trials_file=args.train_trials)

extract_dir = KaldiExtractDataset(dir=args.test_dir, transform=transform_V,
                                  trials_file=args.trials, filer_loader=file_loader)

# train_test_dir = ScriptTestDataset(dir=args.train_test_dir, loader=file_loader, transform=transform_T)
# test_dir = ScriptTestDataset(dir=args.test_dir, loader=file_loader, transform=transform_T)
valid_dir = EgsDataset(dir=args.valid_dir, feat_dim=args.input_dim, loader=file_loader, transform=transform,
                       label_dir=args.label_dir + '/valid')


def train(train_loader, model, ce, optimizer, epoch, scheduler):
    # switch to evaluate mode
    model.train()

    correct = 0.
    total_datasize = 0.
    total_loss = 0.
    total_teacher_loss = 0.
    orth_err = 0

    ce_criterion, xe_criterion = ce
    pbar = tqdm(enumerate(train_loader))
    output_softmax = nn.Softmax(dim=1)

    if args.kd_loss == 'mse':
        kd_loss = nn.MSELoss()
    elif args.kd_loss == 'kld':
        kd_loss = nn.KLDivLoss()

    for batch_idx, (data, label, guide_label) in pbar:

        if args.cuda:
            label = label.cuda(non_blocking=True)
            data = data.cuda(non_blocking=True)
            guide_label = guide_label.cuda()

        data, label = Variable(data), Variable(label)
        guide_label = Variable(guide_label)

        classfier, feats = model(data)

        # with torch.no_grad():
        #     t_classfier, t_feats = teacher_model(data)
        # cos_theta, phi_theta = classfier
        classfier_label = classfier

        if args.loss_type == 'soft':
            loss = ce_criterion(classfier, label)
        elif args.loss_type == 'asoft':
            classfier_label, _ = classfier
            loss = xe_criterion(classfier, label)
        elif args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
            loss_cent = ce_criterion(classfier, label)
            loss_xent = xe_criterion(feats, label)

            loss = args.loss_ratio * loss_xent + loss_cent
        elif args.loss_type in ['amsoft', 'arcsoft']:
            loss = xe_criterion(classfier, label)

        # if args.kd_type == 'vanilla':
        soft_teacher_out = F.softmax(guide_label * args.s / args.temperature, dim=1)
        soft_student_out = F.softmax(classfier * args.s / args.temperature, dim=1)

        # loss = (1 - args.distil_weight) * loss
        teacher_loss = (args.distil_weight / (1 - args.distil_weight) * args.temperature * args.temperature) * kd_loss(
            soft_teacher_out, soft_student_out
        )

        # if args.kd_type == 'em_l2':
        #     teacher_loss += kd_loss(feats, t_feats)

        total_teacher_loss += float(teacher_loss.item())
        # pdb.set_trace()

        loss += teacher_loss

        predicted_labels = output_softmax(classfier_label)
        predicted_one_labels = torch.max(predicted_labels, dim=1)[1]
        minibatch_correct = float((predicted_one_labels.cuda() == label).sum().item())
        minibatch_acc = minibatch_correct / len(predicted_one_labels)
        correct += minibatch_correct

        total_datasize += len(predicted_one_labels)
        total_loss += float(loss.item())
        writer.add_scalar('Train/All_Loss', float(loss.item()), int((epoch - 1) * len(train_loader) + batch_idx + 1))

        if np.isnan(loss.item()):
            print("=> The maximum of probability is %f" % float(torch.max(classfier)))
            optimizer.zero_grad()
            # break
            # print("=> The Sum of probability is %f" % float(torch.sum(classfier, dim=1)))
            raise ValueError('Loss value is NaN!')

        # compute gradient and update weights
        loss.backward()

        if ((batch_idx + 1) % args.accu_steps) == 0:
            # optimizer the net
            optimizer.step()  # update parameters of net
            optimizer.zero_grad()  # reset gradient
        # optimizer.zero_grad()
        # loss.backward()

        if args.loss_ratio != 0:
            if args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
                for param in xe_criterion.parameters():
                    param.grad.data *= (1. / args.loss_ratio)

        if args.grad_clip > 0:
            this_lr = args.lr
            for param_group in optimizer.param_groups:
                this_lr = min(param_group['lr'], this_lr)
            torch.nn.utils.clip_grad_norm_(model.parameters(), this_lr * args.grad_clip)

        # optimizer.step()
        if args.scheduler == 'cyclic':
            scheduler.step()

        if (batch_idx + 1) % args.log_interval == 0:
            epoch_str = 'Train Epoch {}: [{:8d}/{:8d} ({:3.0f}%)]'.format(epoch, batch_idx * len(data),
                                                                          len(train_loader.dataset),
                                                                          100. * batch_idx / len(train_loader))

            if len(args.random_chunk) == 2 and args.random_chunk[0] < args.random_chunk[1]:
                if args.feat_format == 'kaldi':
                    batch_len = data.shape[-2]
                elif args.feat_format == 'wav':
                    batch_len = int(data.shape[-1] / 160)

                epoch_str += ' Batch Len: {:>3d}'.format(batch_len)

            if orth_err > 0:
                epoch_str += ' Orth_err: {:>5d}'.format(int(orth_err))

            if args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
                epoch_str += ' Another Loss: {:.4f}'.format(loss_xent.float())

            epoch_str += ' Teach Loss: {:.8f}'.format(teacher_loss.float())
            epoch_str += ' Avg Loss: {:.4f} Batch Accuracy: {:.4f}%'.format(total_loss / (batch_idx + 1),
                                                                            100. * minibatch_acc)
            pbar.set_description(epoch_str)
            # break

    print('\nEpoch {:>2d}: \33[91mTrain Accuracy: {:.6f}%, Avg loss: {:6f}, Teacher loss: {:.8f}.\33[0m'.format(epoch,
                                                                                                                100 * float(
                                                                                                                    correct) / total_datasize,
                                                                                                                total_loss / len(
                                                                                                                    train_loader),
                                                                                                                total_teacher_loss / len(
                                                                                                                    train_loader)))

    writer.add_scalar('Train/Accuracy', correct / total_datasize, epoch)
    writer.add_scalar('Train/Loss', total_loss / len(train_loader), epoch)
    writer.add_scalar('Train/Teacher_Loss', total_teacher_loss / len(train_loader), epoch)

    # torch.cuda.empty_cache()


def valid_class(valid_loader, model, ce, epoch):
    # switch to evaluate mode
    model.eval()

    total_loss = 0.
    ce_criterion, xe_criterion = ce
    softmax = nn.Softmax(dim=1)

    correct = 0.
    total_datasize = 0.

    with torch.no_grad():
        for batch_idx, (data, label, guide_label) in enumerate(valid_loader):
            data = data.cuda()
            label = label.cuda()

            # compute output
            out, feats = model(data)
            if args.loss_type == 'asoft':
                predicted_labels, _ = out
            else:
                predicted_labels = out

            classfier = predicted_labels
            if args.loss_type == 'soft':
                loss = ce_criterion(classfier, label)
            elif args.loss_type == 'asoft':
                classfier_label, _ = classfier
                loss = xe_criterion(classfier, label)
            elif args.loss_type in ['center', 'mulcenter', 'gaussian', 'coscenter']:
                loss_cent = ce_criterion(classfier, label)
                loss_xent = xe_criterion(feats, label)

                loss = args.loss_ratio * loss_xent + loss_cent
            elif args.loss_type == 'amsoft' or args.loss_type == 'arcsoft':
                loss = xe_criterion(classfier, label)

            total_loss += float(loss.item())
            # pdb.set_trace()
            predicted_one_labels = softmax(predicted_labels)
            predicted_one_labels = torch.max(predicted_one_labels, dim=1)[1]

            batch_correct = (predicted_one_labels.cuda() == label).sum().item()
            correct += batch_correct
            total_datasize += len(predicted_one_labels)

    valid_loss = total_loss / len(valid_loader)
    valid_accuracy = 100. * correct / total_datasize
    writer.add_scalar('Train/Valid_Loss', valid_loss, epoch)
    writer.add_scalar('Train/Valid_Accuracy', valid_accuracy, epoch)
    # torch.cuda.empty_cache()
    print('          \33[91mValid Accuracy: {:.6f}%, Avg loss: {:.6f}.\33[0m'.format(valid_accuracy,
                                                                                     valid_loss))

    return valid_loss


def valid_test(train_extract_loader, model, epoch, xvector_dir):
    # switch to evaluate mode
    model.eval()

    this_xvector_dir = "%s/train/epoch_%s" % (xvector_dir, epoch)
    verification_extract(train_extract_loader, model, this_xvector_dir, epoch, args.test_input)

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

    # torch.cuda.empty_cache()


def test(model, epoch, writer, xvector_dir):
    this_xvector_dir = "%s/test/epoch_%s" % (xvector_dir, epoch)

    extract_loader = torch.utils.data.DataLoader(extract_dir, batch_size=1, shuffle=False, **extract_kwargs)
    verification_extract(extract_loader, model, this_xvector_dir, epoch, test_input=args.test_input)

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


def main():
    # Views the training images and displays the distance on anchor-negative and anchor-positive
    # test_display_triplet_distance = False
    # print the experiment configuration
    print('\nCurrent time is \33[91m{}\33[0m.'.format(str(time.asctime())))
    opts = vars(args)
    keys = list(opts.keys())
    keys.sort()
    options = ["\'%s\': \'%s\'" % (str(k), str(opts[k])) for k in keys]

    print('Parsed options: \n{ %s }' % (', '.join(options)))
    print('Number of Speakers: {}.\n'.format(train_dir.num_spks))

    # create student model
    model_kwargs = args_model(args, train_dir)
    keys = list(model_kwargs.keys())
    keys.sort()
    model_options = ["\'%s\': \'%s\'" % (str(k), str(model_kwargs[k])) for k in keys]
    print('Model options: \n{ %s }' % (', '.join(model_options)))

    print('Testing with %s distance, ' % ('cos' if args.cos_sim else 'l2'))

    model = create_model(args.model, **model_kwargs)

    start_epoch = 0
    if args.save_init and not args.finetune:
        check_path = '{}/checkpoint_{}_{}.pth'.format(args.check_path, start_epoch,
                                                      time.strftime('%Y_%b_%d_%H:%M', time.localtime()))
        if not os.path.exists(check_path):
            torch.save({'state_dict': model.state_dict()}, check_path)

    # Load checkpoint
    iteration = 0
    if args.finetune and args.resume:
        if os.path.isfile(args.resume):
            print('=> loading checkpoint {}'.format(args.resume))
            checkpoint = torch.load(args.resume)
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
            print('=> no checkpoint found at {}'.format(args.resume))

    # Define Loss
    ce_criterion = nn.CrossEntropyLoss()
    if args.loss_type == 'soft':
        xe_criterion = None
    elif args.loss_type == 'asoft':
        ce_criterion = None
        xe_criterion = AngleSoftmaxLoss(lambda_min=args.lambda_min, lambda_max=args.lambda_max)
    elif args.loss_type == 'center':
        xe_criterion = CenterLoss(num_classes=train_dir.num_spks, feat_dim=args.embedding_size)
    elif args.loss_type == 'gaussian':
        xe_criterion = GaussianLoss(num_classes=train_dir.num_spks, feat_dim=args.embedding_size)
    elif args.loss_type == 'coscenter':
        xe_criterion = CenterCosLoss(num_classes=train_dir.num_spks, feat_dim=args.embedding_size)
    elif args.loss_type == 'mulcenter':
        xe_criterion = MultiCenterLoss(num_classes=train_dir.num_spks, feat_dim=args.embedding_size,
                                       num_center=args.num_center)
    elif args.loss_type == 'amsoft':
        ce_criterion = None
        xe_criterion = AMSoftmaxLoss(margin=args.margin, s=args.s)
    elif args.loss_type == 'arcsoft':
        ce_criterion = None
        xe_criterion = ArcSoftmaxLoss(margin=args.margin, s=args.s, iteraion=iteration, all_iteraion=args.all_iteraion)
    elif args.loss_type == 'wasse':
        xe_criterion = Wasserstein_Loss(source_cls=args.source_cls)

    model_para = [{'params': model.parameters()}]
    if args.loss_type in ['center', 'variance', 'mulcenter', 'gaussian', 'coscenter', 'ring']:
        assert args.lr_ratio > 0
        model_para.append({'params': xe_criterion.parameters(), 'lr': args.lr * args.lr_ratio})

    if args.finetune or args.second_wd > 0:
        # if args.loss_type in ['asoft', 'amsoft']:
        classifier_params = list(map(id, model.classifier.parameters()))
        rest_params = filter(lambda p: id(p) not in classifier_params, model.parameters())
        init_lr = args.lr * args.lr_ratio if args.lr_ratio > 0 else args.lr
        init_wd = args.second_wd if args.second_wd > 0 else args.weight_decay
        print('Set the lr and weight_decay of classifier to %f and %f' % (init_lr, init_wd))
        model_para = [{'params': rest_params},
                      {'params': model.classifier.parameters(), 'lr': init_lr, 'weight_decay': init_wd}]

    if args.filter in ['fDLR', 'fBLayer', 'fLLayer', 'fBPLayer', 'sinc', 'wav2spk']:
        filter_params = list(map(id, model.filter_layer.parameters()))
        rest_params = filter(lambda p: id(p) not in filter_params, model_para[0]['params'])
        init_wd = args.filter_wd if args.filter_wd > 0 else args.weight_decay
        init_lr = args.lr * args.lr_ratio if args.lr_ratio > 0 else args.lr
        print('Set the lr and weight_decay of filter layer to %f and %f' % (init_lr, init_wd))
        model_para[0]['params'] = rest_params
        model_para.append({'params': model.filter_layer.parameters(), 'lr': init_lr,
                           'weight_decay': init_wd})

    optimizer = create_optimizer(model_para, args.optimizer, **opt_kwargs)

    if not args.finetune and args.resume:
        if os.path.isfile(args.resume):
            print('=> loading checkpoint {}'.format(args.resume))
            checkpoint = torch.load(args.resume)
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

            saved_ce = checkpoint['criterion']
            if isinstance(saved_ce[1], ArcSoftmaxLoss):
                xe_criterion.iteraion = saved_ce[1].iteraion

            # model.dropout.p = args.dropout_p
        else:
            print('=> no checkpoint found at {}'.format(args.resume))

    # Create teacher model
    teacher_model_kwargs = load_model_args(args.teacher_model_yaml)
    if args.teacher_model == '':
        args.teacher_model = args.model

    # teacher_model = create_model(args.teacher_model, **teacher_model_kwargs)
    # if args.teacher_resume:
    #     if os.path.isfile(args.teacher_resume):
    #         print('=> loading teacher checkpoint {}'.format(args.teacher_resume))
    #         checkpoint = torch.load(args.teacher_resume)
    #         # start_epoch = checkpoint['epoch']
    #
    #         checkpoint_state_dict = checkpoint['state_dict']
    #         if isinstance(checkpoint_state_dict, tuple):
    #             checkpoint_state_dict = checkpoint_state_dict[0]
    #         filtered = {k: v for k, v in checkpoint_state_dict.items() if 'num_batches_tracked' not in k}
    #
    #         # filtered = {k: v for k, v in checkpoint['state_dict'].items() if 'num_batches_tracked' not in k}
    #         if list(filtered.keys())[0].startswith('module'):
    #             new_state_dict = OrderedDict()
    #             for k, v in filtered.items():
    #                 name = k[7:]  # remove `module.`，表面从第7个key值字符取到最后一个字符，去掉module.
    #                 new_state_dict[name] = v  # 新字典的key值对应的value为一一对应的值。
    #
    #             teacher_model.load_state_dict(new_state_dict)
    #         else:
    #             model_dict = teacher_model.state_dict()
    #             model_dict.update(filtered)
    #             teacher_model.load_state_dict(model_dict)
    #     else:
    #         print('=> no checkpoint found at {}'.format(args.resume))

    # Save model config txt
    with open(osp.join(args.check_path, 'model.%s.conf' % time.strftime("%Y.%m.%d", time.localtime())), 'w') as f:
        f.write('model: ' + str(model) + '\n')
        f.write('CrossEntropy: ' + str(ce_criterion) + '\n')
        f.write('Other Loss: ' + str(xe_criterion) + '\n')
        f.write('Optimizer: ' + str(optimizer) + '\n')

    milestones = args.milestones.split(',')
    milestones = [int(x) for x in milestones]
    milestones.sort()
    if args.scheduler == 'exp':
        gamma = np.power(args.base_lr / args.lr, 1 / args.epochs) if args.gamma == 0 else args.gamma
        scheduler = lr_scheduler.ExponentialLR(optimizer, gamma=gamma)
    elif args.scheduler == 'rop':
        scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, patience=args.patience, min_lr=1e-5)
    elif args.scheduler == 'cyclic':
        cycle_momentum = False if args.optimizer == 'adam' else True
        scheduler = lr_scheduler.CyclicLR(optimizer, base_lr=args.base_lr,
                                          max_lr=args.lr,
                                          step_size_up=5 * int(np.ceil(len(train_dir) / args.batch_size)),
                                          cycle_momentum=cycle_momentum,
                                          mode='triangular2')
    else:
        scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=milestones, gamma=0.1)

    ce = [ce_criterion, xe_criterion]

    start = args.start_epoch + start_epoch
    print('Start epoch is : ' + str(start))
    # start = 0
    end = start + args.epochs

    if len(args.random_chunk) == 2 and args.random_chunk[0] <= args.random_chunk[1]:
        min_chunk_size = int(args.random_chunk[0])
        max_chunk_size = int(args.random_chunk[1])
        pad_dim = 2 if args.feat_format == 'kaldi' else 3

        train_loader = torch.utils.data.DataLoader(train_dir, batch_size=args.batch_size,
                                                   collate_fn=PadCollate3d(dim=pad_dim,
                                                                         num_batch=int(
                                                                             np.ceil(len(train_dir) / args.batch_size)),
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

    train_extract_loader = torch.utils.data.DataLoader(train_extract_dir, batch_size=1, shuffle=False, **extract_kwargs)

    if args.cuda:
        if len(args.gpu_id) > 1:
            print("Continue with gpu: %s ..." % str(args.gpu_id))
            torch.distributed.init_process_group(backend="nccl",
                                                 init_method='file:///home/ssd2020/yangwenhao/lstm_speaker_verification/data/sharedfile2',
                                                 rank=0,
                                                 world_size=1)

            model = DistributedDataParallel(model.cuda())
            # teacher_model = DistributedDataParallel(teacher_model.cuda())
            # model = DistributedDataParallel(model.cuda(), find_unused_parameters=True)

        else:
            model = model.cuda()
            # teacher_model = teacher_model.cuda()

        for i in range(len(ce)):
            if ce[i] != None:
                ce[i] = ce[i].cuda()
        try:
            print('Dropout is {}.'.format(model.dropout_p))
        except:
            pass

    # teacher_model.eval()
    xvector_dir = args.check_path
    xvector_dir = xvector_dir.replace('checkpoint', 'xvector')
    start_time = time.time()

    try:
        for epoch in range(start, end):
            # pdb.set_trace()
            # continue
            # if args.filter in ['fDLR', 'fBLayer', 'fLLayer']:
            #     optimizer.param_groups[0]['lr'] = args.lr * args.lr_ratio

            lr_string = '\n\33[1;34m Current \'{}\' learning rate is '.format(args.optimizer)
            for param_group in optimizer.param_groups:
                lr_string += '{:.10f} '.format(param_group['lr'])
            print('%s \33[0m' % lr_string)

            train(train_loader, model, ce, optimizer, epoch, scheduler)
            valid_loss = valid_class(valid_loader, model, ce, epoch)

            if (epoch == 1 or epoch != (end - 2)) and (epoch % 4 == 1 or epoch in milestones or epoch == (end - 1)):
                model.eval()
                check_path = '{}/checkpoint_{}.pth'.format(args.check_path, epoch)
                model_state_dict = model.module.state_dict() \
                    if isinstance(model, DistributedDataParallel) else model.state_dict()
                torch.save({'epoch': epoch,
                            'state_dict': model_state_dict,
                            'criterion': ce},
                           check_path)

                # valid_test(train_extract_loader, model, epoch, xvector_dir)
                test(model, epoch, writer, xvector_dir)
                if epoch != (end - 1):
                    try:

                        if os.path.exists("%s/test/epoch_%s" % (xvector_dir, epoch)):
                            shutil.rmtree("%s/test/epoch_%s" % (xvector_dir, epoch))
                        if os.path.exists("%s/train/epoch_%s" % (xvector_dir, epoch)):
                            shutil.rmtree("%s/train/epoch_%s" % (xvector_dir, epoch))
                    except Exception as e:
                        print('rm dir xvectors error:', e)

            if args.scheduler == 'rop':
                scheduler.step(valid_loss)
            elif args.scheduler == 'cyclic':
                continue
            else:
                scheduler.step()

    except KeyboardInterrupt:
        end = epoch

    # torch.cuda.empty_cache()
    # torch.distributed.destroy_process_group()
    writer.close()
    stop_time = time.time()
    t = float(stop_time - start_time)
    print("Running %.4f minutes for each epoch.\n" % (t / 60 / (max(end - start, 1))))
    # pdb.set_trace()
    # sys.exit(0)


if __name__ == '__main__':
    main()
