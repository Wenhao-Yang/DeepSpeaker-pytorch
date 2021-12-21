#!/usr/bin/env bash

stage=157
waited=0
while [ $(ps 1348898 | wc -l) -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done

lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification
if [ $stage -le 0 ]; then
  model=ETDNN
  for loss in soft; do
    python TrainAndTest/Fbank/TDNNs/train_etdnn_kaldi.py \
      --train-dir ${lstm_dir}/data/Vox1_pyfb80/dev_kaldi \
      --test-dir ${lstm_dir}/data/Vox1_pyfb80/test_kaldi \
      --check-path Data/checkpoint/${model}/fbank80/soft \
      --resume Data/checkpoint/${model}/fbank80/soft/checkpoint_1.pth \
      --epochs 20 \
      --milestones 10,15 \
      --feat-dim 80 \
      --embedding-size 256 \
      --num-valid 2 \
      --loss-type soft \
      --lr 0.01

  done
fi

#stage=1
if [ $stage -le 5 ]; then
  model=TDNN
  feat=fb40
  for loss in soft; do
    python TrainAndTest/Fbank/TDNNs/train_tdnn_var.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb40 \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb40 \
      --check-path Data/checkpoint/${model}/${feat}/${loss}_norm \
      --resume Data/checkpoint/${model}/${feat}/${loss}_norm/checkpoint_1.pth \
      --batch-size 64 \
      --remove-vad \
      --epochs 16 \
      --milestones 8,12 \
      --feat-dim 40 \
      --embedding-size 128 \
      --weight-decay 0.0005 \
      --num-valid 2 \
      --loss-type ${loss} \
      --input-per-spks 192 \
      --gpu-id 0 \
      --veri-pairs 9600 \
      --lr 0.01
  done
fi

#stage=100
if [ $stage -le 10 ]; then
  model=ASTDNN
  feat=fb40_wcmvn
  for loss in soft; do
    #    python TrainAndTest/Fbank/TDNNs/train_astdnn_kaldi.py \
    #      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb40_wcmvn \
    #      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb40_wcmvn \
    #      --check-path Data/checkpoint/${model}/${feat}/${loss} \
    #      --resume Data/checkpoint/${model}/${feat}/${loss}/checkpoint_1.pth \
    #      --epochs 18 \
    #      --batch-size 128 \
    #      --milestones 9,14  \
    #      --feat-dim 40 \
    #      --embedding-size 128 \
    #      --num-valid 2 \
    #      --loss-type ${loss} \
    #      --input-per-spks 240 \
    #      --lr 0.01

    python TrainAndTest/Fbank/TDNNs/train_tdnn_var.py \
      --model ASTDNN \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb40_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb40_wcmvn \
      --check-path Data/checkpoint/${model}/${feat}/${loss}_svar \
      --resume Data/checkpoint/${model}/${feat}/${loss}_svar/checkpoint_1.pth \
      --epochs 18 \
      --batch-size 128 \
      --milestones 9,14 \
      --feat-dim 40 \
      --remove-vad \
      --embedding-size 512 \
      --num-valid 2 \
      --loss-type ${loss} \
      --input-per-spks 240 \
      --lr 0.01 \
      --gpu-id 1

    python TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb40_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb40_wcmvn \
      --nj 12 \
      --model ASTDNN \
      --embedding-size 512 \
      --feat-dim 40 \
      --remove-vad \
      --resume Data/checkpoint/${model}/${feat}/${loss}_svar/checkpoint_18.pth \
      --loss-type soft \
      --num-valid 2 \
      --gpu-id 1

    python Lime/output_extract.py \
      --model ASTDNN \
      --start-epochs 18 \
      --epochs 18 \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb40_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb40_wcmvn \
      --sitw-dir ${lstm_dir}/data/sitw \
      --loss-type soft \
      --remove-vad \
      --check-path Data/checkpoint/${model}/${feat}/${loss}_svar \
      --extract-path Data/gradient/${model}/${feat}/${loss}_svar \
      --gpu-id 1 \
      --embedding-size 512 \
      --sample-utt 5000
  done
fi

#stage=1
if [ $stage -le 15 ]; then
  model=ETDNN
  feat=fb80
  for loss in soft; do
    python TrainAndTest/Fbank/TDNNs/train_tdnn_kaldi.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb80 \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb80 \
      --check-path Data/checkpoint/${model}/${feat}/${loss} \
      --resume Data/checkpoint/${model}/${feat}/${loss}/checkpoint_1.pth \
      --batch-size 128 \
      --remove-vad \
      --epochs 20 \
      --milestones 10,14 \
      --feat-dim 80 \
      --embedding-size 128 \
      --weight-decay 0.0005 \
      --num-valid 2 \
      --loss-type ${loss} \
      --input-per-spks 224 \
      --gpu-id 1 \
      --veri-pairs 9600 \
      --lr 0.01
  done
fi

#stage=100
if [ $stage -le 16 ]; then
  model=ETDNN
  feat=fb80
  for loss in amsoft center; do
    python TrainAndTest/Fbank/TDNNs/train_tdnn_kaldi.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb80 \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb80 \
      --check-path Data/checkpoint/${model}/${feat}/${loss} \
      --resume Data/checkpoint/ETDNN/fb80/soft/checkpoint_20.pth \
      --batch-size 128 \
      --remove-vad \
      --epochs 30 \
      --finetune \
      --milestones 6 \
      --feat-dim 80 \
      --embedding-size 128 \
      --weight-decay 0.0005 \
      --num-valid 2 \
      --loss-type ${loss} \
      --m 4 \
      --margin 0.35 \
      --s 15 \
      --loss-ratio 0.01 \
      --input-per-spks 224 \
      --gpu-id 1 \
      --veri-pairs 9600 \
      --lr 0.001
  done
fi

if [ $stage -le 40 ]; then
  model=TDNN
  resnet_size=34
  datasets=vox1
  feat=fb40
  loss=soft

  for encod in SASP; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/vox1/egs/pyfb/dev_${feat} \
      --valid-dir ${lstm_dir}/data/vox1/egs/pyfb/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/pyfb/test_${feat} \
      --nj 10 \
      --epochs 20 \
      --milestones 10,15 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size 128 \
      --batch-size 128 \
      --accu-steps 1 \
      --input-dim 40 \
      --lr 0.1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat}_${encod}/${loss} \
      --resume Data/checkpoint/${model}/${datasets}/${feat}_${encod}/${loss}/checkpoint_22.pth \
      --input-per-spks 384 \
      --cos-sim \
      --veri-pairs 9600 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type soft \
      --remove-vad

  done
fi


# VoxCeleb1

if [ $stage -le 50 ]; then
  lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification
  model=TDNN_v4
  datasets=vox1
  feat=fb24_kaldi
  loss=soft

  for encod in STAP; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/vox1/egs/pyfb/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/pyfb/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/egs/pyfb/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/pyfb/test_${feat} \
      --nj 8 \
      --epochs 24 \
      --milestones 8,14,20 \
      --model ${model} \
      --scheduler rop \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size 128 \
      --batch-size 128 \
      --accu-steps 1 \
      --input-dim 24 \
      --lr 0.1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat}_${encod}/${loss} \
      --resume Data/checkpoint/${model}/${datasets}/${feat}_${encod}/${loss}/checkpoint_22.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type soft \
      --log-interval 10

  done
fi

if [ $stage -le 60 ]; then
  model=TDNN_v5
  datasets=vox1
  feat=log
  feat_type=spect
  loss=soft
  encod=STAP
  embedding_size=256

  for model in TDNN_v4; do
    echo -e "\n\033[1;4;31m Stage ${stage}:Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/vox1/egs/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/egs/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --nj 8 \
      --epochs 60 \
      --milestones 8,14,20 \
      --model ${model} \
      --scheduler rop \
      --weight-decay 0.001 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size 192 \
      --accu-steps 1 \
      --input-dim 161 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}/${loss}_emsize${embedding_size} \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}/${loss}_emsize${embedding_size}/checkpoint_40.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.3 \
      --s 15 \
      --log-interval 10
  done
fi

if [ $stage -le 70 ]; then
  model=TDNN_v5
  datasets=vox1
  #  feat=fb24
  feat_type=klfb
  loss=minarcsoft
  encod=STAP
  embedding_size=512
  input_dim=40
  input_norm=Mean
  optimizer=sgd
  scheduler=rop

  for embedding_size in 512; do
    #    feat=combined
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_fb${input_dim} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_fb${input_dim}/trials_dir \
      --train-trials trials_2w \
      --shuffle \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_fb${input_dim} \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_fb${input_dim} \
      --nj 16 \
      --epochs 50 \
      --patience 3 \
      --milestones 10,20,30,40 \
      --model ${model} \
      --optimizer ${optimizer} \
      --scheduler ${scheduler} \
      --lr 0.1 \
      --base-lr 0.00000001 \
      --weight-decay 0.0005 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size 128 \
      --accu-steps 1 \
      --random-chunk 200 400 \
      --input-dim ${input_dim} \
      --channels 512,512,512,512,1500 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}_${optimizer}_${scheduler}/input${input_norm}_${encod}_em${embedding_size}_wd5e4_New_var \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}_${optimizer}_${scheduler}/input${input_norm}_${encod}_em${embedding_size}_wd5e4_New_var/checkpoint_50.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --log-interval 10
  done
  exit
fi

if [ $stage -le 74 ]; then
  model=TDNN_v5
  datasets=vox1
  #  feat=fb24
  feat_type=klsp
  loss=soft
  encod=STAP
  embedding_size=256
  input_dim=161
  input_norm=Mean
  # _lrr${lr_ratio}_lsr${loss_ratio}
  feat=klsp
#
#  for loss in arcsoft; do
#
#    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
#    python -W ignore TrainAndTest/train_egs.py \
#      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
#      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
#      --train-trials trials_2w \
#      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
#      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
#      --nj 12 \
#      --epochs 40 \
#      --patience 2 \
#      --milestones 10,20,30 \
#      --model ${model} \
#      --scheduler rop \
#      --weight-decay 0.0005 \
#      --lr 0.1 \
#      --alpha 0 \
#      --feat-format kaldi \
#      --embedding-size ${embedding_size} \
#      --var-input \
#      --batch-size 128 \
#      --accu-steps 1 \
#      --shuffle \
#      --random-chunk 200 400 \
#      --input-dim ${input_dim} \
#      --channels 512,512,512,512,1500 \
#      --encoder-type ${encod} \
#      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var \
#      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var/checkpoint_13.pth \
#      --cos-sim \
#      --dropout-p 0.0 \
#      --veri-pairs 9600 \
#      --gpu-id 0,1 \
#      --num-valid 2 \
#      --loss-type ${loss} \
#      --margin 0.2 \
#      --s 30 \
#      --log-interval 10
#  done

#  for loss in arcsoft; do
#
#    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
#    python -W ignore TrainAndTest/train_egs.py \
#      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
#      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
#      --train-trials trials_2w \
#      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
#      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
#      --nj 12 \
#      --epochs 40 \
#      --patience 2 \
#      --milestones 10,20,30 \
#      --model ${model} \
#      --scheduler rop \
#      --weight-decay 0.0005 \
#      --lr 0.1 \
#      --alpha 0 \
#      --feat-format kaldi \
#      --embedding-size ${embedding_size} \
#      --var-input \
#      --batch-size 128 \
#      --accu-steps 1 \
#      --shuffle \
#      --random-chunk 200 400 \
#      --input-dim ${input_dim} \
#      --channels 256,256,256,256,768 \
#      --encoder-type ${encod} \
#      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_chn256_wd5e4_var \
#      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_chn256_wd5e4_var/checkpoint_13.pth \
#      --cos-sim \
#      --dropout-p 0.0 \
#      --veri-pairs 9600 \
#      --gpu-id 0,1 \
#      --num-valid 2 \
#      --loss-type ${loss} \
#      --margin 0.2 \
#      --s 30 \
#      --log-interval 10
#  done
  loss=arcsoft

  for weight in mel clean aug vox2; do
    mask_layer=attention
#    weight=clean
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
      --nj 12 \
      --epochs 40 \
      --patience 2 \
      --milestones 10,20,30 \
      --model ${model} \
      --scheduler rop \
      --weight-decay 0.0005 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --var-input \
      --batch-size 128 \
      --accu-steps 1 \
      --shuffle \
      --random-chunk 200 400 \
      --input-dim ${input_dim} \
      --mask-layer ${mask_layer} \
      --init-weight ${weight} \
      --channels 256,256,256,256,768 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_attention/${loss}/${input_norm}_${encod}_em${embedding_size}_${weight}42_wd5e4_var \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_attention/${loss}/${input_norm}_${encod}_em${embedding_size}_${weight}42_wd5e4_var/checkpoint_13.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --log-interval 10
  done
  exit
fi

# VoxCeleb2


if [ $stage -le 100 ]; then
  model=TDNN_v5
  datasets=vox2
  #  feat=fb24
  feat_type=klsp
  loss=soft
  encod=STAP
  embedding_size=512
  input_dim=161
  input_norm=Mean
  # _lrr${lr_ratio}_lsr${loss_ratio}

  for loss in arcsoft; do
    feat=fb${input_dim}_ws25
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
      --nj 12 \
      --epochs 40 \
      --patience 2 \
      --milestones 10,20,30 \
      --model ${model} \
      --scheduler rop \
      --weight-decay 0.0001 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --var-input \
      --batch-size 128 \
      --accu-steps 1 \
      --shuffle \
      --random-chunk 200 400 \
      --input-dim ${input_dim} \
      --channels 512,512,512,512,1500 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wde4_var \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wde4_var/checkpoint_13.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --log-interval 10
  done
  exit
fi

if [ $stage -le 101 ]; then
  model=TDNN_v5
  datasets=vox2
  #  feat=fb24
  feat_type=klfb
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_dim=40
  input_norm=Mean
  optimizer=sgd
  scheduler=exp
  # _lrr${lr_ratio}_lsr${loss_ratio}

  for loss in arcsoft; do
    feat=fb${input_dim}
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_valid \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --nj 16 \
      --epochs 50 \
      --patience 3 \
      --milestones 10,20,30 \
      --model ${model} \
      --optimizer ${optimizer} \
      --scheduler ${scheduler} \
      --weight-decay 0.0001 \
      --lr 0.1 \
      --base-lr 0.000005 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --var-input \
      --batch-size 128 \
      --accu-steps 1 \
      --shuffle \
      --random-chunk 200 400 \
      --input-dim ${input_dim} \
      --channels 512,512,512,512,1500 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}_${optimizer}_${scheduler}/input${input_norm}_${encod}_em${embedding_size}_wde4_var \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}_${optimizer}_${scheduler}/input${input_norm}_${encod}_em${embedding_size}_wde4_var/checkpoint_13.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --log-interval 10
  done
  exit
fi

if [ $stage -le 105 ]; then
  model=ECAPA
  datasets=vox2
  #  feat=fb24
  feat_type=pyfb
  loss=soft
  encod=SASP
  embedding_size=192
  input_dim=40
  input_norm=None

  for loss in arcsoft; do
    feat=fb${input_dim}_ws25
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --shuffle \
      --nj 16 \
      --epochs 60 \
      --patience 3 \
      --milestones 10,20,30,40 \
      --model ${model} \
      --optimizer adam \
      --scheduler cyclic \
      --weight-decay 0.00001 \
      --lr 0.001 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --var-input \
      --batch-size 128 \
      --accu-steps 1 \
      --random-chunk 300 301 \
      --input-dim ${input_dim} \
      --channels 512,512,512,512,1536 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/feat${feat}_input${input_norm}_${encod}128_em${embedding_size}_wde5_adam \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/feat${feat}_input${input_norm}_${encod}128_em${embedding_size}_wde5_adam/checkpoint_5.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --log-interval 10
  done
  exit
fi

if [ $stage -le 106 ]; then
  model=RET
  datasets=vox2
  feat_type=pyfb
  loss=soft
  encod=STAP
  embedding_size=512
  input_dim=40
  input_norm=Mean
  resnet_size=14

  for loss in arcsoft; do
    feat=fb${input_dim}_ws25
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --nj 16 \
      --epochs 50 \
      --patience 3 \
      --milestones 10,20,30 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --scheduler rop \
      --weight-decay 0.0001 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --var-input \
      --batch-size 128 \
      --accu-steps 1 \
      --random-chunk 200 400 \
      --input-dim ${input_dim} \
      --channels 512,512,512,512,512,1536 \
      --context 5,5,5 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/feat${feat}_input${input_norm}_${encod}_em${embedding_size}_wde4_var \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/feat${feat}_input${input_norm}_${encod}_em${embedding_size}_wde4_var/checkpoint_9.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.3 \
      --s 15 \
      --remove-vad \
      --log-interval 10
  done
  exit
fi
if [ $stage -le 107 ]; then
  model=TDNN_v5
  datasets=vox2
  feat=fb40
  feat_type=pyfb
  loss=arcsoft
  encod=STAP
  embedding_size=512

  for model in TDNN_v5; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --fix-length \
      --nj 16 \
      --epochs 40 \
      --patience 2 \
      --milestones 8,14,20 \
      --model ${model} \
      --scheduler rop \
      --weight-decay 0.0005 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size 128 \
      --accu-steps 1 \
      --input-dim 40 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}/${loss}_emsize${embedding_size} \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}/${loss}_emsize${embedding_size}/checkpoint_40.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.3 \
      --s 15 \
      --remove-vad \
      --log-interval 10
  done
fi

if [ $stage -le 108 ]; then
  model=DTDNN
  datasets=vox2
  feat=log
  feat_type=spect
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_norm=Mean

  for model in ETDNN_v5; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_v2 \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_${feat}_v2 \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --fix-length \
      --input-norm ${input_norm} \
      --nj 12 \
      --epochs 50 \
      --patience 2 \
      --milestones 10,20,30 \
      --model ${model} \
      --scheduler rop \
      --weight-decay 0.0001 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size 128 \
      --accu-steps 1 \
      --input-dim 161 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}_v2/${loss}_100ce/emsize${embedding_size}_input${input_norm} \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}_v2/${loss}_100ce/emsize${embedding_size}_input${input_norm}/checkpoint_4.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.25 \
      --s 30 \
      --log-interval 10
  done
fi

if [ $stage -le 109 ]; then
  model=RET
  datasets=vox2
  feat=log
  feat_type=klsp
  loss=arcsoft
  encod=STAP
  embedding_size=512
  block_type=basic_v2
  input_norm=Mean
  batch_size=128
  resnet_size=14
  activation=leakyrelu
  scheduler=exp
  optimizer=sgd
  #  --dilation 1,2,3,1 \

  for encod in STAP ; do
    echo -e "\n\033[1;4;31m Stage${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
      --input-norm ${input_norm} \
      --nj 12 \
      --epochs 60 \
      --patience 2 \
      --random-chunk 200 400 \
      --milestones 10,20,30,40,50 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --block-type ${block_type} \
      --activation ${activation} \
      --weight-decay 0.00005 \
      --optimizer ${optimizer} \
      --scheduler ${scheduler} \
      --lr 0.1 \
      --base-lr 0.000006 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size ${batch_size} \
      --accu-steps 1 \
      --input-dim 161 \
      --channels 512,512,512,512,512,1536 \
      --context 5,3,3,5 \
      --dilation 1,1,1,1 \
      --stride 1,1,1,1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_baseline/${loss}_${optimizer}_${scheduler}/input${input_norm}_em${embedding_size}_${block_type}_${activation}_wd5e5_var \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_baseline/${loss}_${optimizer}_${scheduler}/input${input_norm}_em${embedding_size}_${block_type}_${activation}_wd5e5_var/checkpoint_45.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --all-iteraion 0 \
      --log-interval 10
  done

  #  resnet_size=17
  #  for block_type in Basic; do
  #    echo -e "\n\033[1;4;31m stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
  #    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
  #    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
  #      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_v2 \
  #      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
  #      --train-trials trials_2w \
  #      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_${feat}_v2 \
  #      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
  #      --fix-length \
  #      --input-norm ${input_norm} \
  #      --nj 12 \
  #      --epochs 60 \
  #      --patience 3 \
  #      --milestones 10,20,30,40,50 \
  #      --model ${model} \
  #      --resnet-size ${resnet_size} \
  #      --block-type ${block_type} \
  #      --scheduler rop \
  #      --weight-decay 0.00001 \
  #      --lr 0.1 \
  #      --alpha 0 \
  #      --feat-format kaldi \
  #      --embedding-size ${embedding_size} \
  #      --batch-size ${batch_size} \
  #      --accu-steps 1 \
  #      --input-dim 161 \
  #      --channels 512,512,512,512,512,1536 \
  #      --context 5,3,3,5 \
  #      --encoder-type ${encod} \
  #      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_v2/${loss}_0ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size} \
  #      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_v2/${loss}_0ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size}/checkpoint_21.pth \
  #      --cos-sim \
  #      --dropout-p 0.0 \
  #      --veri-pairs 9600 \
  #      --gpu-id 0,1 \
  #      --num-valid 2 \
  #      --loss-type ${loss} \
  #      --margin 0.25 \
  #      --s 30 \
  #      --all-iteraion 0 \
  #      --log-interval 10
  #  done
  exit
fi

if [ $stage -le 110 ]; then
  model=RET_v2
  datasets=vox2
  feat=log
  feat_type=klsp
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_norm=Mean
  batch_size=128
  resnet_size=18
  activation=relu
  #  --dilation 1,2,3,1 \

  for block_type in basic_v2 ; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
      --input-norm ${input_norm} \
      --shuffle \
      --nj 12 \
      --epochs 55 \
      --patience 2 \
      --random-chunk 200 400 \
      --milestones 10,20,30,40,50 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --activation ${activation} \
      --block-type ${block_type} \
      --scheduler rop \
      --weight-decay 0.00001 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size ${batch_size} \
      --accu-steps 1 \
      --input-dim 161 \
      --channels 256,256,512,512,1024,1024 \
      --context 5,3,3,3 \
      --stride 2,1,2,1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_baseline/${loss}/em${embedding_size}_input${input_norm}_${block_type}_${activation}_wde5_stride2121_var \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_baseline/${loss}/em${embedding_size}_input${input_norm}_${block_type}_${activation}_wde5_stride2121_var/checkpoint_5.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --all-iteraion 0 \
      --log-interval 10
  done
  exit
fi

if [ $stage -le 111 ]; then
  model=RET_v2
  datasets=vox2
  feat=log
  feat_type=spect
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_norm=Mean
  batch_size=128
  resnet_size=17
  stride=2

  for block_type in Basic; do
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_v2 \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_${feat}_v2 \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --input-norm ${input_norm} \
      --nj 12 \
      --epochs 50 \
      --patience 3 \
      --milestones 10,20,30 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --block-type ${block_type} \
      --scheduler rop \
      --weight-decay 0.00001 \
      --lr 0.01 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size ${batch_size} \
      --accu-steps 1 \
      --input-dim 161 \
      --channels 512,512,512,512,512,1536 \
      --context 5,3,3,5 \
      --stride 1,${stride},1,${stride} \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_v2/${loss}_0ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size}_stride1${stride}_wde5_shuf \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_v2/${loss}_0ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size}_stride1${stride}_wde5_shuf/checkpoint_57.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.25 \
      --s 30 \
      --all-iteraion 0 \
      --log-interval 10
  done

#  resnet_size=17
#  for block_type in Basic ; do
#    echo -e "\n\033[1;4;31m stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
#    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
#    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
#      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_v2 \
#      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
#      --train-trials trials_2w \
#      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_${feat}_v2 \
#      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
#      --fix-length \
#      --input-norm ${input_norm} \
#      --nj 12 \
#      --epochs 60 \
#      --patience 3 \
#      --milestones 10,20,30,40,50 \
#      --model ${model} \
#      --resnet-size ${resnet_size} \
#      --block-type ${block_type} \
#      --scheduler rop \
#      --weight-decay 0.00001 \
#      --lr 0.1 \
#      --alpha 0 \
#      --feat-format kaldi \
#      --embedding-size ${embedding_size} \
#      --batch-size ${batch_size} \
#      --accu-steps 1 \
#      --input-dim 161 \
#      --channels 512,512,512,512,512,1536 \
#      --context 5,3,3,5 \
#      --encoder-type ${encod} \
#      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_v2/${loss}_0ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size} \
#      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_v2/${loss}_0ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size}/checkpoint_21.pth \
#      --cos-sim \
#      --dropout-p 0.0 \
#      --veri-pairs 9600 \
#      --gpu-id 0,1 \
#      --num-valid 2 \
#      --loss-type ${loss} \
#      --margin 0.25 \
#      --s 30 \
#      --all-iteraion 0 \
#      --log-interval 10
#  done
fi


if [ $stage -le 112 ]; then
  model=RET_v3
  datasets=vox2
  feat=log
  feat_type=klfb
  loss=arcsoft
  encod=STAP
  embedding_size=256
  block_type=shublock
  input_norm=Mean
  batch_size=128
  resnet_size=18
  activation=leakyrelu
  #  --dilation 1,2,3,1 \

  for encod in SASP2 ; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_fb40 \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_fb40/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_fb40_valid \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_fb40 \
      --input-norm ${input_norm} \
      --shuffle \
      --nj 12 \
      --epochs 60 \
      --patience 3 \
      --random-chunk 200 200 \
      --milestones 10,20,30,40,50 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --block-type ${block_type} \
      --activation ${activation} \
      --scheduler rop \
      --weight-decay 0.00001 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size ${batch_size} \
      --accu-steps 1 \
      --input-dim 40 \
      --channels 512,512,512,512,512,1536 \
      --context 5,3,3,3 \
      --dilation 1,2,3,4 \
      --stride 1,1,1,1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_baseline/${loss}/${input_norm}_em${embedding_size}_${block_type}_${activation}_dila4_wde5_2s \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_${encod}_baseline/${loss}/${input_norm}_em${embedding_size}_${block_type}_${activation}_dila4_wde5_2s/checkpoint_10.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --all-iteraion 0 \
      --log-interval 10
  done
fi


# CnCeleb
if [ $stage -le 150 ]; then
  model=TDNN_v5
  datasets=cnceleb
  #  feat=fb24
#  feat_type=pyfb
  feat_type=klfb
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_dim=40
  input_norm=Mean
  lr_ratio=0
  loss_ratio=1
  # _lrr${lr_ratio}_lsr${loss_ratio}

 for loss in arcdist; do
   feat=fb${input_dim}
   #_ws25
   echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
   python -W ignore TrainAndTest/train_egs.py \
     --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev12_${feat} \
     --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w \
     --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev12_${feat}_valid \
     --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
     --nj 12 \
     --shuffle \
     --epochs 60 \
     --patience 3 \
     --milestones 10,20,30,40 \
     --model ${model} \
     --scheduler rop \
     --weight-decay 0.0005 \
     --lr 0.1 \
     --alpha 0 \
     --feat-format kaldi \
     --embedding-size ${embedding_size} \
     --batch-size 128 \
     --random-chunk 200 400 \
     --input-dim ${input_dim} \
     --channels 512,512,512,512,1500 \
     --encoder-type ${encod} \
     --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs12_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var \
     --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs12_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var/checkpoint_40.pth \
     --cos-sim \
     --dropout-p 0.0 \
     --veri-pairs 9600 \
     --gpu-id 0,1 \
     --num-valid 2 \
     --loss-ratio ${loss_ratio} \
     --lr-ratio ${lr_ratio} \
     --loss-type ${loss} \
     --margin 0.2 \
     --s 30 \
     --remove-vad \
     --log-interval 10
  done
fi


if [ $stage -le 151 ]; then

  model=TDNN_v5
  datasets=cnceleb
  feat_type=klfb
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_dim=40
  input_norm=Mean
  lr_ratio=0
  loss_ratio=1
  # _lrr${lr_ratio}_lsr${loss_ratio}

 for loss in arcdist; do
   feat=fb${input_dim}
   python -W ignore TrainAndTest/train_egs.py \
     --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
     --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w \
     --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_valid \
     --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
     --nj 12 \
     --shuffle \
     --epochs 29 \
     --patience 3 \
     --milestones 10,20,30,40 \
     --model ${model} \
     --scheduler rop \
     --weight-decay 0.0005 \
     --lr 0.01 \
     --alpha 0 \
     --feat-format kaldi \
     --embedding-size ${embedding_size} \
     --batch-size 128 \
     --random-chunk 200 400 \
     --input-dim ${input_dim} \
     --channels 512,512,512,512,1500 \
     --encoder-type ${encod} \
     --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_lr${loss_ratio}_wd5e4_var \
     --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_lr${loss_ratio}_wd5e4_var/checkpoint_21.pth \
     --cos-sim \
     --dropout-p 0.0 \
     --veri-pairs 9600 \
     --gpu-id 0,1 \
     --num-valid 2 \
     --loss-ratio ${loss_ratio} \
     --lr-ratio ${lr_ratio} \
     --loss-type ${loss} \
     --margin 0.2 \
     --s 30 \
     --remove-vad \
     --log-interval 10
 done
fi

if [ $stage -le 155 ]; then
  model=TDNN_v5
  datasets=cnceleb
  embedding_size=512
  block_type=basic
  loss=subarc
  scheduler=exp
  optimizer=sgd

  # num_centers=3
  dev_sub=

  for loss in arcsoft; do
    feat=fb${input_dim}
  #   #_ws25
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
   python -W ignore TrainAndTest/train_egs.py \
     --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev${dev_sub}_${feat} \
     --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w \
     --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev${dev_sub}_${feat}_valid \
     --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
     --nj 12 \
     --shuffle \
     --epochs 60 \
     --patience 3 \
     --milestones 10,20,30,40 \
     --model ${model} \
     --optimizer ${optimizer} \
     --scheduler ${scheduler} \
     --weight-decay 0.0005 \
     --lr 0.1 \
     --alpha 0 \
     --feat-format kaldi \
     --embedding-size ${embedding_size} \
     --batch-size 128 \
     --random-chunk 200 400 \
     --input-dim ${input_dim} \
     --channels 512,512,512,512,1500 \
     --encoder-type ${encod} \
     --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs${dev_sub}_baseline/${loss}_${optimizer}_${scheduler}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var \
     --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs${dev_sub}_baseline/${loss}_${optimizer}_${scheduler}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var/checkpoint_40.pth \
     --cos-sim \
     --dropout-p 0.0 \
     --veri-pairs 9600 \
     --gpu-id 0,1 \
     --num-valid 2 \
     --loss-ratio ${loss_ratio} \
     --lr-ratio ${lr_ratio} \
     --loss-type ${loss} \
     --margin 0.2 \
     --s 30 \
     --remove-vad \
     --log-interval 10
  done
  exit
fi


if [ $stage -le 156 ]; then
    model=TDNN_v5
    datasets=cnceleb

   python -W ignore TrainAndTest/train_egs.py \
     --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
     --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w \
     --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_valid \
     --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
     --nj 12 \
     --shuffle \
     --epochs 42 \
     --patience 3 \
     --milestones 10,20,30,40 \
     --model ${model} \
     --scheduler rop \
     --weight-decay 0.0005 \
     --lr 0.1 \
     --alpha 0 \
     --feat-format kaldi \
     --embedding-size ${embedding_size} \
     --batch-size 128 \
     --random-chunk 200 400 \
     --input-dim ${input_dim} \
     --channels 512,512,512,512,1500 \
     --encoder-type ${encod} \
     --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var \
     --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}/${input_norm}_${encod}_em${embedding_size}_wd5e4_var/checkpoint_10.pth \
     --cos-sim \
     --dropout-p 0.0 \
     --veri-pairs 9600 \
     --gpu-id 0,1 \
     --num-valid 2 \
     --loss-ratio ${loss_ratio} \
     --lr-ratio ${lr_ratio} \
     --loss-type ${loss} \
     --margin 0.2 \
     --s 30 \
     --remove-vad \
     --log-interval 10
fi

if [ $stage -le 157 ]; then
  model=TDNN_v5
  datasets=cnceleb
  embedding_size=512
  encod=Ghos_v3
  block_type=basic
  input_norm=Mean
  loss=subarc
  scheduler=exp
  optimizer=sgd
  input_dim=40
  lr_ratio=0
  loss_ratio=0
  feat_type=klfb

  num_centers=3
  dev_sub=
  batch_size=256

  for loss in arcsoft ; do
    feat=fb${input_dim}
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev${dev_sub}_${feat} \
      --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev${dev_sub}_${feat}_valid \
      --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
      --nj 12 \
      --shuffle \
      --epochs 50 \
      --patience 3 \
      --milestones 10,20,30,40 \
      --model ${model} \
      --optimizer ${optimizer} \
      --scheduler ${scheduler} \
      --weight-decay 0.0005 \
      --lr 0.1 \
      --base-lr 0.00001 \
      --alpha 0 \
      --feat-format kaldi \
      --block-type ${block_type} \
      --embedding-size ${embedding_size} \
      --batch-size ${batch_size} \
      --random-chunk 200 400 \
      --input-dim ${input_dim} \
      --channels 512,512,512,512,1500 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs${dev_sub}_baseline/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_${encod}_em${embedding_size}_center${num_centers}_wd5e4_var \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs${dev_sub}_baseline/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_${encod}_em${embedding_size}_center${num_centers}_wd5e4_var/checkpoint_17.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-ratio ${loss_ratio} \
      --lr-ratio ${lr_ratio} \
      --loss-type ${loss} \
      --num-center ${num_centers} \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --log-interval 10 \
      --test-interval 2
  done
  exit
fi

if [ $stage -le 158 ]; then
    model=TDNN_v5
    datasets=cnceleb
  mask_layer=baseline

  weight=vox2_cf
  loss=arcsoft
  scheduler=exp
  optimizer=sgd
  feat=fb${input_dim}
  batch_size=256

  for weight in vox2_cf; do
    #_ws25
    echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/train_egs.py \
     --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
     --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w \
     --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_valid \
     --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
     --nj 12 \
     --epochs 50 \
     --batch-size ${batch_size} \
     --patience 3 \
     --milestones 10,20,30,40 \
     --model ${model} \
     --optimizer ${optimizer} \
     --scheduler ${scheduler} \
     --weight-decay 0.0005 \
     --lr 0.1 \
     --base-lr 0.00001 \
     --alpha 0 \
     --feat-format kaldi \
     --embedding-size ${embedding_size} \
     --random-chunk 200 400 \
     --input-dim ${input_dim} \
     --channels 512,512,512,512,1500 \
     --mask-layer ${mask_layer} \
     --encoder-type ${encod} \
     --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${encod}_em${embedding_size}_wd5e4_var \
     --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${encod}_em${embedding_size}_wd5e4_var/checkpoint_20.pth \
     --cos-sim \
     --dropout-p 0.0 \
     --veri-pairs 9600 \
     --gpu-id 0,1 \
     --num-valid 2 \
     --loss-ratio ${loss_ratio} \
     --lr-ratio ${lr_ratio} \
     --loss-type ${loss} \
     --margin 0.2 \
     --s 30 \
     --remove-vad \
     --log-interval 10 \
     --test-interval 2
  done

  mask_layer=attention0
  for weight in vox2_cf; do
    python -W ignore TrainAndTest/train_egs.py \
     --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
     --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w \
     --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_valid \
     --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
     --nj 12 \
     --epochs 50 \
     --batch-size ${batch_size} \
     --patience 3 \
     --milestones 10,20,30,40 \
     --model ${model} \
     --optimizer ${optimizer} \
     --scheduler ${scheduler} \
     --weight-decay 0.0005 \
     --lr 0.1 \
     --base-lr 0.00001 \
     --alpha 0 \
     --feat-format kaldi \
     --embedding-size ${embedding_size} \
     --random-chunk 200 400 \
     --input-dim ${input_dim} \
     --channels 512,512,512,512,1500 \
     --mask-layer ${mask_layer} \
     --init-weight ${weight} \
     --encoder-type ${encod} \
     --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${encod}_em${embedding_size}_${weight}_wd5e4_var \
     --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${encod}_em${embedding_size}_${weight}_wd5e4_var/checkpoint_20.pth \
     --cos-sim \
     --dropout-p 0.0 \
     --veri-pairs 9600 \
     --gpu-id 0,1 \
     --num-valid 2 \
     --loss-ratio ${loss_ratio} \
     --lr-ratio ${lr_ratio} \
     --loss-type ${loss} \
     --margin 0.2 \
     --s 30 \
     --remove-vad \
     --log-interval 10 \
     --test-interval 2
  done
  exit
fi


# Aishell2
if [ $stage -le 200 ]; then
  #  model=TDNN
  # datasets=aidata
  datasets=aishell2

  feat=fb40
  feat_type=klfb
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_norm=Mean
  batch_size=256
  scheduler=rop
  optimizer=sgd

  for model in TDNN_v5; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # kernprof -l -v TrainAndTest/Spectrogram/train_egs.py \
    python -W ignore TrainAndTest/train_egs.py \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_${feat}_valid \
      --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_${feat} \
      --input-norm ${input_norm} \
      --random-chunk 200 400 \
      --nj 12 \
      --epochs 50 \
      --patience 3 \
      --milestones 10,20,30,40 \
      --model ${model} \
      --optimizer ${optimizer} \
      --scheduler ${scheduler} \
      --weight-decay 0.0005 \
      --lr 0.1 \
      --alpha 0 \
      --feat-format kaldi \
      --channels 512,512,512,512,1500 \
      --embedding-size ${embedding_size} \
      --batch-size ${batch_size} \
      --accu-steps 1 \
      --input-dim 40 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${encod}_em${embedding_size}_wd5e4_var \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_egs_baseline/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${encod}_em${embedding_size}_wd5e4_var/checkpoint_53.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --all-iteraion 0 \
      --remove-vad \
      --log-interval 10
  done
  exit
fi




