#!/usr/bin/env bash

stage=0
if [ $stage -le 0 ]; then
  model=ASTDNN
  feat=mfcc40
  loss=soft
  python Xvector_Extraction/extract_xvector_kaldi.py \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pymfcc40/dev_kaldi \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pymfcc40/test_kaldi \
    --check-path Data/checkpoint/${model}/${feat}/${loss} \
    --resume Data/checkpoint/${model}/${feat}/${loss}/checkpoint_20.pth \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --feat-dim 40 \
    --extract-path Data/xvector/${model}/${feat}/${loss} \
    --model ${model} \
    --dropout-p 0.0\
    --epoch 20 \
    --embedding-size 512
fi

if [ $stage -le 1 ]; then
  model=LoResNet10
  feat=spect_161
  loss=soft
  python Xvector_Extraction/extract_xvector_kaldi.py \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pymfcc40/dev_kaldi \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pymfcc40/test_kaldi \
    --check-path Data/checkpoint/${model}/${feat}/${loss} \
    --resume Data/checkpoint/${model}/${feat}/${loss}/checkpoint_20.pth \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --feat-dim 161 \
    --extract-path Data/xvector/${model}/${feat}/${loss} \
    --model ${model} \
    --dropout-p 0.0 \
    --epoch 20 \
    --embedding-size 1024
fi