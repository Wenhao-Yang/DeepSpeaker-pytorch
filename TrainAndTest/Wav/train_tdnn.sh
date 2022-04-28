#!/usr/bin/env bash

stage=0
waited=0
while [ $(ps 103374 | wc -l) -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done
lstm_dir=/home/yangwenhao/project/lstm_speaker_verification

if [ $stage -le 0 ]; then
  datasets=timit
  model=TDNN_v5
  feat_type=hst
  feat=c20
  block_type=basic
  input_norm=Mean
  dropout_p=0
  encoder_type=STAP
  #  loss=arcsoft
  loss=soft
  avgsize=4
  alpha=0
  embedding_size=128
  block_type=None
  feat_dim=40
  loss=soft
  scheduler=rop
  optimizer=sgd

  lr_ratio=0.1
#  --channels 512,512,512,512,1500 \

  for filter in sinc2down; do
    echo -e "\n\033[1;4;31m Stage${stage} :Training ${model} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
    python TrainAndTest/train_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/train_${feat}_down5 \
      --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/train_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/train_${feat}_valid \
      --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
      --batch-size 128 \
      --input-norm ${input_norm} \
      --test-input fix \
      --feat-format kaldi \
      --nj 10 \
      --epochs 40 \
      --lr 0.1 \
      --input-dim 40 \
      --random-chunk 6400 12800 \
      --chunk-size 9600 \
      --feat-dim ${feat_dim} \
      --optimizer ${optimizer} \
      --scheduler ${scheduler} \
      --filter ${filter} \
      --time-dim 1 \
      --patience 3 \
      --milestones 10,20,30,40 \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_filter/${loss}_${optimizer}_${scheduler}/chn256_${input_norm}_${encoder_type}_${block_type}_dp${dropout_p}_alpha${alpha}_em${embedding_size}_wd5e4/${filter}${feat_dim}_adalr${lr_ratio} \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_filter/${loss}_${optimizer}_${scheduler}/chn256_${input_norm}_${encoder_type}_${block_type}_dp${dropout_p}_alpha${alpha}_em${embedding_size}_wd5e4/${filter}${feat_dim}_adalr${lr_ratio}/checkpoint_9.pth \
      --stride 1 \
      --block-type ${block_type} \
      --channels 256,256,256,256,750 \
      --encoder-type ${encoder_type} \
      --embedding-size ${embedding_size} \
      --avg-size ${avgsize} \
      --alpha ${alpha} \
      --num-valid 2 \
      --margin 0.2 \
      --s 30 \
      --m 3 \
      --lr-ratio ${lr_ratio} \
      --filter-wd 0.001 \
      --weight-decay 0.0005 \
      --dropout-p ${dropout_p} \
      --gpu-id 0 \
      --cos-sim \
      --extract \
      --all-iteraion 0 \
      --loss-type ${loss}
  done
  exit
fi
