#!/usr/bin/env python -u
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: test_accuracy.py
@Time: 19-8-6 下午1:29
@Overview: Train the resnet 34 with asoftmax.
"""
#from __future__ import print_function
import argparse
import pathlib
import pdb
import random
import time

from tensorboardX import SummaryWriter
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
from TrainAndTest.common_func import create_optimizer
from eval_metrics import evaluate_kaldi_eer
from Process_Data.kaldi_file_io import KaldiTrainDataset, KaldiTestDataset, KaldiValidDataset
from Define_Model.model import PairwiseDistance
from Process_Data.audio_processing import toMFB, totensor, truncatedinput, read_MFB, read_audio, \
    mk_MFB, concateinputfromMFB, PadCollate, varLengthFeat, to2tensor
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
parser = argparse.ArgumentParser(description='PyTorch Speaker Recognition')
# Model options

# options for vox1
parser.add_argument('--train-dir', type=str, default='/home/yangwenhao/projects/kaldi/egs/voxceleb/v4/data/vox1_fb24/train_no_sli',
                    help='path to dataset')
parser.add_argument('--test-dir', type=str, default='/home/yangwenhao/projects/kaldi/egs/voxceleb/v4/data/vox1_fb24/test_no_sli',
                    help='path to voxceleb1 test dataset')

parser.add_argument('--feat-dim', default=24, type=int, metavar='N',
                    help='acoustic feature dimension')
parser.add_argument('--check-path', default='Data/checkpoint/TDNN/XVextor/soft/kaldi',
                    help='folder to output model checkpoints')
parser.add_argument('--resume',
                    default='Data/checkpoint/TDNN/XVextor/soft/kaldi/checkpoint_10.pth',
                    type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')

parser.add_argument('--start-epoch', default=1, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('--epochs', type=int, default=16, metavar='E',
                    help='number of epochs to train (default: 10)')

# Training options
parser.add_argument('--cos-sim', action='store_true', default=True,
                    help='using Cosine similarity')

parser.add_argument('--batch-size', type=int, default=64, metavar='BS',
                    help='input batch size for training (default: 128)')
parser.add_argument('--test-batch-size', type=int, default=1, metavar='BST',
                    help='input batch size for testing (default: 64)')
parser.add_argument('--test-input-per-file', type=int, default=1, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--input-per-spks', type=int, default=200, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')

#parser.add_argument('--n-triplets', type=int, default=1000000, metavar='N',
parser.add_argument('--margin', type=float, default=3, metavar='MARGIN',
                    help='the margin value for the triplet loss function (default: 1.0')
parser.add_argument('--loss-ratio', type=float, default=2.0, metavar='LOSSRATIO',
                    help='the ratio softmax loss - triplet loss (default: 2.0')

parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                    help='learning rate (default: 0.125)')
parser.add_argument('--lr-decay', default=0, type=float, metavar='LRD',
                    help='learning rate decay ratio (default: 1e-4')
parser.add_argument('--weight-decay', default=1e-4, type=float,
                    metavar='W', help='weight decay (default: 0.0)')
parser.add_argument('--momentum', default=0.9, type=float,
                    metavar='W', help='momentum for sgd (default: 0.9)')
parser.add_argument('--dampening', default=0, type=float,
                    metavar='W', help='dampening for sgd (default: 0.0)')
parser.add_argument('--optimizer', default='sgd', type=str,
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
writer = SummaryWriter(args.check_path, filename_suffix='kaldi_fixlen')

kwargs = {'num_workers': 0, 'pin_memory': True} if args.cuda else {}
opt_kwargs = {'lr': args.lr,
              'lr_decay': args.lr_decay,
              'weight_decay': args.weight_decay,
              'dampening': args.dampening,
              'momentum': args.momentum}

l2_dist = nn.CosineSimilarity(dim=1, eps=1e-6) if args.cos_sim else PairwiseDistance(2)

if args.mfb:
    transform = transforms.Compose([
        concateinputfromMFB(num_frames=c.MINIMUIN_LENGTH),
        # varLengthFeat(),
        to2tensor()
    ])
else:
    transform = transforms.Compose([
                        truncatedinput(),
                        toMFB(),
                        totensor(),
                    ])

train_dir = KaldiTrainDataset(dir=args.train_dir, samples_per_speaker=args.input_per_spks, transform=transform)
test_dir = KaldiTestDataset(dir=args.test_dir, transform=transform)

indices = list(range(len(test_dir)))
random.shuffle(indices)
indices = indices[:4800]
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
    model = XVectorTDNN(len(train_dir.speakers), dropout_p=0.0)

    if args.cuda:
        model.cuda()

    optimizer = create_optimizer(model.parameters(), args.optimizer, **opt_kwargs)
    scheduler = MultiStepLR(optimizer, milestones=[11], gamma=0.1)
    # criterion = AngularSoftmax(in_feats=args.embedding_size,
    #                           num_classes=len(train_dir.classes))
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
    
    # pdb.set_trace()
    train_loader = torch.utils.data.DataLoader(train_dir, batch_size=args.batch_size,
                                               # collate_fn=PadCollate(dim=1),
                                               shuffle=True, **kwargs)
    valid_loader = torch.utils.data.DataLoader(valid_dir, batch_size=int(args.batch_size/2),
                                               # collate_fn=PadCollate(dim=1),
                                               shuffle=False, **kwargs)
    test_loader = torch.utils.data.DataLoader(test_part, batch_size=args.test_batch_size, shuffle=False, **kwargs)
    criterion = nn.CrossEntropyLoss().cuda()

    for epoch in range(start, end):
        # pdb.set_trace()
        compute_dropout(model, epoch, end)
        train(train_loader, model, optimizer, criterion, scheduler, epoch)
        test(test_loader, valid_loader, model, epoch)
        scheduler.step()
        # break

    writer.close()

def compute_dropout(model, epoch, end):

    init_dropout = 0.1
    final_dropout = 0.2

    if epoch < 0.2 * end:
        dropout_p = init_dropout
    elif epoch < 0.5 * end:
        dropout_p = final_dropout * (epoch - end*0.2) / end*0.3
    elif epoch < end:
        dropout_p = final_dropout * (epoch - end*0.5) / end*0.5

    print('\33\n[1;34m Current dropout is {}.'.format(dropout_p))

    model.set_global_dropout(dropout_p)


def train(train_loader, model, optimizer, criterion, scheduler, epoch):
    # switch to evaluate mode
    model.train()

    correct = 0.
    total_datasize = 0.
    total_loss = 0.
    output_softmax = nn.Softmax(dim=1)

    pbar = tqdm(enumerate(train_loader))
    for param_group in optimizer.param_groups:
        print('\'{}\' learning rate is {}.\33[0m'.format(args.optimizer, param_group['lr']))

    for batch_idx, (data, label) in pbar:

        if args.cuda:
            data = data.cuda()
            label = label.cuda()
        data, label = Variable(data), Variable(label)

        # pdb.set_trace()
        feats = model.pre_forward(data)
        classfier = model(feats)

        predicted_labels = output_softmax(classfier)
        predicted_one_labels = torch.max(predicted_labels, dim=1)[1]

        loss = criterion(classfier, label)

        try:
            batch_correct = float((predicted_one_labels == label).sum().item())
            minibatch_acc = batch_correct / len(predicted_one_labels)
        except:
            pdb.set_trace()

        correct += batch_correct
        total_datasize += len(predicted_one_labels)
        total_loss += loss.item()
        #pdb.set_trace()

        # compute gradient and update weights
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch_idx % args.log_interval == 0:
            pbar.set_description('Train Epoch: {:3d} [{:8d}/{:8d} ({:3.0f}%)] Avg Loss: {:.6f} Batch Accuracy: {:.4f}%'.format(
                epoch,
                batch_idx * len(data),
                len(train_loader.dataset),
                100. * batch_idx / len(train_loader),
                total_loss/(batch_idx+1),
                100. * minibatch_acc))

    # options for vox1
    check_path = pathlib.Path('{}/checkpoint_{}.pth'.format(args.check_path, epoch))
    if not check_path.parent.exists():
        os.makedirs(str(check_path.parent))

    torch.save({'epoch': epoch,
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'scheduler': scheduler.state_dict()},
                #'criterion': criterion.state_dict()
                str(check_path))

    print('\33[91m TDNN Train Accuracy:{:.4f}%. Avg loss is {:.4f}.\n\33[0m'.format(100 * correct / total_datasize, total_loss/len(train_loader)))
    writer.add_scalar('Train/Accuracy', 100. * correct / total_datasize, epoch)
    writer.add_scalar('Train/Loss', total_loss / len(train_loader), epoch)

def test(test_loader, valid_loader, model, epoch):
    # switch to evaluate mode
    model.eval()

    valid_pbar = tqdm(enumerate(valid_loader))
    softmax = nn.Softmax(dim=1)

    correct = 0.
    total_datasize = 0.
    for batch_idx, (data, label) in valid_pbar:
        data = Variable(data.cuda())
        # compute output
        # pdb.set_trace()
        out = model.pre_forward(data)
        cls = model(out)

        predicted_labels = cls
        true_labels = Variable(label.cuda())

        # pdb.set_trace()
        predicted_one_labels = softmax(predicted_labels)
        predicted_one_labels = torch.max(predicted_one_labels, dim=1)[1]

        batch_correct = (predicted_one_labels.cuda() == true_labels.cuda()).sum().item()
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
    for batch_idx, (data_a, data_p, label) in pbar:

        if args.cuda:
            data_a, data_p = data_a.cuda(), data_p.cuda()
        data_a, data_p, label = Variable(data_a), Variable(data_p), Variable(label)

        # compute output
        out_a = model.pre_forward(data_a)
        out_p = model.pre_forward(data_p)

        dists = l2_dist.forward(out_a, out_p)
        dists = dists.data.cpu().numpy()
        distances.append(dists)
        labels.append(label.data.cpu().numpy())

        if batch_idx % args.log_interval == 0:
            pbar.set_description('Test Epoch: {} [{}/{} ({:.0f}%)]'.format(
                epoch, batch_idx * len(data_a) / args.test_input_per_file, len(test_loader.dataset),
                100. * batch_idx / len(test_loader)))

    labels = np.array([sublabel for label in labels for sublabel in label])
    distances = np.array([subdist for dist in distances for subdist in dist])

    # err, accuracy= evaluate_eer(distances,labels)
    eer, eer_threshold, accuracy = evaluate_kaldi_eer(distances, labels, cos=args.cos_sim, re_thre=True)
    writer.add_scalar('Test/EER', 100. * eer, epoch)
    writer.add_scalar('Test/Threshold', eer_threshold, epoch)

    print('\33[91mFor {}_distance, Test ERR: {:.8f}. Threshold: {:.8f}. Valid Accuracy is {}.\n\33[0m'.format( \
        'cos' if args.cos_sim else 'l2', 100. * eer, eer_threshold, valid_accuracy))


if __name__ == '__main__':
    main()

