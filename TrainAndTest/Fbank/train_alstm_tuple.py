#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: train_alstm_tuple.py
@Time: 2020/3/6 3:30 PM
@Overview:
"""
# from __future__ import print_function
import argparse
import pathlib
import pdb
import random
import time

from tensorboardX import SummaryWriter

from Define_Model.LossFunction import TupleLoss
from Process_Data import constants as c
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
from torch.autograd import Variable
import torch.backends.cudnn as cudnn
import os

import numpy as np
from torch.optim.lr_scheduler import StepLR, MultiStepLR
from tqdm import tqdm

from Define_Model.TDNN import XVectorTDNN
from TrainAndTest.common_func import create_optimizer, AverageMeter
from eval_metrics import evaluate_kaldi_eer
from Process_Data.KaldiDataset import KaldiTrainDataset, KaldiTestDataset, KaldiValidDataset, TrainDataset, \
    KaldiTupleDataset
from Define_Model.model import PairwiseDistance, LSTM_End, AttentionLSTM
from Process_Data.audio_processing import toMFB, totensor, truncatedinput, read_MFB, read_audio, \
    mk_MFB, concateinputfromMFB, PadCollate, varLengthFeat, to2tensor, RNNPadCollate
import warnings

warnings.filterwarnings("ignore")
# Version conflict

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
parser = argparse.ArgumentParser(description='PyTorch LSTM Speaker Recognition')
# Model options

# options for vox1
parser.add_argument('--train-dir', type=str,
                    default='/home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1/dev_no_sli',
                    help='path to dataset')
parser.add_argument('--test-dir', type=str,
                    default='/home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1/test_no_sli',
                    help='path to test dataset')

parser.add_argument('--feat-dim', default=40, type=int, metavar='N',
                    help='acoustic feature dimension')
parser.add_argument('--embedding-dim', default=512, type=int, metavar='N',
                    help='acoustic feature dimension')
parser.add_argument('--check-path', default='Data/checkpoint/ALSTM/tuple/kaldi',
                    help='folder to output model checkpoints')
parser.add_argument('--resume',
                    default='Data/checkpoint/ALSTM/tuple/kaldi/checkpoint_16.pth',
                    type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')

parser.add_argument('--start-epoch', default=1, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('--epochs', type=int, default=90, metavar='E',
                    help='number of epochs to train (default: 10)')

# Training options
parser.add_argument('--num-lstm', default=3, type=int, metavar='N', help='num of layers of lstm')
parser.add_argument('--cos-sim', action='store_true', default=True,
                    help='using Cosine similarity')

parser.add_argument('--batch-size', type=int, default=64, metavar='BS',
                    help='input batch size for training (default: 128)')
parser.add_argument('--test-batch-size', type=int, default=192, metavar='BST',
                    help='input batch size for testing (default: 64)')
parser.add_argument('--test-input-per-file', type=int, default=4, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--input-per-spks', type=int, default=16, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')

parser.add_argument('--tuple-size', type=int, default=6, metavar='N',
                    help='the number of enrolled utterance + 1 (default: 6')
parser.add_argument('--nagative-pair', type=int, default=5, metavar='N',
                    help='the number of enrolled utterance + 1 (default: 6')
parser.add_argument('--margin', type=float, default=3, metavar='MARGIN',
                    help='the margin value for the triplet loss function (default: 1.0')
parser.add_argument('--loss-ratio', type=float, default=2.0, metavar='LOSSRATIO',
                    help='the ratio softmax loss - triplet loss (default: 2.0')

parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                    help='learning rate (default: 0.125)')
parser.add_argument('--lr-decay', default=0, type=float, metavar='LRD',
                    help='learning rate decay ratio (default: 1e-4')
parser.add_argument('--weight-decay', default=5e-4, type=float,
                    metavar='W', help='weight decay (default: 0.0)')
parser.add_argument('--momentum', default=0.9, type=float,
                    metavar='W', help='momentum for sgd (default: 0.9)')
parser.add_argument('--dampening', default=0, type=float,
                    metavar='W', help='dampening for sgd (default: 0.0)')
parser.add_argument('--optimizer', default='adam', type=str,
                    metavar='OPT', help='The optimizer to use (default: Adagrad)')

# Device options
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='enables CUDA training')
parser.add_argument('--gpu-id', default='0', type=str,
                    help='id(s) for CUDA_VISIBLE_DEVICES')
parser.add_argument('--seed', type=int, default=2, metavar='S',
                    help='random seed (default: 0)')
parser.add_argument('--log-interval', type=int, default=10, metavar='LI',
                    help='how many batches to wait before logging training status')

parser.add_argument('--mfb', action='store_true', default=True,
                    help='start from MFB file')
parser.add_argument('--makemfb', action='store_true', default=False,
                    help='need to make mfb file')

args = parser.parse_args()

# Set the device to use by setting CUDA_VISIBLE_DEVICES env variable in
# order to prevent any memory allocation on unused GPUs
os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id

args.cuda = not args.no_cuda and torch.cuda.is_available()
np.random.seed(args.seed)
torch.manual_seed(args.seed)

if args.cuda:
    cudnn.benchmark = True

# Define visulaize SummaryWriter instance
writer = SummaryWriter(args.check_path, filename_suffix='lstm-tuple')

kwargs = {'num_workers': 0, 'pin_memory': True} if args.cuda else {}
if not os.path.exists(args.check_path):
    os.makedirs(args.check_path)
opt_kwargs = {'lr': args.lr,
              'lr_decay': args.lr_decay,
              'weight_decay': args.weight_decay,
              'dampening': args.dampening,
              'momentum': args.momentum}

l2_dist = nn.CosineSimilarity(dim=1, eps=1e-6) if args.cos_sim else PairwiseDistance(2)

if args.mfb:
    transform = transforms.Compose([
        concateinputfromMFB(num_frames=300, remove_vad=True),
        # varLengthFeat(max_chunk_size=300),
        to2tensor()
    ])
    transform_T = transforms.Compose([
        concateinputfromMFB(num_frames=300, input_per_file=args.test_input_per_file, remove_vad=True),
        # varLengthFeat(),
        to2tensor()
    ])
else:
    transform = transforms.Compose([
        truncatedinput(),
        toMFB(),
        totensor(),
    ])

train_dir = KaldiTupleDataset(dir=args.train_dir, transform=transform,
                              nagative_pair=args.nagative_pair, samples_per_spk=args.input_per_spks)

test_dir = KaldiTestDataset(dir=args.test_dir, transform=transform_T)

indices = list(range(len(test_dir)))
random.shuffle(indices)
indices = indices[:6400]
test_part = torch.utils.data.Subset(test_dir, indices)

valid_dir = KaldiValidDataset(valid_set=train_dir.valid_set, spk_to_idx=train_dir.spk_to_idx,
                              valid_uid2feat=train_dir.valid_uid2feat, valid_utt2spk_dict=train_dir.valid_utt2spk_dict,
                              transform=transform)


def main():
    # Views the training images and displays the distance on anchor-negative and anchor-positive
    # print the experiment configuration
    print('\33[91mCurrent time is {}\33[0m'.format(str(time.asctime())))
    print('Parsed options: {}'.format(vars(args)))
    print('Number of Classes: {}\n'.format(len(train_dir.speakers)))

    # instantiate
    # model and initialize weights
    model = AttentionLSTM(input_dim=args.feat_dim, num_class=train_dir.num_spks,
                          batch_size=args.batch_size * args.tuple_size,
                          project_dim=args.embedding_dim, num_lstm=args.num_lstm, hidden_shape=128,
                          dropout_p=0.1, attention_dim=128)

    if args.cuda:
        model.cuda()

    optimizer = create_optimizer(model.parameters(), args.optimizer, **opt_kwargs)
    scheduler = MultiStepLR(optimizer, milestones=[60], gamma=0.1)

    start = 0
    # optionally resume from a checkpoint
    if args.resume:
        if os.path.isfile(args.resume):
            print('=> loading checkpoint {}'.format(args.resume))
            checkpoint = torch.load(args.resume)
            start = checkpoint['epoch']
            checkpoint = torch.load(args.resume)
            filtered = {k: v for k, v in checkpoint['state_dict'].items() if 'num_batches_tracked' not in k}
            model.load_state_dict(filtered)
            optimizer.load_state_dict(checkpoint['optimizer'])
            scheduler.load_state_dict(checkpoint['scheduler'])
            # criterion.load_state_dict(checkpoint['criterion'])
        else:
            print('=> no checkpoint found at {}'.format(args.resume))

    start += args.start_epoch
    print('Start epoch is : ' + str(start))
    end = start + args.epochs

    train_loader = torch.utils.data.DataLoader(train_dir, batch_size=args.batch_size, shuffle=True, **kwargs)
    valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=int(args.batch_size * args.tuple_size),
                                               shuffle=False, **kwargs)
    test_loader = torch.utils.data.DataLoader(test_part, batch_size=int(
        args.batch_size * args.tuple_size / args.test_input_per_file), shuffle=False, **kwargs)
    # criterion = nn.CrossEntropyLoss().cuda()
    criterion = [nn.CrossEntropyLoss().cuda(), TupleLoss(args.batch_size, args.tuple_size).cuda()]
    check_path = '{}/checkpoint_{}.pth'.format(args.check_path, -1)
    torch.save({'epoch': -1, 'state_dict': model.state_dict(), 'optimizer': optimizer.state_dict()},
               check_path)

    for epoch in range(start, end):
        # pdb.set_trace()
        # compute_dropout(model, optimizer, epoch, end)
        train(train_loader, model, optimizer, criterion, epoch)
        test(valid_loader, test_loader, model, epoch)
        scheduler.step()
        # break
    writer.close()


def train(train_loader, model, optimizer, criterion, epoch):
    # switch to evaluate mode
    model.train()

    correct = 0.
    total_datasize = 0.
    total_loss = 0.
    ce_losses = AverageMeter()
    tuple_losses = AverageMeter()
    output_softmax = nn.Softmax(dim=1)

    # print('\33\n[1;34m Current dropout is {:.4f}. '.format(model.dropout_p), end='')
    for param_group in optimizer.param_groups:
        print('\33[1;34m\'{}\' learning rate is {:.6f}.\33[0m'.format(args.optimizer, param_group['lr']))

    pbar = tqdm(enumerate(train_loader))
    for batch_idx, (data, label) in pbar:
        if len(data) != args.batch_size:
            continue

        pair_label = label[:, 0]
        cls_label = label[:, 1:]

        vec_shape = data.shape
        data = data.reshape(vec_shape[0] * vec_shape[1], vec_shape[2], vec_shape[3])

        cls_label_shape = cls_label.shape
        cls_label = cls_label.reshape(cls_label_shape[0] * cls_label_shape[1])

        if args.cuda:
            data = data.float().cuda()
            cls_label = cls_label.cuda()
            pair_label = pair_label.cuda()

        feats, classfier = model(data)
        ce_loss = criterion[0](classfier, cls_label)
        tuple_loss = criterion[1](feats, pair_label)
        loss = ce_loss + args.loss_ratio * tuple_loss

        predicted_labels = output_softmax(classfier)
        predicted_one_labels = torch.max(predicted_labels, dim=1)[1]
        batch_correct = float((predicted_one_labels == cls_label).sum().item())
        minibatch_acc = batch_correct / len(predicted_one_labels)
        correct += batch_correct
        total_datasize += len(predicted_one_labels)

        ce_losses.update(ce_loss.item(), len(data))
        tuple_losses.update(tuple_loss.item(), len(data))
        total_loss += loss.item()
        # pdb.set_trace()

        # compute gradient and update weights
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch_idx % args.log_interval == 0:
            pbar.set_description('Train Epoch: {:3d} [{:7d}/{:7d} ({:3.0f}%)] ' \
                                 'Avg Loss: {:.4f} CE Loss: {:.4f} ' \
                                 'Tuple Loss: {:.4f} Batch Accuracy: {:.4f}%'.format(epoch,
                                                                                     batch_idx * args.batch_size,
                                                                                     len(train_loader.dataset),
                                                                                     100. * batch_idx / len(train_loader),
                                                                                     total_loss / (batch_idx + 1),
                                                                                     ce_losses.avg,
                                                                                     tuple_losses.avg,
                                                                                     100. * minibatch_acc))

    # options for vox1
    check_path = pathlib.Path('{}/checkpoint_{}.pth'.format(args.check_path, epoch))
    torch.save({'epoch': epoch,
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict()},
               # 'criterion': criterion.state_dict()
               str(check_path))

    print(
        '\33[91m LSTM Tuple Train Accuracy:{:.4f}%. Avg loss is {:.4f}.\n\33[0m'.format(100 * correct / total_datasize,
                                                                                        total_loss / len(train_loader)))
    writer.add_scalar('Train/Accuracy', 100. * correct / total_datasize, epoch)
    writer.add_scalar('Train/Loss', total_loss / len(train_loader), epoch)


def test(valid_loader, test_loader, model, epoch):
    # switch to evaluate mode
    model.eval()

    valid_pbar = tqdm(enumerate(valid_loader))
    softmax = nn.Softmax(dim=1)

    correct = 0.
    total_datasize = 0.
    for batch_idx, (data, label) in valid_pbar:

        if len(data) != args.batch_size * args.tuple_size:
            continue

        if args.cuda:
            data = data.float().squeeze().cuda()
            label = label.cuda()

        data, label = Variable(data), Variable(label)
        feats, classfier = model(data)

        predicted_one_labels = softmax(classfier)
        predicted_one_labels = torch.max(predicted_one_labels, dim=1)[1]
        batch_correct = (predicted_one_labels.cuda() == label.cuda()).sum().item()
        minibatch_acc = float(batch_correct / len(predicted_one_labels))
        correct += batch_correct
        total_datasize += len(predicted_one_labels)

        if batch_idx % args.log_interval == 0:
            valid_pbar.set_description(
                'Valid Epoch: {:2d} [{:8d}/{:8d} ({:3.0f}%)] Batch Accuracy: {:.4f}%'.format(
                    epoch,
                    batch_idx * len(data),
                    len(valid_loader.dataset),
                    100. * batch_idx / len(valid_loader),
                    100. * minibatch_acc
                ))

    valid_accuracy = 100. * correct / total_datasize
    writer.add_scalar('Test/Valid_Accuracy', valid_accuracy, epoch)

    labels, distances = [], []
    pbar = tqdm(enumerate(test_loader))
    for batch_idx, (a, p, label) in pbar:
        if len(a) != int(args.batch_size * args.tuple_size / args.test_input_per_file):
            continue
        vec_shape = a.shape
        # pdb.set_trace()
        data_a = a.reshape(vec_shape[0] * vec_shape[1], vec_shape[2], vec_shape[3])
        data_p = p.reshape(vec_shape[0] * vec_shape[1], vec_shape[2], vec_shape[3])

        if args.cuda:
            data_a, data_p = data_a.float().cuda(), data_p.float().cuda()
        data_a, data_p, label = Variable(data_a), Variable(data_p), Variable(label)

        # compute output
        out_a, _ = model(data_a)
        out_p, _ = model(data_p)

        dists_a = l2_dist.forward(out_a, out_p)
        dists_a = dists_a.data.cpu().numpy()
        dists_a = dists_a.reshape(vec_shape[0], vec_shape[1]).mean(axis=1)
        distances.append(dists_a)

        labels.append(label.data.cpu().numpy())

        if batch_idx % args.log_interval == 0:
            pbar.set_description('Test Epoch: {} [{}/{} ({:.0f}%)]'.format(
                epoch, batch_idx * len(data_a) / args.test_input_per_file, len(test_loader.dataset),
                       100. * batch_idx / len(test_loader)))

    labels = np.array([sublabel for label in labels for sublabel in label])
    distances = np.array([subdist for dist in distances for subdist in dist])
    eer, eer_threshold, accuracy = evaluate_kaldi_eer(distances, labels, cos=args.cos_sim, re_thre=True)
    writer.add_scalar('Test/EER', 100. * eer, epoch)

    print('\33[91mERR: {:.8f}. Threshold: {:.8f}. Valid Accuracy is {:.4f}%.\33[0m\n'.format(100. * eer, eer_threshold,
                                                                                             valid_accuracy))


if __name__ == '__main__':
    main()
