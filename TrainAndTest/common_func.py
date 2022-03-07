#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: common_func.py
@Time: 2019/12/16 6:36 PM
@Overview:
"""
import argparse
import os
import pdb

import kaldi_io
import kaldiio
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.nn.parallel.distributed import DistributedDataParallel
from torch.optim import lr_scheduler
from tqdm import tqdm
import Process_Data.constants as c

from Define_Model.CNN import AlexNet
from Define_Model.Optimizer import SAMSGD
from Define_Model.ResNet import LocalResNet, ResNet20, ThinResNet, ResNet, SimpleResNet, GradResNet, \
    TimeFreqResNet, MultiResNet
from Define_Model.Loss.SoftmaxLoss import AdditiveMarginLinear, SubMarginLinear
from Define_Model.TDNN.ARET import RET, RET_v2, RET_v3
from Define_Model.TDNN.DTDNN import DTDNN
from Define_Model.TDNN.ECAPA_TDNN import ECAPA_TDNN
from Define_Model.TDNN.ETDNN import ETDNN_v4, ETDNN, ETDNN_v5
from Define_Model.TDNN.FTDNN import FTDNN
from Define_Model.TDNN.TDNN import TDNN_v2, TDNN_v4, TDNN_v5, TDNN_v6, MixTDNN_v5
from Define_Model.demucs_feature import Demucs
from Eval.eval_metrics import evaluate_kaldi_eer, evaluate_kaldi_mindcf

import yaml


def create_optimizer(parameters, optimizer, **kwargs):
    # setup optimizer
    # parameters = filter(lambda p: p.requires_grad, parameters)
    if optimizer == 'sgd':
        opt = optim.SGD(parameters,
                        lr=kwargs['lr'],
                        momentum=kwargs['momentum'],
                        dampening=kwargs['dampening'],
                        weight_decay=kwargs['weight_decay'])

    elif optimizer == 'adam':
        opt = optim.Adam(parameters,
                               lr=kwargs['lr'],
                               weight_decay=kwargs['weight_decay'])

    elif optimizer == 'adagrad':
        opt = optim.Adagrad(parameters,
                            lr=kwargs['lr'],
                            lr_decay=kwargs['lr_decay'],
                            weight_decay=kwargs['weight_decay'])
    elif optimizer == 'RMSprop':
        opt = optim.RMSprop(parameters,
                            lr=kwargs['lr'],
                            momentum=kwargs['momentum'],
                            weight_decay=kwargs['weight_decay'])
    elif optimizer == 'samsgd':
        opt = SAMSGD(parameters,
                     lr=kwargs['lr'],
                     momentum=kwargs['momentum'],
                     dampening=kwargs['dampening'],
                     weight_decay=kwargs['weight_decay'])

    return opt


# ALSTM  ASiResNet34  ExResNet34  LoResNet  ResNet20  SiResNet34  SuResCNN10  TDNN

__factory = {
    'AlexNet': AlexNet,
    'LoResNet': LocalResNet,
    'ResNet20': ResNet20,
    'SiResNet34': SimpleResNet,
    'ThinResNet': ThinResNet,
    'MultiResNet': MultiResNet,
    'ResNet': ResNet,
    'DTDNN': DTDNN,
    'TDNN': TDNN_v2,
    'TDNN_v4': TDNN_v4,
    'TDNN_v5': TDNN_v5,
    'TDNN_v6': TDNN_v6,
    'MixTDNN_v5': MixTDNN_v5,
    'ETDNN': ETDNN,
    'ETDNN_v4': ETDNN_v4,
    'ETDNN_v5': ETDNN_v5,
    'FTDNN': FTDNN,
    'ECAPA': ECAPA_TDNN,
    'RET': RET,
    'RET_v2': RET_v2,
    'RET_v3': RET_v3,
    'GradResNet': GradResNet,
    'TimeFreqResNet': TimeFreqResNet,
    'Demucs': Demucs
}


def create_model(name, **kwargs):
    if name not in __factory.keys():
        raise KeyError("Unknown model: {}".format(name))

    model = __factory[name](**kwargs)

    if kwargs['loss_type'] in ['asoft', 'amsoft', 'arcsoft', 'arcdist', 'minarcsoft', 'minarcsoft2']:
        model.classifier = AdditiveMarginLinear(feat_dim=kwargs['embedding_size'],
                                                num_classes=kwargs['num_classes'])
    elif 'sub' in kwargs['loss_type']:
        model.classifier = SubMarginLinear(feat_dim=kwargs['embedding_size'], num_classes=kwargs['num_classes'],
                                           num_center=kwargs['num_center'], )

    return model


def create_scheduler(optimizer, args, train_dir):
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

    return scheduler


class AverageMeter(object):
    """Computes and stores the average and current value.
       Code imported from https://github.com/pytorch/examples/blob/master/imagenet/main.py#L247-L262
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


# def l2_alpha(C):
#     return np.log(0.99 * (C - 2) / (1 - 0.99))
def verification_extract(extract_loader, model, xvector_dir, epoch, test_input='fix',
                         ark_num=50000, gpu=True, mean_vector=True,
                         verbose=0, xvector=False):
    """

    :param extract_loader:
    :param model:
    :param xvector_dir:
    :param epoch:
    :param test_input:
    :param ark_num:
    :param gpu:
    :param verbose:
    :param xvector: extract xvectors in embedding-a layer
    :return:
    """
    model.eval()

    if not os.path.exists(xvector_dir):
        os.makedirs(xvector_dir)
    # pbar =
    pbar = tqdm(extract_loader, ncols=100) if verbose>0 else extract_loader

    uid2vectors = {}
    with torch.no_grad():
        if test_input == 'fix':
            data = torch.tensor([])
            num_seg_tensor = [0]
            uid_lst = []

            batch_size = 128 if torch.cuda.is_available() else 80
            for batch_idx, (a_data, a_uid) in enumerate(pbar):
                vec_shape = a_data.shape
                if vec_shape[1] != 1:
                    a_data = a_data.reshape(vec_shape[0] * vec_shape[1], 1, vec_shape[2], vec_shape[3])

                data = torch.cat((data, a_data), dim=0)
                num_seg_tensor.append(num_seg_tensor[-1] + len(a_data))
                uid_lst.append(a_uid[0])

                if data.shape[0] >= batch_size or batch_idx + 1 == len(extract_loader):
                    if data.shape[0] > (3 * batch_size):
                        i = 0
                        out = []
                        while i < data.shape[0]:
                            data_part = data[i:(i + batch_size)]
                            data_part = data_part.cuda() if next(model.parameters()).is_cuda else data_part
                            model_out = model.xvector(data_part) if xvector else model(data_part)
                            try:
                                _, out_part, _, _ = model_out
                            except:
                                _, out_part = model_out
                            out.append(out_part)
                            i += batch_size
                        out = torch.cat(out, dim=0)
                    else:

                        data = data.cuda() if next(model.parameters()).is_cuda else data
                        model_out = model.xvector(data) if xvector else model(data)
                        try:
                            _, out, _, _ = model_out
                        except:
                            _, out = model_out

                    out = out.data.cpu().float().numpy()
                    # print(out.shape)
                    if len(out.shape) == 3:
                        out = out.squeeze(0)

                    for i, uid in enumerate(uid_lst):
                        if mean_vector:
                            uid2vectors[uid] = out[num_seg_tensor[i]:num_seg_tensor[i + 1]].mean(axis=0)  # , uid[0])
                        else:
                            uid2vectors[uid] = out[num_seg_tensor[i]:num_seg_tensor[i + 1]]

                    data = torch.tensor([])
                    num_seg_tensor = [0]
                    uid_lst = []

        elif test_input == 'var':
            for batch_idx, (a_data, a_uid) in enumerate(pbar):
                vec_shape = a_data.shape

                if vec_shape[1] != 1:
                    a_data = a_data.reshape(vec_shape[0] * vec_shape[1], 1, vec_shape[2], vec_shape[3])

                a_data = a_data.cuda() if next(model.parameters()).is_cuda else a_data
                if vec_shape[2] > 10 * c.NUM_FRAMES_SPECT:
                    num_half = int(vec_shape[2] / 2)
                    half_a = a_data[:, :, :num_half, :]
                    half_b = a_data[:, :, -num_half:, :]
                    a_data = torch.cat((half_a, half_b), dim=0)

                try:
                    if xvector:
                        model_out = model.module.xvector(a_data) if isinstance(model,
                                                                               DistributedDataParallel) else model.xvector(
                            a_data)
                    else:
                        model_out = model(a_data)
                except Exception as e:
                    pdb.set_trace()
                    print('\ninput shape is ', a_data.shape)
                    raise e

                if isinstance(model_out, tuple):
                    if len(model_out) == 4:
                        _, out, _, _ = model_out
                        
                    elif len(model_out) == 2:
                        _, out = model_out

                else:
                    out = model_out

                if out.shape[0] != 1:
                    out = out.mean(dim=0, keepdim=True)

                out = out.data.cpu().float().numpy()
                # print(out.shape)

                if len(out.shape) == 3:
                    out = out.squeeze(0)

                if not (len(out.shape) == 2 and out.shape[0] == 1):
                    print(a_data.shape, a_uid, out.shape)
                    pdb.set_trace()

                uid2vectors[a_uid[0]] = out[0]

    uids = list(uid2vectors.keys())
    # print('There are %d vectors' % len(uids))
    scp_file = xvector_dir + '/xvectors.scp'
    ark_file = xvector_dir + '/xvectors.ark'
    # scp = open(scp_file, 'w')

    # write scp and ark file
    # pdb.set_trace()
    writer = kaldiio.WriteHelper('ark,scp:%s,%s' % (ark_file, scp_file))
    for uid in uids:
        writer(str(uid), uid2vectors[uid])

    # for set_id in range(int(np.ceil(len(uids) / ark_num))):
    #     ark_file = xvector_dir + '/xvector.{}.ark'.format(set_id)
    #     with open(ark_file, 'wb') as ark:
    #         ranges = np.arange(len(uids))[int(set_id * ark_num):int((set_id + 1) * ark_num)]
    #         for i in ranges:
    #             key = uids[i]
    #             vec = uid2vectors[key]
    #             len_vec = len(vec.tobytes())
    #             try:
    #                 kaldi_io.write_vec_flt(ark, vec, key=key)
    #             except Exception as e:
    #                 pdb.set_trace()
    #             # print(ark.tell())
    #             scp.write(str(uids[i]) + ' ' + str(ark_file) + ':' + str(ark.tell() - len_vec - 10) + '\n')
    # scp.close()
    # print('Saving %d xvectors to %s' % (len(uids), xvector_dir))
    torch.cuda.empty_cache()

def verification_test(test_loader, dist_type, log_interval, xvector_dir, epoch):
    # switch to evaluate mode
    labels, distances = [], []
    dist_fn = nn.CosineSimilarity(dim=1).cuda() if dist_type == 'cos' else nn.PairwiseDistance(2)

    # pbar = tqdm(enumerate(test_loader))
    with torch.no_grad():
        for batch_idx, (data_a, data_p, label) in enumerate(test_loader):
            out_a = torch.tensor(data_a).cuda()  # .view(-1, 4, embedding_size)
            out_p = torch.tensor(data_p).cuda()  # .view(-1, 4, embedding_size)
            dists = dist_fn.forward(out_a, out_p).cpu().numpy()

            distances.append(dists)
            labels.append(label.numpy())
            del out_a, out_p  # , ae, pe

        # if batch_idx % log_interval == 0:
        #     pbar.set_description('Verification Epoch {}: [{}/{} ({:.0f}%)]'.format(
        #         epoch, batch_idx * len(data_a), len(test_loader.dataset), 100. * batch_idx / len(test_loader)))

    labels = np.array([sublabel for label in labels for sublabel in label])
    distances = np.array([subdist for dist in distances for subdist in dist])
    # this_xvector_dir = "%s/epoch_%s" % (xvector_dir, epoch)
    with open('%s/scores' % xvector_dir, 'w') as f:
        for d, l in zip(distances, labels):
            f.write(str(d) + ' ' + str(l) + '\n')

    eer, eer_threshold, accuracy = evaluate_kaldi_eer(distances, labels,
                                                      cos=True if dist_type == 'cos' else False,
                                                      re_thre=True)
    mindcf_01, mindcf_001 = evaluate_kaldi_mindcf(distances, labels)

    return eer, eer_threshold, mindcf_01, mindcf_001


# https://github.com/clovaai/voxceleb_trainer
def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
        res.append(correct_k.mul_(100.0 / batch_size))

    return res


def correct_output(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    # batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
        res.append(correct_k)

    return res


def args_parse(description: str = 'PyTorch Speaker Recognition: Classification'):
    # Training settings
    parser = argparse.ArgumentParser(description=description)

    # Data options
    parser.add_argument('--train-dir', type=str, required=True, help='path to dataset')
    parser.add_argument('--train-test-dir', type=str, required=True, help='path to dataset')
    parser.add_argument('--valid-dir', type=str, required=True, help='path to dataset')
    parser.add_argument('--test-dir', type=str, required=True, help='path to voxceleb1 test dataset')
    parser.add_argument('--log-scale', action='store_true', default=False, help='log power spectogram')
    parser.add_argument('--exp', action='store_true', default=False, help='exp power spectogram')

    parser.add_argument('--trials', type=str, default='trials', help='path to voxceleb1 test dataset')
    parser.add_argument('--train-trials', type=str, default='trials', help='path to voxceleb1 test dataset')

    parser.add_argument('--sitw-dir', type=str, help='path to voxceleb1 test dataset')
    parser.add_argument('--var-input', action='store_true', default=True, help='need to make mfb file')
    parser.add_argument('--test-input', type=str, default='fix', choices=['var', 'fix'],
                        help='batchnorm with instance norm')
    parser.add_argument('--random-chunk', nargs='+', type=int, default=[], metavar='MINCHUNK')
    parser.add_argument('--chunk-size', type=int, default=300, metavar='CHUNK')

    parser.add_argument('--remove-vad', action='store_true', default=False, help='using Cosine similarity')
    parser.add_argument('--extract', action='store_true', default=True, help='need to make mfb file')
    parser.add_argument('--shuffle', action='store_false', default=True, help='need to shuffle egs')

    parser.add_argument('--nj', default=10, type=int, metavar='NJOB', help='num of job')
    parser.add_argument('--feat-format', type=str, default='kaldi', choices=['kaldi', 'npy', 'wav'],
                        help='number of jobs to make feats (default: 10)')

    parser.add_argument('--check-path', help='folder to output model checkpoints')
    parser.add_argument('--save-init', action='store_true', default=True, help='need to make mfb file')
    parser.add_argument('--resume', metavar='PATH', help='path to latest checkpoint (default: none)')

    parser.add_argument('--start-epoch', default=1, type=int, metavar='N',
                        help='manual epoch number (useful on restarts)')
    parser.add_argument('--epochs', type=int, default=20, metavar='E',
                        help='number of epochs to train (default: 10)')
    parser.add_argument('--scheduler', default='multi', type=str,
                        metavar='SCH', help='The optimizer to use (default: Adagrad)')
    parser.add_argument('--patience', default=3, type=int,
                        metavar='PAT', help='patience for scheduler (default: 4)')
    parser.add_argument('--gamma', default=0, type=float,
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
    parser.add_argument('--activation', type=str, default='relu', help='activation functions')
    parser.add_argument('--filter', type=str, default='None', help='replace batchnorm with instance norm')
    parser.add_argument('--init-weight', type=str, default='mel', help='replace batchnorm with instance norm')
    parser.add_argument('--power-weight', type=str, default='none', help='replace batchnorm with instance norm')
    parser.add_argument('--weight-p', default=0.1, type=float, help='replace batchnorm with instance norm')
    parser.add_argument('--scale', default=0.2, type=float, metavar='FEAT', help='acoustic feature dimension')

    parser.add_argument('--filter-fix', action='store_true', default=False, help='replace batchnorm with instance norm')

    parser.add_argument('--input-norm', type=str, default='Mean', help='batchnorm with instance norm')

    parser.add_argument('--mask-layer', type=str, default='None', help='time or freq masking layers')
    parser.add_argument('--mask-len', type=str, default='5,5', help='maximum length of time or freq masking layers')
    parser.add_argument('--block-type', type=str, default='basic', help='replace batchnorm with instance norm')
    parser.add_argument('--downsample', type=str, default='None', help='replace batchnorm with instance norm')

    parser.add_argument('--red-ratio', default=8, type=int, metavar='N', help='acoustic feature dimension')
    parser.add_argument('--relu-type', type=str, default='relu', help='replace batchnorm with instance norm')
    parser.add_argument('--transform', type=str, default="None", help='add a transform layer after embedding layer')

    parser.add_argument('--vad', action='store_true', default=False, help='vad layers')
    parser.add_argument('--inception', action='store_true', default=False, help='multi size conv layer')
    parser.add_argument('--inst-norm', action='store_true', default=False, help='batchnorm with instance norm')

    parser.add_argument('--encoder-type', type=str, default='None', help='path to voxceleb1 test dataset')
    parser.add_argument('--channels', default='64,128,256', type=str, metavar='CHA',
                        help='The channels of convs layers)')
    parser.add_argument('--first-2d', action='store_true', default=False,
                        help='replace first tdnn layer with conv2d layers')
    parser.add_argument('--dilation', default='1,1,1,1', type=str, metavar='CHA', help='The dilation of convs layers)')
    parser.add_argument('--feat-dim', default=64, type=int, metavar='N', help='acoustic feature dimension')
    parser.add_argument('--input-dim', default=257, type=int, metavar='N', help='acoustic feature dimension')
    parser.add_argument('--accu-steps', default=1, type=int, metavar='N',
                        help='manual epoch number (useful on restarts)')

    parser.add_argument('--alpha', default=12, type=float, metavar='FEAT', help='acoustic feature dimension')
    parser.add_argument('--ring', default=12, type=float, metavar='RING', help='acoustic feature dimension')

    parser.add_argument('--kernel-size', default='5,5', type=str, metavar='KE', help='kernel size of conv filters')
    parser.add_argument('--context', default='5,3,3,5', type=str, metavar='KE', help='kernel size of conv filters')

    parser.add_argument('--padding', default='', type=str, metavar='KE', help='padding size of conv filters')
    parser.add_argument('--stride', default='1', type=str, metavar='ST', help='stride size of conv filters')
    parser.add_argument('--fast', type=str, default='None', help='max pooling for fast')

    parser.add_argument('--cos-sim', action='store_true', default=False, help='using Cosine similarity')
    parser.add_argument('--avg-size', type=int, default=4, metavar='ES', help='Dimensionality of the embedding')
    parser.add_argument('--time-dim', default=1, type=int, metavar='FEAT', help='acoustic feature dimension')
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
    parser.add_argument('--dropout-p', type=float, default=0.0, metavar='BST',
                        help='input batch size for testing (default: 64)')

    # loss configure
    parser.add_argument('--loss-type', type=str, default='soft',
                        help='path to voxceleb1 test dataset')
    parser.add_argument('--num-center', type=int, default=2, help='the num of source classes')
    parser.add_argument('--source-cls', type=int, default=1951,
                        help='the num of source classes')
    parser.add_argument('--finetune', action='store_true', default=False,
                        help='using Cosine similarity')
    parser.add_argument('--lr-ratio', type=float, default=0.0, metavar='LOSSRATIO',
                        help='the ratio softmax loss - triplet loss (default: 2.0')

    parser.add_argument('--alpha-t', type=float, default=1.0, help='the ratio for LNCL')
    parser.add_argument('--lncl', action='store_true', default=False, help='Label Noise Correct Loss')

    parser.add_argument('--loss-ratio', type=float, default=0.1, metavar='LOSSRATIO',
                        help='the ratio softmax loss - triplet loss (default: 2.0')

    # args for additive margin-softmax
    parser.add_argument('--margin', type=float, default=0.3, metavar='MARGIN',
                        help='the margin value for the angualr softmax loss function (default: 3.0')
    parser.add_argument('--s', type=float, default=15, metavar='S',
                        help='the margin value for the angualr softmax loss function (default: 3.0')
    parser.add_argument('--stat-type', type=str, default='maxmargin',
                        help='path to voxceleb1 test dataset')

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
    parser.add_argument('--second-wd', default=0, type=float,
                        metavar='SWEI', help='weight decay (default: 0.0)')
    parser.add_argument('--filter-wd', default=0, type=float,
                        metavar='FWEI', help='weight decay (default: 0.0)')
    parser.add_argument('--momentum', default=0.9, type=float,
                        metavar='MOM', help='momentum for sgd (default: 0.9)')
    parser.add_argument('--dampening', default=0, type=float,
                        metavar='DAM', help='dampening for sgd (default: 0.0)')
    parser.add_argument('--optimizer', default='sgd', type=str,
                        metavar='OPT', help='The optimizer to use (default: Adagrad)')
    parser.add_argument('--grad-clip', default=0., type=float,
                        help='gradient clip threshold (default: 0)')
    # Device options
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='enables CUDA training')
    parser.add_argument('--gpu-id', default='0', type=str,
                        help='id(s) for CUDA_VISIBLE_DEVICES')
    parser.add_argument('--seed', type=int, default=123456, metavar='S',
                        help='random seed (default: 0)')
    parser.add_argument('--log-interval', type=int, default=10, metavar='LI',
                        help='how many batches to wait before logging training status')
    parser.add_argument('--test-interval', type=int, default=4, metavar='TI',
                        help='how many batches to wait before logging training status')

    parser.add_argument('--acoustic-feature', choices=['fbank', 'spectrogram', 'mfcc'], default='fbank',
                        help='choose the acoustic features type.')
    parser.add_argument('--makemfb', action='store_true', default=False,
                        help='need to make mfb file')
    parser.add_argument('--makespec', action='store_true', default=False,
                        help='need to make spectrograms file')

    if 'Knowledge' in description:
        parser.add_argument('--kd-type', type=str, default='vanilla', help='path to voxceleb1 test dataset')
        parser.add_argument('--distil-weight', type=float, default=0.5, help='path to voxceleb1 test dataset')
        parser.add_argument('--teacher-model-yaml', type=str, required=True, help='path to teacher model')
        parser.add_argument('--teacher-resume', type=str, required=True, help='path to teacher model')
        parser.add_argument('--label-dir', type=str, default='', help='path to teacher model')
        parser.add_argument('--temperature', type=float, default=20, help='path to voxceleb1 test dataset')
        parser.add_argument('--teacher-model', type=str, default='', help='path to voxceleb1 test dataset')

    args = parser.parse_args()

    return args


def args_model(args, train_dir):
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

    mask_len = [int(x) for x in args.mask_len.split(',')] if len(args.mask_len) > 1 else []

    model_kwargs = {'input_dim': args.input_dim, 'feat_dim': args.feat_dim, 'kernel_size': kernel_size,
                    'context': context, 'filter_fix': args.filter_fix, 'dilation': dilation,
                    'first_2d': args.first_2d, 'red_ratio': args.red_ratio, 'activation': args.activation,
                    'mask': args.mask_layer, 'mask_len': mask_len, 'block_type': args.block_type,
                    'filter': args.filter, 'exp': args.exp, 'inst_norm': args.inst_norm, 'input_norm': args.input_norm,
                    'stride': stride, 'fast': args.fast, 'avg_size': args.avg_size, 'time_dim': args.time_dim,
                    'padding': padding, 'encoder_type': args.encoder_type, 'vad': args.vad,
                    'transform': args.transform, 'embedding_size': args.embedding_size, 'ince': args.inception,
                    'resnet_size': args.resnet_size, 'num_classes': train_dir.num_spks, 'downsample': args.downsample,
                    'num_classes_b': train_dir.num_doms, 'init_weight': args.init_weight,
                    'power_weight': args.power_weight, 'scale': args.scale, 'weight_p': args.weight_p,
                    'channels': channels, 'alpha': args.alpha, 'dropout_p': args.dropout_p,
                    'loss_type': args.loss_type, 'm': args.m, 'margin': args.margin, 's': args.s,
                    'num_center': args.num_center,
                    'iteraion': 0, 'all_iteraion': args.all_iteraion}

    return model_kwargs


def argparse_adv(description: str = 'PyTorch Speaker Recognition'):
    parser = argparse.ArgumentParser(description=description)
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

    parser.add_argument('--accu-steps', default=1, type=int, metavar='N',
                        help='manual epoch number (useful on restarts)')

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
    parser.add_argument('--num-center', type=int, default=3, help='the num of source classes')
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

    return args


def save_model_args(model_dict, save_path):
    with open(save_path, 'w') as f:
        yamlText = yaml.dump(model_dict)
        f.write(yamlText)


def load_model_args(model_yaml):
    with open(model_yaml, 'r') as f:
        model_args = yaml.load(f, Loader=yaml.FullLoader)

    return model_args
