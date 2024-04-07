#!/usr/bin/env bash

stage=607
waited=0
while [ `ps 99278 | wc -l` -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done
#stage=10

lstm_dir=/home/yangwenhao/project/lstm_speaker_verification

# ===============================    LoResNet10    ===============================
if [ $stage -le 0 ]; then
  for loss in asoft soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"

    python TrainAndTest/test_sitw.py \
      --nj 12 \
      --check-path Data/checkpoint/LoResNet10/spect/${loss} \
      --veri-pairs 12800 \
      --loss-type ${loss} \
      --gpu-id 0 \
      --epochs 20
  done
fi

if [ $stage -le 5 ]; then
  model=LoResNet10
  #  --resume Data/checkpoint/LoResNet10/spect/${loss}_dp25_128/checkpoint_24.pth \
  #  for loss in soft ; do
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
    python TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/Vox1_spect/dev_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_spect/all_wcmvn \
      --nj 12 \
      --model ${model} \
      --embedding-size 128 \
      --resume Data/checkpoint/LoResNet10/spect/${loss}_wcmvn/checkpoint_24.pth \
      --xvector-dir Data/xvector/LoResNet10/spect/${loss}_wcmvn \
      --loss-type ${loss} \
      --trials trials \
      --num-valid 0 \
      --gpu-id 0
  done

#  for loss in center ; do
fi

if [ $stage -le 6 ]; then
  model=LoResNet10
  #  --resume Data/checkpoint/LoResNet10/spect/${loss}_dp25_128/checkpoint_24.pth \
  #  for loss in soft ; do
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"

    python TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/Vox1_spect/dev_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_spect/test_wcmvn \
      --nj 12 \
      --model ${model} \
      --channels 64,128,256,256 \
      --resnet-size 18 \
      --extract \
      --kernel-size 3,3 \
      --embedding-size 128 \
      --resume Data/checkpoint/LoResNet18/spect/soft_dp25/checkpoint_24.pth \
      --xvector-dir Data/xvector/LoResNet18/spect/soft_dp05 \
      --loss-type ${loss} \
      --trials trials.backup \
      --num-valid 0 \
      --gpu-id 0
  done

fi

# ===============================    ExResNet    ===============================

if [ $stage -le 7 ]; then
  model=ExResNet
  datasets=vox1
  feat=fb64_3w
  loss=soft
  for encod in SAP SASP STAP None; do
    echo -e "\n\033[1;4;31m Test ${model}_${encod} with ${loss}\033[0m\n"
    python TrainAndTest/test_vox1.py \
      --train-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/vox1/pydb/dev_${feat} \
      --test-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/vox1/pydb/test_${feat} \
      --nj 12 \
      --model ${model} \
      --resnet-size 10 \
      --remove-vad \
      --kernel-size 5,5 \
      --embedding-size 128 \
      --resume Data/checkpoint/${model}10/${datasets}_${encod}/${feat}/${loss}/checkpoint_24.pth \
      --xvector-dir Data/xvector/${model}10/${datasets}_${encod}/${feat}/${loss} \
      --loss-type ${loss} \
      --trials trials \
      --num-valid 2 \
      --gpu-id 0
  done
fi

# ===============================    TDNN    ===============================

#stage=200
if [ $stage -le 15 ]; then
  model=TDNN
  #  feat=fb40
  #  for loss in soft ; do
  #    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
  #    python TrainAndTest/test_egs.py \
  #      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb40_no_sil \
  #      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb40_no_sil \
  #      --nj 12 \
  #      --model ${model} \
  #      --embedding-size 128 \
  #      --feat-dim 40 \
  #      --resume Data/checkpoint/${model}/${feat}/${loss}/checkpoint_18.pth
  #      --loss-type soft \
  #      --num-valid 2 \
  #      --gpu-id 1
  #  done

  feat=fb40_wcmvn
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
    python TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb40_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb40_wcmvn \
      --nj 14 \
      --model ${model} \
      --embedding-size 128 \
      --feat-dim 40 \
      --remove-vad \
      --extract \
      --valid \
      --resume Data/checkpoint/TDNN/fb40_wcmvn/soft_fix/checkpoint_40.pth \
      --xvector-dir Data/xvectors/TDNN/fb40_wcmvn/soft_fix \
      --loss-type soft \
      --num-valid 2 \
      --gpu-id 1
  done

fi

#stage=200
if [ $stage -le 20 ]; then
  model=LoResNet10
  feat=spect
  datasets=libri
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
    #    python TrainAndTest/test_egs.py \
    #      --train-dir ${lstm_dir}/data/libri/spect/dev_noc \
    #      --test-dir ${lstm_dir}/data/libri/spect/test_noc \
    #      --nj 12 \
    #      --model ${model} \
    #      --channels 4,32,128 \
    #      --embedding-size 128 \
    #      --resume Data/checkpoint/${model}/${datasets}/${feat}/${loss}/checkpoint_15.pth \
    #      --loss-type soft \
    #      --dropout-p 0.25 \
    #      --num-valid 1 \
    #      --gpu-id 1
    #
    #    python TrainAndTest/test_egs.py \
    #      --train-dir ${lstm_dir}/data/libri/spect/dev_noc \
    #      --test-dir ${lstm_dir}/data/libri/spect/test_noc \
    #      --nj 12 \
    #      --model ${model} \
    #      --channels 4,32,128 \
    #      --embedding-size 128 \
    #      --resume Data/checkpoint/${model}/${datasets}/${feat}/${loss}_var/checkpoint_15.pth \
    #      --loss-type soft \
    #      --dropout-p 0.25 \
    #      --num-valid 1 \
    #      --gpu-id 1
    #    python TrainAndTest/test_egs.py \
    #      --train-dir ${lstm_dir}/data/libri/spect/dev_noc \
    #      --test-dir ${lstm_dir}/data/libri/spect/test_noc \
    #      --nj 12 \
    #      --model ${model} \
    #      --channels 4,32,128 \
    #      --embedding-size 128 \
    #      --alpha 9.8 \
    #      --extract \
    #      --resume Data/checkpoint/LoResNet10/libri/spect_noc/soft/checkpoint_15.pth \
    #      --xvector-dir Data/xvectors/LoResNet10/libri/spect_noc/soft_128 \
    #      --loss-type ${loss} \
    #      --dropout-p 0.25 \
    #      --num-valid 2 \
    #      --gpu-id 1
    python TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/libri/spect/dev_noc \
      --test-dir ${lstm_dir}/data/libri/spect/test_noc \
      --nj 12 \
      --model ${model} \
      --channels 4,32,128 \
      --embedding-size 128 \
      --alpha 9.8 \
      --extract \
      --resume Data/checkpoint/LoResNet10/libri/spect_noc/soft_fix_43/checkpoint_15.pth \
      --xvector-dir Data/xvectors/LoResNet10/libri/spect_noc/soft_128 \
      --loss-type ${loss} \
      --dropout-p 0.25 \
      --num-valid 2 \
      --gpu-id 1

    #    python TrainAndTest/test_egs.py \
    #      --train-dir ${lstm_dir}/data/libri/spect/dev_noc \
    #      --test-dir ${lstm_dir}/data/libri/spect/test_noc \
    #      --nj 12 \
    #      --model ${model} \
    #      --channels 4,16,64 \
    #      --embedding-size 128 \
    #      --resume Data/checkpoint/LoResNet10/libri/spect_noc/soft_var/checkpoint_15.pth \
    #      --loss-type soft \
    #      --dropout-p 0.25 \
    #      --num-valid 2 \
    #      --gpu-id 1
  done
fi

#stage=250
if [ $stage -le 25 ]; then
  model=LoResNet10
  feat=spect_wcmvn
  datasets=timit
  for loss in soft; do
    #    echo -e "\033[31m==> Loss type: ${loss} variance_fix length \033[0m"
    #    python TrainAndTest/test_egs.py \
    #      --train-dir ${lstm_dir}/data/timit/spect/train_noc \
    #      --test-dir ${lstm_dir}/data/timit/spect/test_noc \
    #      --nj 12 \
    #      --model ${model} \
    #      --channels 4,16,64 \
    #      --embedding-size 128 \
    #      --resume Data/checkpoint/LoResNet10/timit_spect/soft_fix/checkpoint_15.pth \
    #      --loss-type soft \
    #      --dropout-p 0.25 \
    #      --num-valid 2 \
    #      --gpu-id 1

    echo -e "\033[31m==> Loss type: ${loss} variance_fix length \033[0m"
    python TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/timit/spect/train_noc \
      --test-dir ${lstm_dir}/data/timit/spect/train_noc \
      --nj 12 \
      --model ${model} \
      --xvector-dir Data/xvectors/LoResNet10/timit_spect/soft_var \
      --channels 4,16,64 \
      --embedding-size 128 \
      --resume Data/checkpoint/LoResNet10/timit_spect/soft_var/checkpoint_15.pth \
      --loss-type soft \
      --dropout-p 0.25 \
      --num-valid 2 \
      --gpu-id 1
  done
fi

if [ $stage -le 26 ]; then
  feat_type=spect
  feat=log
  loss=soft
  encod=None
  dataset=timit
  block_type=None

  for loss in soft; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model LoResNet \
      --resnet-size 8 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/train_${feat} \
      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/train_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${dataset}/${feat_type}/test_${feat} \
      --feat-format kaldi \
      --input-norm None \
      --input-dim 161 \
      --nj 12 \
      --embedding-size 128 \
      --loss-type ${loss} \
      --encoder-type None \
      --block-type ${block_type} \
      --kernel-size 5,5 \
      --stride 2 \
      --channels 4,16,64 \
      --alpha 10.8 \
      --margin 0.3 \
      --s 30 \
      --m 3 \
      --input-length var \
      --frame-shift 300 \
      --dropout-p 0.5 \
      --xvector-dir Data/xvector/LoResNet8/timit/spect_egs_log/soft_dp05/epoch_12_var \
      --resume Data/checkpoint/LoResNet8/timit/spect_egs_log/soft_dp05/checkpoint_12.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

# ===============================    ResNet20    ===============================

#stage=100
if [ $stage -le 30 ]; then
  model=ResNet20
  feat=spect_wcmvn
  datasets=vox
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} fix length \033[0m"
    python TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/Vox1_spect/dev_257_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_spect/test_257_wcmvn \
      --nj 12 \
      --model ${model} \
      --embedding-size 128 \
      --resume Data/checkpoint/ResNet20/spect_257_wcmvn/soft_dp0.5/checkpoint_24.pth \
      --loss-type soft \
      --dropout-p 0.5 \
      --num-valid 2 \
      --gpu-id 1
  done
fi

#stage=100
if [ $stage -le 40 ]; then
  model=ExResNet34
  #  for loss in soft asoft ; do
  for loss in soft; do
    echo -e "\n\033[1;4;31m Test ${model} with ${loss} vox_wcmvn\033[0m\n"
    python -W ignore TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb64_wcmvn \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb64_wcmvn \
      --nj 12 \
      --epochs 30 \
      --model ExResNet34 \
      --remove-vad \
      --resnet-size 34 \
      --embedding-size 128 \
      --feat-dim 64 \
      --kernel-size 3,3 \
      --stride 1 \
      --time-dim 1 --avg-size 1 \
      --resume Data/checkpoint/ExResNet34/vox1/fb64_wcmvn/soft_14/checkpoint_22.pth \
      --xvector-dir Data/xvectors/ExResNet34/vox1/fb64_wcmvn/soft_14 \
      --input-per-spks 192 \
      --num-valid 2 \
      --extract \
      --gpu-id 1 \
      --loss-type ${loss}

    #    echo -e "\n\033[1;4;31m Test ${model} with ${loss} vox_noc \033[0m\n"
    #    python -W ignore TrainAndTest/test_egs.py \
    #      --train-dir ${lstm_dir}/data/Vox1_pyfb64/dev_noc \
    #      --test-dir ${lstm_dir}/data/Vox1_pyfb64/test_noc \
    #      --nj 12 \
    #      --epochs 30 \
    #      --model ExResNet34 \
    #      --remove-vad \
    #      --resnet-size 34 \
    #      --embedding-size 128 \
    #      --feat-dim 64 \
    #      --kernel-size 3,3 \
    #      --stride 1 \
    #      --avg-size 1 \
    #      --resume Data/checkpoint/ExResNet34/vox1/fb64_wcmvn/soft_14/checkpoint_22.pth \
    #      --input-per-spks 192 \
    #      --time-dim 1 \
    #      --extract \
    #      --num-valid 2 \
    #      --loss-type ${loss}
  done
fi

# ===============================    TDNN    ===============================

if [ $stage -le 50 ]; then
  #  for loss in soft asoft ; do
  model=SiResNet34
  datasets=vox1
  feat=fb64_mvnorm
  for loss in soft; do
    echo -e "\n\033[1;4;31m Training ${model} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/Vox1_pyfb/dev_fb64 \
      --test-dir ${lstm_dir}/data/Vox1_pyfb/test_fb64 \
      --nj 14 \
      --epochs 40 \
      --model ${model} \
      --resnet-size 34 \
      --embedding-size 128 \
      --feat-dim 64 \
      --remove-vad \
      --extract \
      --valid \
      --kernel-size 3,3 \
      --stride 1 \
      --mvnorm \
      --input-length fix \
      --test-input-per-file 4 \
      --xvector-dir Data/xvectors/${model}/${datasets}/${feat}/${loss} \
      --resume Data/checkpoint/SiResNet34/vox1/fb64_cmvn/soft/checkpoint_21.pth \
      --input-per-spks 192 \
      --gpu-id 1 \
      --num-valid 2 \
      --loss-type ${loss}
  done
fi

# ===============================    TDNN    ===============================

if [ $stage -le 55 ]; then
  #  for loss in soft asoft ; do
  model=GradResNet
  datasets=vox1
  feat=fb64_mvnorm
  for loss in soft; do
    echo -e "\n\033[1;4;31m Training ${model} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/vox1/spect/dev_power \
      --test-dir ${lstm_dir}/data/vox1/spect/test_power \
      --nj 12 \
      --epochs 18 \
      --model ${model} \
      --resnet-size 8 \
      --inst-norm \
      --embedding-size 128 \
      --feat-dim 161 \
      --valid \
      --input-length fix \
      --test-input-per-file 4 \
      --xvector-dir Data/xvector/GradResNet8_inst/vox1_power/spect_time/soft_dp25 \
      --resume Data/checkpoint/GradResNet8_inst/vox1_power/spect_time/soft_dp25/checkpoint_18.pth \
      --input-per-spks 224 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type ${loss}
  done
fi

if [ $stage -le 56 ]; then
  #  for loss in soft asoft ; do
  model=GradResNet
  datasets=vox1
  feat=spect
  for loss in mulcenter center; do
    echo -e "\n\033[1;4;31m Training ${model} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/test_vox1.py \
      --train-dir ${lstm_dir}/data/vox1/spect/dev_power \
      --test-dir ${lstm_dir}/data/vox1/spect/test_power \
      --nj 12 \
      --epochs 18 \
      --model ${model} \
      --resnet-size 8 \
      --inst-norm \
      --embedding-size 128 \
      --feat-dim 161 \
      --valid \
      --input-length fix \
      --stride 2 \
      --xvector-dir Data/xvector/GradResNet8/vox1_power/spect_egs/${loss}_dp25 \
      --resume Data/checkpoint/GradResNet8/vox1/spect_egs/${loss}_dp25/checkpoint_24.pth \
      --input-per-spks 224 \
      --gpu-id 0 \
      --num-valid 2 \
      --extract \
      --loss-type ${loss}
  done
fi

# stage=100
if [ $stage -le 60 ]; then
  dataset=army
  resnet_size=10
  for loss in soft; do # 32,128,512; 8,32,128
    #  Data/xvector/LoResNet10/army_v1/spect_egs_mean/soft_dp01
    echo -e "\n\033[1;4;31m Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_vox1.py \
      --model LoResNet \
      --train-dir ${lstm_dir}/data/${dataset}/spect/dev_8k \
      --test-dir ${lstm_dir}/data/${dataset}/spect/test_8k \
      --feat-format kaldi \
      --resnet-size ${resnet_size} \
      --input-per-spks 224 \
      --nj 16 \
      --embedding-size 128 \
      --channels 64,128,256,256 \
      --loss-type ${loss} \
      --input-length fix \
      --time-dim 1 \
      --test-input-per-file 4 \
      --inst-norm \
      --stride 2 \
      --dropout-p 0.1 \
      --xvector-dir Data/xvector/LoResNet${resnet_size}/army_v1/spect_egs_mean/soft_dp01 \
      --resume Data/checkpoint/LoResNet${resnet_size}/army_v1/spect_egs_mean/soft_dp01/checkpoint_24.pth \
      --trials trials \
      --gpu-id 0
  done

fi

if [ $stage -le 74 ]; then
  feat_type=klfb
  feat=fb40
  loss=arcsoft
  model=TDNN_v5
  encod=STAP
  dataset=vox2
  subset=test
  test_set=vox1
  input_dim=40
  input_norm=Mean

  # Training set: voxceleb 2 40-dimensional log fbanks kaldi  Loss: arcsoft sgd exp
  # Cosine Similarity
  #
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #|     vox1-test     |   2.3913%   |   0.2701    |   0.2368    |    0.3318    | 20211115 09:10:35 |

  for embedding_size in 512; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev_${feat}_valid \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
      --feat-format kaldi \
      --input-norm ${input_norm} \
      --input-dim ${input_dim} \
      --nj 12 \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type ${encod} \
      --channels 512,512,512,512,1500 \
      --stride 1,1,1,1 \
      --margin 0.2 \
      --s 30 \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/${model}/${dataset}/${feat_type}_egs_baseline/${loss}_sgd_exp/input${input_norm}_${encod}_em${embedding_size}_wde4_var/${test_set}_${subset}_epoch_50_var \
      --resume Data/checkpoint/${model}/${dataset}/${feat_type}_egs_baseline/${loss}_sgd_exp/input${input_norm}_${encod}_em${embedding_size}_wde4_var/checkpoint_50.pth \
      --gpu-id 1 \
      --remove-vad \
      --cos-sim
  done
  exit
fi

if [ $stage -le 75 ]; then
  feat_type=klfb
  feat=fb40
  loss=arcsoft
  encoder_type=STAP

  model=SlimmableTDNN
  datasets=vox1
  subset=test
  test_set=vox1
  input_dim=40
  input_norm=Mean
  optimizer=sgd
  scheduler=rop
  mask_layer=baseline
  batch_size=256
  alpha=0

  # Training set: voxceleb 1 40-dimensional log fbanks kaldi  Loss: arcsoft
  # Cosine Similarity
  #
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #|     vox1-test     |   4.3054%   |   0.2299    |   0.4212    |    0.6275    | 20211104 15:29:25 | embedding_size=256
  #|     vox1-test     |   4.3478%   |   0.1949    |   0.4755    |    0.5709    | 20211104 15:30:08 | embedding_size=512

  # Training set: voxceleb 1 40-dimensional log fbanks kaldi  Loss: arcsoft  sgd exp
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #|     vox1-test     |   4.9841%   |   0.1783    |   0.5531    |    0.6566    | 20211115 09:03:38 |

  # Training set: voxceleb 1 40-dimensional log fbanks kaldi epoch 45 where lr=0.0001
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #|     vox1-test     |   4.4115%   |   0.1958    |   0.4680    |    0.5846    | 20211130 17:14:14 | arcsoft
  #|     vox1-test     |   4.7561%   |   0.1878    |   0.4709    |    0.6445    | 20211130 17:18:04 | minarcsoft*0.1+arc
  #|     vox1-dev      |   0.1744%   |   0.3415    |   0.0157    |    0.0271    | 20211130 17:53:52 | arcsoft
  #|     vox1-dev      |   0.1552%   |   0.3450    |   0.0147    |    0.0334    | 20211130 17:35:29 | minarcsoft*0.1+arc
  # 20211130 18:08 min seems to be better on dev set

  # TDNN_v5-vox1-klfb40
  #|     vox1-test     |  4.73±0.05  |             | 0.4881±0.0154 | 0.5986±0.0136 |
  # SlimmableTDNN-vox1-klfb40
  #|     vox1-test     |  5.01±0.10  |             | 0.5041±0.0418 | 0.6068±0.0700 | width 1.0
  #|     vox1-test     |  5.00±0.16  |             | 0.4716±0.0230 | 0.5766±0.0314 | width 0.75
  #|     vox1-test     |  4.93±0.14  |             | 0.4987±0.0354 | 0.6291±0.0250 | width 0.5
  #|     vox1-test     |  5.44±0.22  |             | 0.5182±0.0244 | 0.6418±0.0057 | width 0.25

  for seed in 123456 123457 123458; do
  for embedding_size in 512; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    model_dir=${model}/${datasets}/${feat_type}${input_dim}_egs_${mask_layer}/${seed}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${encoder_type}_em${embedding_size}_dp00_alpha${alpha}_${loss_str}wd5e4_var3

    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --width-mult-list 1.0,0.75,0.5,0.25 \
      --train-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
      --feat-format kaldi \
      --input-norm ${input_norm} \
      --input-dim ${input_dim} \
      --nj 4 \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --channels 512,512,512,512,1536 \
      --stride 1,1,1,1 \
      --encoder-type ${encoder_type} \
      --margin 0.2 \
      --s 30 \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/${model_dir}/${test_set}_${subset}_best_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --gpu-id 2 \
      --remove-vad \
      --cos-sim
  done
  done
  exit
fi

if [ $stage -le 76 ]; then
  feat_type=pyfb
  feat=fb40
  loss=soft
  model=TDNN_v5
  encod=None
  dataset=vox1
  subset=test
  test_set=sitw

  # Training set: voxceleb 1 40-dimensional log fbanks ws25  Loss: soft
  # Cosine Similarity
  #
  # |   Test Set   |   EER ( % ) | Threshold | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  # +--------------+-------------+-----------+-------------+--------------+-------------------+
  # |  vox1-test   |   4.5864%   |   0.2424    |   0.4426    |    0.5638    | 20210531 17:00:32 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # | cnceleb-test |  16.6445%   |   0.2516    |   0.7963    |    0.9313    | 20210531 17:37:23 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # | aidata-test  |  10.8652%   |   0.3349    |   0.7937    |    0.9379    | 20210531 17:26:26 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # |  magic-test  |  18.1604%   |   0.3161    |   0.9939    |    0.9977    | 20210531 17:13:37 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # |   sitw dev      |    x%    |   0.2708  |    0.3919   |     0.5955   | 20210529     |
  # +-----------------+---------------+-----------+-------------+--------------+--------------+
  # |   sitw eval     |    x%    |   0.2695  |    0.4683   |     0.7143   | 20210529     |
  # +-----------------+---------------+-----------+-------------+--------------+-------------------+
  # |   magic-test    |   x%    |   0.3359  |    0.9984   |     0.9990   | 20210529 22:11:08 |
  # +-----------------+---------------+-----------+-------------+--------------+-------------------+
  # +-----------------+---------------+-----------+---------------+----------------+--------------+
  # |  aishell2 test  |   x%    |   0.2786811   |    0.8212      |     0.9527     |   20210515   |
  # +-----------------+---------------+-----------+---------------+----------------+--------------+
  # |   aidata-test   |    x%    |   0.3503  |    0.7233     |     0.9196     | 20210529 21:04:32 |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+

  # sitw dev Test  ERR: 4.0046%, Threshold: 0.2708 mindcf-0.01: 0.3919, mindcf-0.001: 0.5955.
  # Test  ERR: 4.5107%, Threshold: 0.2695 mindcf-0.01: 0.4683, mindcf-0.001: 0.7143

  for subset in dev eval; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat}_ws25 \
      --feat-format kaldi \
      --input-norm Mean \
      --input-dim 40 \
      --nj 12 \
      --embedding-size 256 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --channels 512,512,512,512,1500 \
      --margin 0.25 \
      --s 30 \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/vox1/pyfb_egs_baseline/soft/featfb40_ws25_inputMean_STAP_em256_wd5e4_var/${test_set}_${subset}_epoch_40_var \
      --resume Data/checkpoint/TDNN_v5/vox1/pyfb_egs_baseline/soft/featfb40_ws25_inputMean_STAP_em256_wd5e4_var/checkpoint_40.pth \
      --gpu-id 1 \
      --remove-vad \
      --cos-sim
  done
  exit
fi

if [ $stage -le 77 ]; then
  feat_type=spect
  feat=log
  loss=arcsoft
  model=TDNN_v5
  encod=None
  dataset=aishell2
  test_set=aishell2

  # Training set: aishell 2 Loss: arcosft

  # |   Test Set      |   EER (%)  |   Threshold   |  MinDCF-0.01   |   MinDCF-0.01  |     Date     |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |  aishell2 test  |    1.4740%    |   0.2053137   |    0.2740      |     0.4685     |   20210517   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |   vox1 test     |   22.3118%    |   0.2578884   |    0.8733      |     0.8923     |   20210517   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |  aidata test    |   11.4180%    |   0.3180055   |    0.7140      |     0.8919     |   20210517   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |  cnceleb test   |   27.6964%    |   0.2075080   |    0.9081      |     0.9997     |   20210517   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/aishell2/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/aishell2/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/aishell2/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
      --trials trials_30w \
      --feat-format kaldi \
      --input-norm Mean \
      --block-type basic \
      --input-dim 161 \
      --nj 12 \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --channels 512,512,512,512,1500 \
      --stride 1 \
      --margin 0.25 \
      --s 30 \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/aishell2/spect_egs_baseline/arcsoft_0ce/inputMean_STAP_em512_wde4/${test_set}_${subset}_epoch_60_var \
      --resume Data/checkpoint/TDNN_v5/aishell2/spect_egs_baseline/arcsoft_0ce/inputMean_STAP_em512_wde4/checkpoint_60.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

if [ $stage -le 78 ]; then
  feat_type=klsp
  feat=log
  loss=arcsoft
  model=TDNN_v5
  encod=None
  dataset=vox1
  test_set=vox1

#  for subset in test; do # 32,128,512; 8,32,128
#    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
#    python -W ignore TrainAndTest/test_egs.py \
#      --model ${model} \
#      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
#      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev/trials_dir \
#      --train-trials trials_2w \
#      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_valid \
#      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset} \
#      --trials trials \
#      --feat-format kaldi \
#      --input-norm Mean \
#      --block-type basic \
#      --input-dim 161 \
#      --nj 12 \
#      --embedding-size 512 \
#      --loss-type ${loss} \
#      --encoder-type STAP \
#      --channels 512,512,512,512,1500 \
#      --stride 1 \
#      --margin 0.2 \
#      --s 30 \
#      --input-length var \
#      --frame-shift 300 \
#      --xvector-dir Data/xvector/TDNN_v5/vox1/klsp_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/${test_set}_${subset}_epoch_40_var \
#      --resume Data/checkpoint/TDNN_v5/vox1/klsp_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/checkpoint_40.pth \
#      --gpu-id 0 \
#      --cos-sim
#  done

#  for subset in test; do # 32,128,512; 8,32,128
#    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
#    python -W ignore TrainAndTest/test_egs.py \
#      --model ${model} \
#      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
#      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev/trials_dir \
#      --train-trials trials_2w \
#      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_valid \
#      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset} \
#      --trials trials \
#      --feat-format kaldi \
#      --input-norm Mean \
#      --block-type basic \
#      --input-dim 161 \
#      --nj 12 \
#      --embedding-size 512 \
#      --loss-type ${loss} \
#      --encoder-type STAP \
#      --channels 256,256,256,256,768 \
#      --stride 1 \
#      --margin 0.2 \
#      --s 30 \
#      --input-length var \
#      --frame-shift 300 \
#      --xvector-dir Data/xvector/TDNN_v5/vox1/klsp_egs_baseline/arcsoft/Mean_STAP_em512_chn256_wd5e4_var/${test_set}_${subset}_epoch_40_var \
#      --resume Data/checkpoint/TDNN_v5/vox1/klsp_egs_baseline/arcsoft/Mean_STAP_em512_chn256_wd5e4_var/checkpoint_40.pth \
#      --gpu-id 0 \
#      --cos-sim
#  done
  subset=test
  for weight in mel clean aug vox2; do
    mask_layer=attention
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset} \
      --trials trials \
      --feat-format kaldi \
      --input-norm Mean \
      --mask-layer ${mask_layer} \
      --init-weight ${weight} \
      --block-type basic \
      --input-dim 161 \
      --nj 12 \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --channels 256,256,256,256,768 \
      --stride 1 \
      --margin 0.2 \
      --s 30 \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/vox1/klsp_egs_attention/arcsoft/Mean_STAP_em512_${weight}_wd5e4_var/${test_set}_${subset}_epoch_40_var \
      --resume Data/checkpoint/TDNN_v5/vox1/klsp_egs_attention/arcsoft/Mean_STAP_em512_${weight}_wd5e4_var/checkpoint_40.pth \
      --gpu-id 0 \
      --cos-sim
  done

  exit
fi

if [ $stage -le 79 ]; then
  feat_type=pyfb
  feat=fb40
  loss=arcsoft
  model=TDNN_v5
  encod=None
  dataset=vox2
  test_set=cnceleb

  # Training set: voxceleb 2 40-dimensional log fbanks ws25  Loss: soft
  # Cosine Similarity
  # Data/checkpoint/TDNN_v5/vox2/pyfb_egs_baseline/soft/featfb40_ws25_inputMean_STAP_em512_wd5e4_var/checkpoint_40.pth
  # |   Test Set      |    EER ( % )  | Threshold | MinDCF-0.01 | MinDCF-0.001 |     Date     |
  # +-----------------+---------------+-----------+-------------+--------------+--------------+
  # |   vox1 test     |    2.6670%    |   0.2869  |    0.2984   |     0.4581   | 20210529     |
  # +-----------------+---------------+-----------+-------------+--------------+--------------+
  # |  cnceleb test   |   13.8038%    |   0.2597  |    0.7632   |     0.9349   | 20210529     |
  # +-----------------+---------------+-----------+-------------+--------------+--------------+
  # |   sitw dev      |    4.0046%    |   0.2708  |    0.3919   |     0.5955   | 20210529     |
  # +-----------------+---------------+-----------+-------------+--------------+--------------+
  # |   sitw eval     |    4.5107%    |   0.2695  |    0.4683   |     0.7143   | 20210529     |
  # +-----------------+---------------+-----------+-------------+--------------+-------------------+
  # |   magic-test    |   14.8940%    |   0.3359  |    0.9984   |     0.9990   | 20210529 22:11:08 |
  # +-----------------+---------------+-----------+-------------+--------------+-------------------+
  # +-----------------+---------------+-----------+---------------+----------------+--------------+
  # |  aishell2 test  |   10.8300%    |   0.2787  |    0.8212      |     0.9527     |   20210515   |
  # +-----------------+---------------+-----------+---------------+----------------+--------------+
  # |   aidata-test   |    8.7480%    |   0.3503  |    0.7233     |     0.9196     | 20210529 21:04:32 |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+

  # sitw dev Test  ERR: 4.0046%, Threshold: 0.2708 mindcf-0.01: 0.3919, mindcf-0.001: 0.5955.
  # Test  ERR: 4.5107%, Threshold: 0.2695 mindcf-0.01: 0.4683, mindcf-0.001: 0.7143

  # Data/checkpoint/TDNN_v5/vox2/pyfb_egs_baseline/arcsoft/featfb40_ws25_inputMean_STAP_em512_wde4_var/checkpoint_50.phi_theta
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # |   Test Set   |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # |  vox1-test   |   2.3277%   |   0.3319    |   0.2805    |    0.4108    | 20210812 20:38:25 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # | cnceleb-test |  15.5626%   |   0.2350    |   0.7575    |    0.8728    | 20210812 21:10:24 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # |   sitw-dev   |   2.8109%   |   0.3261    |   0.3045    |    0.4622    | 20210813 13:43:48 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  # |  sitw-eval   |   3.4445%   |   0.3201    |   0.3290    |    0.5059    | 20210813 13:45:34 |
  # +--------------+-------------+-------------+-------------+--------------+-------------------+
  #  for test_set in vox1 aishell2; do # 32,128,512; 8,32,128
  for s in advertisement drama entertainment interview live_broadcast movie play recitation singing speech vlog; do
    subset=test
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/vox2/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --trials trials_${s} \
      --score-suffix ${s} \
      --valid-dir ${lstm_dir}/data/vox2/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat}_ws25 \
      --feat-format kaldi \
      --input-norm Mean \
      --block-type basic \
      --input-dim 40 \
      --nj 12 \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --channels 512,512,512,512,1500 \
      --stride 1,1,1,1 \
      --margin 0.3 \
      --s 15 \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/vox2/pyfb_egs_baseline/${loss}/featfb40_ws25_inputMean_STAP_em512_wde4_var/${test_set}_${subset}_epoch_50_var \
      --resume Data/checkpoint/TDNN_v5/vox2/pyfb_egs_baseline/${loss}/featfb40_ws25_inputMean_STAP_em512_wde4_var/checkpoint_50.pth \
      --gpu-id 0 \
      --remove-vad \
      --cos-sim
  done
  exit
fi

if [ $stage -le 80 ]; then
  feat_type=spect
  feat=log
  loss=arcsoft
  model=TDNN_v5
  encod=None
  dataset=vox1
  test_set=aidata

  # Training set: voxceleb 2 161-dimensional spectrogram  Loss: arcosft
  # Cosine Similarity
  #
  # |   Test Set      |    EER ( % )  |   Threshold   |  MinDCF-0.01   |   MinDCF-0.01  |     Date     |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |   vox1 test     |    2.3542%    |   0.2698025   |    0.2192      |     0.2854     |   20210426   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |   sitw dev      |    2.8109%    |   0.2630014   |    0.2466      |     0.4026     |   20210515   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |   sitw eval     |    3.2531%    |   0.2642460   |    0.2984      |     0.4581     |   20210515   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |  cnceleb test   |   16.8276%    |   0.2165570   |    0.6923      |     0.8009     |   20210515   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |  aishell2 test  |   10.8300%    |   0.2786811   |    0.8212      |     0.9527     |   20210515   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+
  # |   aidata test   |   10.0972%    |   0.2952531   |    0.7859      |     0.9520     |   20210515   |
  # +-----------------+---------------+---------------+----------------+----------------+--------------+

  # 20210515
  # test_set=sitw
  # dev
  # Test ERR is 2.8109%, Threshold is 0.2630014419555664
  #  mindcf-0.01 0.2466, mindcf-0.001 0.4026.
  # eval
  # Test ERR is 3.2531%, Threshold is 0.26424601674079895
  #  mindcf-0.01 0.2984, mindcf-0.001 0.4581.

  # 20210515
  # test_set=cnceleb
  # aishell2 test 30w trials
  # aidata test 50w trials

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/vox2/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
      --feat-format kaldi \
      --input-norm Mean \
      --input-dim 161 \
      --nj 12 \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --channels 512,512,512,512,1500 \
      --margin 0.25 \
      --s 30 \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/vox2_v2/spect_egs/arcsoft_0ce/inputMean_STAP_em512_wde4/${test_set}_${subset}_epoch_60_var \
      --resume Data/checkpoint/TDNN_v5/vox2_v2/spect_egs/arcsoft_0ce/inputMean_STAP_em512_wde4/checkpoint_60.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

# ===============================    RET    ===============================
if [ $stage -le 81 ]; then
  feat_type=spect
  feat=log
  loss=arcsoft
  encod=None
  dataset=vox1
  block_type=Basic
  model=RET
  for loss in arcsoft; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model RET \
      --train-dir ${lstm_dir}/data/vox2/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --feat-format kaldi \
      --input-norm Mean \
      --input-dim 161 \
      --channels 512,512,512,512,512,1500 \
      --nj 12 \
      --alpha 0 \
      --margin 0.25 \
      --s 30 \
      --block-type ${block_type} \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --input-length var \
      --frame-shift 300 \
      --xvector-dir Data/checkpoint/RET/vox2/spect_STAP_v2/arcsoft_100ce/emsize512_inputMean_Basic/epoch_25_var \
      --resume Data/checkpoint/RET/vox2/spect_STAP_v2/arcsoft_100ce/emsize512_inputMean_Basic/checkpoint_25.pth \
      --gpu-id 0 \
      --cos-sim
  done
fi

if [ $stage -le 82 ]; then
  feat_type=spect
  feat=log
  input_norm=Mean
  loss=arcsoft
  encod=STAP
  dataset=vox1
  block_type=cbam
  model=RET
  embedding_size=512
  train_set=vox2
  # test_set=vox1
  # 1.6172%, Threshold is 0.29920902848243713
  # mindcf-0.01 0.1592, mindcf-0.001 0.2065.

  # test_set=sitw
  # dev
  # Test ERR is 2.3489%, Threshold is 0.2773
  # mindcf-0.01 0.2098, mindcf-0.001 0.3596.
  # eval
  # Test ERR is 2.6791%, Threshold is 0.2732
  # mindcf-0.01 0.2346, mindcf-0.001 0.4054.

  test_set=cnceleb
  # 20210515
  #  Test ERR is 19.5295%, Threshold is 0.28571683168411255
  #  mindcf-0.01 0.7313, mindcf-0.001 0.8193.

  for loss in arcsoft; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage${stage}: Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --resnet-size 14 \
      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_${feat} \
      --feat-format kaldi \
      --input-norm ${input_norm} \
      --input-dim 161 \
      --channels 512,512,512,512,512,1536 \
      --context 5,5,5 \
      --nj 12 \
      --alpha 0 \
      --margin 0.25 \
      --s 30 \
      --block-type ${block_type} \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --input-length var \
      --xvector-dir Data/xvector/RET14/vox2/spect_STAP_v2/arcsoft_0ce/em512_inputMean_cbam_bs128_wde4_shuf/${test_set}_test_epoch20_var \
      --resume Data/checkpoint/RET14/vox2/spect_STAP_v2/arcsoft_0ce/em512_inputMean_cbam_bs128_wde4_shuf/checkpoint_20.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

if [ $stage -le 83 ]; then
  feat_type=pyfb
  feat=fb40_ws25
  input_norm=Mean
  loss=soft
  encod=STAP
  block_type=basic
  model=TDNN_v5
  embedding_size=256
  train_set=cnceleb
  test_set=cnceleb
  # 20210515
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #|   Test Set   |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test |  16.8387%   |   0.1933    |   0.7987    |    0.8964    | 20210825 20:54:13 |
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-spee |   7.9099%   |   0.2843    |   0.4350    |    0.5942    | 20210825 21:01:33 |
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-sing |  25.5825%   |   0.1310    |   0.9821    |    0.9965    | 20210825 21:06:39 |
  #+--------------+-------------+-------------+-------------+--------------+-------------------+

  # 20210902 test with fix length 300 frames
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #|   Test Set   |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test |  14.9190%   |   0.1512    |   0.7366    |    0.8458    | 20210902 12:45:19 | soft
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test |  14.8080%   |   0.1580    |   0.7482    |    0.8556    | 20210902 12:50:19 | arcsoft
  #+--------------+-------------+-------------+-------------+--------------+-------------------+

  # 20210902 test with fix length 300 frames arcsoft
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-adve |  26.3158%   |   0.1290    |   1.0000    |    1.0000    | 20210902 15:41:44 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-dram |  17.0068%   |   0.1298    |   0.8836    |    0.9730    | 20210902 15:41:51 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-ente |  16.8028%   |   0.1429    |   0.8303    |    0.9222    | 20210902 15:42:13 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-inte |  12.7590%   |   0.1756    |   0.7412    |    0.8366    | 20210902 15:42:59 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-live |  10.3733%   |   0.1970    |   0.5995    |    0.7959    | 20210902 15:43:14 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-movi |  19.7368%   |   0.1273    |   0.9162    |    0.9430    | 20210902 15:43:18 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-play |  14.0000%   |   0.1541    |   0.8593    |    0.9600    | 20210902 15:43:22 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-reci |   8.5714%   |   0.2315    |   0.6518    |    0.8383    | 20210902 15:43:26 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-sing |  25.4834%   |   0.0985    |   0.9856    |    0.9975    | 20210902 15:43:39 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-spee |   5.8965%   |   0.2486    |   0.3730    |    0.5044    | 20210902 15:43:52 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-vlog |  11.3402%   |   0.1905    |   0.7051    |    0.8299    | 20210902 15:43:58 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+

  # 20211025 test with fix length 300 frames soft
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|    cnceleb-dev    |   5.8668%   |   0.1983    |   0.5304    |    0.7234    | 20211026 14:29:48 |  30w trials
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|  cnceleb-dev-dev  |   5.7318%   |   0.1989    |   0.5328    |    0.8036    | 20211026 19:46:28 | 640w
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|    cnceleb-test   |  14.9190%   |   0.1512    |   0.7366    |    0.8458    | 20210902 12:45:19 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-adve |  26.3158%   |   0.0976    |   0.9997    |    1.0000    | 20211025 22:09:29 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-dram |  15.1927%   |   0.1357    |   0.8360    |    0.9366    | 20211025 22:09:41 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-ente |  15.7526%   |   0.1438    |   0.8186    |    0.9053    | 20211025 22:10:18 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-inte |  13.6238%   |   0.1683    |   0.7267    |    0.8177    | 20211025 22:11:35 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-live |  10.5035%   |   0.1903    |   0.5658    |    0.7634    | 20211025 22:12:00 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-movi |  24.1228%   |   0.1062    |   0.9538    |    0.9912    | 20211025 22:12:08 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-play |  16.0000%   |   0.1427    |   0.9299    |    0.9600    | 20211025 22:12:14 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-reci |   5.7143%   |   0.2620    |   0.5899    |    0.8766    | 20211025 22:12:21 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-sing |  24.9380%   |   0.0765    |   0.9824    |    0.9961    | 20211025 22:12:42 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-spee |   6.3279%   |   0.2391    |   0.3689    |    0.4642    | 20211025 22:13:05 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-vlog |  10.8247%   |   0.1890    |   0.6853    |    0.7926    | 20211025 22:13:16 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+

  # 20211025 test with fix length 300 frames gradient reverse layers soft
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|   cnceleb-dev     |   3.8844%   |   0.2333    |   0.2444    |    0.3655    | 20211026 14:19:11 | 30w trials
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #|   cnceleb-test    |  15.5182%   |   0.1565    |   0.7982    |    0.8954    | 20211025 22:37:18 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-adve |  26.3158%   |   0.1151    |   1.0000    |    1.0000    | 20211025 22:37:26 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-dram |  17.3469%   |   0.1265    |   0.9295    |    0.9955    | 20211025 22:37:37 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-ente |  16.6861%   |   0.1481    |   0.8578    |    0.9481    | 20211025 22:38:13 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-inte |  13.9664%   |   0.1733    |   0.7933    |    0.8799    | 20211025 22:39:29 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-live |  10.9809%   |   0.1977    |   0.7429    |    0.9281    | 20211025 22:39:53 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-movi |  23.6842%   |   0.1128    |   0.9276    |    0.9605    | 20211025 22:40:01 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-play |  12.0000%   |   0.1706    |   0.9897    |    1.0000    | 20211025 22:40:07 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-reci |   8.5714%   |   0.2392    |   0.5378    |    0.7623    | 20211025 22:40:13 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-sing |  25.2851%   |   0.0965    |   0.9918    |    0.9980    | 20211025 22:40:35 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-spee |   6.4238%   |   0.2436    |   0.4618    |    0.6023    | 20211025 22:40:57 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test-vlog |  14.0464%   |   0.1789    |   0.6943    |    0.8328    | 20211025 22:41:08 |
  #+-------------------+-------------+-------------+-------------+--------------+-------------------+


  #  for loss in soft arcsoft; do # 32,128,512; 8,32,128
#  for s in advertisement drama entertainment interview live_broadcast movie play recitation singing speech vlog; do
#    echo -e "\n\033[1;4;31m Stage${stage}: Testing with ${loss} \033[0m\n"
#    python -W ignore TrainAndTest/test_egs.py \
#      --model ${model} \
#      --resnet-size 14 \
#      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
#      --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
#      --train-trials trials_2w \
#      --trials trials_${s} \
#      --score-suffix ${s} \
#      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
#      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_${feat} \
#      --feat-format kaldi \
#      --input-norm ${input_norm} \
#      --input-dim 40 \
#      --channels 512,512,512,512,1500 \
#      --context 5,3,3,5 \
#      --nj 12 \
#      --alpha 0 \
#      --margin 0.15 \
#      --s 30 \
#      --stride 1 \
#      --block-type ${block_type} \
#      --embedding-size ${embedding_size} \
#      --loss-type ${loss} \
#      --encoder-type STAP \
#      --input-length fix \
#      --remove-vad \
#      --frame-shift 300 \
#      --xvector-dir Data/xvector/TDNN_v5/cnceleb/pyfb_egs_baseline/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_var/${test_set}_test_epoch60_fix \
#      --resume Data/checkpoint/TDNN_v5/cnceleb/pyfb_egs_baseline/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_var/checkpoint_60.pth \
#      --gpu-id 0 \
#      --extract \
#      --cos-sim
#  done
#  for s in vlog; do
#    python -W ignore TrainAndTest/test_egs.py \
#      --model ${model} \
#      --resnet-size 14 \
#      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
#      --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
#      --train-trials trials_2w \
#      --trials subtrials/trials_vlog_${s} \
#      --score-suffix vl${s} \
#      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
#      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/dev_${feat} \
#      --feat-format kaldi \
#      --input-norm ${input_norm} \
#      --input-dim 40 \
#      --channels 512,512,512,512,1500 \
#      --context 5,3,3,5 \
#      --nj 12 \
#      --alpha 0 \
#      --margin 0.15 --s 30 \
#      --stride 1 \
#      --block-type ${block_type} \
#      --embedding-size ${embedding_size} \
#      --loss-type ${loss} \
#      --encoder-type STAP \
#      --input-length fix \
#      --remove-vad \
#      --frame-shift 300 \
#      --xvector-dir Data/xvector/TDNN_v5/cnceleb/pyfb_egs_baseline/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_var/${test_set}_dev_epoch60_fix \
#      --resume Data/checkpoint/TDNN_v5/cnceleb/pyfb_egs_baseline/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_var/checkpoint_60.pth \
#      --gpu-id 0 \
#      --extract \
#      --cos-sim
#  done

#  python -W ignore TrainAndTest/test_egs.py \
#      --model ${model} \
#      --resnet-size 14 \
#      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
#      --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
#      --train-trials trials_2w \
#      --trials trials_640w \
#      --score-suffix dev_640w \
#      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
#      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/dev_${feat} \
#      --feat-format kaldi \
#      --input-norm ${input_norm} \
#      --input-dim 40 \
#      --channels 512,512,512,512,1500 \
#      --context 5,3,3,5 \
#      --nj 12 \
#      --alpha 0 \
#      --margin 0.15 \
#      --s 30 \
#      --stride 1 \
#      --block-type ${block_type} \
#      --embedding-size ${embedding_size} \
#      --loss-type ${loss} \
#      --encoder-type STAP \
#      --input-length fix \
#      --remove-vad \
#      --frame-shift 300 \
#      --xvector-dir Data/xvector/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/${test_set}_dev_epoch60_fix \
#      --resume Data/checkpoint/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/checkpoint_60.pth \
#      --gpu-id 1 \
#      --verbose 2 \
#      --cos-sim

#  for s in advertisement drama entertainment interview live_broadcast movie play recitation singing speech vlog; do
  for s in vlog; do
#    echo -e "\n\033[1;4;31m Stage${stage}: Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --resnet-size 14 \
      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --trials subtrials/trials_vlog_${s} \
      --score-suffix vl${s} \
      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/dev_${feat} \
      --feat-format kaldi \
      --input-norm ${input_norm} \
      --input-dim 40 \
      --channels 512,512,512,512,1500 \
      --context 5,3,3,5 \
      --nj 12 \
      --alpha 0 \
      --margin 0.15 --s 30 \
      --stride 1 \
      --block-type ${block_type} \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type STAP \
      --input-length fix \
      --remove-vad \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/${test_set}_dev_epoch60_fix \
      --resume Data/checkpoint/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/checkpoint_60.pth \
      --gpu-id 1 \
      --extract \
      --cos-sim
  done
  exit
#  for s in vlog; do
#    wc -l data/cnceleb/dev/subtrials/trials_vlog_${s}
#  done
fi

if [ $stage -le 84 ]; then
  feat_type=pyfb
  feat=fb40_ws25
  input_norm=Mean
  loss=arcsoft
  encod=STAP
  block_type=basic
  model=TDNN_v5
  embedding_size=256
  train_set=cnceleb
  test_set=cnceleb
  # 20210515
#      --trials trials_${s} \
#      --score-suffix ${s} \

  #  for loss in soft arcsoft; do # 32,128,512; 8,32,128
  for s in all; do
    echo -e "\n\033[1;4;31m Stage${stage}: Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --resnet-size 14 \
      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_${feat} \
      --feat-format kaldi \
      --input-norm ${input_norm} \
      --input-dim 40 \
      --channels 512,512,512,512,1500 \
      --context 5,3,3,5 \
      --nj 12 \
      --alpha 0 \
      --stride 1 \
      --block-type ${block_type} \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type STAP \
      --input-length fix \
      --remove-vad \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/cnceleb/pyfb_egs_revg/soft/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2dr1/${test_set}_test_epoch60_fix \
      --resume Data/checkpoint/TDNN_v5/cnceleb/pyfb_egs_revg/soft/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2dr1/checkpoint_60.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

#exit
if [ $stage -le 90 ]; then
  feat_type=spect
  feat=log
  loss=arcsoft
  encod=None
  dataset=vox1
  block_type=cbam
  for loss in arcsoft; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model LoResNet --resnet-size 8 \
      --train-dir ${lstm_dir}/data/vox2/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/aidata/${feat_type}/dev_${feat} \
      --feat-format kaldi \
      --input-norm Mean --input-dim 161 \
      --nj 12 \
      --embedding-size 256 \
      --encoder-type None \
      --block-type ${block_type} \
      --kernel-size 5,7 --stride 2,3 \
      --channels 64,128,256 \
      --alpha 0 \
      --loss-type ${loss} --margin 0.3 --s 30 --m 3 \
      --input-length var \
      --dropout-p 0.5 \
      --xvector-dir Data/xvector/LoResNet8/vox2/spect_egs/arcsoft/None_cbam_dp05_em256_k57/epoch_40_var_aidata \
      --resume Data/checkpoint/LoResNet8/vox2/spect_egs/arcsoft/None_cbam_dp05_em256_k57/checkpoint_40.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

if [ $stage -le 91 ]; then
  feat_type=spect
  model=LoResNet
  feat=log
  loss=soft
  encod=None
  dataset=vox1
  block_type=basic
  embedding_size=128

  for loss in soft; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size 8 \
      --train-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test_${feat} \
      --feat-format kaldi \
      --input-norm Mean --input-dim 161 \
      --nj 12 \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type ${encod} \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2,2 \
      --channels 64,128,256 \
      --alpha 0 \
      --margin 0.3 --s 30 --m 3 \
      --input-length var \
      --dropout-p 0.25 \
      --xvector-dir Data/xvector/LoResNet8/vox1/spect_egs_None/soft_dp25/epoch_20_var \
      --resume Data/checkpoint/LoResNet8/vox1/spect_egs_None/soft_dp25/checkpoint_20.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

if [ $stage -le 92 ]; then
  feat_type=klsp
  model=LoResNet resnet_size=8
  feat=log
  loss=arcsoft
  encod=None
  alpha=0
  datasets=vox1 testset=sitw
#  test_subset=
  block_type=cbam
  encoder_type=None
  embedding_size=256

#  sname=dev #dev_aug_com
  sname=dev_aug_com
  model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_baseline/${loss}/${encoder_type}_${block_type}_em${embedding_size}_alpha${alpha}_dp25_wd5e4_${sname}_var
  for test_subset in dev test; do
    echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --resnet-size 8 \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
      --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
      --feat-format kaldi \
      --input-norm Mean --input-dim 161 \
      --nj 12 \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type ${encod} \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2,2 \
      --channels 64,128,256 \
      --alpha ${alpha} \
      --margin 0.2 --s 30 \
      --input-length var \
      --dropout-p 0.25 \
      --time-dim 1 --avg-size 4 \
      --xvector-dir Data/xvector/${model_dir} \
      --resume Data/checkpoint/${model_dir}/checkpoint_40.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
#+--------------+-------------+-------------+-------------+--------------+-------------------+
#|   Test Set   |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+--------------+-------------+-------------+-------------+--------------+-------------------+
#|  vox1-test   |   3.2715%   |   0.2473    |   0.3078    |    0.4189    | 20210818 19:07:02 |
#+--------------+-------------+-------------+-------------+--------------+-------------------+
#| vox1-test-aug|   2.8367%   |   0.2615    |   0.2735    |    0.4051    | 20210818 19:11:29 |
#+--------------+-------------+-------------+-------------+--------------+-------------------+
fi

if [ $stage -le 93 ]; then
  feat_type=klsp
  model=LoResNet resnet_size=8
  feat=log
  loss=arcsoft
  encod=SAP2
  alpha=0
  datasets=vox1
  block_type=cbam
  encoder_type=None
  embedding_size=256

  for sname in dev ; do
    model_dir=LoResNet8/vox1/klsp_egs_baseline/arcsoft_sgd_rop/Mean_cbam_SAP2_dp25_alpha0_em256_wd5e4_var
    echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --resnet-size 8 \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
      --feat-format kaldi \
      --input-norm Mean --input-dim 161 \
      --nj 12 \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type ${encod} \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2,2 \
      --channels 64,128,256 \
      --alpha ${alpha} \
      --margin 0.2 --s 30 \
      --input-length var \
      --dropout-p 0.25 \
      --time-dim 1 --avg-size 4 \
      --xvector-dir Data/xvector/${model_dir} \
      --resume Data/checkpoint/${model_dir}/checkpoint_50.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
#+--------------+-------------+-------------+-------------+--------------+-------------------+
#|   Test Set   |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+--------------+-------------+-------------+-------------+--------------+-------------------+
#|  vox1-test   |   3.2715%   |   0.2473    |   0.3078    |    0.4189    | 20210818 19:07:02 |
#+--------------+-------------+-------------+-------------+--------------+-------------------+
#|  vox1-test   |   2.8367%   |   0.2615    |   0.2735    |    0.4051    | 20210818 19:11:29 |
#+--------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   2.9852%   |   0.2544    |   0.3110    |    0.3925    | 20211129 14:03:34 | SAP2
fi

if [ $stage -le 94 ]; then
  feat_type=klsp
  model=LoResNet resnet_size=8
  feat=log
  loss=arcsoft
  encod=None
  alpha=0
  datasets=vox1
  testset=sitw
#  test_subset=
  block_type=cbam
  encoder_type=None
  embedding_size=256

#  sname=dev #dev_aug_com
  sname=dev #_aug_com

  for test_subset in test; do
    echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size 8 \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
      --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
      --feat-format kaldi --nj 12 \
      --input-norm Mean --input-dim 161 \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type ${encod} \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2,2 \
      --channels 32,64,128 \
      --alpha ${alpha} \
      --margin 0.2 --s 30 \
      --input-length var \
      --dropout-p 0.2 \
      --time-dim 1 --avg-size 4 \
      --xvector-dir Data/xvector/${model}${resnet_size}/${datasets}/${feat_type}_egs_baseline/${loss}/Mean_cbam_None_dp20_alpha0_em256_wd5e4_chn32_var \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_egs_baseline/${loss}/Mean_cbam_None_dp20_alpha0_em256_wd5e4_chn32_var/checkpoint_50.pth \
      --gpu-id 0 \
      --cos-sim
  done
#  exit
fi
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   3.6585%   |   0.2510    |   0.3411    |    0.4408    | 20210930 11:08:10 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

if [ $stage -le 95 ]; then
  feat_type=klsp
  model=LoResNet resnet_size=8
  feat=log
  loss=arcsoft
  encod=None
  alpha=0
  datasets=vox1 testset=vox1
#  test_subset=
  block_type=cbam
  encoder_type=None
  embedding_size=256
  
#  sname=dev #dev_aug_com
  sname=dev #_aug_com
  test_subset=test
  input_norm=Mean
  model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_attention/${loss}/${input_norm}_${block_type}_${encod}_dp125_alpha${alpha}_em${embedding_size}_${weight}42_chn16_wd5e4_var
  for weight in mel clean aug vox2 ; do
    echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size 8 \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w --score-suffix ${weight} \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
      --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
      --feat-format kaldi --nj 12 \
      --input-norm Mean --input-dim 161 \
      --embedding-size ${embedding_size} \
      --mask-layer attention --init-weight ${weight} \
      --encoder-type ${encod} \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2,2 \
      --channels 16,32,64 \
      --alpha ${alpha} \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --input-length var \
      --dropout-p 0.125 \
      --time-dim 1 --avg-size 4 \
      --xvector-dir Data/xvector/${model_dir} \
      --resume Data/checkpoint/${model_dir}/checkpoint_50.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi
if [ $stage -le 96 ]; then
  feat_type=klsp
  model=LoResNet resnet_size=8
  feat=log
  loss=arcsoft
  encod=AVG
  alpha=0
  datasets=vox1 testset=vox1
#  test_subset=
  block_type=cbam
  encoder_type=AVG embedding_size=256
  
#  sname=dev #dev_aug_com
  sname=dev #_aug_com
  test_subset=test
  input_norm=Mean

  for weight in None ; do
    echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size 8 \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
      --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
      --feat-format kaldi --nj 12 \
      --input-norm Mean --input-dim 161 \
      --embedding-size ${embedding_size} \
      --loss-type ${loss} \
      --encoder-type ${encod} \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2,2 \
      --channels 32,64,128 \
      --alpha ${alpha} \
      --margin 0.2 --s 30 \
      --input-length var \
      --dropout-p 0.125 \
      --time-dim 1 --avg-size 4 \
      --xvector-dir Data/xvector/${model}${resnet_size}/${datasets}/${feat_type}_egs_kd/${loss}_sgd_rop/${input_norm}_${block_type}_${encod}_dp20_alpha${alpha}_em${embedding_size}_wd5e4_chn32_var \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_egs_kd/${loss}_sgd_rop/${input_norm}_${block_type}_${encod}_dp20_alpha${alpha}_em${embedding_size}_wd5e4_chn32_var/checkpoint_50.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# chn16
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   4.2100%   |   0.2511    |   0.3781    |    0.5214    | 20211004 15:15:00 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   4.1676    |   0.2556    |   0.3846    |    0.4620    | 20220113 20:28:41 | kd soft
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# chn32
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   3.6585%   |   0.2510    |   0.3411    |    0.4408    | 20210930 11:08:10 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   3.6161    |   0.2559    |   0.3371    |    0.4334    | 20220113 20:31:33 | kd soft
#+-------------------+-------------+-------------+-------------+--------------+-------------------+


if [ $stage -le 97 ]; then
  feat_type=klsp
  model=LoResNet resnet_size=8
  feat=log
  loss=arcsoft
  encod=AVG
  alpha=0
  datasets=vox1 testset=vox1
#  test_subset=
  block_type=cbam
  encoder_type=AVG embedding_size=256
  
#  sname=dev #dev_aug_com
  sname=dev #_aug_com
  test_subset=test
  batch_size=256
  avg_size=4
  input_norm=Mean
  mask_layer=baseline
  scheduler=rop optimizer=sgd

#  for weight in None ; do
  echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
  for seed in 123456 123457 123458; do
  for chn in 64 ; do
    if [ $chn -eq 64 ];then
      channels=64,128,256
      dp=0.25
      dp_str=25
    elif [ $chn -eq 32 ];then
      channels=32,64,128
      dp=0.2
      dp_str=20
    elif [ $chn -eq 16 ];then
      channels=16,32,64
      dp=0.125
      dp_str=125
    fi

    model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${seed}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_avg${avg_size}_${encoder_type}_em${embedding_size}_dp${dp_str}_alpha${alpha}_chn${chn}_wd5e4_vares

#    Mean_batch256_cbam_avg4_AVG_em256_dp25_alpha0_chn64_wd5e4_vares
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size ${resnet_size} \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
      --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
      --feat-format kaldi --nj 4 \
      --input-norm ${input_norm} --input-dim 161 \
      --embedding-size ${embedding_size} \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2,2 \
      --channels ${channels} \
      --alpha ${alpha} \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --input-length var \
      --dropout-p ${dp} \
      --time-dim 1 --avg-size ${avg_size} \
      --xvector-dir Data/xvector/${model_dir} \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --gpu-id 1 \
      --cos-sim
  done
  done
  exit
fi
#|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#|     vox1-test     |   3.3245    |   0.2646    |    0.3348     |    0.4285     | 20220826 17:49:48 |
#|     vox1-test     |   3.1442    |   0.2583    |    0.2946     |    0.3872     | 20220826 17:52:01 |
#|     vox1-test     |   3.4464    |   0.2494    |    0.3261     |    0.4060     | 20220826 17:54:15 |
#

# ===============================    MultiResNet    ===============================
if [ $stage -le 100 ]; then
  datasets=army
  model=MultiResNet resnet_size=18
  #  loss=soft
  encod=None
  transform=None
  loss_ratio=0.01
  alpha=13
  for loss in soft; do
    echo -e "\n\033[1;4;31m Testing ${model}_${resnet_size} in army with ${loss} kernel 5,5 \033[0m\n"

    python TrainAndTest/test_egs_multi.py \
      --model ${model} --resnet-size ${resnet_size} \
      --train-dir-a ${lstm_dir}/data/${datasets}/spect/aishell2_dev_8k_v4 \
      --train-dir-b ${lstm_dir}/data/${datasets}/spect/vox_dev_8k_v4 \
      --train-test-dir ${lstm_dir}/data/${datasets}/spect/dev_8k_v2/trials_dir \
      --valid-dir-a ${lstm_dir}/data/${datasets}/egs/spect/aishell2_valid_8k_v4 \
      --valid-dir-b ${lstm_dir}/data/${datasets}/egs/spect/vox_valid_8k_v4 \
      --test-dir ${lstm_dir}/data/magic/spect/test_8k \
      --feat-format kaldi \
      --input-norm Mean --input-dim 81 \
      --batch-size 128 --nj 10 \
      --lr 0.1 \
      --fast \
      --mask-layer freq --mask-len 20 \
      --stride 1 \
      --xvector-dir Data/xvector/MultiResNet18/army_x4/spect_egs_None/soft/dp25_b256_13_fast_None_mask/epoch_36_var_magic \
      --resume Data/checkpoint/MultiResNet18/army_x4/spect_egs_None/soft/dp25_b256_13_fast_None_mask/checkpoint_36.pth \
      --channels 32,64,128,256 \
      --embedding-size 128 \
      --transform ${transform} \
      --encoder-type ${encod} \
      --time-dim 1 --avg-size 4 \
      --num-valid 4 \
      --alpha ${alpha} \
      --margin 0.3 --s 30 --m 3 \
      --input-length var \
      --loss-ratio ${loss_ratio} \
      --weight-decay 0.0005 \
      --dropout-p 0.1 \
      --gpu-id 0 \
      --cos-sim --extract \
      --loss-type ${loss}
  done
  exit
fi
#exit

if [ $stage -le 101 ]; then
  feat_type=spect feat=log
  loss=arcsoft
  encod=None
  dataset=army_v1
  block_type=None
  for loss in soft; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Testing with ${loss} \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model LoResNet --resnet-size 10 \
      --train-dir ${lstm_dir}/data/army/spect/dev_8k \
      --test-dir ${lstm_dir}/data/army/spect/test_8k \
      --feat-format kaldi --nj 12 \
      --input-norm Mean --input-dim 161 \
      --embedding-size 128 \
      --encoder-type None \
      --block-type ${block_type} \
      --kernel-size 5,5 --stride 2 \
      --channels 64,128,256,256 \
      --alpha 12 \
      --loss-type ${loss} --margin 0.3 --s 30 --m 3 \
      --input-length var \
      --frame-shift 300 \
      --dropout-p 0.1 \
      --xvector-dir Data/xvector/LoResNet10/army_v1/spect_egs_mean/soft_dp01/epoch_20_var \
      --resume Data/checkpoint/LoResNet10/army_v1/spect_egs_mean/soft_dp01/checkpoint_20.pth \
      --gpu-id 0 \
      --cos-sim
  done
fi


if [ $stage -le 200 ]; then
  feat_type=klsp
  model=ThinResNet resnet_size=18
  feat=log
  loss=arcsoft
  encod=SAP2
  alpha=0
  datasets=vox1
  testset=vox1
#  test_subset=
  block_type=basic
  encoder_type=None
  embedding_size=256
#  sname=dev #dev_aug_com
  sname=dev #_aug_com
  downsample=k1
  for seed in 123456 123457 123458; do
  for test_subset in test; do
    echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size ${resnet_size} \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
      --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
      --feat-format kaldi --nj 6 \
      --input-norm Mean --input-dim 161 \
      --encoder-type ${encod} --embedding-size ${embedding_size} \
      --block-type ${block_type} --downsample ${downsample} \
      --kernel-size 5,5 --stride 2,2 --fast none1 \
      --channels 16,32,64,128 \
      --alpha ${alpha} \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --time-dim 1 --avg-size 4 \
      --test-input var \
      --dropout-p 0.25 \
      --xvector-dir Data/xvector/${model_dir}/${test_subset}_epoch_50_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --gpu-id 0 --cos-sim
  done
  done
  exit
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# ThinResNet18 klfb40
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-dev      |   1.0300    |   0.2914    |   0.1291    |    0.2308    | 20211221 22:57:16 |
#|     vox1-test     |   4.2683%   |   0.2369    |   0.3929    |    0.4767    | 20211119 15:09:05 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
# attention vox2_rcf
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-dev      |   0.9700    |   0.2949    |   0.1282    |    0.2440    | 20211221 23:07:13 |
#|     vox1-test     |   4.2895    |   0.2371    |   0.4231    |    0.5714    | 20211221 22:43:00 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# ThinResNet34 klsp
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-dev      |   0.4700    |   0.3264    |   0.0629    |    0.1140    | 20211221 23:30:06 |
#|     vox1-test     |   3.7116    |   0.2465    |   0.3838    |    0.4681    | 20211221 23:15:57 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
# attention vox2
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-dev      |   0.4600    |   0.3283    |   0.0631    |    0.1092    | 20211221 23:43:06 |
#|     vox1-test     |   3.5790    |   0.2471    |   0.4012    |    0.5222    | 20211221 23:17:22 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
fi


if [ $stage -le 201 ]; then
  feat_type=klsp
  model=ThinResNet resnet_size=10
  datasets=vox2 testset=vox1 test_subset=test
  feat=log
  loss=arcsoft
  encod=AVG alpha=0 avg_size=5
  
  input_norm=Mean
#  test_subset=
  block_type=basic encoder_type=SAP2 embedding_size=256

#  sname=dev #dev_aug_com
  sname=dev #_aug_com
  downsample=k1
  fast=none1 chn=16
#  mask_layer=rvec
#  mask_layer=baseline
  mask_layer=rvec mask_len=5,10 weight_norm=max
  weight=rclean_max
  scheduler=rop optimizer=sgd
  batch_size=256
#  123456 123457 123458
#  10 18 34 50
#  for mask_layer in attention0 ;do
#  for weight_norm in max ; do
#  echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"

 for ((i=0; i<=160; i=i+4)); do
   mask_sub="$i,$((i+4))"
#
#        
  for testset in vox1 ; do
  for resnet_size in 34 ; do
  for seed in 123456 123457 123458 ;do
  for sub_trials in hard ; do

#    for chn in 16 32 64 ; do
      epoch=
      if [ $resnet_size -le 34 ];then
        expansion=1
      else
        expansion=4
      fi
      if [ $chn -eq 16 ]; then
        channels=16,32,64,128
        chn_str=
      elif [ $chn -eq 32 ]; then
        channels=32,64,128,256
        chn_str=chn32_
      elif [ $chn -eq 64 ]; then
        channels=64,128,256,512
        chn_str=chn64_
      fi

      avg_str=avg${avg_size}_
      if [ $avg_size -eq 0 ]; then
        avg_str=
      fi

      at_str=
      if [[ $mask_layer == attention* ]];then
        at_str=_${weight}
      #        --score-suffix
      elif [ "$mask_layer" = "both" ];then
        at_str=_`echo $mask_len | sed  's/,//g'`
      fi
    #--score-suffix ${sub_trials} \
      model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${seed}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_down${downsample}_${avg_str}${encoder_type}_em${embedding_size}_dp01_alpha${alpha}_${fast}${at_str}_${chn_str}wde5_var

      python -W ignore TrainAndTest/test_egs.py \
        --model ${model} --resnet-size ${resnet_size} \
        --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
        --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
        --train-trials trials --mask-sub ${mask_sub} \
        --score-suffix ${mask_sub} --test-mask \
        --trials trials \
        --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
        --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
        --feat-format kaldi --nj 12 \
        --input-norm ${input_norm} --input-dim 161 \
        --mask-layer ${mask_layer} --init-weight ${weight} --weight-norm ${weight_norm} \
        --fast ${fast} --downsample ${downsample} \
        --encoder-type ${encoder_type} --embedding-size ${embedding_size} \
        --block-type ${block_type} --expansion ${expansion} \
        --kernel-size 5,5 --stride 2,2 \
        --channels ${channels} \
        --alpha ${alpha} \
        --loss-type ${loss} --margin 0.2 --s 30 \
        --time-dim 1 --avg-size ${avg_size} \
        --test-input var --dropout-p 0.1 \
        --xvector-dir Data/xvector/${model_dir}/${test_subset}_epoch${epoch}_var \
        --resume Data/checkpoint/${model_dir}/best.pth \
        --gpu-id 2 \
        --verbose 0 \
        --cos-sim
#        Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
    done
  done
  done
  done
  done
  exit

#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# ResNet 10
#|     vox1-test     |   4.3531    |   0.2193    |   0.4171    |    0.5100    | 20220623 17:24:15 | epoch 15
#|     vox1-test     |   4.3372    |   0.2150    |   0.3845    |    0.5043    | 20220623 17:29:27 | epoch 39
#|     vox1-test     |   4.2683    |   0.2184    |   0.3853    |    0.5423    | 20220623 17:32:15 | epoch 32
#                    |  4.32~0.04  |             |0.3956~0.0152|0.5189~0.0167 |

# ResNet 18
#|     vox1-test     |   4.1145    |   0.2274    |   0.3849    |    0.4335    | 20220623 17:39:23 | epoch 19
#|     vox1-test     |   3.9714    |   0.2366    |   0.3860    |    0.4865    | 20220623 17:43:36 | epoch 16
#|     vox1-test     |   4.0668    |   0.2217    |   0.3735    |    0.5064    | 20220623 17:45:58 | epoch 33
#                    |  4.05~0.06  |             |0.3815~0.0057|0.4755~0.0308 |

# ResNet 34
#|     vox1-test     |   3.7381    |   0.2293    |   0.3676    |    0.5141    | 20220623 17:49:39 | epoch 25
#|     vox1-test     |   3.8706    |   0.2312    |   0.3489    |    0.4994    | 20220623 17:53:07 | epoch 20
#|     vox1-test     |   3.9343    |   0.2242    |   0.3502    |    0.4836    | 20220623 17:58:38 | epoch 30
#                    |  3.84~0.08  |             |0.3556±0.0085|0.4990±0.0125 |

# ResNet 50
#|     vox1-test     |   4.3266    |   0.2061    |   0.3992    |    0.4841    | 20220623 18:10:53 | epoch 35
#|     vox1-test     |   4.4008    |   0.2086    |   0.3986    |    0.5743    | 20220623 18:22:06 | epoch 21
#|     vox1-test     |   4.2895    |   0.2120    |   0.3709    |    0.5213    | 20220623 20:23:30 | epoch 21


# avg5 vox1 sap2
#+-------------------+-------------+-------------+---------------+---------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  |  MinDCF-0.01  | MinDCF-0.001  |       Date        |
#+-------------------+-------------+-------------+---------------+---------------+-------------------+
# ResNet 8
#|     vox1-test     |  5.16±0.07  |             | 0.4481±0.0179 | 0.6074±0.0292 | chn16
#|     vox1-test     |  5.12±0.10  |             | 0.4621±0.0071 | 0.5449±0.0284 | chn16 attention rclean
#|  vox1-test-rcle   |  5.16±0.02  |             | 0.4637±0.0093 | 0.5872±0.0136 | chn16 attention3 rclean
#|  vox1-test-vox2   |  5.14±0.03  |             | 0.4767±0.0115 | 0.6072±0.0224 | chn16 attention vox2_rclean

#|                   |  4.31±0.05  |             | 0.4005±0.0137 | 0.4999±0.0095 | chn32
#|                   |  4.01±0.06  |             | 0.3653±0.0092 | 0.4315±0.0262 | chn64

# ResNet 10
#|     vox1-test     |  4.24±0.07  |             | 0.3889±0.0162 | 0.5185±0.0525 |
#|  vox1-test-rcle   |  4.20±0.04  |             | 0.3907±0.0083 | 0.5191±0.0248 | attention rclean
#|  vox1-test-rcle   |  4.17±0.08  |             | 0.3870±0.0301 | 0.4881±0.0359 | attention rclean_max

#|     sitw-test     |  8.24±0.17  |             | 0.5871±0.0075 | 0.7768±0.0057 |
#|  sitw-test-rcle   |  7.93±0.12  |             | 0.5740±0.0034 | 0.7664±0.0134 | attention rclean
#|  sitw-test-rcle   |  7.62±0.22  |             | 0.5684±0.0022 | 0.7555±0.0052 | attention rclean_max

# ResNet 18
#|     vox1-test     |  3.68±0.10  |             | 0.3592±0.0043 | 0.4604±0.0213 |
#|  vox1-test-rcle   |  3.72±0.07  |             | 0.3650±0.0096 | 0.4555±0.0395 | attention rclean

#|     sitw-test     |  6.97±0.17  |             | 0.5203±0.0099 | 0.7152±0.0083 |
#|  sitw-test-rcle   |  7.02±0.17  |             | 0.5136±0.0023 | 0.6977±0.0062 | attention rclean

# ResNet 34 vox1
#|     vox1-test     |  3.53±0.05  |             | 0.3498±0.0040 | 0.4261±0.0375 |
#|     sitw-test     |  6.27±0.09  |             | 0.4681±0.0061 | 0.6555±0.0072 |
#|   aishell2-test   |  7.08±0.55  |             | 0.6882±0.0235 | 0.8727±0.0055 |

# ResNet 34 vox2
#|     vox1-test     |  2.08±0.09  |             | 0.1965±0.0011 | 0.3089±0.0059 | vox2
#|     sitw-test     |  3.27±0.13  |             | 0.2661±0.0100 | 0.4016±0.0047 | vox2
#|   aishell2-test   |  4.87±0.16  |             | 0.5419±0.0137 | 0.7380±0.0197 | vox2

# ResNet 34 cham_v2 k5 avg5_sap2 vox2
#|     vox1-test     |   1.7550    |   0.2879    |    0.1853     |    0.2727     | 20220828 17:10:59 |
#|     sitw-test     |   3.3352    |   0.2572    |    0.2532     |    0.3882     | 20220828 17:12:29 |

#|   vox1-dev-easy   |   1.8414    |   0.2631    |    0.1776     |    0.3000     | 20220828 18:20:17 |
#|   vox1-dev-hard   |   3.0756    |   0.3064    |    0.2722     |    0.4277     | 20220828 19:38:28 |


# ResNet8
#|     sitw-test     |  9.84±0.04  |             | 0.6933±0.0020 | 0.8924±0.0067 | chn16
#|     sitw-test     |  9.69±0.20  |             | 0.6813±0.0016 | 0.8779±0.0069 | attention rclean
#|  sitw-test-rcle   |  9.47±0.17  |             | 0.6814±0.0082 | 0.8835±0.0187 | attention3 rclean

#|  sitw-test-vox2   |  9.53±0.11  |             | 0.6822±0.0101 | 0.8696±0.0194 | attention vox2_rclean

#|     sitw-test     |  8.40±0.11  |             | 0.6035±0.0068 | 0.7976±0.0112 | chn32
#|     sitw-test     |  7.97±0.27  |             | 0.5486±0.0070 | 0.7329±0.0127 | chn64

# ResNet10

# ResNet18

# ResNet34

# avg5 vox1 AVG
#+-------------------+-------------+-------------+---------------+---------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  |  MinDCF-0.01  | MinDCF-0.001  |       Date        |
#+-------------------+-------------+-------------+---------------+---------------+-------------------+
#
# ResNet18
#|    vox1-test      |  4.60±0.15  |             | 0.4451±0.0142 | 0.5114±0.0321 |
#|  vox1-test-rcle   |  4.58±0.04  |             | 0.4428±0.0206 | 0.5543±0.0267 |

#|    sitw-test      |  9.60±0.36  |             | 0.6083±0.0018 | 0.7975±0.0040 |
#|  sitw-test-rcle   |  9.17±0.28  |             | 0.6124±0.0100 | 0.8091±0.0113 |

# ResNet34
#|     vox1-test     |  4.07±0.03  |             | 0.4027±0.0124 | 0.5078±0.0588 |
#|     sitw-test     |  8.57±0.24  |             | 0.5746±0.0072 | 0.7969±0.0228 |
fi


if [ $stage -le 201 ]; then
  model=ThinResNet resnet_size=34
#  feat_type=klfb # /${feat_type}_fb40  --remove-vad
#feat-format kaldi
  feat_type=wave feat_format=wav
  input_dim=40
  feat=log
  loss=arcsoft
  encod=ASTP2
  alpha=0
  datasets=vox1 testset=vox1 test_subset=dev
#  test_subset=
  block_type=seblock #basic
  red_ratio=2
  encoder_type=None embedding_size=256

#  sname=dev #dev_aug_com
  sname=dev #_aug_com
  downsample=None

  mask_layer=baseline
  filter_layer=fbank
#        --downsample ${downsample} \
#      --trials trials_20w \
#  model_dir=ThinResNet34/vox1/klfb_egs_attention/arcsoft_sgd_rop/Mean_basic_downNone_none1_SAP2_dp125_alpha0_em256_vox2_rcfmax_wd5e4_var
#  for testset in vox1 ; do
  echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"

  for lamda_beta in 2.0 ;do
  for mani in 123;do
  for seed in 123456 ;do
    model_dir=ThinResNet34/vox1/wave_egs_baseline/arcsoft_sgd_rop/Mean_batch256_seblock_red2_downk1_avg5_ASTP2_em256_dp01_alpha0_none1_wde4_var2ses_bashuf2_dist_mani${mani}_lamda${lamda_beta}/${seed}
    #
    # _hard --extract
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size ${resnet_size} \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
      --train-test-dir ${lstm_dir}/data/vox1/test \
      --train-trials trials_2w --trials trials_hard --extract \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/${testset}/${test_subset} \
      --feat-format ${feat_format} --nj 12 \
      --input-norm Mean --input-dim ${input_dim} --filter ${filter_layer} --feat-dim ${input_dim} \
      --embedding-size ${embedding_size} \
      --mask-layer ${mask_layer} --init-weight vox2_rcf \
      --block-type ${block_type} --downsample ${downsample} --red-ratio ${red_ratio} \
      --kernel-size 5,5 --stride 2,1 --fast none1 \
      --channels 16,32,64,128 --alpha ${alpha} \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --encoder-type ${encod} --time-dim 1 --avg-size 5 \
      --test-input var --dropout-p 0.1 \
      --xvector-dir Data/xvector/${model_dir}/${testset}_${test_subset}_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --gpu-id 0 --verbose 2 \
      --cos-sim
    done
    done
  done
  exit
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# Arcsoft fb40 thin34_basic_none1s
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   4.0403%   |   0.2446    |   0.4034    |    0.5689    | 20211130 16:56:42 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   3.9343    |   0.2493    |   0.3624    |    0.5463    | 20211222 20:15:48 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
# Arcsoft fb40 thin34_cbam
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   4.0138%   |   0.2442    |   0.4186    |    0.5426    | 20211203 16:16:54 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# Arcsoft fb40 thin18_basic_v2_k5
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   4.1676%   |   0.2354    |   0.3765    |    0.5602    | 20211202 15:09:09 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+

# Arcsoft fb40 thin34_basic vox2
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   1.8452    |   0.2847    |   0.1973    |    0.3190    | 20211210 15:47:27 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|   cnceleb-test    |   14.0979   |   0.2445    |   0.6538    |    0.8029    | 20211210 16:10:01 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|   aishell2-test   |   9.9600    |   0.3146    |   0.7508    |    0.8895    | 20211210 19:20:30 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
fi

if [ $stage -le 202 ]; then
  data_path=${lstm_dir}/data/vox1/dev
  xvector_dir=Data/xvector/ThinResNet34/vox2/klfb_egs_baseline/arcsoft_sgd_rop/chn32_Mean_basic_downNone_none1_SAP2_dp01_alpha0_em256_wde4_var
  train_feat_dir=${xvector_dir}/vox1_dev_xvector_var

  for test_set in vox1 cnceleb aishell2;do
    echo -e "\n\033[1;4;31m Testing in ${test_set}: \033[0m"
    
    test_feat_dir=${xvector_dir}/${test_set}_test_xvector_var
    trials=${lstm_dir}/data/${test_set}/test/trials
    ./Score/plda.sh $data_path $train_feat_dir $test_feat_dir $trials
  done
# PLDA ThinResNet34
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|     vox1-test     |   1.903     |    -----    |   0.3710    |    0.6383    | 20211210 15:47:27 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|  cnceleb-test     |   17.05     |    -----    |   0.7488    |    0.8584    | 20211210 15:47:27 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
#|  aishell2-test    |   12.17     |    -----    |   0.8454    |    0.9474    | 20211210 15:47:27 |
#+-------------------+-------------+-------------+-------------+--------------+-------------------+
  exit
fi


if [ $stage -le 203 ]; then
  feat_type=klfb input_dim=80 feat=log
  model=ThinResNet resnet_size=34
  
  datasets=vox1 testset=vox1 test_subset=test sname=dev
  block_type=cbam downsample=k3 expansion=1 red_ratio=2
  encoder_type=SAP2 embedding_size=256
  # datasets=vox2 testset=vox1 test_subset=dev sname=dev
  # block_type=seblock downsample=k1 expansion=1 red_ratio=2
  # encoder_type=ASTP2 embedding_size=256
  kernel=5,5 fast=none1
  loss=arcsoft
  input_norm=Mean
  mask_layer=baseline
  scheduler=rop optimizer=sgd
  batch_size=256
  avg_size=5 alpha=0
#  encoder_type=SAP2
#  for input_dim in 64 80 ; do
  proser_ratio=1 proser_gamma=0.01 dummy=0
#        --downsample ${downsample} \
#      --trials trials_20w \
#      --mask-layer attention --init-weight vox2_rcf \
  echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
  valid_dir=dev_fb${input_dim}_valid
  seed=123456
  subname=all
  for seed in 123456 123457 123458 ; do
  for testset in vox1 ; do
#  for subname in easy hard; do #  all  --trials trials_${subname} --score-suffix ${subname}
    if [ $resnet_size -le 34 ];then
      expansion=1
    else
      expansion=2
      exp_str=_exp${expansion}
    fi
#    if [ $input_dim -eq 40 ];then
#      valid_dir=valid_fb40
#    fi
#    Mean_batch256_seblock_downk1_none1_ASTP2_dp01_alpha1_em256_wd5e4_vares_bashuf2_dummy100_beta1_gamma0.01
#    model_dir=${model}${resnet_size}/${datasets}/${feat_type}${input_dim}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/Mean_batch256_seblock_red2_downk1_avg5_ASTP2_em256_dp01_alpha0_none1_wd5e4_vares_bashuf2/${seed}
#    _dummy${dummy}_beta${proser_ratio}_gamma${proser_gamma}
#${input_norm}_batch${batch_size}_${block_type}_red2_down${downsample}_${fast}_${encoder_type}_dp01_alpha${alpha}_em${embedding_size}_wd5e4_vares_bashuf2
#    model_dir=ThinResNet34/vox2/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch128_seblock_red2_downk1_avg5_ASTP2_em256_dp01_alpha0_none1_wde5_vares_bashuf2_dist/123456
    # model_dir=ThinResNet34/vox2/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch128_seblock_red2_downk1_avg5_ASTP2_em256_dp01_alpha0_none1_wde5_vares_bashuf2_dist/123456
    # model_dir=ThinResNet34/vox2/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch128_seblock_red2_downk1_avg5_ASTP2_em256_dp01_alpha0_none1_wde5_vares_bashuf2_dist/${seed}

    model_dir=ThinResNet34/vox1/klfb80_egs_baseline/arcsoft_sgd_rop/Mean_batch256_cbam_red2_downk3_avg5_SAP2_em256_dp01_alpha0_none1_wd5e4_vares_bashuf2_dist_mani123_mani123_lamda2.0/${seed}
    # Mean_batch256_cbam_downk3_avg5_SAP2_em256_dp01_alpha0_none1_wd5e4_varesmix2_bashuf2_dist
    
#         --extract \
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} --resnet-size ${resnet_size} \
      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_fb${input_dim} \
      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev_fb${input_dim}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${valid_dir} \
      --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset}_fb${input_dim} \
      --feat-format kaldi --nj 8 \
      --input-norm Mean --input-dim ${input_dim} --remove-vad \
      --block-type ${block_type} --red-ratio ${red_ratio} --expansion ${expansion} \
      --kernel-size ${kernel} --downsample ${downsample} \
      --channels 16,32,64,128 \
      --fast ${fast} --stride 2,1 \
      --alpha ${alpha} \
      --loss-type ${loss} --margin 0.2 --s 30 --num-center ${dummy} \
      --embedding-size ${embedding_size} \
      --encoder-type ${encoder_type} \
      --time-dim 1 --avg-size ${avg_size} --dropout-p 0.1 \
      --test-input var \
      --xvector-dir Data/xvector/${model_dir}/${testset}_${test_subset}_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --gpu-id 2 --verbose 0 \
      --cos-sim
  done
  done
  exit
fi


if [ $stage -le 210 ]; then
  feat_type=klsp feat=log
  model=ThinResNet resnet_size=8
  loss=arcsoft
  encod=AVG alpha=0
  datasets=vox2 testset=sitw test_subset=test
  input_norm=Mean
#  test_subset=
  block_type=basic
  encoder_type=SAP2 embedding_size=256
#  sname=dev #dev_aug_com
  sname=dev #_aug_com
  downsample=k1 fast=none1

  chn=16
  mask_layer=rvec
#  mask_layer=attention
  weight=rclean
  scheduler=rop optimizer=sgd
  batch_size=256
  avg_size=5

#  123456 123457 123458
#  10 18 34 50
  for resnet_size in 34 ; do
  for testset in vox1 sitw ; do
  for seed in 123456 123457 123458 ;do
#    for chn in 16 32 64 ; do
      epoch=
      echo -e "\n\033[1;4;31mStage ${stage}: Testing ${model}_${resnet_size} in ${datasets} with ${loss} kernel 5,5 \033[0m\n"
      if [ $resnet_size -le 34 ];then
        expansion=1
      else
        expansion=4
        batch_size=256
      fi
      if [ $chn -eq 16 ]; then
        channels=16,32,64,128
        chn_str=
      elif [ $chn -eq 32 ]; then
        channels=32,64,128,256
        chn_str=chn32_
      elif [ $chn -eq 64 ]; then
        channels=64,128,256,512
        chn_str=chn64_
      fi

      if [ $avg_size -eq 0 ]; then
        avg_str=
      else
        avg_str=avg${avg_size}_
      fi

      if [ "$mask_layer" = "attention" ];then
        at_str=_${weight}
      else
        at_str=
      fi

      model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${seed}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_down${downsample}_${avg_str}${encoder_type}_em${embedding_size}_dp01_alpha${alpha}_${fast}${at_str}_${chn_str}wde5_var

      python -W ignore TrainAndTest/test_egs.py \
        --model ${model} --resnet-size ${resnet_size} \
        --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
        --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
        --train-trials trials_2w \
        --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
        --test-dir ${lstm_dir}/data/${testset}/${feat_type}/${test_subset} \
        --feat-format kaldi --nj 8 \
        --input-norm ${input_norm} --input-dim 161 \
        --mask-layer ${mask_layer} --init-weight ${weight} \
        --embedding-size ${embedding_size} \
        --downsample ${downsample} \
        --encoder-type ${encoder_type} --expansion ${expansion} \
        --block-type ${block_type} \
        --kernel-size 5,5 --stride 2,2 --fast ${fast} \
        --channels ${channels} \
        --alpha ${alpha} \
        --loss-type ${loss} --margin 0.2 --s 30 \
        --time-dim 1 --avg-size ${avg_size} \
        --input-length var \
        --dropout-p 0.1 \
        --xvector-dir Data/xvector/${model_dir}/${test_subset}_epoch${epoch}_var \
        --resume Data/checkpoint/${model_dir}/best.pth \
        --gpu-id 4 \
        --cos-sim
#        Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
    done
  done
  done
  exit

fi


if [ $stage -le 300 ]; then
  feat_type=klfb
  feat=fb40
  input_norm=Mean
  loss=arcsoft
  encod=STAP
  block_type=basic
  model=TDNN_v5
  embedding_size=512
  train_set=cnceleb test_set=cnceleb
  subset=dev
  # 20210902 test
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #|   Test Set   |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test |  14.9190%   |   0.1512    |   0.7366    |    0.8458    | 20210902 12:45:19 | soft
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test |  14.3642%   |   0.1225    |   0.7395    |    0.8437    | 20210902 12:50:19 | arcsoft
  #+--------------+-------------+-------------+-------------+--------------+-------------------+
  #| cnceleb-test |  14.4973%   |   0.1296    |   0.7453    |    0.8601    | 20210902 12:50:19 | arcdist
  #+--------------+-------------+-------------+-------------+--------------+-------------------+

  # for test_set in cnceleb; do # 32,128,512; 8,32,128
#    --trials trials_${s} --score-suffix ${s} --extract \

#  for s in advertisement drama entertainment interview live_broadcast movie play recitation singing speech vlog; do
# --xvector-dir Data/xvector/TDNN_v5/cnceleb/klfb_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/${test_set}_${subset}_epoch50_fix \
  #      --resume Data/checkpoint/TDNN_v5/cnceleb/klfb_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/checkpoint_50.pth \
  #   echo -e "\n\033[1;4;31m Stage${stage}: Testing with ${loss} \033[0m\n"
  #   python -W ignore TrainAndTest/test_egs.py \
  #     --model ${model} --resnet-size 14 \
  #     --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
  #     --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
  #     --train-trials trials_2w \
  #     --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
  #     --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
  #     --feat-format kaldi --input-norm ${input_norm} --input-dim 40 \
  #     --channels 512,512,512,512,1500 \
  #     --context 5,3,3,5 \
  #     --nj 10 \
  #     --alpha 0 \
  #     --margin 0.2 --s 30 \
  #     --stride 1 \
  #     --block-type ${block_type} \
  #     --embedding-size ${embedding_size} \
  #     --loss-type ${loss} \
  #     --encoder-type STAP \
  #     --input-length fix \
  #     --remove-vad \
  #     --resume Data/checkpoint/TDNN_v5/cnceleb/klfb_egs_baseline/arcdist/Mean_STAP_em512_lr1_wd5e4_var/checkpoint_50.pth \
  #     --xvector-dir Data/xvector/TDNN_v5/cnceleb/klfb_egs_baseline/arcdist/Mean_STAP_em512_lr1_wd5e4_var/${test_set}_${subset}_epoch50_fix \
  #     --frame-shift 300 \
  #     --gpu-id 0 \
  #     --cos-sim
  # done
       # --verbose 2 \

 # for s in adve_adve adve_spee dram_reci ente_reci inte_sing live_vlog play_sing sing_vlog adve_dram adve_vlog dram_sing ente_sing inte_spee movi_movi play_spee spee_spee adve_ente dram_spee ente_spee inte_vlog movi_play play_vlog spee_vlog adve_inte dram_dram dram_vlog ente_vlog live_live movi_reci reci_reci vlog_vlog adve_live dram_ente ente_ente inte_inte live_movi movi_sing reci_sing adve_movi dram_inte ente_inte inte_live live_play movi_spee reci_spee adve_play dram_live ente_live inte_movi live_reci movi_vlog reci_vlog adve_reci dram_movi ente_movi inte_play live_sing play_play sing_sing adve_sing dram_play ente_play inte_reci live_spee play_reci sing_spee; do
 for s in adad adpl drdr drre enli envl insi lire more plsi revl vlvl addr adre dren drsi enmo inin insp lisi mosi plsp sisi aden adsi drin drsp enpl inli invl lisp mosp plvl sisp adin adsp drli drvl enre inmo lili livl movl rere sivl adli advl drmo enen ensi inpl limo momo plpl resi spsp admo drpl enin ensp inre lipl mopl plre resp spvl; do
   python -W ignore TrainAndTest/test_egs.py \
     --model ${model} --resnet-size 14 \
     --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
     --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w --trials subtrials/trials_${s} --score-suffix ${s} \
     --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
     --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/dev_${feat} \
     --feat-format kaldi --nj 12 \
     --input-norm ${input_norm} --input-dim 40 --remove-vad \
     --channels 512,512,512,512,1500 \
     --context 5,3,3,5 \
     --alpha 0 \
     --loss-type ${loss} --margin 0.2 --s 30 \
     --stride 1 \
     --block-type ${block_type} \
     --embedding-size ${embedding_size} \
     --encoder-type STAP \
     --input-length fix \
     --frame-shift 300 \
     --xvector-dir Data/xvector/TDNN_v5/cnceleb/klfb_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/${test_set}_dev_epoch50_fix \
     --resume Data/checkpoint/TDNN_v5/cnceleb/klfb_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/checkpoint_50.pth \
     --gpu-id 0 --extract \
     --cos-sim
 done

#  python -W ignore TrainAndTest/test_egs.py \
#      --model ${model} --resnet-size 14 \
#      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
#      --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
#      --train-trials trials_2w --trials trials_640w --score-suffix dev_640w \
#      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
#      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/dev_${feat} \
#      --feat-format kaldi \
#      --input-norm ${input_norm} \
#      --input-dim 40 \
#      --channels 512,512,512,512,1500 \
#      --context 5,3,3,5 \
#      --nj 12 \
#      --alpha 0 \
#      --loss-type ${loss} --margin 0.15 --s 30 \
#      --stride 1 \
#      --block-type ${block_type} \
#      --encoder-type STAP --embedding-size ${embedding_size} \
#      --input-length fix \
#      --remove-vad \
#      --frame-shift 300 \
#      --xvector-dir Data/xvector/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/${test_set}_dev_epoch60_fix \
#      --resume Data/checkpoint/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/checkpoint_60.pth \
#      --gpu-id 1 \
#      --verbose 2 \
#      --cos-sim

#  for s in advertisement drama entertainment interview live_broadcast movie play recitation singing speech vlog; do
#  for s in vlog; do
##    echo -e "\n\033[1;4;31m Stage${stage}: Testing with ${loss} \033[0m\n"
#    python -W ignore TrainAndTest/test_egs.py \
#      --model ${model} --resnet-size 14 \
#      --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
#      --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
#      --train-trials trials_2w \
#      --trials subtrials/trials_vlog_${s} \
#      --score-suffix vl${s} \
#      --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/valid_${feat} \
#      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/dev_${feat} \
#      --feat-format kaldi \
#      --input-norm ${input_norm} \
#      --input-dim 40 \
#      --channels 512,512,512,512,1500 \
#      --context 5,3,3,5 \
#      --nj 12 \
#      --alpha 0 \
#      --margin 0.15 --s 30 \
#      --stride 1 \
#      --block-type ${block_type} \
#      --embedding-size ${embedding_size} \
#      --loss-type ${loss} \
#      --encoder-type STAP \
#      --input-length fix \
#      --remove-vad \
#      --frame-shift 300 \
#      --xvector-dir Data/xvector/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/${test_set}_dev_epoch60_fix \
#      --resume Data/checkpoint/TDNN_v5/cnceleb/pyfb_egs_revg/${loss}/featfb40_ws25_inputMean_STAP_em256_wde3_step5_domain2/checkpoint_60.pth \
#      --gpu-id 1 \
#      --extract \
#      --cos-sim
#  done
  exit
#  for s in vlog; do
#    wc -l data/cnceleb/dev/subtrials/trials_vlog_${s}
#  done
fi

if [ $stage -le 301 ]; then
  model=ThinResNet resnet_size=34
  input_dim=80  input_norm=Inst feat_type=klfb
  feat=fb${input_dim}
  loss=arcsoft

#  encoder_type=SAP2 embedding_size=512
  encoder_type=SAP2 embedding_size=256
  # block_type=seblock downsample=k1 red_ratio=2
  # block_type=seblock downsample=k1 red_ratio=2
  block_type=cbam downsample=k3 red_ratio=2
  kernel=5,5 fast=none1
  loss=arcsoft
  alpha=0

  batch_size=256
  mask_layer=baseline mask_len=5,5
  # train_set=cnceleb test_set=cnceleb
  train_set=vox1 test_set=vox1
  train_subset=
#  subset=dev
  subset=test test_input=var
  epoch=13

#     --trials subtrials/trials_${s} --score-suffix ${s} \
# Data/checkpoint/ThinResNet34/cnceleb/klfb80_egs_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em512_wd5e4_var
#--score-norm as-norm --n-train-snts 100000 --cohort-size 5000 \
#     --vad-select \

echo -e "\n\033[1;4;31m Stage${stage}: Test ${model}${resnet_size} in ${test_set}_egs with ${loss} with ${input_norm} normalization \033[0m\n"

for seed in 123456 123457 123458 ; do
  s=all
  for epoch in best ; do     #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
  # for ((epoch=1; epoch<=46; epoch=epoch+1)); do
#    model_dir=ThinResNet34/cnceleb/klfb40_egs12_both_binary/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em512_dom1_wd5e4_var_es
    # model_dir=ThinResNet34/cnceleb/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_seblock_red2_downk1_avg5_ASTP2_em256_dp01_alpha0_none1_wde4_vares_bashuf2_dist_mani234_lamda2.0/123456
    # model_dir=ThinResNet34/vox1/klfb80_egs_baseline/arcsoft_sgd_rop/Mean_batch256_seblock_red2_downk1_avg5_SAP2_em256_dp01_alpha0_none1_wde4_varesmix2_bashuf2/${seed}
    #  model_dir=ThinResNet10/vox1/klfb80_egs_kd_baseline/arcsoft_sgd_rop/Mean_batch256_seblock_red2_downk3_avg5_ASTP2_em256_dp01_alpha0_none1_wd5e4_var_attention1000_time_feat_bashuf/${seed}
    #  model_dir=ThinResNet10/vox1/klfb80_egs_baseline/arcsoft_sgd_rop/Mean_batch256_seblock_red2_downk1_avg5_SAP2_em256_dp01_alpha0_none1_wde4_varesmix2_bashuf2/${seed}
    # model_dir=ThinResNet34/cnceleb/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_seblock_red2_downk1_avg5_ASTP2_em256_dp01_alpha0_none1_wde4_varesmix2_bashuf2_dist/123456
    # model_dir=ThinResNet34/vox1/klfb80_egs_baseline/arcsoft_sgd_rop/Mean_batch256_cbam_downk3_avg5_SAP2_em256_dp01_alpha0_none_wde4_varesmix2_bashuf2_dist/123456
    #_core/percent0.5_random/123456

    # center extract
    # model_dir=ThinResNet34/vox1/klfb_egs_baseline/arcsoft_sgd_step/Mean_batch256_seblock_red2_downk1_avg5_SAP2_em256_dp01_alpha0_none1_wd5e4_varesmix2_bashuf2_dist_cnc_core/percent0.5_random/123456 # _cnc
    # model_dir=ThinResNet34/cnceleb/klfb_egs_baseline/arcsoft_sgd_step/Mean_batch256_seblock_red2_downk1_avg5_SAP2_em256_dp01_alpha0_none1_wd5e4_varesmix2_bashuf2_dist_core/percent0.5_random/123456
    model_dir=ThinResNet34/vox1/klfb80_egs_baseline/arcsoft_sgd_rop/Inst_batch256_cbam_downk3_avg5_SAP2_em256_dp01_alpha0_none1_wd5e4_varesmix2_bashuf2_dist/baseline/${seed}

   python -W ignore TrainAndTest/train_egs/test_egs.py \
     --model ${model} --resnet-size ${resnet_size} \
     --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev${train_subset}_${feat} \
     --train-extract-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev${train_subset}_${feat} \
     --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
     --train-trials trials_2w \
     --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev${train_subset}_${feat}_valid \
     --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
     --feat-format kaldi --nj 6 --remove-vad \
     --input-norm ${input_norm} --input-dim ${input_dim} \
     --mask-layer ${mask_layer} --mask-len ${mask_len} \
     --kernel-size ${kernel} --fast ${fast} --stride 2,1 \
     --channels 16,32,64,128 \
     --time-dim 1 --avg-size 5 \
     --loss-type ${loss} --margin 0.2 --s 30 \
     --block-type ${block_type} --downsample ${downsample} --red-ratio ${red_ratio} \
     --encoder-type ${encoder_type} --embedding-size ${embedding_size} --alpha 0 \
     --test-input ${test_input} --frame-shift 300 \
     --xvector-dir Data/xvector/${model_dir}/${test_set}_${subset}_${epoch}_${test_input}_nomean \
     --resume Data/checkpoint/${model_dir}/${epoch}.pth \
     --gpu-id 5 --verbose 1 \
     --cos-sim
     # checkpoint_${epoch}.pth _${epoch}
#     --extract \
#      --model-yaml Data/checkpoint/ThinResNet34/cnceleb/klfb40_egs12_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em512_wd5e4_var/model.2022.02.22.yaml \
 done
done

# ThinResNet 18 dev 1 both mask 5,5
# ThinResNet18/cnceleb/klfb_egs_both/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em512_wd5e4_var/model.2022.03.25.yaml
# +-------------------+-------------+-------------+-------------+--------------+-------------------+
# |     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
# +-------------------+-------------+-------------+-------------+--------------+-------------------+
# |   cnceleb-test2   |   15.1695   |   0.1361    |   0.6795    |    0.8206    | 20220413 22:01:21 |
# |   cnceleb-test    |   13.5036   |   0.1474    |   0.6502    |    0.7434    | 20220426 15:34:33 | vad select
# |   cnceleb-test    |   13.5657   |   0.1475    |   0.6518    |    0.7377    | 20220325 16:26:40 |

# ThinResNet 34 dev 1 2
# ThinResNet34/cnceleb/klfb40_egs12_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em512_wd5e4_var/model.2022.02.22.yaml
# |   cnceleb-test2   |   2.1231    |   0.2031    |   0.0924    |    0.1497    | 20220413 22:37:30 |
# |   cnceleb-test    |   12.7860   |   0.1296    |   0.6069    |    0.7224    | 20220222 01:49:12 |
# |   cnceleb-test    |   12.7521   |   0.1296    |   0.6118    |    0.7273    | 20220426 15:48:18 | vad select
# |   cnceleb-test    |   12.6165   |   -1.5863   |   0.6032    |    0.7168    | 20220426 16:28:10 | vad select as-norm

# ThinResNet 34 dev 1 2 early stopping spechaug
#ThinResNet34/cnceleb/klfb40_egs12_both_binary/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em512_dom1_wd5e4_var_es/checkpoint_13.pth
#|   cnceleb-test    |  10.2831    |    0.1450   |   0.5341    |    0.6478    | 20220513 21:34:44 |
#|   cnceleb-test    |   9.9780    |   -1.5883   |   0.5206    |    0.6432    | 20220515 10:37:41 | as-norm

# for s in adad adpl drdr drre enli envl insi lire more plsi revl vlvl addr adre dren drsi enmo inin insp lisi mosi plsp sisi aden adsi drin drsp enpl inli invl lisp mosp plvl sisp adin adsp drli drvl enre inmo lili livl movl rere sivl adli advl drmo enen ensi inpl limo momo plpl resi spsp admo drpl enin ensp inre lipl mopl plre resp spvl; do
#    model_dir=ThinResNet34/cnceleb/klfb80_egs_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em512_wd5e4_var
#   python -W ignore TrainAndTest/test_egs.py \
#     --model ${model} --resnet-size ${resnet_size} \
#     --train-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat} \
#     --train-test-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}/trials_dir \
#     --train-trials trials_2w --trials subtrials/trials_${s} --score-suffix ${s} \
#     --valid-dir ${lstm_dir}/data/${train_set}/${feat_type}/dev_${feat}_valid \
#     --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/dev_${feat} \
#     --feat-format kaldi --nj 8 \
#     --input-norm ${input_norm} --input-dim 80 --remove-vad \
#     --kernel-size ${kernel} \
#     --channels 32,64,128,256 \
#     --fast none1 --stride 2,2 \
#     --time-dim 1 --avg-size 5 \
#     --alpha 0 \
#     --loss-type ${loss} --margin 0.2 --s 30 \
#     --block-type ${block_type} --downsample ${downsample} \
#     --embedding-size ${embedding_size} \
#     --encoder-type ${encoder_type} \
#     --input-length fix \
#     --frame-shift 300 \
#     --xvector-dir Data/xvector/${model_dir}/${test_set}_dev_epoch60_fix \
#     --resume Data/checkpoint/${model_dir}/checkpoint_60.pth \
#     --gpu-id 5 \
#     --extract --cos-sim \
#     --verbose 0
# done
 exit
#  for s in vlog; do
#    wc -l data/cnceleb/dev/subtrials/trials_vlog_${s}
#  done
fi

if [ $stage -le 400 ]; then
  feat_type=klfb feat=fb40
  loss=arcsoft
  model=TDNN_v5
  encod=STAP embedding_size=512
#  dataset=aishell2 test_set=aishell2 subset=test
  dataset=vox2 test_set=vox1 subset=dev

  input_dim=40 input_norm=Mean
  # Training set: aishell2 40-dimensional log fbanks kaldi  Loss: arcsoft
  # Cosine Similarity
  #|     Test Set      |   EER (%)   |  Threshold  | MinDCF-0.01 | MinDCF-0.001 |       Date        |
  #|     vox1-test     |   21.5960   |   0.2504    |   0.8862    |    0.9153    | 20211213 16:16:06 |
  #|   cnceleb-test    |   25.9654   |   0.2082    |   0.8930    |    0.9493    | 20211213 16:21:13 |
  #|   aishell2-test   |   1.5800    |   0.2139    |   0.3112    |    0.5945    | 20211213 16:22:51 |

#  model_dir=TDNN_v5/aishell2/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_STAP_em512_wd5e4_var
  model_dir=TDNN_v5/vox2/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch128_STAP_em512_wde5_vares_dist_mani-1_lamda2/123456
  echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
#  test_set=vox1
#easy hard
  for subname in easy hard ; do # 32,128,512; 8,32,128
#  --trials trials_${subname} --score-suffix ${subname} \
#  for test_set in vox1 sitw ; do # 32,128,512; 8,32,128
#  for subname in all ;do
    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_${feat}/trials_dir \
      --train-trials trials_2w --trials trials_${subname} --score-suffix ${subname} \
      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/valid_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
      --feat-format kaldi --nj 6 \
      --input-norm ${input_norm} --input-dim ${input_dim} --remove-vad \
      --embedding-size ${embedding_size} \
      --encoder-type ${encod} \
      --channels 512,512,512,512,1500 \
      --stride 1,1,1,1 \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --test-input var \
      --frame-shift 300 \
      --xvector-dir Data/xvector/${model_dir}/${test_set}_${subset}_epoch_best_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --gpu-id 0 --verbose 4 --extract \
      --cos-sim
  done
  exit
fi


if [ $stage -le 450 ]; then
  feat_type=klsp feat=klsp
  loss=arcsoft
  model=ECAPA
  encoder_type=ASTP embedding_size=192
  dataset=vox2 test_set=vox1 subset=test
  input_dim=161 input_norm=Mean
  block_type=res2tdnn

  mask_layer=baseline
  scheduler=rop optimizer=sgd
  input_dim=161
  batch_size=128
  chn=512
  seed=123456

  # Training set: vox2 161-dimensional log spectrogram kaldi  Loss: arcsoft
#      --remove-vad \
  for test_set in vox1 aishell2 sitw; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    model_dir=${model}/${dataset}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_${encoder_type}_em${embedding_size}_${chn_str}wd2e5_vares_bashuf/${seed}

    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset} \
      --feat-format kaldi --nj 4 \
      --input-norm ${input_norm} --input-dim ${input_dim} \
      --embedding-size ${embedding_size} \
      --encoder-type ${encoder_type} \
      --channels 512,512,512,512,1536 \
      --stride 1,1,1,1 \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --test-input var --frame-shift 300 \
      --xvector-dir Data/xvector/${model_dir}/${test_set}_${subset}_best_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --check-yaml Data/checkpoint/${model_dir}/model.2022.09.07.yaml \
      --gpu-id 1 \
      --cos-sim
  done
  exit
fi
#|     vox1-test     |   1.5907    |   0.2671    |    0.2124     |    0.2949     | 20220911 17:05:26 |
#|   aishell2-test   |   6.7900    |   0.3375    |    0.6747     |    0.8591     | 20220911 17:10:06 |
#|     sitw-test     |   3.4718    |   0.2345    |    0.2884     |    0.4428     | 20220911 17:11:53 |

if [ $stage -le 451 ]; then
  feat_type=klfb feat=klfb
  loss=arcsoft
  model=ECAPA
  encoder_type=SASP2 embedding_size=192
  dataset=vox2 test_set=vox1 subset=test
  input_dim=40 input_norm=Mean
  block_type=res2tdnn

  mask_layer=baseline
  scheduler=rop optimizer=sgd
  batch_size=128
  chn=512
  seed=123456

  # Training set: vox2 161-dimensional log spectrogram kaldi  Loss: arcsoft
#      --remove-vad \
  echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
  for test_set in sitw ; do # 32,128,512; 8,32,128 aishell2 sitw
  for seed in 123456 123457 123458; do 
    # model_dir=${model}/${dataset}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_${encoder_type}_em${embedding_size}_${chn_str}wd2e5_vares_bashuf/${seed}
    model_dir=ECAPA/vox2/klfb_egs_baseline/arcsoft_adam_cyclic/Mean_batch256_SASP2_em192_wde5_2sesmix2_dist/${seed}
    # model_dir=ECAPA/vox2/klfb_egs_baseline/arcsoft_adam_cyclic/Mean_batch256_SASP2_em192_wde5_2sresmix2_dist_mani12_lamda0.2/${seed}

    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40 \
      --train-test-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40_valid \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_fb40 \
      --feat-format kaldi --nj 4 \
      --input-norm ${input_norm} --input-dim ${input_dim} \
      --embedding-size ${embedding_size} \
      --encoder-type ${encoder_type} \
      --channels 512,512,512,512,1536 \
      --stride 1,1,1,1 \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --test-input var --frame-shift 300 \
      --xvector-dir Data/xvector/${model_dir}/${test_set}_${subset}_best_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --check-yaml Data/checkpoint/${model_dir}/model.2022.09.07.yaml \
      --gpu-id 0 \
      --cos-sim --remove-vad
  done
  done
  exit
fi

if [ $stage -le 452 ]; then
  feat_type=wave feat=wave
  loss=arcsoft
  model=ECAPA
  encoder_type=SASP2 embedding_size=192
  dataset=vox2 test_set=vox1 subset=test
  input_dim=80 input_norm=Mean
  block_type=res2tdnn

  mask_layer=baseline
  filter_layer=fbank feat_dim=80
  scheduler=rop optimizer=sgd
  batch_size=128
  chn=512
  seed=123456

  # Training set: vox2 161-dimensional log spectrogram kaldi  Loss: arcsoft
#      --remove-vad \
  echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
  for test_set in vox1 sitw ; do # 32,128,512; 8,32,128 aishell2 sitw
  for seed in 123456 123457 123458; do 
    # model_dir=${model}/${dataset}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_${encoder_type}_em${embedding_size}_${chn_str}wd2e5_vares_bashuf/${seed}
    model_dir=ECAPA/vox2/wave_egs_baseline/arcsoft_adam_cyclic/Mean_batch128_SASP2_em192_wde5_2sesmix2_dist/${seed}

    python -W ignore TrainAndTest/test_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev \
      --train-test-dir ${lstm_dir}/data/${dataset}/${subset} \
      --train-trials trials \
      --valid-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_valid \
      --test-dir ${lstm_dir}/data/${test_set}/${subset} \
      --feat-format wav --nj 4 \
      --input-norm ${input_norm} --input-dim ${input_dim} \
      --filter ${filter_layer} --feat-dim ${feat_dim} \
      --embedding-size ${embedding_size} \
      --encoder-type ${encoder_type} \
      --channels 512,512,512,512,1536 \
      --stride 1,1,1,1 \
      --loss-type ${loss} --margin 0.2 --s 30 \
      --test-input var --frame-shift 300 \
      --xvector-dir Data/xvector/${model_dir}/${test_set}_${subset}_best_var \
      --resume Data/checkpoint/${model_dir}/best.pth \
      --check-yaml Data/checkpoint/${model_dir}/model.2022.09.07.yaml \
      --gpu-id 2 \
      --cos-sim
  done
  done
  exit
fi

if [ $stage -le 500 ]; then
  model=ThinResNet resnet_size=18
  # datasets=aidata testset=aidata
  datasets=vox1 testset=vox1
  feat_type=wave feat=log
  loss=arcsoft
  alpha=0
  input_norm=Mean
#  test_subset=
  block_type=seblock red_ratio=2
  encoder_type=ASTP2 embedding_size=256
#  sname=dev #dev_aug_com
  sname=train #_aug_com
  downsample=k1 fast=none1
  test_subset=test
  chn=16
#  mask_layer=rvec
  mask_layer=baseline mask_len=5,10
  weight=rclean_max weight_norm=max
  scheduler=rop optimizer=sgd
  batch_size=256
  
  avg_size=5
  filter_layer=fbank
  feat_dim=40 input_dim=40
  lamda_beta=1

  for testset in aidata ; do
  for resnet_size in 18 ; do
  for seed in 123456 123457 123458 ;do
#  for sub_trials in hard ; do _${sub_trials} --score-suffix ${sub_trials}
#    for chn in 16 32 64 ; do
      epoch=
      if [ $resnet_size -le 34 ];then
        expansion=1
      else
        expansion=2
        exp_str=_exp${expansion}
      fi
      if [ $chn -eq 16 ]; then
        channels=16,32,64,128
        chn_str=
      elif [ $chn -eq 32 ]; then
        channels=32,64,128,256
        chn_str=chn32_
      elif [ $chn -eq 64 ]; then
        channels=64,128,256,512
        chn_str=chn64_
      fi

      if [ $avg_size -eq 0 ]; then
        avg_str=
      else
        avg_str=avg${avg_size}_
      fi

      at_str=
      if [[ $mask_layer == attention* ]];then
        at_str=_${weight}
      #        --score-suffix
      elif [ "$mask_layer" = "both" ];then
        at_str=_`echo $mask_len | sed  's/,//g'`
      fi

      model_dir=${model}${resnet_size}/${datasets}/${feat_type}${input_dim}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_red${red_ratio}${exp_str}_down${downsample}_avg${avg_size}_${encoder_type}_em${embedding_size}_dp01_alpha${alpha}_${fast}${at_str}_${chn_str}wd5e4_vares_bashuf2_${filter_layer}${feat_dim}_mixup${lamda_beta}_2/${seed}
      # _mixup${lamda_beta}_0

      python -W ignore TrainAndTest/test_egs.py \
        --model ${model} --resnet-size ${resnet_size} \
        --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname} \
        --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
        --train-trials trials_2w --extract-trials --trials trials \
        --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/${sname}_valid \
        --test-dir ${lstm_dir}/data/${testset}/${test_subset} \
        --feat-format wav --nj 12 \
        --input-norm ${input_norm} --input-dim ${input_dim} \
        --filter ${filter_layer} --feat-dim ${feat_dim} \
        --mask-layer ${mask_layer} --init-weight ${weight} --weight-norm ${weight_norm} \
        --block-type ${block_type} --downsample ${downsample} --red-ratio ${red_ratio} --expansion ${expansion} \
        --kernel-size 5,5 --fast ${fast} --stride 2,1 \
        --expansion ${expansion} --channels ${channels} \
        --alpha ${alpha} \
        --loss-type ${loss} --margin 0.2 --s 30 \
        --time-dim 1 --avg-size ${avg_size} --encoder-type ${encoder_type} --embedding-size ${embedding_size} \
        --test-input var \
        --dropout-p 0.1 \
        --xvector-dir Data/xvector/${model_dir}/${test_subset}_epoch${epoch}_var \
        --resume Data/checkpoint/${model_dir}/best.pth \
        --gpu-id 4 --verbose 0 \
        --cos-sim
#        Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
    done
  done
#  done
  done
  exit
#  resnet18_seblcok_red2_astp2-wav-fbank40-baseline
#|    aidata-test    |  5.33±0.14  |             | 0.4665±0.0047 | 0.7887±0.0031 |
#|    aidata-test    |  5.86±0.13  |             | 0.4554±0.0058 | 0.7793±0.0189 | # mixup0_0.2
#|    aidata-test    |  5.23±0.16  |             | 0.4232±0.0072 | 0.7721±0.0056 | # clean + half_mixup0_0.2
#|    aidata-test    |  5.14±0.02  |             | 0.4364±0.0147 | 0.7679±0.0181 | # clean + half_mixup0_0.5
fi

if [ $stage -le 600 ]; then
  model=ThinResNet resnet_size=18
  train_set=vox2 test_set=vox1 # #jukebox cnceleb
  # train_set=vox2 test_set=vox1 # #jukebox cnceleb
  train_subset=
  subset=test test_input=var test_subset=test
  gpu_id=6
echo -e "\n\033[1;4;31m Stage${stage}: Test ${model}${resnet_size} in ${test_set}_egs with ${loss} with ${input_norm} normalization \033[0m\n"

for seed in 123456  ; do
  sname=dev
  for epoch in 23 ; do     #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
    # vox2
    # model_dir=ThinResNet34/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox2/wave_fb80_dist/123456
    # epoch=35 yaml_name=model.2023.06.27.yaml
    # model_dir=ThinResNet18/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox2/wave_fb80_dist2_fgrl5/123456
    # yaml_name=model.2023.08.04.yaml
    
    # baseline vox1
    # model_dir=ThinResNet34/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox1/wave_fb80_dist2/123456
    # epoch=25 yaml_name=model.2023.09.10.yaml
    # aug5
    # model_dir=ThinResNet34/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox1/wave_fb80_dist2_aug5/123456
    # epoch=31 yaml_name=model.2023.09.15.yaml
    # aug5_bandpass
    # model_dir=ThinResNet34/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox1/wave_fb80_dist2_aug5band/123456
    # epoch=33 yaml_name=model.2023.09.18.yaml
    # ecapa band 
    # model_dir=ThinResNet34/Mean_batch128_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox1/wave_fb80_dist2_band/123456
    # epoch=43 yaml_name=model.2023.09.19.yaml
    # model_dir=ThinResNet18/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox2/wave_fb80_dist2/123456
    # epoch=18 yaml_name=model.2023.08.01.yaml
    # model_dir=ThinResNet18/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox2/wave_fb80_dist2_fgrl82/123456
    # epoch=38 yaml_name=model.2023.11.19.yaml
    model_dir=ThinResNet18/Mean_batch128_k7_seblock_downk1_avg1_SAP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox2/wave_fb80_dist2_frl21/123456
    epoch=30 yaml_name=model.2023.08.28.yaml

    # model_dir=ECAPA_brain/Mean_batch192_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_band4025/123456
    # epoch=23 yaml_name=model.2023.11.16.yaml

    # model_dir=ThinResNet34/Mean_batch128_seblock_downk1_avg1_SASP2_em256_dp01_alpha0_none1_wd5e5_varesmix8/arcsoft_sgd_rop/vox1/wave_fb80_dist2/123456
    # epoch=31 yaml_name=model.2023.10.10.yaml
    # model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug64radio/123456
    # epoch=12 yaml_name=model.2023.11.13.yaml

    for test_subset in all; do #test_radio_chn2
      for trials in trials_all; do
        python -W ignore TrainAndTest/train_egs/test_egs.py \
          --train-dir ${lstm_dir}/data/${train_set}/${sname} \
          --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
          --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
          --feat-format wav --nj 4 \
          --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
          --xvector-dir Data/xvector/${model_dir}/${test_set}_${test_subset}_${test_input} \
          --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
          --gpu-id ${gpu_id} \
          --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 1 \
          --cos-sim --test
      done

      for trials in original easy hard female male females males ; do # original easy hard
        python -W ignore TrainAndTest/train_egs/test_egs.py \
          --train-dir ${lstm_dir}/data/${train_set}/${sname} \
          --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
          --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
          --feat-format wav --nj 4 \
          --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
          --xvector-dir Data/xvector/${model_dir}/${test_set}_${test_subset}_${test_input} \
          --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
          --gpu-id ${gpu_id} --score-suffix ${trials} \
          --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
          --cos-sim --extract
      done
    done

 done
done

fi


if [ $stage -le 601 ]; then
  model=ThinResNet resnet_size=18
  train_set=vox1 test_set=vox1 # #jukebox cnceleb
  train_subset=
  subset=test test_input=var test_subset=test
  gpu_id=5
  
  sname=dev
  # for epoch in 24 ; do #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
  for epoch in avg3 ; do #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41

    # vox1 1235 1236
    # for model_name in ecapa_aug53_attenoise10100_prob08 ecapa_aug53_pattenoise10100_prob08 ecapa_aug53_noise10100_prob08 ecapa_aug53_burr10 ecapa_aug53_inspecaug05 ecapa_aug53_dp111_before ; do

    for model_name in ecapa_aug53 ecapa_aug53_dp111 ecapa_aug53_attenoise10100 ecapa_aug53_attenoise10100_prob08 ecapa_aug53_pattenoise10100_prob08 ecapa_aug53_noise10100_prob08 ecapa_aug53_burr10 ecapa_aug53_inspecaug05 ecapa_aug53_dp111_attenoise10100 ecapa_aug53_radionoise1010 ecapa_aug53_radionoise10100 ; do
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1

    echo -e "\n\033[1;4;31m Stage${stage}: Test ${model_name} in ${test_set} \033[0m\n"
      for test_subset in test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3; do #test_radio_chn2
      for seed in 1234 1235 1236 ; do
        if [[ $model_name == ecapa_aug53 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.16.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.17.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.17.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp111 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_dp111/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.17.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.18.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_burr10 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_burr1210/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.24.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.24.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.24.yaml
          fi
        elif [[ $model_name == ecapa_aug53_magdp111 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_mag111/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.21.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.22.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.22.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp111_before ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_dp111_before/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.26.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.26.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.27.yaml
          fi
        elif [[ $model_name == ecapa_aug53_multilayer10 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_attenoise_multilayers1/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.20.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.21.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.21.yaml
          fi
        elif [[ $model_name == ecapa_aug53_inspecaug05 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_inspecaug05/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.19.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.20.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.20.yaml
          fi
        elif [[ $model_name == ecapa_aug53_noise10100_prob08 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_noise10100_prob08/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.27.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.27.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.29.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10100_prob08 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_attenoise10100_prob08/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.27.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.27.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.27.yaml
          fi
        elif [[ $model_name == ecapa_aug53_pattenoise10100_prob08 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_pattenoise10100_prob08/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.28.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.28.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.28.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10100_before ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_attenoise10100_before/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.25.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.26.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.26.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp111_attenoise10100 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_dp111_attenoise10100/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.20.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.20.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.21.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10100 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_attenoise10100/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.18.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.18.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.19.yaml
          fi
        elif [[ $model_name == ecapa_aug53_radionoise1010 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_radionoise/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.23.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.23.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.24.yaml
          fi
        elif [[ $model_name == ecapa_aug53_radionoise10100 ]];then
          model_dir=${common_path}/wave_fb80_dist_aug53_radionoise10100/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.26.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.27.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.27.yaml
          fi
        fi

          xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_${test_input}_${epoch}
          for trials in trials_all; do
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --test
          done

          for trials in original ; do # original easy hard
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} --score-suffix ${trials}-${epoch} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --extract
          done
      done
    done
    done
 done
 exit
fi

if [ $stage -le 602 ]; then
  model=ThinResNet resnet_size=18
  train_set=vox1 test_set=vox1 # #jukebox cnceleb

  train_subset=
  subset=test test_input=var test_subset=test
  gpu_id=1
  
  sname=dev_orgsnr1
  for epoch in 24 ; do #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
    # vox1 1235 1236
    for model_name in ecapa_aug53_attenoise_multilayers1 ; do # ecapa_aug53 
      echo -e "\n\033[1;4;31m Stage${stage}: Test ${model_name} in ${test_set}_egs  \033[0m\n"

      for test_subset in test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3; do #test_radio_chn2
      for seed in 1234 1235 1236; do
        if [[ $model_name == ecapa_aug53 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_aug53/${seed}
          if [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.21.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.21.yaml
          elif [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.20.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp111 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_aug53_dp111/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.24.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.26.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.28.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp111_attenoise10100 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_aug53_dp111_attenoise10100/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.25.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.27.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.29.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10100_prob2x05 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_dist_aug53_attenoise10100_prob2x0.5/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.16.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.16.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.17.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10100_prob2x07 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_dist_aug53_attenoise10100_prob2x07/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.17.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.18.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.17.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10_prob08 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_dist_aug53_attenoise10_probones08/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.20.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.21.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.21.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise_multilayers1 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_dist_aug53_attenoise_multilayers1/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.20.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.21.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.21.yaml
          fi
        elif [[ $model_name == ecapa_aug53_db10 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_dist_aug53_db10/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.18.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.19.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.19.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10100 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_aug53_attenoise10100/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.25.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.26.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.28.yaml
          fi
        elif [[ $model_name == ecapa_aug53_radionoise ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_aug53_radionoise/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.26.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.27.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.01.29.yaml
          fi
        fi
          xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_${test_input}
          for trials in trials_all; do
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --test
          done

          for trials in original ; do # original easy hard
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} --score-suffix ${trials} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --extract
          done
      done
    done
    done
 done
 exit
fi


if [ $stage -le 603 ]; then
  model=ECAPA_brain 
  train_set=vox2 test_set=vox1 #test_set=himia # # #jukebox cnceleb

  train_subset=
  subset=test test_input=var test_subset=test
  gpu_id=1

  sname=dev_2radsnr05 #dev
  for epoch in 12 ; do #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
    # vox1 1235 1236
    for model_name in ecapa_orgsnr05_aug53 ; do #ecapa_aug53_dp111 ecapa_aug53_attenoise10100 ecapa_aug53_dp111_attenoise10100 ecapa_aug53_radionoise
      # for test_subset in test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3; do #test_radio_chn2  
      echo -e "\n\033[1;4;31m Stage${stage}: Test ${model_name} in dataset: ${test_set}_${test_subset} \033[0m\n"

      for test_subset in all all_radsnr05 all_radsnr1 ; do #test
      # for test_subset in srctest ; do #test_radio_chn2
      # for test_subset in test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3; do #test_radio_chn2
      for seed in 1234 ; do
        if [[ $model_name == ecapa_aug53 ]];then
          # model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_chn768_2sesmix2/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug53/${seed}
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53/${seed}
          if [[ $seed == 123456 ]];then
            yaml_name=model.2024.01.15.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.21.yaml
          elif [[ $seed == 1234 ]];then
            yaml_name=model.2024.01.29.yaml
          fi
        elif [[ $model_name == ecapa_orgsnr05_aug53 ]];then
          # model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_chn768_2sesmix2/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug53/${seed}
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_orgsnr05_aug53/${seed}
          if [[ $seed == 123456 ]];then
            yaml_name=model.2024.01.15.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.01.21.yaml
          elif [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.20.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise10100 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_chn768_2sesmix2/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug53_attenoise/${seed}
          yaml_name=model.2024.01.18.yaml
          #yaml_name=model.2024.01.18.yaml
          #yaml_name=model.2024.01.18.yaml
        elif [[ $model_name == ecapa_aug53_attenoise1050 ]];then
          # model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_chn768_2sesmix2/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug53_attenoise1050/${seed}
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53_attenoise1050/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.07.yaml
          else
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise510 ]];then
          # model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_chn768_2sesmix2/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug53_attenoise1050/${seed}
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53_attenoise510/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.10.yaml
          else
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise1050_probones08 ]];then
          # model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_chn768_2sesmix2/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug53_attenoise1050/${seed}
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53_attenoise1050_probones08/${seed}
          if [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.15.yaml
          else
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_attenoise1050_probones08_vanilla05 ]];then
          # model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_chn768_2sesmix2/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug53_attenoise1050/${seed}
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53_attenoise1050_probones08_vanilla05/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.17.yaml
          else
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp111 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53_dp111/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.05.yaml
          else
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp05 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53_dp05/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.07.yaml
          else
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_db05 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/${train_set}/wave_fb80_dist_aug53_db05/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.14.yaml
          else
            yaml_name=model.2024.01.18.yaml
          fi
        elif [[ $model_name == ecapa_aug53_dp111_attenoise10100 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_dist_aug53_dp111_attenoise10100/${seed}
          yaml_name=model.2024.01.21.yaml
        elif [[ $model_name == ecapa_aug53_radionoise ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_dist_aug53_radionoise/${seed}
          yaml_name=model.2024.01.24.yaml
        fi
          xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_${test_input}
          for trials in trials_all; do
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/${sname} \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --test
          done

          # for trials in original ; do # original easy hard
          for trials in original easy hard ; do # voxsrc2020 voxsrc2021 voxsrc2022
          # for trials in 1m mic ; do # original easy hard
          # for trials in original easy hard voxsrc2020 voxsrc2021 voxsrc2022; do # original 
          # for trials in 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 ; do # original easy hard
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/${sname} \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} --score-suffix ${trials} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --extract
          done
      done
    done
    done
 done
 exit
fi


if [ $stage -le 604 ]; then
  model=ECAPA_brain 
  train_set=vox1 test_set=vox1 # #jukebox cnceleb

  train_subset=
  subset=test test_input=var test_subset=test
  gpu_id=2
  echo -e "\n\033[1;4;31m Stage${stage}: Test ${model} in ${test_set}_egs with ${loss} with ${input_norm} normalization \033[0m\n"

  sname=dev_orgsnr1
  for epoch in 18 ; do #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
    # vox1 1235 1236
    for model_name in aug51 aug52 aug53 aug54 aug55 aug56; do # aug51 aug52 aug53 aug54 aug55 ecapa_aug53_dp111 ecapa_aug53_attenoise10100 ecapa_aug53_dp111_attenoise10100 ecapa_aug53_radionoise
      for test_subset in test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3; do #test_radio_chn2
      for seed in 1234 1235 1236 ; do
        if [[ $model_name == aug51 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_band05_aug51/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.01.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.08.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.10.yaml
          fi
        elif [[ $model_name == aug52 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_band05_aug52/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.02.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.08.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.10.yaml
          fi
        elif [[ $model_name == aug53 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_band05_aug53/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.03.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.09.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.10.yaml
          fi
        elif [[ $model_name == aug54 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_band05_aug54/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.02.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.09.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.10.yaml
          fi
        elif [[ $model_name == aug55 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_band05_aug55/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.04.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.09.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.11.yaml
          fi
        elif [[ $model_name == aug56 ]];then
          model_dir=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox1/wave_fb80_orgsnr1_band05_aug56/${seed}
          if [[ $seed == 1234 ]];then
            yaml_name=model.2024.02.06.yaml
          elif [[ $seed == 1235 ]];then
            yaml_name=model.2024.02.09.yaml
          elif [[ $seed == 1236 ]];then
            yaml_name=model.2024.02.11.yaml
          fi
        fi
          xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_${test_input}
          for trials in trials_all; do
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --test
          done

          for trials in original ; do # original easy hard
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
              --feat-format wav --nj 4 \
              --check-yaml Data/checkpoint/${model_dir}/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} --score-suffix ${trials} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
              --cos-sim --extract
          done
      done
    done
    done
 done
fi


if [ $stage -le 605 ]; then
  model=ThinResNet resnet_size=18
  train_set=vox1 test_set=vox1 # #jukebox cnceleb
  train_subset=
  subset=test test_input=var test_subset=test
  gpu_id=3
  
  sname=dev_half
  for epoch in avg3 ; do #1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41

    for model_name in baseline channel_dropout ;do 
    #noise1010 attenoise1010 noise0110 noise0210 noise2010 noise10010 noise1001 noise1002 noise1020 noise10100 noise10100 noise1010_magnitude noise1010_time noise1010_frequency; do
    # baseline channel_dropout
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_half_aug53
    echo -e "\n\033[1;4;31m Stage${stage}: Test ${model_name} in ${test_set} \033[0m\n"
      for test_subset in test ; do #test_radio_chn2
      for seed in 1234 1235 1236 ; do
        if [[ $model_name == baseline ]];then
          model_dir=${common_path}/${seed}
          yaml_name=${common_path}/model.yaml
        elif [[ $model_name == channel_dropout ]];then
          model_dir=${common_path}_dp111/${seed}
          yaml_name=${common_path}_dp111/model.yaml
        elif [[ $model_name == noise1010_magnitude ]];then
          model_dir=${common_path}_noise1010_prob10_magnitude/${seed}
          yaml_name=${common_path}_noise1010_prob10_magnitude/model.yaml
        elif [[ $model_name == noise1010_time ]];then
          model_dir=${common_path}_noise1010_prob10_time/${seed}
          yaml_name=${common_path}_noise1010_prob10_time/model.yaml
        elif [[ $model_name == noise1010_frequency ]];then
          model_dir=${common_path}_noise1010_prob10_frequency/${seed}
          yaml_name=${common_path}_noise1010_prob10_frequency/model.yaml
        else
          model_dir=${common_path}_${model_name}_prob10/${seed}
          yaml_name=${common_path}_${model_name}_prob10/model.yaml
        fi

        xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_${test_input}_${epoch}
        for trials in trials_all; do
          python -W ignore TrainAndTest/train_egs/test_egs.py \
            --train-dir ${lstm_dir}/data/${train_set}/${sname} \
            --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
            --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
            --feat-format wav --nj 4 \
            --check-yaml Data/checkpoint/${yaml_name} \
            --xvector-dir ${xvector_dir} \
            --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
            --gpu-id ${gpu_id} \
            --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
            --cos-sim --test
        done

        for trials in original ; do # original easy hard
          python -W ignore TrainAndTest/train_egs/test_egs.py \
            --train-dir ${lstm_dir}/data/${train_set}/${sname} \
            --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
            --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
            --feat-format wav --nj 4 \
            --check-yaml Data/checkpoint/${yaml_name} \
            --xvector-dir ${xvector_dir} \
            --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
            --gpu-id ${gpu_id} --score-suffix ${trials}-${epoch} \
            --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
            --cos-sim --extract
        done
      done
    done
    done
 done
 exit
fi

if [ $stage -le 606 ]; then
  model=ThinResNet resnet_size=18
  train_set=vox2 test_set=vox1 # #jukebox cnceleb
  train_subset=dev
  subset=test test_input=var test_subset=test
  gpu_id=0
  
  sname=dev
  for chn in 384 ; do
    if [[ $chn == 384 ]];then
      chn_str=_chn384
    elif [[ $chn == 256 ]];then
      chn_str=
    fi

  for epoch in avg3 ; do # avg2 1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
    for model_name in baseline ;do 
    # common_path=ECAPA_brain/Mean_batch48_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mix
    # common_path=ECAPA_brain/Mean_batch48_SASP2_em192${chn_str}_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mix
    # common_path=ECAPA_brain/Mean_batch48_inbn_SASP2_em192${chn_str}_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mix
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_aug53
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_radsnr05_aug53
    score_norm=as-norm

    echo -e "\n\033[1;4;31m Stage${stage}: Test ${model_name} in ${test_set} \033[0m\n"
      for test_subset in test ; do #test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3
      # all all_radsnr0 all_radsnr05 all_radsnr1 all_radsnr2 all_radsnr5 
      # test test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3
      for seed in 1234 ; do
        if [[ $model_name == baseline ]];then
          model_dir=${common_path}/${seed}
          yaml_name=${common_path}/model.yaml
        elif [[ $model_name == shuffle ]];then
          model_dir=${common_path}_shuffle/${seed}
          yaml_name=${common_path}_shuffle/model.yaml
        elif [[ $model_name == sep ]];then
          model_dir=${common_path}sep/${seed}
          yaml_name=${common_path}sep/model.yaml
        elif [[ $model_name == wasse1 ]];then
          model_dir=${common_path}wasse1/${seed}
          yaml_name=${common_path}wasse1/model.yaml
        elif [[ $model_name == fix ]];then
          model_dir=${common_path}wasse1fix/${seed}
          yaml_name=${common_path}wasse1fix/model.yaml
        elif [[ $model_name == cosine ]];then
          model_dir=${common_path}cosine1/${seed}
          yaml_name=${common_path}cosine1/model.yaml
        elif [[ $model_name == grl ]];then
          model_dir=${common_path}grl/${seed}
          yaml_name=${common_path}grl/model.yaml
        elif [[ $model_name == warm ]];then
          model_dir=${common_path}grlwarm/${seed}
          yaml_name=${common_path}grlwarm/model.yaml
        elif [[ $model_name == hidden ]];then
          model_dir=${common_path}grlwarmhidden/${seed}
          yaml_name=${common_path}grlwarmhidden/model.yaml
        elif [[ $model_name == inst05 ]];then
          model_dir=${common_path}_inst05/${seed}
          yaml_name=${common_path}_inst05/model.yaml
        elif [[ $model_name == inbnx1 ]];then
          model_dir=${common_path}_inbnx1/${seed}
          yaml_name=${common_path}_inbnx1/model.yaml
        elif [[ $model_name == inbnx2 ]];then
          model_dir=${common_path}_inbnx2/${seed}
          yaml_name=${common_path}_inbnx2/model.yaml
        elif [[ $model_name == inbnx3 ]];then
          model_dir=${common_path}_inbnx3/${seed}
          yaml_name=${common_path}_inbnx3/model.yaml
        elif [[ $model_name == inbn05 ]];then
          model_dir=${common_path}_inbn05/${seed}
          yaml_name=${common_path}_inbn05/model.yaml
        elif [[ $model_name == group4 ]];then
          model_dir=${common_path}_group4/${seed}
          yaml_name=${common_path}_group4/model.yaml
        elif [[ $model_name == group16 ]];then
          model_dir=${common_path}_group16/${seed}
          yaml_name=${common_path}_group16/model.yaml
        elif [[ $model_name == group32 ]];then
          model_dir=${common_path}_group32/${seed}
          yaml_name=${common_path}_group32/model.yaml
        elif [[ $model_name == dp05warm ]];then
          model_dir=${common_path}_dp05warm/${seed}
          yaml_name=${common_path}_dp05warm/model.yaml
        elif [[ $model_name == inbn05dpwarm ]];then
          model_dir=${common_path}_inbn05dpwarm/${seed}
          yaml_name=${common_path}_inbn05dpwarm/model.yaml
        elif [[ $model_name == mfa ]];then
          model_dir=${common_path}crossentropy_mfa_STAP/${seed}
          yaml_name=${common_path}crossentropy_mfa_STAP/model.yaml
        elif [[ $model_name == concat ]];then
          model_dir=${common_path}crossentropy_concat_STAP/${seed}
          yaml_name=${common_path}crossentropy_concat_STAP/model.yaml
        elif [[ $model_name == wassmfafix ]];then
          model_dir=${common_path}wasse0.1_mfa_STAPfix/${seed}
          yaml_name=${common_path}wasse0.1_mfa_STAPfix/model.yaml
        fi

        xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_${test_input}_${epoch}_${score_norm}
        train_xvector_dir=Data/xvector/${model_dir}/${train_set}_${train_subset}_${test_input}_${epoch}_${score_norm}
        for trials in trials_all; do
          python -W ignore TrainAndTest/train_egs/test_egs.py \
            --train-dir ${lstm_dir}/data/${train_set}/${sname} \
            --train-extract-dir ${lstm_dir}/data/${train_set}/${train_subset} \
            --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
            --feat-format wav --nj 4 --batch-size 64 \
            --check-yaml Data/checkpoint/${yaml_name} \
            --xvector-dir ${xvector_dir} \
            --train-xvector-dir ${train_xvector_dir} \
            --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
            --gpu-id ${gpu_id} \
            --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 1 \
            --cos-sim --test --score-norm ${score_norm} --cohort-size 100
        done

        # for trials in original ; do # original easy hard
        #   python -W ignore TrainAndTest/train_egs/test_egs.py \
        #     --train-dir ${lstm_dir}/data/${train_set}/${sname} \
        #     --train-extract-dir ${lstm_dir}/data/${train_set}/dev \
        #     --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
        #     --feat-format wav --nj 4 \
        #     --check-yaml Data/checkpoint/${yaml_name} \
        #     --xvector-dir ${xvector_dir} \
        #     --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
        #     --gpu-id ${gpu_id} --score-suffix ${trials}-${epoch} \
        #     --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
        #     --cos-sim --extract
        # done
      done
    done
    done
    done
  done

  train_set=vox2 test_set=vox1 # #jukebox cnceleb
  train_subset=dev_2radsnr05
  for epoch in avg2 ; do # avg2 1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
  for model_name in baseline ;do 
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_radsnr05_aug53
    score_norm=as-norm

    echo -e "\n\033[1;4;31m Stage${stage}: Test ${model_name} in ${test_set} \033[0m\n"
      for test_subset in test  ; do 
      for seed in 1234 ; do
          if [[ $model_name == baseline ]];then
            model_dir=${common_path}/${seed}
            yaml_name=${common_path}/model.yaml
          fi
          xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_${test_input}_${epoch}_${score_norm}
          train_xvector_dir=Data/xvector/${model_dir}/${train_set}_${train_subset}_${test_input}_${epoch}_${score_norm}
          for trials in trials_all; do
            python -W ignore TrainAndTest/train_egs/test_egs.py \
              --train-dir ${lstm_dir}/data/${train_set}/${sname} \
              --train-extract-dir ${lstm_dir}/data/${train_set}/${train_subset} \
              --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
              --feat-format wav --nj 4 --batch-size 64 \
              --check-yaml Data/checkpoint/${yaml_name} \
              --xvector-dir ${xvector_dir} \
              --train-xvector-dir ${train_xvector_dir} \
              --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
              --gpu-id ${gpu_id} \
              --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 1 \
              --cos-sim --test --score-norm ${score_norm} --cohort-size 100
          done
      done
      done
  done
  done
fi

if [ $stage -le 607 ]; then
  model=ThinResNet resnet_size=18
  train_set=cnceleb test_set=cnceleb # #jukebox cnceleb
  train_subset=dev12_org_radsnr1
  subset=test test_input=fix test_subset=test
  gpu_id=0
  
  sname=dev
  chn_str=
  for chn in 384 ; do
    if [[ $chn == 384 ]];then
      chn_str=_chn384      
    fi

  for epoch in avg2 ; do # avg2 1 2 5 6 9 10 12 13 17 20 21 25 26 27 29 30 33 37 40 41
    for model_name in baseline ;do 
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/cnceleb/wave_fb80_inst2_aug53
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/cnceleb/wave_fb80_inst2_radsnr05_aug53
    score_norm=as-norm

    echo -e "\n\033[1;4;31m Stage${stage}: Test ${model_name} in ${test_set} \033[0m\n"
      for test_subset in test test_radsnr1 ; do #test_radio_chn2 test_radchn2_dist1 test_radchn2_dist3
      for seed in 1234 ; do
        if [[ $model_name == baseline ]];then
          model_dir=${common_path}/${seed}
          yaml_name=${common_path}/model.yaml
        elif [[ $model_name == bp ]];then
          model_dir=${common_path}dp/${seed}
          yaml_name=${common_path}dp/model.yaml
        fi

        xvector_dir=Data/xvector/${model_dir}/${testset}_${test_subset}_var_${epoch}_${score_norm}
        train_xvector_dir=Data/xvector/${model_dir}/${train_set}_${train_subset}_${test_input}_${epoch}_${score_norm}
        for trials in trials_all; do
          python -W ignore TrainAndTest/train_egs/test_egs.py \
            --train-dir ${lstm_dir}/data/${train_set}/${sname} \
            --train-extract-dir ${lstm_dir}/data/${train_set}/${train_subset} \
            --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials ${trials} \
            --feat-format wav --nj 4 --batch-size 64 \
            --check-yaml Data/checkpoint/${yaml_name} \
            --xvector-dir ${xvector_dir} \
            --train-xvector-dir ${train_xvector_dir} --score-norm ${score_norm} --cohort-size 1000 \
            --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
            --gpu-id ${gpu_id} \
            --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 1 \
            --cos-sim --test
        done

        for trials in original ; do # original easy hard --train-xvector-dir ${train_xvector_dir} \
          python -W ignore TrainAndTest/train_egs/test_egs.py \
            --train-dir ${lstm_dir}/data/${train_set}/${sname} \
            --train-extract-dir ${lstm_dir}/data/${train_set}/${train_subset} \
            --test-dir ${lstm_dir}/data/${test_set}/${test_subset} --trials trials_${trials} \
            --feat-format wav --nj 4 \
            --check-yaml Data/checkpoint/${yaml_name} \
            --xvector-dir ${xvector_dir} \
            --train-xvector-dir ${train_xvector_dir} --score-norm ${score_norm} --cohort-size 1000 \
            --resume Data/checkpoint/${model_dir}/checkpoint_${epoch}.pth \
            --gpu-id ${gpu_id} --score-suffix ${trials}-${epoch} \
            --test-input ${test_input} --chunk-size 48000 --frame-shift 32000 --verbose 0 \
            --cos-sim --extract
        done
      done
    done
    done
    done
 done
 exit
fi