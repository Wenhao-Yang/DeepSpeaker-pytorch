#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: make_spectrogram.py
@Time: 2020/2/28 5:53 PM
@Overview: Make Spectorgrams with kaldi data format.
"""

from __future__ import print_function
import argparse
import os
import pathlib
import sys
import pdb
from multiprocessing import Process, Queue, Pool, Manager
import time
import numpy as np
from kaldi_io import kaldi_io

import Process_Data.constants as c
from Process_Data.audio_processing import Make_Spect

def compute_wav_path(wav, feat_scp, feat_ark, utt2dur, utt2num_frames):
    feat, duration = Make_Spect(wav_path=wav[1], windowsize=0.02, stride=0.01, duration=True)
    # np_fbank = Make_Fbank(filename=uid2path[uid], use_energy=True, nfilt=c.TDNN_FBANK_FILTER)

    len_vec = len(feat.tobytes())
    key = wav[0]
    kaldi_io.write_mat(feat_ark, feat, key=key)

    feat_scp.write(str(key) + ' ' + str(feat_ark.name) + ':' + str(feat_ark.tell() - len_vec - 10) + '\n')
    utt2dur.write('%s %.6f' % (str(key), duration))
    utt2num_frames.write('%s %d' % (str(key), len(feat)))


class MakeFeatsProcess(Process):

    def __init__(self, out_dir, proid, task_queue, error_queue):
        super(MakeFeatsProcess, self).__init__()  # 重构run函数必须要写
        self.item = item
        self.proid = proid
        self.t_queue = task_queue
        self.e_queue = error_queue

        #  wav_scp = os.path.join(data_path, 'wav.scp')
        feat_scp = os.path.join(out_dir, 'feat.%d.scp' % proid)
        feat_ark = os.path.join(out_dir, 'feat.%d.ark' % proid)
        utt2dur = os.path.join(out_dir, 'utt2dur.%d' % proid)
        utt2num_frames = os.path.join(out_dir, 'utt2num_frames.%d' % proid)

        self.feat_scp = open(feat_scp, 'w')
        self.feat_ark = open(feat_ark, 'wb')
        self.utt2dur = open(utt2dur, 'w')
        self.utt2num_frames = open(utt2num_frames, 'w')

    def run(self):
        while not self.t_queue.empty():
            wav = self.t_queue.get()

            pair = wav.split()
            try:
                feat, duration = Make_Spect(wav_path=pair[1], windowsize=0.02, stride=0.01, duration=True)
                # np_fbank = Make_Fbank(filename=uid2path[uid], use_energy=True, nfilt=c.TDNN_FBANK_FILTER)

                len_vec = len(feat.tobytes())
                key = pair[0]
                kaldi_io.write_mat(self.feat_ark, feat, key=key)

                self.feat_scp.write(
                    str(key) + ' ' + str(self.feat_ark.name) + ':' + str(self.feat_ark.tell() - len_vec - 10) + '\n')
                self.utt2dur.write('%s %.6f' % (str(key), duration))
                self.utt2num_frames.write('%s %d' % (str(key), len(feat)))

            except:
                print("Error: %s" % pair[0])
                self.e_queue.put(pair[0])

            # if self.queue.qsize() % 1000 == 0:
            print('==> Process %s: %s left' % (str(self.proid), str(self.t_queue.qsize())))

        self.feat_scp.close()
        self.feat_ark.close()
        self.utt2dur.close()
        self.utt2num_frames.close()

        print('>> Process {} finished!'.format(self.proid))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Computing spectrogram!')
    parser.add_argument('--nj', type=int, default=1, metavar='E',
                        help='number of jobs to make feats (default: 10)')
    parser.add_argument('--data-dir', type=str,
                        default='/home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1/temp',
                        help='number of jobs to make feats (default: 10)')
    parser.add_argument('--out-dir', type=str,
                        default='/home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/temp',
                        help='number of jobs to make feats (default: 10)')

    parser.add_argument('--conf', type=str, default='condf/spect.conf', metavar='E',
                        help='number of epochs to train (default: 10)')

    parser.add_argument('--vad-proportion-threshold', type=float, default=0.12, metavar='E',
                        help='number of epochs to train (default: 10)')
    parser.add_argument('--vad-frames-context', type=int, default=2, metavar='E',
                        help='number of epochs to train (default: 10)')
    args = parser.parse_args()


    data_dir = args.data_dir
    out_dir = args.out_dir
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    wav_scp_f = os.path.join(data_dir, 'wav.scp')
    assert os.path.exists(data_dir)
    assert os.path.exists(wav_scp_f)

    print('Copy wav.scp, spk2utt, utt2spk to %s' % out_dir)
    for f in ['wav.scp', 'spk2utt', 'utt2spk']:
        orig_f = os.path.join(data_dir, f)
        targ_f = os.path.join(out_dir, f)
        os.system('cp %s %s' % (orig_f, targ_f))

    with open(wav_scp_f, 'r') as f:
        wav_scp = f.readlines()
        assert len(wav_scp) > 0

    nj = args.nj if len(wav_scp) > args.nj else 1
    num_utt = len(wav_scp)
    # completed_queue = Queue()
    manager = Manager()
    task_queue = manager.Queue()
    error_queue = manager.Queue()

    for u in wav_scp:
        task_queue.put(u)

    print('Plan to make feats for %d utterances in %s.' % (task_queue.qsize(), str(time.asctime())))
    pool = Pool(processes=nj)  # 创建nj个进程
    for i in range(0, nj):
        write_dir = os.path.join(out_dir, 'Split%d/%d' % (nj, i))
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)

        pool.apply_async(MakeFeatsProcess, args=(write_dir, i, task_queue, error_queue))

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
    print('\n>> Splited Data root is %s. Concat all scripts together.' % str(Split_dir))

    all_scp_path = [os.path.join(Split_dir, '%d/feat.%d.scp' % (i, i)) for i in range(nj)]
    feat_scp = os.path.join(out_dir, 'feats.scp')
    with open(feat_scp, 'w') as feat_scp_f:
        for item in all_scp_path:
            for txt in open(item, 'r').readlines():
                feat_scp_f.write(txt)

    all_scp_path = [os.path.join(Split_dir, '%d/utt2dur.%d' % (i, i)) for i in range(nj)]
    utt2dur = os.path.join(out_dir, 'utt2dur')
    with open(utt2dur, 'w') as utt2dur_f:
        for item in all_scp_path:
            for txt in open(str(item), 'r').readlines():
                utt2dur_f.write(txt)

    all_scp_path = [os.path.join(Split_dir, '%d/utt2num_frames.%d' % (i, i)) for i in range(nj)]
    utt2num_frames = os.path.join(out_dir, 'utt2num_frames')
    with open(utt2num_frames, 'w') as utt2num_frames_f:
        for item in all_scp_path:
            for txt in open(str(item), 'r').readlines():
                utt2num_frames_f.write(txt)

    print('For multi process Completed, write all files in: %s' % out_dir)
    sys.exit()

"""
For multi threads, average making seconds for 47 speakers is 4.579958657
For one threads, average making seconds for 47 speakers is 4.11888732301

For multi process, average making seconds for 47 speakers is 1.67094940328
For one process, average making seconds for 47 speakers is 3.64203325738
"""
