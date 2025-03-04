#!/usr/bin/env python
# encoding: utf-8
'''
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: VS Code
@File: del_insert.py
@Time: 2023/05/08 15:53
@Overview: 
'''
# from __future__ import print_function

import argparse
import json
import fcntl
import os
import pdb
import pickle
import random
import time
from collections import OrderedDict
from hyperpyyaml import load_hyperpyyaml

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
import pandas as pd
from Define_Model.FilterLayer import FreqMaskIndexLayer
import torchmetrics

from Define_Model.SoftmaxLoss import AngleLinear, AdditiveMarginLinear
# from Define_Model.model import PairwiseDistance
from Process_Data.Datasets.KaldiDataset import ScriptEvalDataset, ScriptTrainDataset, \
    ScriptTestDataset, ScriptValidDataset
from Process_Data.audio_processing import CAMNormInput, ConcateOrgInput, mvnormal, ConcateVarInput, read_WaveInt
from TrainAndTest.common_func import args_parse
#, create_model, load_model_args, args_model
from Define_Model.model import create_classifier, create_model, save_model_args, load_model_args
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
args = args_parse('PyTorch Speaker Recognition: Gradient')

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
l2_dist = nn.CosineSimilarity(dim=1, eps=1e-6) if args.cos_sim else nn.PairwiseDistance(p=2)

if args.test_input == 'var':
    transform = transforms.Compose([
        CAMNormInput(threshold=args.threshold, pro_type=args.pro_type, 
                     norm_cam=args.norm_cam, init_input=args.init_input,
                     scaled=args.cam_scaled),
        ConcateOrgInput(remove_vad=args.remove_vad),
    ])
elif args.test_input == 'fix':
    transform = transforms.Compose([
        CAMNormInput(threshold=args.threshold, pro_type=args.pro_type,
                     norm_cam=args.norm_cam, init_input=args.init_input,
                     scaled=args.cam_scaled),
        ConcateVarInput(remove_vad=args.remove_vad),
    ])

# file_loader = read_mat
# train_dir = ScriptTrainDataset(dir=args.train_dir, samples_per_speaker=args.input_per_spks,
#                                loader=file_loader, transform=transform, return_uid=True, verbose=0)
if args.cam in ['mask', 'igos']:
    grad_reverse = True
else:
    grad_reverse = False

valid_dir = ScriptEvalDataset(select_dir=args.select_input_dir, grad_reverse=grad_reverse,
                              valid_dir=args.eval_dir, transform=transform,
                              verbose=args.verbose)

def valid_eval(valid_loader, model, file_dir, set_name, config_args):
    # switch to evaluate mode
    model.eval()

    # label_pred = []
    pbar = tqdm() if args.verbose > 0 else enumerate(valid_loader)
    output_softmax = nn.Softmax(dim=1)
    correct = .0
    total = .0

    result_file_suffix = ''             # result.<init>.<norm>.<mask>
    result_file_suffix += '.' + args.init_input
    
    if args.pro_type != 'none':
        if args.norm_cam != 'none':
            result_file_suffix += '.' + args.norm_cam
            
        if args.cam_scaled != 'none':
            result_file_suffix += '.' + args.cam_scaled
        
    if args.test_mask:
        result_file_suffix += '.mask'

    result_file = file_dir + '/result{}.json'.format(result_file_suffix)

    # top_1_accuracy = torchmetrics.Accuracy(task="multiclass",
    #                                        num_classes=config_args['num_classes'],
    #                                        top_k=1)
    top_accuracy = torchmetrics.Accuracy(task="multiclass",
                                         num_classes=config_args['num_classes'],
                                         top_k=5)
    # accuracy(preds, target)
    preds, target = [], []
    with torch.no_grad():
        for batch_idx, (data, label) in pbar:
            logit, _ = model(data.cuda())

            if args.loss_type == 'asoft':
                classifed, _ = logit
            else:
                classifed = logit
            classifed = output_softmax(classifed)
            preds.append(classifed.cpu())
            target.append(label.cpu())

            # pdb.set_trace()
            total += 1
            predicted = torch.max(classifed, dim=1)[1]
            correct += (predicted.cpu() == label.cpu()).sum().item()

            if batch_idx % args.log_interval == 0 and args.verbose > 0:
                pbar.set_description('Eval: [{:8d} ({:3.0f}%)] '.format(
                    batch_idx + 1,
                    100. * batch_idx / len(valid_loader)))

        preds = torch.cat(preds, dim=0)
        target = torch.cat(target, dim=0)
        top_acc = float(top_accuracy(preds, target))*100

        if args.test_mask:
            mask_str = args.mask_sub.split(',')
            start = int(mask_str[0])
            end = int(mask_str[1])
            this_result = [start, end, correct/total*100, args.mask_type, top_acc]
        else:
            this_result = [args.pro_type, args.threshold, correct/total*100, top_acc]

        if not os.path.exists(result_file):
            results = [this_result]
            with open(result_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(results, f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        else:
            with open(result_file, 'r+') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                results = json.load(f)
                results.append(this_result)
                f.seek(0)
                json.dump(results, f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # label_pred.append(['accuracy', correct/total*100])
        # filename = file_dir + '/label_pred.%s.%.4f.json' % (args.pro_type, args.threshold)
        # df = pd.DataFrame(label_pred, columns=['label', 'predict'])
        # # df.to_csv(filename)
        # df.to_json(filename)

        # with open(filename, 'wb') as f:
        #     pickle.dump(label_pred, f)
        if args.pro_type == 'none' and args.test_mask:
            this_str = 'mask'
            conf_str = args.mask_sub 
        else:
            this_str = args.pro_type
            conf_str = '{:.4f}'.format(args.threshold)

        print(f'{this_str}_{args.init_input} [{conf_str}] Accuracy: {this_result[2]:>8.4f}%, Top5_Accuracy: {this_result[-1]:>8.4f}%')
        if args.verbose > 0:
            save_f = result_file.lstrip('Data/gradient/')
            print(f'\t{save_f}\n')

        torch.cuda.empty_cache()

def main():
    if args.verbose > 1:
        # print('\nNumber of Speakers: {}.'.format(train_dir.num_spks))
        # print the experiment configuration
        print('Current time is \33[91m{}\33[0m.'.format(str(time.asctime())))
        options = vars(args)
        options_keys = list(options.keys())
        options_keys.sort()
        options_str = ''
        for k in options_keys:
            options_str += '\'{}\': \'{}\', '.format(k, options[k])
        print('Parsed options: \n {}'.format(options_str))

    # instantiate model and initialize weights
    if args.check_yaml != None and os.path.exists(args.check_yaml):
        if args.verbose > 0:
            print('\nLoading model check yaml from: \n\t{}'.format(args.check_yaml.lstrip('Data/checkpoint/')))
        model_kwargs = load_model_args(args.check_yaml)
    else:
        print('Error in finding check yaml file:\n{}'.format(args.check_yaml))
        exit(0)

    # if 'embedding_model' in model_kwargs:
    #     model = model_kwargs['embedding_model']
    #     if 'classifier' in model_kwargs:
    #         model.classifier = model_kwargs['classifier']
    # else:
    #     if args.verbose > 0: 
    #         keys = list(model_kwargs.keys())
    #         keys.sort()
    #         model_options = ["\'%s\': \'%s\'" % (str(k), str(model_kwargs[k])) for k in keys]
    #         print('Model options: \n{ %s }' % (', '.join(model_options)))
    #         print('Testing with %s distance, ' % ('cos' if args.cos_sim else 'l2'))

    #     model = create_model(args.model, **model_kwargs)
    with open(args.check_yaml, 'r') as f:
        config_args = load_hyperpyyaml(f)

    if 'embedding_model' in config_args:
        model = config_args['embedding_model']

    if 'classifier' in config_args:
        model.classifier = config_args['classifier']
    else:
        create_classifier(model, **config_args)


    valid_loader = DataLoader(valid_dir, batch_size=args.batch_size, shuffle=False, **kwargs)

    resume_path = args.check_path + '/checkpoint_{}.pth'
    # print('=> Saving output in {}\n'.format(args.extract_path))
    epochs = np.arange(args.start_epochs, args.epochs + 1)

    for e in epochs:
        # Load model from Checkpoint file
        if os.path.isfile(resume_path.format(e)):
            if args.verbose > 0:
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

        if args.feat_format == 'wav':
            trans = model.input_mask[0]
            model.input_mask.__delitem__(0) # 从save_dir_输入为feat而不是wav
            transform.transforms[0].data_preprocess = trans
        
        if args.test_mask:
            mask_str = args.mask_sub.split(',')
            mask_type = args.mask_type
            baselines = None
            
            if os.path.exists(args.baseline_file):
                baselines = [] 
                with open(args.baseline_file, 'r') as f:
                    for l in f.readlines():
                        _, upath = l.split()
                        the_data = read_WaveInt(upath)
                        the_data = trans(torch.tensor(the_data).reshape(1, 1, -1).float())
                        baselines.append(the_data)
                        
                baselines = torch.cat(baselines, dim=-2).mean(dim=-2, keepdim=True) 
                if args.verbose > 1:
                    print('Baselines shape: ', baselines.shape)

            start = int(mask_str[0])
            end   = int(mask_str[1])
            transform.transforms.append(FreqMaskIndexLayer(start=start, mask_len=end,
                                                        mask_type=mask_type, mask_value=baselines))
            if args.verbose > 0:
                print('mask %s set values in frequecy from %d to %d.' % (mask_type, start, end))

        model.cuda()

        file_dir = args.extract_path # + '/epoch_%d' % e
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        valid_eval(valid_loader, model, file_dir, '%s_valid'% args.train_set_name,
                   config_args)


if __name__ == '__main__':
    main()
