#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: plt_weight_banks.py
@Time: 2020/10/12 23:16
@Overview:
"""
import matplotlib.pyplot as plt
import numpy as np
from scipy import interpolate

import Process_Data.constants as c
from Lime import gassuan_weight
from Process_Data.xfcc.common import get_filterbanks

timit_soft = get_filterbanks(nfilt=23, nfft=320, samplerate=16000, lowfreq=0,
                             highfreq=None, filtertype='dnn.timit.soft', multi_weight=False)
mel = get_filterbanks(nfilt=23, nfft=320, samplerate=16000, lowfreq=0,
                      highfreq=None, filtertype='mel', multi_weight=False)

tim_so = np.array(c.TIMIT_FIlTER_SOFT)
tim_fr = np.load('Lime/Analysis/fratio/timit/fratio_1500_log.npy')

tim_fr = gassuan_weight(tim_fr)
tim_fr = tim_fr / tim_fr.sum()

x = np.linspace(0, 8000, 161)
m = np.arange(0, 2840.0230467083188)
m = 700 * (10 ** (m / 2595.0) - 1)
n = np.array([m[i] - m[i - 1] for i in range(1, len(m))])
n = 1 / n

f = interpolate.interp1d(m[1:], n)
xnew = np.arange(np.min(m[1:]), np.max(m[1:]), (np.max(m[1:]) - np.min(m[1:])) / 161)
ynew = f(xnew)
ynew = ynew / ynew.sum()

xmore = np.arange(np.min(m[1:]), np.max(m[1:]), (np.max(m[1:]) - np.min(m[1:])) / 1024)
ymore = f(xmore)
ymore = ymore / ymore.sum()

# pdf = PdfPages('Lime/LoResNet8/timit/soft/grad_filter_noedge.pdf')
plt.rc('font', family='Times New Roman')

fig = plt.figure(figsize=(6, 4.5), tight_layout=True)

# style.use('grayscale')
# ax.set_title('Resolution')
plt.plot(xmore, ymore, marker='x', markevery=64)

ff = interpolate.interp1d(x, tim_fr)
tim_fr_enw = ff(xmore)
tim_fr_enw /= tim_fr_enw.sum()

plt.plot(xmore, tim_fr_enw, marker='o', markevery=64)

tim_so = gassuan_weight(tim_so)

ff = interpolate.interp1d(x, tim_so)
tim_so_enw = ff(xmore)
tim_so_enw = tim_so_enw / tim_so_enw.sum()

plt.plot(xmore, tim_so_enw, marker='^', markevery=64)
plt.legend(['Mel', 'F-ratio', 'Gradient'], fontsize=16)
plt.ylabel('Weight', fontsize=12)
plt.xlabel('Frequency(Hz)', fontsize=12)

# plt.title('a) Scale Comparison', y=-1)
# ax.set_xticks([])
plt.subplots_adjust(left=0, bottom=0, right=1, top=1)
plt.savefig('Lime/LoResNet8/timit/soft/grad.eps', format='eps')
plt.show()

plt.figure(figsize=(6, 1.5), tight_layout=True)
for m in mel:
    plt.plot(xnew, m, color='#1f77b4', linewidth=0.8)
plt.ylabel('Weight', fontsize=12)
plt.xlabel('Frequency(Hz)', fontsize=12)

# plt.title('b) Mel filters')
fig.tight_layout()

plt.savefig('Lime/LoResNet8/timit/soft/mel.eps', format='eps')
plt.show()
# ax.set_xticks([])

plt.figure(figsize=(6, 1.5), tight_layout=True)
for m in timit_soft:
    plt.plot(x, m, color='#2ca02c', linewidth=0.8)
# plt.set_title('c) Gradient filters')
plt.ylabel('Weight', fontsize=12)
plt.xlabel('Frequency(Hz)', fontsize=12)

# plt.xlabel('Frequency', fontsize=18)
plt.savefig('Lime/LoResNet8/timit/soft/gradient.eps', format='eps')
plt.show()

# pdf.savefig()
# pdf.close()
# plt.show()
