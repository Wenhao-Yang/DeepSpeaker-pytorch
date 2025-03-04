#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: train_egs_dist.py
@Time: 2022/4/20 16:21
@Overview:
"""
from __future__ import print_function
from Light.dataset import Sampler_Loaders, SubScriptDatasets
from Light.model import SpeakerLoss
from Process_Data.audio_processing import AdaptiveBandPass
from TrainAndTest.train_egs.train_egs import select_samples
import torch._utils

import argparse
import hashlib
# import signal
# import yaml
import os
# import os.path as osp
# import pdb
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
# import torchvision.transforms as transforms
from hyperpyyaml import load_hyperpyyaml
from kaldi_io import read_vec_flt
from tensorboardX import SummaryWriter
from torch.autograd import Variable
from torch.nn.parallel import DistributedDataParallel
# from torch.optim import lr_scheduler
from tqdm import tqdm
import torch.distributed as dist

from Define_Model.Optimizer import EarlyStopping
from Process_Data.Datasets.KaldiDataset import ScriptVerifyDataset
import Process_Data.constants as C
from Define_Model.model import create_classifier,  create_model
from Define_Model.Optimizer import create_optimizer, create_scheduler
from TrainAndTest.common_func import load_checkpoint, on_main, resume_checkpoint, verification_test, verification_extract, args_parse, args_model

from Define_Model.model import save_model_args
from logger import NewLogger
# import pytorch_lightning as pl

warnings.filterwarnings("ignore")

try:
    torch._utils._rebuild_tensor_v2
except AttributeError:
    def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks):
        tensor = torch._utils._rebuild_tensor(
            storage, storage_offset, size, stride)
        tensor.requires_grad = requires_grad
        tensor._backward_hooks = backward_hooks
        return tensor
    torch._utils._rebuild_tensor_v2 = _rebuild_tensor_v2

# Training settings
# args = args_parse('PyTorch Speaker Recognition: Classification')
# Set the device to use by setting CUDA_VISIBLE_DEVICES env variable in
# order to prevent any memory allocation on unused GPUs
# os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id
# os.environ['MASTER_ADDR'] = '127.0.0.1'
# os.environ['MASTER_PORT'] = '29555'

# args.cuda = not args.no_cuda and torch.cuda.is_available()
# setting seeds
# pl.seed_everything(args.seed)


def all_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        cudnn.benchmark = True

def test_results(best_res):
    best_str  = 'EER(%):       {:>7.3f}  '.format(best_res['EER'])
    best_str += 'Threshold: {:>7.4f}  '.format(best_res['Threshold'])
    best_str += 'MinDcf-0.01:  {:.4f}  '.format(best_res['MinDCF_01'])
    best_str += 'MinDcf-0.001: {:.4f}  '.format(best_res['MinDCF_001'])
    best_str += 'Mix2,3: {:.4f}, {:.4f}'.format(best_res['mix2'], best_res['mix3'])
        
    print(best_str)
    
    return best_str


def save_checkpoint(model, optimizer, scheduler,
                    check_path, epoch):
    model.eval()
    
    this_check_path = '{}/checkpoint_{}.pth'.format(
        check_path, epoch)
    model_state_dict = model.module.state_dict() \
        if isinstance(model, DistributedDataParallel) else model.state_dict()
        
    torch.save({'epoch': epoch, 'state_dict': model_state_dict},
                this_check_path)

    this_optim_path = '{}/optim_{}.pth'.format(
        check_path, epoch)
    torch.save({'epoch': epoch,
                'scheduler': scheduler.state_dict(),
                'optimizer': optimizer.state_dict(),
                }, this_optim_path)


def check_earlystop_break(early_stopping_scheduler,
                    start, end, epoch, check_path, valid_test_result):
    check_stop = torch.tensor(
        int(early_stopping_scheduler.early_stop)).cuda()
    dist.all_reduce(check_stop, op=dist.ReduceOp.SUM)
    
    top_k = early_stopping_scheduler.top_k() if on_main() else []
    
    if check_stop or epoch == end - 1:
        end = epoch
        if on_main():
            
            print('Best steps model : ', top_k)
            best_step = early_stopping_scheduler.best_epoch
            
            if best_step % early_stopping_scheduler.train_lengths == 0:
                best_epoch = int(best_step / early_stopping_scheduler.train_lengths)
            else:
                best_epoch = '{:.4f}'.format(best_step / early_stopping_scheduler.train_lengths)
                
            best_res = valid_test_result[best_epoch]
            best_str = test_results(best_res=best_res)
            
            with open(os.path.join(check_path,
                                   'result.%s.txt' % time.strftime("%Y.%m.%d", time.localtime())), 'a+') as f:
                f.write(best_str + '\n')

            try:
                shutil.copy('{}/checkpoint_{}.pth'.format(check_path, best_epoch),
                            '{}/best.pth'.format(check_path))
            except Exception as e:
                print(e)
        return True
    
    return False

def train(train_loader, model, optimizer, epoch, scheduler, config_args, writer):
    # switch to train mode
    model.train()

    correct = 0.
    total_datasize = 0.
    total_loss = 0.
    orth_err = 0
    total_other_loss = 0.
    loss_nan = 0

    pbar = tqdm(enumerate(train_loader), total=len(train_loader), leave=True, ncols=150) if torch.distributed.get_rank(
    ) == 0 else enumerate(train_loader)

    output_softmax = nn.Softmax(dim=1)
    return_domain = True if 'domain' in config_args and config_args['domain'] == True else False
    return_idx = False if 'return_idx' not in config_args else config_args['return_idx']

    # lambda_ = (epoch / config_args['epochs']) ** 2

    if 'augment_pipeline' in config_args:
        num_pipes = config_args['num_pipes'] if 'num_pipes' in config_args else 1
        augment_pipeline = []
        for _, augment in enumerate(config_args['augment_pipeline']):
            if isinstance(augment, AdaptiveBandPass):
                augment_pipeline.append(augment)
            else:
                augment_pipeline.append(augment.cuda())

        # augment pipeline reverse
        if 'augment_prob' in config_args and isinstance(config_args['augment_prob'], list):
            p = np.array(config_args['augment_prob'])
            rp = 1/p
            rp /= rp.sum()
            min_score, max_score = 0.1, 20
            max_diff = max_score - min_score

            augp_a = (rp - p) / max_diff
            augp_b = p - augp_a * min_score

    # pdb.set_trace()
    for batch_idx, data_cols in pbar:

        if 'sample_score' in config_args and 'sample_ratio' in config_args:
            data, label, scores = data_cols
            batch_weight = None
        elif return_idx:
            data, label, batch_idxs = data_cols
            batch_weight = None
        elif not return_domain:
            data, label = data_cols
            if 'train_second_dir' in config_args:
                repeats = data.shape[-2]
                
                label = label.view((-1,1)).repeat(1, repeats).reshape(-1)
                # print(data.shape, label.shape)
                if data.shape[-2] > 1:
                    data = data.reshape(-1, 1, 1, data.shape[-1])
            
            batch_weight = None
        else:
            data, label, domain_label = data_cols
            domain_weight = torch.Tensor(C.DOMAIN_WEIGHT).cuda()
            domain_weight = torch.exp(6*(-domain_weight+0.75))
            domain_weight /= domain_weight.min()

            batch_weight = domain_weight[domain_label]
            model.module.loss.xe_criterion.ce.reduction = 'none'

        # print(data.shape)
        # pdb.set_trace()
        if 'augment_pipeline' in config_args:
            with torch.no_grad():
                wavs_aug_tot = []
                labels_aug_tot = []
                wavs_aug_tot.append(data.cuda()) # data_shape [batch, 1,1,time]
                labels_aug_tot.append(label.cuda())

                wavs = data.squeeze().cuda()
                wav_label = label.squeeze().cuda()

                # augment = np.random.choice(augment_pipeline)
                # for count, augment in enumerate(augment_pipeline):
                if 'sample_score' in config_args and 'sample_ratio' in config_args:
                    if config_args['sample_ratio'] < 1:
                        sample_ratio = int(config_args['sample_ratio'] * len(wavs))
                        # plain sum
                        
                        if 'batch_sample' not in config_args or config_args['batch_sample'] == 'norm':
                            scores = scores/scores.sum()
                            score_idx = np.random.choice(len(wavs), sample_ratio,
                                                            p=scores.squeeze().numpy(), replace=False)
                        elif config_args['batch_sample'] == 'norm_mean':
                            if 'score_mean_ratio' in config_args:
                                scores -= scores.mean() * config_args['score_mean_ratio']
                            else:
                                scores -= scores.mean()
                                
                            scores = scores.abs()
                            scores = scores/scores.sum()
                            score_idx = np.random.choice(len(wavs), sample_ratio,
                                                            p=scores.squeeze().numpy(), replace=False)
                        elif config_args['batch_sample'] == 'max':
                            score_idx = np.argsort(scores)[0][-sample_ratio:]
                        elif config_args['batch_sample'] == 'soft':
                            scores = scores.squeeze().unsqueeze(0)
                            scores = output_softmax(scores/scores.mean()) #overflow
                            score_idx = np.random.choice(len(wavs), sample_ratio,
                                                        p=scores.squeeze().numpy(), replace=False)
                        elif config_args['batch_sample'] == 'rand':
                            score_idx = np.random.choice(len(wavs), sample_ratio, replace=False)

                        if 'repeat_batch' in config_args:
                            # repeat sampled samples to make batch_size equal 
                            while len(score_idx) < len(wavs):
                                score_idx = np.concatenate((score_idx, score_idx))
                            score_idx = score_idx[:len(wavs)]

                        scores = scores[score_idx]
                        wavs = wavs[score_idx]
                        wav_label = wav_label[score_idx]

                if 'augment_prob' not in config_args:
                    if num_pipes <= len(augment_pipeline):
                        augs_idx = np.random.choice(len(augment_pipeline), size=num_pipes, replace=False)
                    else:
                        augs_idx = np.random.choice(len(augment_pipeline), size=num_pipes-len(augment_pipeline), replace=False)
                        augs_idx = np.concatenate([augs_idx, np.arange(len(augment_pipeline))])

                    sample_idxs = [np.arange(len(wavs))] * len(augs_idx)

                elif isinstance(config_args['augment_prob'], list) and 'sample_score' in config_args:
                    augs_idx = []
                    for s in scores:
                        this_p = augp_a * float(s) + augp_b
                        this_p /= this_p.sum()
                        augs_idx.append(np.random.choice(len(augment_pipeline), size=num_pipes, 
                                                    p=this_p, replace=False))

                    # max_id = np.array([[i, np.sum([i==j for j in augs_idx])] for i in range(len(augment_pipeline))])
                    # augs_idx = max_id[:, 0][np.argsort(max_id[:, 1])[-num_pipes:]]
                    augs_idx = np.array(augs_idx)
                    sample_idxs = [np.where(np.sum(augs_idx == i, axis=1) >= 1)[0] for i in range(len(augment_pipeline))]
                    augs_idx = [i for i in range(len(augment_pipeline))]

                elif isinstance(config_args['augment_prob'], list):
                    augs_idx = []
                    this_p = np.array(config_args['augment_prob'])
                    this_p /= this_p.sum()

                    for i in range(len(wavs)):
                        augs_idx.append(np.random.choice(len(augment_pipeline), size=num_pipes, 
                                                    p=this_p, replace=False))

                    augs_idx = np.array(augs_idx)
                    sample_idxs = [np.where(np.sum(augs_idx == i, axis=1) >= 1)[0] for i in range(len(augment_pipeline))]
                    augs_idx = [i for i in range(len(augment_pipeline))]
                else: 
                    this_lr = optimizer.param_groups[0]['lr']
                    augs_idx = config_args['augment_prob'](ratio=this_lr)
                    sample_idxs = [np.arange(len(data))] * len(augs_idx)

                # augs_idx = set(augs_idx)
                # other_idx = set(np.arange(len(augment_pipeline))) - augs_idx
                augs = [augment_pipeline[i] for i in augs_idx]
                # other_augments = [augment_pipeline[i] for i in other_idx]
            
                # p = p / p.sum()
                for data_idx, augment in zip(sample_idxs, augs):
                    # Apply augment
                    # print(data_idx)
                    wavs_aug = augment(wavs[data_idx], torch.tensor([1.0]*len(wavs[[data_idx]])).cuda())
                    # Managing speed change
                    if wavs_aug.shape[1] > wavs[data_idx].shape[1]:
                        wavs_aug = wavs_aug[:, 0 : wavs[data_idx].shape[1]]
                    else:
                        zero_sig = torch.zeros_like(wavs[data_idx])
                        zero_sig[:, 0 : wavs_aug.shape[1]] = wavs_aug
                        wavs_aug = zero_sig

                    if 'concat_augment' in config_args and config_args['concat_augment']:
                        wavs_aug_tot.append(wavs_aug.unsqueeze(1).unsqueeze(1))
                        labels_aug_tot.append(wav_label[data_idx])
                    else:
                        wavs = wavs_aug
                        wavs_aug_tot[0] = wavs_aug.unsqueeze(1).unsqueeze(1)
                        labels_aug_tot[0] = wav_label[data_idx]

                # if 'rest_prob' in config_args:
                #     for aug_i in range(len(wavs_aug_tot)-1):
                #         if np.random.uniform(0,1) < config_args['rest_prob']:
                #             augment = np.random.choice(other_augments)
                #             wavs_aug = augment(wavs_aug_tot[aug_i].squeeze().cuda(), torch.tensor([1.0]*len(wavs)).cuda())
                #             if wavs_aug.shape[1] > wavs.shape[1]:
                #                 wavs_aug = wavs_aug[:, 0 : wavs.shape[1]]
                #             else:
                #                 zero_sig = torch.zeros_like(wavs)
                #                 zero_sig[:, 0 : wavs_aug.shape[1]] = wavs_aug
                #                 wavs_aug = zero_sig
                #             wavs_aug_tot[aug_i] = wavs_aug.unsqueeze(1).unsqueeze(1)
            
                data = torch.cat(wavs_aug_tot, dim=0)
                # if 'sample_score' in config_args and 'sample_ratio' in config_args:
                #     n_augment = len(wavs_aug_tot)-1
                #     new_label = [label]
                #     new_label.extend([label[score_idx]] * n_augment)
                # else:
                #     n_augment = len(wavs_aug_tot)
                #     new_label = [label] * n_augment
                label = torch.cat(labels_aug_tot)
                # print(len(labels_aug_tot), wavs.shape)
                # print(label)
                
                # print(labels_aug_tot)                
                if 'train_second_dir' in config_args:
                    data_shape = data.shape
                    data = data.reshape(2, -1, 1, wavs.shape[-1]).transpose(0,1)
                    data = data.reshape(data_shape)
                    label = label.reshape(2, -1).transpose(0,1).reshape(-1)
                    
                    if 'domain_mix' in config_args and config_args['domain_mix']:
                        label = torch.cat([label, label.reshape(2, -1)[0]])
                    # print(data)
                    # print(label)
                
        if torch.cuda.is_available():
            label = label.cuda()
            data  = data.cuda()

        data, label = Variable(data), Variable(label)
        classfier, feats = model(data)

        loss, other_loss = model.module.loss((classfier, feats), label,
                                             batch_weight=batch_weight, epoch=epoch, other=True)
        
        if np.isnan(loss.item()):
            optimizer.zero_grad()  # reset gradient
            torch.cuda.empty_cache()
            loss_nan += 1
            if loss_nan  > 100:
                raise ValueError('Loss value is NaN!')
            else:
                if torch.distributed.get_rank() == 0:
                    print('==> Loss value is NaN! for {} step'.format(loss_nan))
                continue

        predicted_labels = output_softmax(classfier.clone())
        predicted_one_labels = torch.max(predicted_labels, dim=1)[1]

        minibatch_correct = float(
            (predicted_one_labels.cpu() == label.cpu()).sum().item())
        minibatch_acc = minibatch_correct / len(predicted_one_labels)

        if return_idx:
            # return_idx.append((predicted_one_labels.cpu(), label.cpu()))
            config_args['forgetting_events'].after_loss(predicted_one_labels, loss, label, batch_idxs, epoch)

        correct += minibatch_correct

        # if 'augment_prob' in config_args:
        #     config_args['augment_prob'].update(1/(float(loss.item())+1) * 5 + (minibatch_acc - correct/(total_datasize+1))*5)
        total_datasize += len(predicted_one_labels)
        # print(loss.shape)
        total_loss += float(loss.item())
        total_other_loss += other_loss
        # if isinstance(augment_pipeline[0], AdaptiveBandPass):
        #     augment_pipeline[0].update(1/(float(loss.item())+1))

        if torch.distributed.get_rank() == 0:
            writer.add_scalar('Train/All_Loss', float(loss.item()),
                              int((epoch - 1) * len(train_loader) + batch_idx + 1))

        # compute gradient and update weights
        loss.backward()

        if 'grad_clip' in config_args and config_args['grad_clip'] > 0:
            this_lr = config_args['lr']
            for param_group in optimizer.param_groups:
                this_lr = min(param_group['lr'], this_lr)
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), config_args['grad_clip'])

        if ((batch_idx + 1) % config_args['accu_steps']) == 0:
            # optimizer the net
            optimizer.step()  # update parameters of net
            optimizer.zero_grad()  # reset gradient

            if config_args['model'] == 'FTDNN' and ((batch_idx + 1) % 4) == 0:
                if isinstance(model, DistributedDataParallel):
                    # The key method to constrain the first two convolutions, perform after every SGD step
                    model.module.step_ftdnn_layers()
                    orth_err += model.module.get_orth_errors()
                else:
                    # The key method to constrain the first two convolutions, perform after every SGD step
                    model.step_ftdnn_layers()
                    orth_err += model.get_orth_errors()

        if config_args['loss_ratio'] != 0:
            if config_args['loss_type'] in ['center', 'mulcenter', 'gaussian', 'coscenter']:
                for param in model.module.loss.xe_criterion.parameters():
                    param.grad.data *= (1. / config_args['loss_ratio'])

        # optimizer.step()
        if config_args['scheduler'] == 'cyclic':
            scheduler.step()

        # if torch.distributed.get_rank() == 0:
        if torch.distributed.get_rank() == 0 and (batch_idx + 1) % config_args['log_interval'] == 0:
            epoch_str = 'Train Epoch {} '.format(epoch)

            if len(config_args['random_chunk']) == 2 and config_args['random_chunk'][0] <= \
                    config_args['random_chunk'][
                        1]:
                batch_length = data.shape[-1] if config_args['feat_format'] == 'wav' and 'trans_fbank' not in config_args else data.shape[-2]

            pbar.set_description(epoch_str)
            pbar.set_postfix(batch_length=batch_length, accuracy='{:>6.2f}%'.format(
                100. * minibatch_acc), average_loss='{:.4f}'.format(total_loss / (batch_idx + 1)))

        # if (batch_idx + 1) == 20:
        #     break

    this_epoch_str = 'Epoch {:>2d}: \33[91mTrain Accuracy: {:.6f}%, Avg loss: {:6f}'.format(epoch, 100 * float(
        correct) / total_datasize, total_loss / len(train_loader))

    if total_other_loss != 0:
        this_epoch_str += ' {} Loss: {:6f}'.format(
            config_args['loss_type'], total_other_loss / len(train_loader))
        
    # if isinstance(augment_pipeline[0], AdaptiveBandPass):
    #     this_epoch_str += ' Adaptive probbility: {}'.format(augment_pipeline[0].p())
    # if 'augment_prob' in config_args and not isinstance(config_args['augment_prob'], list):
    #     this_epoch_str += ' Aug probbility: {}'.format(config_args['augment_prob'].p)

    this_epoch_str += '.\33[0m'

    if torch.distributed.get_rank() == 0:
        print(this_epoch_str)
        writer.add_scalar('Train/Accuracy', correct / total_datasize, epoch)
        writer.add_scalar('Train/Loss', total_loss / len(train_loader), epoch)

    torch.cuda.empty_cache()


def valid_class(valid_loader, model, epoch, config_args, writer):
    # switch to evaluate mode
    model.eval()

    total_loss = 0.
    total_other_loss = 0.
    # ce_criterion, xe_criterion = ce
    softmax = nn.Softmax(dim=1)

    correct = 0.
    total_datasize = 0.
    # lambda_ = (epoch / config_args['epochs']) ** 2
    if 'valid_pipeline' in config_args:
        augment_pipeline = []
        for _, augment in enumerate(config_args['valid_pipeline']):
            augment_pipeline.append(augment.cuda())

    with torch.no_grad():
        for batch_idx, (data, label) in enumerate(valid_loader):
            if 'valid_augpipe' in config_args:
                with torch.no_grad():
                    wavs_aug_tot = []
                    wavs_aug_tot.append(data.cuda()) # data_shape [batch, 1,1,time]
                    wavs = data.squeeze().cuda()

                    for augment in augment_pipeline:
                        # Apply augment
                        wavs_aug = augment(wavs, torch.tensor([1.0]*len(wavs)).cuda())
                        # Managing speed change
                        if wavs_aug.shape[1] > wavs.shape[1]:
                            wavs_aug = wavs_aug[:, 0 : wavs.shape[1]]
                        else:
                            zero_sig = torch.zeros_like(wavs)
                            zero_sig[:, 0 : wavs_aug.shape[1]] = wavs_aug
                            wavs_aug = zero_sig

                        if 'concat_augment' in config_args and config_args['concat_augment']:
                            wavs_aug_tot.append(wavs_aug.unsqueeze(1).unsqueeze(1))
                        else:
                            wavs = wavs_aug
                            wavs_aug_tot[0] = wavs.unsqueeze(1).unsqueeze(1)
                    
                    data = torch.cat(wavs_aug_tot, dim=0)
                    n_augment = len(wavs_aug_tot)
                    label = torch.cat([label] * n_augment)

            if torch.cuda.is_available():
                data = data.cuda()
                label = label.cuda()

            # pdb.set_trace()
            classfier, feats = model(data)
            # print(classfier.shape, feats.shape, label.shape)
            loss, other_loss = model.module.loss((classfier, feats), label, other=True)

            total_loss += float(loss.item())
            total_other_loss += other_loss
            # pdb.set_trace()
            predicted_one_labels = softmax(classfier)
            predicted_one_labels = torch.max(predicted_one_labels, dim=1)[1]

            batch_correct = (predicted_one_labels.cuda() == label).sum().item()
            correct += batch_correct
            total_datasize += len(predicted_one_labels)

    total_batch = len(valid_loader)
    all_total_loss = [None for _ in range(torch.distributed.get_world_size())]
    all_correct = [None for _ in range(torch.distributed.get_world_size())]
    all_total_batch = [None for _ in range(torch.distributed.get_world_size())]
    all_total_datasize = [None for _ in range(
        torch.distributed.get_world_size())]
    all_other_loss = [None for _ in range(torch.distributed.get_world_size())]

    torch.distributed.all_gather_object(all_total_loss, total_loss)
    torch.distributed.all_gather_object(all_correct, correct)
    torch.distributed.all_gather_object(all_total_batch, total_batch)
    torch.distributed.all_gather_object(all_total_datasize, total_datasize)
    torch.distributed.all_gather_object(all_other_loss, total_other_loss)

    # torch.distributed.all_reduce()
    total_loss = np.sum(all_total_loss)
    correct = np.sum(all_correct)
    total_batch = np.sum(all_total_batch)
    total_datasize = np.sum(all_total_datasize)
    all_other_loss = np.sum(all_other_loss)

    valid_loss = total_loss / total_batch

    # if 'augment_prob' in config_args and not isinstance(config_args['augment_prob'], list):
    #     config_args['augment_prob'].update(20/(valid_loss+1))

    if 'valid_update' in config_args:
        config_args['aug_prob'].update(valid_loss)

    valid_accuracy = 100. * correct / total_datasize

    if torch.distributed.get_rank() == 0:
        writer.add_scalar('Train/Valid_Loss', valid_loss, epoch)
        writer.add_scalar('Train/Valid_Accuracy', valid_accuracy, epoch)
        torch.cuda.empty_cache()

        this_epoch_str = '          \33[91mValid Accuracy: {:.6f}%, Avg loss: {:.6f}'.format(
            valid_accuracy, valid_loss)

        if all_other_loss != 0:
            this_epoch_str += ' {} Loss: {:6f}'.format(
                config_args['loss_type'], all_other_loss / len(valid_loader))

        this_epoch_str += '.\33[0m'
        print(this_epoch_str)

    return valid_loss


def valid_test(train_extract_loader, model, epoch, xvector_dir, config_args, writer):
    # switch to evaluate mode
    model.eval()

    this_xvector_dir = "%s/train/tmp_xvectors" % (xvector_dir)
    if torch.distributed.get_rank() == 0 and os.path.exists(this_xvector_dir):
        shutil.rmtree(this_xvector_dir)
    verification_extract(train_extract_loader, model, this_xvector_dir,
                         epoch, test_input=config_args['test_input'])

    verify_dir = ScriptVerifyDataset(dir=config_args['train_test_dir'], trials_file=config_args['train_trials'],
                                     xvectors_dir=this_xvector_dir,
                                     loader=read_vec_flt)

    kwargs = {'num_workers': config_args['nj'], 'pin_memory': False}
    verify_loader = torch.utils.data.DataLoader(
        verify_dir, batch_size=128, shuffle=False, **kwargs)
    eer, eer_threshold, mindcf_01, mindcf_001 = verification_test(test_loader=verify_loader,
                                                                  dist_type=(
                                                                      'cos' if config_args['cos_sim'] else 'l2'),
                                                                  log_interval=config_args['log_interval'],
                                                                  xvector_dir=this_xvector_dir,
                                                                  epoch=epoch)
    mix3 = 100. * eer * mindcf_01 * mindcf_001
    mix2 = 100. * eer * mindcf_001
    mix8 = 100. * eer * mindcf_01

    if torch.distributed.get_rank() == 0:
        print('          \33[91mTrain EER: {:.4f}%, Threshold: {:.4f}, '
              'mindcf-0.01: {:.4f}, mindcf-0.001: {:.4f}, mix2,3: {:.4f}, {:.4f}. \33[0m'.format(100. * eer,
                                                                                                 eer_threshold,
                                                                                                 mindcf_01, mindcf_001, mix2, mix3))

        writer.add_scalar('Train/EER', 100. * eer, epoch)
        writer.add_scalar('Train/Threshold', eer_threshold, epoch)
        writer.add_scalar('Train/mindcf-0.01', mindcf_01, epoch)
        writer.add_scalar('Train/mindcf-0.001', mindcf_001, epoch)
        writer.add_scalar('Train/mix3', mix3, epoch)
        writer.add_scalar('Train/mix2', mix2, epoch)
        writer.add_scalar('Train/mix8', mix8, epoch)

    torch.cuda.empty_cache()

    return {'EER': 100. * eer, 'Threshold': eer_threshold, 'MinDCF_01': mindcf_01,
            'MinDCF_001': mindcf_001, 'mix3': mix3, 'mix2': mix2, 'mix8': mix8}


def main():
    parser = argparse.ArgumentParser(
        description='PyTorch ( Distributed ) Speaker Recognition: Classification')
    # parser.add_argument('--local_rank', default=-1, type=int,
    #                     help='node rank for distributed training')
    parser.add_argument('--train-config', default='', type=str,
                        help='node rank for distributed training')
    parser.add_argument('--seed', type=int, default=123456,
                        help='random seed (default: 0)')
    args = parser.parse_args()
    
    all_seed(args.seed)
    
    torch.distributed.init_process_group(backend='nccl')
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)
    torch.multiprocessing.set_sharing_strategy('file_system')

    # load train config file args.train_config
    with open(args.train_config, 'r') as f:
        config_args = load_hyperpyyaml(f)

    # Create logger & Define visulaize SummaryWriter instance
    check_path = config_args['check_path'] + '/' + str(args.seed)
    if torch.distributed.get_rank() == 0:
        if not os.path.exists(check_path):
            print('Making checkpath...', check_path)
            os.makedirs(check_path)

        new_yaml_name = check_path + '/model.%s.yaml' % time.strftime("%Y.%m.%d", time.localtime())
        shutil.copy(args.train_config, new_yaml_name)
        with open(new_yaml_name, 'a') as f:
            import socket
            f.write('\nhostname: {}'.format(socket.gethostname()))
            f.write('\noriginal_yaml: {}'.format(args.train_config))
        
        model_yaml = config_args['check_path'] + '/model.yaml'
        if not os.path.isfile(model_yaml):
            shutil.copy(args.train_config, model_yaml)
            with open(model_yaml, 'a') as f:
                import socket
                f.write('\nhostname: {}'.format(socket.gethostname()))
                f.write('\noriginal_yaml: {}'.format(args.train_config))
        else:
            with open(new_yaml_name, 'rb') as f1, open(model_yaml, 'rb') as f2:
                hash1 = hashlib.md5(f1.read()).hexdigest()
                hash2 = hashlib.md5(f2.read()).hexdigest()
                if hash1 != hash2:
                    print('{} is not the same as model.yaml'.format(os.path.basename(new_yaml_name)))
            
        writer = SummaryWriter(logdir=check_path, filename_suffix='SV')
        sys.stdout = NewLogger(
            os.path.join(check_path, 'log.%s.txt' % time.strftime("%Y.%m.%d", time.localtime())))
    else:
        writer = None
    # Dataset
    train_dir, valid_dir, train_extract_dir = SubScriptDatasets(config_args)
    train_loader, train_sampler, valid_loader, valid_sampler, train_extract_loader, train_extract_sampler = Sampler_Loaders(
        train_dir, valid_dir, train_extract_dir, config_args)

    torch.distributed.barrier()
    if torch.distributed.get_rank() == 0:
        print('\nCurrent time is \33[91m{}\33[0m.'.format(str(time.asctime())))
        print('Number of Speakers: {}.\n'.format(train_dir.num_spks))
        if train_dir.num_spks != config_args['num_classes']:
            print('Number of Speakers in training set is not equal to the asigned number.\n'.format(
                train_dir.num_spks))

        print('Testing with %s distance, ' %
              ('cos' if config_args['cos_sim'] else 'l2'))

    # model = create_model(config_args['model'], **model_kwargs)
    if 'embedding_model' in config_args:
        model = config_args['embedding_model']

    if 'classifier' in config_args:
        model.classifier = config_args['classifier']
    else:
        create_classifier(model, **config_args)

    start_epoch = 0
    check_path = config_args['check_path'] + '/' + str(args.seed)
    if 'finetune' not in config_args or not config_args['finetune']:
        this_check_path = '{}/checkpoint_{}_{}.pth'.format(check_path, start_epoch,
                                                           time.strftime('%Y_%b_%d_%H:%M', time.localtime()))
        if not os.path.exists(this_check_path):
            torch.save({'state_dict': model.state_dict()}, this_check_path)

    # Load checkpoint
    if 'fintune' in config_args:
        load_checkpoint(model, config_args)

    model.loss = SpeakerLoss(config_args)

    model_para = [{'params': model.parameters()}]
    if config_args['loss_type'] in ['center', 'variance', 'mulcenter', 'gaussian', 'coscenter', 'ring']:
        assert config_args['lr_ratio'] > 0
        model_para.append({'params': model.loss.xe_criterion.parameters(
        ), 'lr': config_args['lr'] * config_args['lr_ratio']})

    if 'multi_lr' in config_args:
        name2lr = config_args['multi_lr']
        lr2ps = {}
        for k in set(name2lr.keys()):
            if name2lr[k] != 0:
                lr2ps[name2lr[k]] = []
                
        lr_list = list(lr2ps.keys())
        lr_list.sort()

        default_lr = config_args['lr']
        model_para = []

        if 'second_wd' in config_args:
            init_wd = config_args['second_wd'] if config_args['second_wd'] > 0 else config_args['weight_decay']
            classifier_params = {'params': [], 'weight_decay': init_wd}

        for n,p in model.named_parameters():
            
            this_key = default_lr
            for key in name2lr:
                if key in n:
                    this_key = name2lr[key]
            if this_key == 0:
                continue

            if 'second_wd' in config_args and 'classifier' in n:
                classifier_params['params'].append(p)
                classifier_params['lr'] = this_key
            else:
                lr2ps[this_key].append(p)
            
        model_para.extend([{'params': lr2ps[lr], 'lr': lr} for lr in lr_list])
        if 'second_wd' in config_args and 'lr' in classifier_params:
            model_para.append(classifier_params)
            # if 'classifier' not in set(name2lr.keys()):
            lr_list.append(classifier_params['lr'])

        config_args['lr_list'] = lr_list
        if torch.distributed.get_rank() == 0:
            print('learning rate lst: ', lr_list)

    elif 'second_wd' in config_args and config_args['second_wd'] > 0:
        # if config_args['loss_type in ['asoft', 'amsoft']:
        classifier_params = list(map(id, model.classifier.parameters()))
        rest_params = filter(lambda p: id(
            p) not in classifier_params, model.parameters())

        init_lr = config_args['lr'] * \
            config_args['lr_ratio'] if config_args['lr_ratio'] > 0 else config_args['lr']
        init_wd = config_args['second_wd'] if config_args['second_wd'] > 0 else config_args['weight_decay']

        if torch.distributed.get_rank() == 0:
            print('Set the lr and weight_decay of classifier to %f and %f' %
              (init_lr, init_wd))
        model_para = [{'params': rest_params},
                      {'params': model.classifier.parameters(), 'lr': init_lr, 'weight_decay': init_wd}]

    if 'filter_wd' in config_args:
        # if config_args['filter'] in ['fDLR', 'fBLayer', 'fLLayer', 'fBPLayer', 'sinc2down']:
        filter_params = list(map(id, model.input_mask[0].parameters()))
        rest_params = filter(lambda p: id(
            p) not in filter_params, model_para[0]['params'])
        init_wd = config_args['filter_wd'] if 'filter_wd' in config_args else config_args['weight_decay']
        init_lr = config_args['lr'] * \
            config_args['lr_ratio'] if config_args['lr_ratio'] > 0 else config_args['lr']
        if torch.distributed.get_rank() == 0:
            print('Set the lr and weight_decay of filter layer to %f and %f' % (init_lr, init_wd))

        model_para[0]['params'] = rest_params
        model_para.append({'params': model.input_mask[0].parameters(), 'lr': init_lr,
                            'weight_decay': init_wd})

    opt_kwargs = {'lr': config_args['lr'], 'lr_decay': config_args['lr_decay'],
                  'weight_decay': config_args['weight_decay'],
                  'dampening': config_args['dampening'],
                  'momentum': config_args['momentum'],
                  'nesterov': config_args['nesterov']}

    optimizer = create_optimizer(
        model_para, config_args['optimizer'], **opt_kwargs)
    scheduler = create_scheduler(optimizer, config_args, train_loader)
    
    top_k_epoch = config_args['top_k_epoch'] if 'top_k_epoch' in config_args else 5
    if 'early_stopping' in config_args:
        early_stopping_scheduler = EarlyStopping(patience=config_args['early_patience'],
                                                min_delta=config_args['early_delta'],
                                                top_k_epoch=top_k_epoch)
    else:
        early_stopping_scheduler = None
    # Save model config txt
    if torch.distributed.get_rank() == 0:
        with open(os.path.join(check_path,
                               'model.%s.conf' % time.strftime("%Y.%m.%d", time.localtime())),
                  'w') as f:
            f.write('Model:     ' + str(model) + '\n')
            f.write('Optimizer: ' + str(optimizer) + '\n')
            f.write('Scheduler: ' + str(scheduler) + '\n')

    if 'resume' in config_args and 'fintune' not in config_args:
        resume_checkpoint(model, scheduler, optimizer, config_args)

    start = 1 + start_epoch
    if torch.distributed.get_rank() == 0:
        print('Start epoch is : ' + str(start))
    end = start + config_args['epochs']

    if torch.distributed.get_world_size() > 1:
        print("Continue with gpu: %s ..." % str(local_rank))
        # model = nn.SyncBatchNorm.convert_sync_batchnorm(model)
        model = DistributedDataParallel(
            model.cuda(), device_ids=[local_rank])
    else:
        model = model.cuda()

    try:
        print('Dropout is {}.'.format(model.dropout_p))
    except:
        pass

    xvector_dir = check_path.replace('checkpoint', 'xvector')
    start_time = time.time()

    all_lr, valid_test_result = [],{}

    try:
        for epoch in range(start, end):
            train_sampler.set_epoch(epoch)
            valid_sampler.set_epoch(epoch)
            train_extract_sampler.set_epoch(epoch)
            if 'linear_snr' in config_args:
                total_snr = np.linspace(config_args['snr_start'], config_args['snr_stop'],
                                       config_args['snr_num'])
                snr_idx = min(epoch-1, config_args['snr_num']-1)
                this_snr = total_snr[snr_idx]
                
                for aug in config_args['augment_pipeline']:
                    if hasattr(aug, 'add_noise'):
                        aug.add_noise.snr_high = this_snr
                snr_str = ' snr: {:.2f}'.format(this_snr)
            else:
                snr_str = ''

            # if torch.distributed.get_rank() == 0:
            this_lr = [ param_group['lr'] for param_group in optimizer.param_groups]
            all_lr.append(max(this_lr))
            if torch.distributed.get_rank() == 0:
                lr_string = '\33[1;34m \'{}\' learning rate: '.format(config_args['optimizer'])
                lr_string += " ".join(['{:.8f} '.format(i) for i in this_lr])
                lr_string += snr_str
                print('%s \33[0m' % lr_string)
                writer.add_scalar('Train/lr', this_lr[0], epoch)

            torch.distributed.barrier()

            train(train_loader, model, optimizer,
                  epoch, scheduler, config_args, writer)

            valid_loss = valid_class(
                valid_loader, model, epoch, config_args, writer)
            
            if early_stopping_scheduler != None or epoch in [start, end-1]:
                valid_test_dict = valid_test(
                    train_extract_loader, model, epoch, xvector_dir, config_args, writer)
            else:
                valid_test_dict = {}
            
            valid_test_dict['Valid_Loss'] = valid_loss
            valid_test_result[epoch] = valid_test_dict

            if torch.distributed.get_rank() == 0 and early_stopping_scheduler != None:
                early_stopping_scheduler(
                    valid_test_dict[config_args['early_meta']], epoch)

                if early_stopping_scheduler.best_epoch + early_stopping_scheduler.patience >= end and this_lr[0] <= 0.1 ** 3 * config_args['lr']:
                    if config_args['scheduler'] != 'cyclic' or ('cyclic_epoch' in config_args and epoch - start >= 6*config_args['cyclic_epoch']):
                        early_stopping_scheduler.early_stop = True

                if config_args['scheduler'] != 'cyclic' and this_lr[0] <= 0.1 ** 3 * config_args['lr']:
                    if len(all_lr) > 5:
                        if all_lr[-5] >= this_lr[0]:
                            early_stopping_scheduler.early_stop = True

                        if this_lr[0] <= 0.1 ** 3 * config_args['lr'] and all_lr[-5] > this_lr[0]:
                            early_stopping_scheduler.early_stop = False

                top_k = early_stopping_scheduler.top_k()
            else:
                current_results = [[valid_test_result[e]['Valid_Loss'], e] for e in valid_test_result]
                tops = torch.tensor(current_results)
                top_k = tops[torch.argsort(tops[:, 0])][:top_k_epoch, 1].long().tolist()

            if on_main() and (epoch % config_args['test_interval'] == 0 or epoch in config_args['milestones'] or epoch >= (
                    end - 4) or epoch in top_k):
                save_checkpoint(model, optimizer, scheduler,
                    check_path, epoch)
                
            if early_stopping_scheduler != None:
                break_training = check_earlystop_break(early_stopping_scheduler,
                    start, end, epoch, check_path, valid_test_result)
            else:
                break_training = False
                if epoch == end - 1:
                    best_str = test_results(best_res=valid_test_dict)
                    
                    with open(os.path.join(check_path,
                                        'result.%s.txt' % time.strftime("%Y.%m.%d", time.localtime())), 'a+') as f:
                        f.write(best_str + '\n')



            if break_training:
                break

            if config_args['scheduler'] == 'rop':
                scheduler.step(valid_loss)
            elif config_args['scheduler'] == 'cyclic':
                pass
            else:
                scheduler.step()

            if torch.distributed.get_rank() == 0 and epoch == start:
                print("INFO: Epoch time: {:.4f} minutes.".format(float(time.time() - start_time) / 60))

    except KeyboardInterrupt:
        end = epoch

    stop_time = time.time()
    t = float(stop_time - start_time)

    if not torch.distributed.is_initialized() or torch.distributed.get_rank() == 0:
        writer.close()
        print("Running %.4f minutes for each epoch.\n" %
              (t / 60 / (max(end - start, 1))))

    time.sleep(5)
    exit(0)

if __name__ == '__main__':
    main()
