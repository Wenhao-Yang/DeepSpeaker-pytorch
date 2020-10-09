#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: make_egs.py
@Time: 2020/8/21 11:19
@Overview:
"""

from __future__ import print_function

import argparse
import os
import random
import shutil
import sys
import time
from multiprocessing import Pool, Manager

import kaldi_io
import numpy as np
import torch
from kaldiio import WriteHelper
from tqdm import tqdm

from Process_Data.KaldiDataset import ScriptTrainDataset, ScriptValidDataset
from Process_Data.audio_augment.common import RunCommand
from Process_Data.audio_processing import ConcateInput

parser = argparse.ArgumentParser(description='Computing Filter banks!')
parser.add_argument('--nj', type=int, default=18, metavar='E', help='number of jobs to make feats (default: 10)')
parser.add_argument('--data-dir', type=str,
                    help='number of jobs to make feats (default: 10)')
parser.add_argument('--data-format', type=str, default='wav', choices=['flac', 'wav'],
                    help='number of jobs to make feats (default: 10)')
parser.add_argument('--domain', action='store_true', default=False, help='set domain in dataset')

parser.add_argument('--out-dir', type=str, required=True, help='number of jobs to make feats (default: 10)')
parser.add_argument('--out-set', type=str, default='dev_reverb', help='number of jobs to make feats (default: 10)')
parser.add_argument('--feat-format', type=str, choices=['kaldi', 'npy', 'kaldi_cmp'],
                    help='number of jobs to make feats (default: 10)')
parser.add_argument('--out-format', type=str, choices=['kaldi', 'npy', 'kaldi_cmp'],
                    help='number of jobs to make feats (default: 10)')
parser.add_argument('--num-frames', type=int, default=300, metavar='E',
                    help='number of jobs to make feats (default: 10)')

parser.add_argument('--feat-type', type=str, default='fbank', choices=['fbank', 'spectrogram', 'mfcc'],
                    help='number of jobs to make feats (default: 10)')
parser.add_argument('--train', action='store_true', default=False, help='using Cosine similarity')

parser.add_argument('--remove-vad', action='store_true', default=False, help='using Cosine similarity')
parser.add_argument('--compress', action='store_true', default=False, help='using Cosine similarity')
parser.add_argument('--input-per-spks', type=int, default=384, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--num-valid', type=int, default=2, metavar='IPFT',
                    help='input sample per file for testing (default: 8)')
parser.add_argument('--seed', type=int, default=123456, metavar='S',
                    help='random seed (default: 0)')
parser.add_argument('--conf', type=str, default='condf/spect.conf', metavar='E',
                    help='number of epochs to train (default: 10)')
args = parser.parse_args()


def PrepareEgProcess(lock_i, lock_t, train_dir, idx_queue, t_queue):

    while True:
        lock_i.acquire()  # 加上锁
        if not idx_queue.empty():
            idx = idx_queue.get()
            lock_i.release()  # 释放锁

            if args.domain:
                feature, label, domlab = train_dir.__getitem__(idx)
                pairs = (label, domlab, feature)
            else:
                feature, label = train_dir.__getitem__(idx)
                pairs = (label, feature)
            # lock_t.acquire()
            t_queue.put(pairs)
            # lock_t.release()
            # print('\rProcess [%6s] There are [%6s] egs' \
            #       ' left.' % (str(os.getpid()), str(idx_queue.qsize())), end='')
        else:
            lock_i.release()  # 释放锁
            # print('\n>> Process {}: idx queue empty!'.format(os.getpid()))
            break


def SaveEgProcess(lock_t, out_dir, ark_dir, ark_prefix, proid, t_queue, e_queue, i_queue):
    #  wav_scp = os.path.join(data_path, 'wav.scp')
    feat_dir = os.path.join(ark_dir, ark_prefix)
    if not os.path.exists(feat_dir):
        os.makedirs(feat_dir)

    feat_scp = os.path.join(out_dir, 'feat.%d.temp.scp' % proid)
    feat_ark = os.path.join(feat_dir, 'feat.%d.ark' % proid)
    feat_scp_f = open(feat_scp, 'w')

    # utt2dur = os.path.join(out_dir, 'utt2dur.%d' % proid)
    # utt2num_frames = os.path.join(out_dir, 'utt2num_frames.%d' % proid)
    # utt2dur_f = open(utt2dur, 'w')
    # utt2num_frames_f = open(utt2num_frames, 'w')

    if args.out_format == 'kaldi':
        feat_ark_f = open(feat_ark, 'wb')
    if args.out_format == 'kaldi_cmp':
        writer = WriteHelper('ark,scp:%s,%s' % (feat_ark, feat_scp), compression_method=1)

    temp_dir = out_dir + '/temp'
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    while True:
        lock_t.acquire()  # 加上锁
        if not t_queue.empty():
            comm = task_queue.get()
            lock_t.release()  # 释放锁

            try:
                if args.domain:
                    key = ' '.join((str(comm[0]), str(comm[1])))
                else:
                    key = str(comm[0])
                feat = comm[-1].astype(np.float32).squeeze()
                # print(feat.shape)

                if args.out_format == 'kaldi':
                    kaldi_io.write_mat(feat_ark_f, feat, key='')
                    offsets = feat_ark + ':' + str(feat_ark_f.tell() - len(feat.tobytes()) - 15)
                    # print(offsets)
                    feat_scp_f.write(key + ' ' + offsets + '\n')

                elif args.out_format == 'kaldi_cmp':
                    writer(str(key), feat)

                elif args.feat_format == 'npy':
                    npy_path = os.path.join(feat_dir, '%s.npy' % key)
                    np.save(npy_path, feat)
                    feat_scp_f.write(key + ' ' + npy_path + '\n')

            except Exception as e:
                print(e)
                e_queue.put(key)

            if t_queue.qsize() % 100 == 0:
                print('\rProcess [%6s] There are [%6s] egs left, with [%6s] errors.' %
                      (str(os.getpid()), str(t_queue.qsize() + i_queue.qsize()), str(e_queue.qsize())), end='')
        elif i_queue.empty():
            lock_t.release()

            # print('\n>> Process {}: all queue empty!'.format(os.getpid()))
            break
        else:
            lock_t.release()
            time.sleep(5)

    feat_scp_f.close()

    if args.feat_format == 'kaldi':
        feat_ark_f.close()
    elif args.feat_format == 'kaldi_cmp':
        writer.close()

    new_feat_scp = os.path.join(out_dir, 'feat.%d.scp' % proid)
    if args.feat_format == 'kaldi' and args.compress:
        new_feat_ark = os.path.join(feat_dir, 'feat.%d.ark' % proid)
        compress_command = "copy-feats --compress=true scp:{} ark,scp:{},{}".format(feat_scp, new_feat_ark,
                                                                                    new_feat_scp)
        pid, stdout, stderr = RunCommand(compress_command)
        # print(stdout)
        if os.path.exists(new_feat_scp) and os.path.exists(new_feat_ark):
            os.remove(feat_ark)
    else:
        shutil.copy(feat_scp, new_feat_scp)
        # pass
    assert os.path.exists(new_feat_scp)


transform = ConcateInput(num_frames=args.num_frames, remove_vad=args.remove_vad)

if args.feat_format == 'npy':
    file_loader = np.load
elif args.feat_format == 'kaldi':
    file_loader = kaldi_io.read_mat

train_dir = ScriptTrainDataset(dir=args.data_dir, samples_per_speaker=args.input_per_spks, loader=file_loader,
                               transform=transform, num_valid=args.num_valid, domain=args.domain)

valid_dir = ScriptValidDataset(valid_set=train_dir.valid_set, loader=file_loader, spk_to_idx=train_dir.spk_to_idx,
                               dom_to_idx=train_dir.dom_to_idx, valid_utt2dom_dict=train_dir.valid_utt2dom_dict,
                               valid_uid2feat=train_dir.valid_uid2feat, valid_utt2spk_dict=train_dir.valid_utt2spk_dict,
                               transform=transform, domain=args.domain)

if __name__ == "__main__":
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    nj = args.nj
    data_dir = args.data_dir
    out_dir = os.path.join(args.out_dir, args.out_set)

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    wav_scp_f = os.path.join(data_dir, 'wav.scp')
    spk2utt_f = os.path.join(data_dir, 'spk2utt')
    assert os.path.exists(data_dir), data_dir
    assert os.path.exists(wav_scp_f), wav_scp_f
    assert os.path.exists(spk2utt_f), spk2utt_f

    if data_dir != out_dir:
        print('Copy wav.scp, spk2utt, utt2spk, trials to %s' % out_dir)
        for f in ['wav.scp', 'spk2utt', 'utt2spk', 'trials']:
            orig_f = os.path.join(data_dir, f)
            targ_f = os.path.join(out_dir, f)
            if os.path.exists(orig_f):
                os.system('Cp %s %s' % (orig_f, targ_f))

    start_time = time.time()

    manager = Manager()
    lock_i = manager.Lock()
    lock_t = manager.Lock()
    task_queue = manager.Queue()
    idx_queue = manager.Queue()
    error_queue = manager.Queue()

    if args.train:

        num_utt = [i for i in range(len(train_dir))]

        random.seed(args.seed)
        random.shuffle(num_utt)
        for i in tqdm(num_utt):
            idx_queue.put(i)

        print('\n>> Plan to make egs for %d speakers with %d utterances in %s with %d jobs.\n' % (
            train_dir.num_spks, num_utt, str(time.asctime()), nj))

        pool = Pool(processes=int(nj * 2))  # 创建nj个进程
        for i in range(0, nj):
            write_dir = os.path.join(out_dir, 'Split%d/%d' % (nj, i))
            if not os.path.exists(write_dir):
                os.makedirs(write_dir)

            ark_dir = os.path.join(args.out_dir, args.feat_type)
            if not os.path.exists(ark_dir):
                os.makedirs(ark_dir)
            pool.apply_async(PrepareEgProcess, args=(lock_i, lock_t, train_dir, idx_queue, task_queue))
            # if (i + 1) % 2 == 1:
            pool.apply_async(SaveEgProcess, args=(lock_t, write_dir, ark_dir, args.out_set,
                                                  i, task_queue, error_queue, idx_queue))

        pool.close()  # 关闭进程池，表示不能在往进程池中添加进程
        pool.join()  # 等待进程池中的所有进程执行完毕，必须在close()之后调用
    else:

        # valid set
        num_utt = len(valid_dir)
        for i in tqdm(range(len(valid_dir))):
            idx_queue.put(i)

        print('\n>> Plan to make feats for %d speakers with %d utterances in %s with %d jobs.\n' % (
            idx_queue.qsize(), num_utt, str(time.asctime()), nj))

        pool = Pool(processes=int(nj * 1.5))  # 创建nj个进程
        for i in range(0, nj):
            write_dir = os.path.join(out_dir, 'Split%d/%d' % (nj, i))
            if not os.path.exists(write_dir):
                os.makedirs(write_dir)

            ark_dir = os.path.join(args.out_dir, args.feat_type)
            if not os.path.exists(ark_dir):
                os.makedirs(ark_dir)
            pool.apply_async(PrepareEgProcess, args=(lock_i, lock_t, valid_dir, idx_queue, task_queue))
            if (i + 1) % 2 == 1:
                pool.apply_async(SaveEgProcess, args=(lock_t, write_dir, ark_dir, args.out_set,
                                                      i, task_queue, error_queue, idx_queue))

        pool.close()  # 关闭进程池，表示不能在往进程池中添加进程
        pool.join()  # 等待进程池中的所有进程执行完毕，必须在close()之后调用

    if error_queue.qsize() > 0:
        print('\n>> Saving Completed with errors in: ')
        while not error_queue.empty():
            print(error_queue.get() + ' ', end='')
        print('')
    else:
        print('\n>> Saving Completed without errors.!')

    Split_dir = os.path.join(out_dir, 'Split%d' % nj)
    print('   Splited Data root is \n     %s. \n   Concat all scripts together.' % str(Split_dir))

    all_scp_path = [os.path.join(Split_dir, '%d/feat.%d.scp' % (i, i)) for i in range(nj)]
    assert len(all_scp_path) > 0, print(Split_dir)
    feat_scp = os.path.join(out_dir, 'feats.scp')
    numofutt = 0
    with open(feat_scp, 'w') as feat_scp_f:
        for item in all_scp_path:
            if not os.path.exists(item):
                continue
            for txt in open(item, 'r').readlines():
                feat_scp_f.write(txt)
                numofutt += 1
    if numofutt != num_utt:
        print('Errors in %s ?' % feat_scp)

    # print('Delete tmp files in: %s' % Split_dir)

    end_time = time.time()
    print('For multi process Completed, write all files in: \n\t%s. \nAnd %.2fs collapse.\n' % (
    out_dir, end_time - start_time))
    sys.exit()

"""

"""
