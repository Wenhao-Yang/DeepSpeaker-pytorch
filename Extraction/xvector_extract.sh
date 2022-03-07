#!/usr/bin/env bash

stage=100

lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification

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
    --dropout-p 0.0 \
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

if [ $stage -le 2 ]; then
  model=LoResNet10
  dataset=timit
  feat=spect_161
  loss=soft

  python Xvector_Extraction/extract_xvector_kaldi.py \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/timit/train_spect_noc \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/timit/test_spect_noc \
    --resume Data/checkpoint/LoResNet10/timit_spect/soft_fix/checkpoint_15.pth \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --feat-dim 161 \
    --embedding-size 128 \
    --extract-path Data/xvector/${model}/${dataset}/${feat}/${loss} \
    --model ${model} \
    --dropout-p 0.0 \
    --epoch 20 \
    --embedding-size 1024
fi

if [ $stage -le 3 ]; then
  model=LoResNet
  dataset=vox1
  loss=soft
  feat_type=spect
  feat=log
  loss=soft
  encod=None
  test_set=vox1
  resnet_size=8
  block_type=cbam

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore Extraction/extract_xvector_egs.py \
      --model ${model} \
      --train-config-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev_${feat} \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_log \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat} \
      --feat-format kaldi \
      --input-norm Mean \
      --input-dim 40 \
      --nj 12 \
      --resnet-size ${resnet_size} \
      --embedding-size 256 \
      --loss-type ${loss} \
      --encoder-type None \
      --avg-size 4 \
      --time-dim 1 \
      --stride 1 \
      --block-type ${block_type} \
      --channels 64,128,256 \
      --margin 0.25 \
      --s 30 \
      --xvector \
      --frame-shift 300 \
      --xvector-dir Data/xvector/LoResNet8/vox1/spect_egs/soft/None_cbam_dp25_alpha12_em256/${test_set}_${subset}_var \
      --resume Data/checkpoint/LoResNet8/vox1/spect_egs/soft/None_cbam_dp25_alpha12_em256/checkpoint_5.pth \
      --gpu-id 0 \
      --remove-vad \
      --cos-sim
  done
  exit
fi

if [ $stage -le 20 ]; then
  model=LoResNet
  dataset=army
  feat=spect_81
  loss=soft
  resnet_size=10

  python Xvector_Extraction/extract_xvector_kaldi.py \
    --train-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/army/spect/dev_8k \
    --test-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/army/spect/thre_enrolled \
    --resume Data/checkpoint/LoResNet10/army_v1/spect_egs_fast_None/soft_dp01/checkpoint_20.pth \
    --feat-dim 81 \
    --train-spk 3162 \
    --embedding-size 128 \
    --batch-size 1 \
    --fast \
    --time-dim 1 \
    --stride 1 \
    --dropout-p 0.1 \
    --channels 32,64,128,256 \
    --alpha 12.0 \
    --input-norm Mean \
    --encoder-type None \
    --extract-path Data/xvector/${model}${resnet_size}/${dataset}/${feat}/${loss} \
    --model ${model} \
    --resnet-size ${resnet_size} \
    --dropout-p 0.0 \
    --epoch 20
fi

if [ $stage -le 40 ]; then
  model=MultiResNet
  dataset=army
  feat=spect_81
  loss=soft
  resnet_size=10

  python Xvector_Extraction/extract_xvector_multi.py \
    --enroll-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/army/spect/thre_enrolled \
    --test-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/army/spect/thre_notenrolled \
    --resume Data/checkpoint/MultiResNet10/army_x2/spect_egs_None/center_dp25_b192_16_0.01/checkpoint_24.pth \
    --feat-dim 81 \
    --train-spk-a 1951 \
    --train-spk-b 1211 \
    --embedding-size 128 \
    --batch-size 64 \
    --time-dim 1 \
    --avg-size 4 \
    --stride 1 \
    --channels 16,64,128,256 \
    --alpha 12.0 \
    --input-norm Mean \
    --encoder-type None \
    --transform None \
    --extract-path Data/xvector/${model}${resnet_size}/${dataset}/${feat}/${loss}_nan \
    --model ${model} \
    --resnet-size ${resnet_size} \
    --dropout-p 0.25 \
    --epoch 24
fi

if [ $stage -le 60 ]; then
  model=TDNN_v5
  dataset=vox2
  loss=soft
  feat_type=spect
  feat=log
  loss=arcsoft
  model=TDNN_v5
  encod=STAP
  dataset=vox2
  test_set=cnceleb
  #       --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_${feat} \

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore Extraction/extract_xvector_egs.py \
      --model ${model} \
      --train-config-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev_${feat} \
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
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/vox2_v2/spect_egs/arcsoft_0ce/inputMean_STAP_em512_wde4/${test_set}_${subset}_var \
      --resume Data/checkpoint/TDNN_v5/vox2_v2/spect_egs/arcsoft_0ce/inputMean_STAP_em512_wde4/checkpoint_60.pth \
      --gpu-id 0 \
      --cos-sim
  done
  exit
fi

if [ $stage -le 70 ]; then
  model=TDNN_v5
  dataset=vox1
  loss=soft
  feat_type=pyfb
  feat=fb40
  loss=soft
  model=TDNN_v5
  encod=STAP
  test_set=vox1

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore Extraction/extract_xvector_egs.py \
      --model ${model} \
      --train-config-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev_${feat}_ws25 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_${feat}_ws25 \
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
      --xvector \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/vox1/pyfb_egs_baseline/soft/featfb40_ws25_inputMean_STAP_em256_wde3_var/${test_set}_${subset}_var \
      --resume Data/checkpoint/TDNN_v5/vox1/pyfb_egs_baseline/soft/featfb40_ws25_inputMean_STAP_em256_wde3_var/checkpoint_50.pth \
      --gpu-id 0 \
      --remove-vad \
      --cos-sim
  done
  exit
fi

if [ $stage -le 71 ]; then
  model=TDNN_v5
  dataset=vox1
  loss=soft
  feat_type=klfb
  feat=combined
  loss=soft
  model=TDNN_v5
  encod=STAP
  test_set=vox1

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore Extraction/extract_xvector_egs.py \
      --model ${model} \
      --train-config-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev_${feat}_fb40 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_combined \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_fb40 \
      --feat-format kaldi \
      --input-norm Mean \
      --input-dim 40 \
      --nj 12 \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --channels 512,512,512,512,1500 \
      --margin 0.25 \
      --s 30 \
      --xvector \
      --frame-shift 300 \
      --xvector-dir Data/xvector/TDNN_v5/vox1/klfb_egs_baseline/soft/featcombined_inputMean_STAP_em512_wde3_var_v3/${test_set}_${subset}_var \
      --resume Data/checkpoint/TDNN_v5/vox1/klfb_egs_baseline/soft/featcombined_inputMean_STAP_em512_wde3_var_v2/checkpoint_50.pth \
      --gpu-id 0 \
      --remove-vad \
      --cos-sim
  done
  exit
fi

if [ $stage -le 80 ]; then
  model=TDNN_v5
  dataset=vox1
  loss=soft
  feat_type=pyfb
  feat=fb40
  loss=soft
  model=TDNN_v5
  encod=STAP
  dataset=vox2
  test_set=vox1

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore Extraction/extract_xvector_egs.py \
      --model ${model} \
      --train-config-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev_${feat}_ws25 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_${feat} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_${feat}_ws25 \
      --feat-format kaldi \
      --input-norm Mean \
      --input-dim 40 \
      --nj 12 \
      --embedding-size 512 \
      --loss-type ${loss} \
      --encoder-type STAP \
      --channels 512,512,512,512,1500 \
      --margin 0.25 \
      --s 30 \
      --frame-shift 300 \
      --xvector \
      --xvector-dir Data/xvector/TDNN_v5/vox2/pyfb_egs_baseline/soft/featfb40_ws25_inputMean_STAP_em512_wd5e4_var/${test_set}_${subset}_var \
      --resume Data/checkpoint/TDNN_v5/vox2/pyfb_egs_baseline/soft/featfb40_ws25_inputMean_STAP_em512_wd5e4_var/checkpoint_40.pth \
      --gpu-id 0 \
      --remove-vad \
      --cos-sim
  done
  exit
fi


if [ $stage -le 100 ]; then

  datasets=cnceleb
  testset=cnceleb
  feat_type=klfb
  model=ThinResNet
  resnet_size=18
  encoder_type=SAP2
  embedding_size=512
  block_type=basic
  downsample=k3
  kernel=5,5
  loss=arcsoft
  alpha=0
  input_norm=Mean
  mask_layer=baseline
  scheduler=rop
  optimizer=sgd
  input_dim=40
  batch_size=256
  fast=none1
  mask_layer=baseline
  weight=vox2_rcf
  scale=0.2
  subset=

  checkpoint_dir=Data/checkpoint/ThinResNet18/cnceleb/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em256_wd5e4_var
  xvector_dir=Data/xvector/ThinResNet18/cnceleb/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em256_wd5e4_var

  model_yaml= #${checkpoint_dir}/model.2022.01.14.yaml
  resume=${checkpoint_dir}/checkpoint_60.pth

  echo -e "\n\033[1;4;31m Stage ${stage}: Extracting ${model} in ${test_set} with ${loss} \033[0m\n"

  for subset in test; do # 32,128,512; 8,32,128
    echo -e "\n\033[1;4;31m Stage ${stage}: Testing ${model} in ${test_set} with ${loss} \033[0m\n"
    python -W ignore Extraction/extract_xvector_egs.py \
      --model ${model} \
      --train-dir ${lstm_dir}/data/${dataset}/egs/${feat_type}/dev${subset}_fb${input_dim} \
      --train-extract-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev${subset}_fb${input_dim} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/${subset}_fb${input_dim} \
      --feat-format kaldi \
      --input-norm Mean \
      --input-dim ${input_dim} \
      --nj 12 \
      --input-norm ${input_norm} \
      --mask-layer ${mask_layer} \
      --resnet-size ${resnet_size} \
      --kernel-size ${kernel} \
      --downsample ${downsample} \
      --channels 16,32,64,128 \
      --fast ${fast} \
      --stride 2,1 \
      --block-type ${block_type} \
      --embedding-size ${embedding_size} \
      --time-dim 1 \
      --avg-size 5 \
      --encoder-type ${encoder_type} \
      --loss-type ${loss} \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --frame-shift 300 \
      --xvector-dir ${xvector_dir}/${test_set}_${subset}_var \
      --check-yaml ${model_yaml} \
      --resume ${resume} \
      --gpu-id 0 \
      --remove-vad \
      --test-input fix \
      --cos-sim
  done
  exit
fi
