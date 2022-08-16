#!/usr/bin/env bash

stage=351
waited=0
lstm_dir=/home/yangwenhao/project/lstm_speaker_verification
while [ $(ps 12700 | wc -l) -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done

if [ $stage -le 0 ]; then
  for model in LoResNet10; do
    python Lime/output_extract.py \
      --model ${model} \
      --epochs 19 \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/dev \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/test \
      --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
      --check-path /home/yangwenhao/local/project/DeepSpeaker-pytorch/Data/checkpoint/LoResNet10/spect/soft \
      --extract-path Lime/${model} \
      --dropout-p 0.5 \
      --sample-utt 500

  done
fi

if [ $stage -le 1 ]; then
  #  for model in LoResNet10 ; do
  #  python Lime/output_extract.py \
  #    --model LoResNet10 \
  #    --start-epochs 36 \
  #    --epochs 36 \
  #    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/dev \
  #    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/test \
  #    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
  #    --loss-type center \
  #    --check-path /home/yangwenhao/local/project/DeepSpeaker-pytorch/Data/checkpoint/LoResNet10/spect_cmvn/center_dp25 \
  #    --extract-path Data/gradient \
  #    --dropout-p 0 \
  #    --gpu-id 0 \
  #    --embedding-size 1024 \
  #    --sample-utt 2000

  python Lime/output_extract.py \
    --model LoResNet10 \
    --start-epochs 24 \
    --epochs 24 \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/dev_wcmvn \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/test_wcmvn \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --loss-type soft \
    --check-path Data/checkpoint/LoResNet10/spect/soft_wcmvn \
    --extract-path Data/gradient/LoResNet10/spect/soft_wcmvn \
    --dropout-p 0.25 \
    --gpu-id 1 \
    --embedding-size 128 \
    --sample-utt 5000

  for loss in amsoft center; do
    python Lime/output_extract.py \
      --model LoResNet10 \
      --start-epochs 38 \
      --epochs 38 \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/dev_wcmvn \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/test_wcmvn \
      --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
      --loss-type ${loss} \
      --check-path Data/checkpoint/LoResNet10/spect/${loss}_wcmvn \
      --extract-path Data/gradient/LoResNet10/spect/${loss}_wcmvn \
      --dropout-p 0.25 \
      --s 15 \
      --margin 0.35 \
      --gpu-id 1 \
      --embedding-size 128 \
      --sample-utt 5000
  done
fi

#stage=2
if [ $stage -le 2 ]; then
  model=ExResNet34
  datasets=vox1
  #  feat=fb64_wcmvn
  #  loss=soft
  #  python Lime/output_extract.py \
  #      --model ${model} \
  #      --start-epochs 30 \
  #      --epochs 30 \
  #      --resnet-size 34 \
  #      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/dev_fb64_wcmvn \
  #      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/test_fb64_wcmvn \
  #      --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
  #      --loss-type ${loss} \
  #      --stride 1 \
  #      --remove-vad \
  #      --kernel-size 3,3 \
  #      --check-path Data/checkpoint/ExResNet34/vox1/fb64_wcmvn/soft_var \
  #      --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss}_var \
  #      --dropout-p 0.0 \
  #      --gpu-id 0 \
  #      --embedding-size 128 \
  #      --sample-utt 10000

  feat=fb64_wcmvn
  loss=soft
  python Lime/output_extract.py \
    --model ExResNet34 \
    --start-epochs 30 \
    --epochs 30 \
    --resnet-size 34 \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb64/dev_noc \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb64/test_noc \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --loss-type ${loss} \
    --stride 1 \
    --remove-vad \
    --kernel-size 3,3 \
    --check-path Data/checkpoint/ExResNet/spect/soft \
    --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss}_kaldi \
    --dropout-p 0.0 \
    --gpu-id 1 \
    --time-dim 1 \
    --avg-size 1 \
    --embedding-size 128 \
    --sample-utt 5000
fi

#stage=100
if [ $stage -le 3 ]; then
  model=ResNet20
  datasets=vox1
  feat=spect_256_wcmvn
  loss=soft
  python Lime/output_extract.py \
    --model ${model} \
    --start-epochs 24 \
    --epochs 24 \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/dev_257_wcmvn \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_spect/test_257_wcmvn \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --loss-type ${loss} \
    --check-path Data/checkpoint/ResNet20/spect_257_wcmvn/soft_dp0.5 \
    --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss}_wcmvn \
    --dropout-p 0.5 \
    --gpu-id 1 \
    --embedding-size 128 \
    --sample-utt 5000
fi

if [ $stage -le 4 ]; then
  model=LoResNet
  train_set=vox2
  test_set=vox1
  feat=log
  loss=arcsoft
  resnet_size=8
  encoder_type=None
  embedding_size=256
  block_type=cbam
  kernel=5,7
  python Lime/output_extract.py \
    --model ${model} \
    --resnet-size ${resnet_size} \
    --start-epochs 40 \
    --epochs 41 \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/vox2/spect/dev_log \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/vox1/spect/test_log \
    --input-norm Mean \
    --kernel-size ${kernel} \
    --stride 2,3 \
    --channels 64,128,256 \
    --encoder-type ${encoder_type} \
    --block-type ${block_type} \
    --time-dim 1 \
    --avg-size 4 \
    --embedding-size ${embedding_size} \
    --alpha 0 \
    --loss-type ${loss} \
    --check-path Data/checkpoint/LoResNet8/vox2/spect_egs/arcsoft/None_cbam_dp05_em256_k57 \
    --extract-path Data/gradient/LoResNet8/vox2/spect_egs/arcsoft/None_cbam_dp05_em256_k57 \
    --dropout-p 0.5 \
    --gpu-id 1 \
    --sample-utt 5000

  exit
fi

if [ $stage -le 12 ]; then
  model=ThinResNet
  datasets=vox1
  feat=fb64
  loss=soft
  python Lime/output_extract.py \
    --model ThinResNet \
    --start-epochs 22 \
    --epochs 23 \
    --resnet-size 34 \
    --train-dir ${lstm_dir}/data/${datasets}/pyfb/dev_${feat} \
    --test-dir ${lstm_dir}/data/${datasets}/pyfb/test_${feat} \
    --loss-type ${loss} \
    --stride 1 \
    --remove-vad \
    --kernel-size 5,5 \
    --encoder-type None \
    --check-path Data/checkpoint/ThinResNet34/vox1/fb64_None/soft \
    --extract-path Data/gradient/ThinResNet34/vox1/fb64_None/soft \
    --dropout-p 0.0 \
    --gpu-id 0 \
    --time-dim 1 \
    --avg-size 1 \
    --embedding-size 128 \
    --sample-utt 5000
fi
#stage=300
#stage=1000

if [ $stage -le 20 ]; then
  model=LoResNet10
  datasets=timit
  feat=spect
  loss=soft

  #  python Lime/output_extract.py \
  #    --model LoResNet10 \
  #    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/timit/spect/train_noc \
  #    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/timit/spect/test_noc \
  #    --start-epochs 15 \
  #    --check-path Data/checkpoint/LoResNet10/timit_spect/soft_fix \
  #    --epochs 15 \
  #    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
  #    --sample-utt 1500 \
  #    --embedding-size 128 \
  #    --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss}_fix \
  #    --model ${model} \
  #    --channels 4,16,64 \
  #    --dropout-p 0.25

  python Lime/output_extract.py \
    --model LoResNet10 \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/timit/spect/train_noc \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/timit/spect/test_noc \
    --start-epochs 15 \
    --check-path Data/checkpoint/LoResNet10/timit_spect/soft_var \
    --epochs 15 \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --sample-utt 10000 \
    --embedding-size 128 \
    --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss}_var \
    --model ${model} \
    --channels 4,16,64 \
    --dropout-p 0.25
fi

if [ $stage -le 21 ]; then
  model=LoResNet
  dataset=timit
  train_set=timit
  test_set=timit
  feat_type=spect
  feat=log
  loss=soft
  resnet_size=8
  encoder_type=None
  embedding_size=128
  block_type=basic
  kernel=5,5
  python Lime/output_extract.py \
    --model ${model} \
    --resnet-size ${resnet_size} \
    --start-epochs 12 \
    --epochs 12 \
    --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/train_${feat} \
    --train-set-name timit \
    --test-set-name timit \
    --test-dir ${lstm_dir}/data/${dataset}/${feat_type}/test_${feat} \
    --input-norm None \
    --kernel-size ${kernel} \
    --stride 2 \
    --channels 4,16,64 \
    --encoder-type ${encoder_type} \
    --block-type ${block_type} \
    --time-dim 1 \
    --avg-size 4 \
    --embedding-size ${embedding_size} \
    --alpha 10.8 \
    --loss-type ${loss} \
    --dropout-p 0.5 \
    --check-path Data/checkpoint/LoResNet8/timit/spect_egs_log/soft_dp05 \
    --extract-path Data/gradient/LoResNet8/timit/spect_egs_log/soft_dp05/epoch_12_var_50 \
    --gpu-id 1 \
    --sample-utt 50
  exit
fi

if [ $stage -le 22 ]; then
  model=LoResNet
  dataset=vox2
  train_set=vox2
  test_set=vox1
  feat_type=klsp
  feat=log
  loss=arcsoft
  resnet_size=8
  encoder_type=None
  embedding_size=256
  block_type=cbam
  kernel=5,5
  echo -e "\n\033[1;4;31m stage${stage} Training ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"

  python Lime/output_extract.py \
    --model ${model} \
    --resnet-size ${resnet_size} \
    --start-epochs 61 \
    --epochs 61 \
    --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
    --train-set-name vox2 \
    --test-set-name vox1 \
    --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test \
    --input-norm Mean \
    --kernel-size ${kernel} \
    --stride 2 \
    --channels 64,128,256 \
    --encoder-type ${encoder_type} \
    --block-type ${block_type} \
    --time-dim 1 \
    --avg-size 4 \
    --embedding-size ${embedding_size} \
    --alpha 0 \
    --loss-type ${loss} \
    --dropout-p 0.1 \
    --check-path Data/checkpoint/LoResNet8/vox2/klsp_egs_baseline/arcsoft/Mean_cbam_None_dp01_alpha0_em256_var \
    --extract-path Data/gradient/LoResNet8/vox2/klsp_egs_baseline/arcsoft/Mean_cbam_None_dp01_alpha0_em256_var/epoch_61_var \
    --gpu-id 1 \
    --margin 0.2 \
    --s 30 \
    --sample-utt 5994
  exit
fi

if [ $stage -le 23 ]; then
  model=LoResNet
  dataset=vox1
  train_set=vox1
  test_set=vox1
  feat_type=klsp
  feat=log
  loss=arcsoft
  resnet_size=8
  encoder_type=None
  embedding_size=256
  block_type=cbam
  kernel=5,5
  echo -e "\n\033[1;4;31m stage${stage} Training ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"

  python Lime/output_extract.py \
    --model ${model} \
    --resnet-size ${resnet_size} \
    --start-epochs 40 \
    --epochs 40 \
    --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
    --train-set-name ${train_set} \
    --test-set-name ${train_set} \
    --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test \
    --input-norm Mean \
    --kernel-size ${kernel} \
    --stride 2 \
    --channels 64,128,256 \
    --encoder-type ${encoder_type} \
    --block-type ${block_type} \
    --time-dim 1 \
    --avg-size 4 \
    --embedding-size ${embedding_size} \
    --alpha 0 \
    --loss-type ${loss} \
    --dropout-p 0.25 \
    --check-path Data/checkpoint/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var \
    --extract-path Data/gradient/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var/epoch_40_var_40 \
    --gpu-id 1 \
    --margin 0.2 \
    --s 30 \
    --sample-utt 1211

  python Lime/output_extract.py \
    --model ${model} \
    --resnet-size ${resnet_size} \
    --start-epochs 40 \
    --epochs 40 \
    --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
    --train-set-name ${train_set} \
    --test-set-name ${train_set} \
    --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test \
    --input-norm Mean \
    --kernel-size ${kernel} \
    --stride 2 \
    --channels 64,128,256 \
    --encoder-type ${encoder_type} \
    --block-type ${block_type} \
    --time-dim 1 \
    --avg-size 4 \
    --embedding-size ${embedding_size} \
    --alpha 0 \
    --loss-type ${loss} \
    --dropout-p 0.25 \
    --check-path Data/checkpoint/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_aug_com_var \
    --extract-path Data/gradient/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_aug_com_var/epoch_40_var_40 \
    --gpu-id 1 \
    --margin 0.2 \
    --s 30 \
    --sample-utt 1211
  exit
fi

#stage=500

if [ $stage -le 30 ]; then
  model=LoResNet10
  datasets=libri
  feat=spect_noc
  loss=soft

  #  python Lime/output_extract.py \
  #    --model LoResNet10 \
  #    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/libri/spect/dev_noc \
  #    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/libri/spect/test_noc \
  #    --start-epochs 15 \
  #    --check-path Data/checkpoint/LoResNet10/${datasets}/${feat}/${loss} \
  #    --epochs 15 \
  #    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
  #    --sample-utt 4000 \
  #    --embedding-size 128 \
  #    --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss} \
  #    --model ${model} \
  #    --channels 4,32,128 \
  #    --dropout-p 0.25

  #  python Lime/output_extract.py \
  #    --model LoResNet10 \
  #    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/libri/spect/dev_noc \
  #    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/libri/spect/test_noc \
  #    --start-epochs 15 \
  #    --check-path Data/checkpoint/LoResNet10/${datasets}/${feat}/${loss}_var \
  #    --epochs 15 \
  #    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
  #    --sample-utt 4000 \
  #    --embedding-size 128 \
  #    --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss}_var \
  #    --model ${model} \
  #    --channels 4,32,128 \
  #    --dropout-p 0.25
  python Lime/output_extract.py \
    --model LoResNet10 \
    --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/libri/spect/dev_noc \
    --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/libri/spect/test_noc \
    --start-epochs 15 \
    --check-path Data/checkpoint/LoResNet10/${datasets}/${feat}/${loss} \
    --epochs 15 \
    --sitw-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/sitw \
    --sample-utt 4000 \
    --alpha 9.8 \
    --embedding-size 128 \
    --extract-path Data/gradient/${model}/${datasets}/${feat}/${loss} \
    --model ${model} \
    --channels 4,16,64 \
    --dropout-p 0.25
fi

if [ $stage -le 40 ]; then
  model=TDNN
  feat=fb40
  datasets=vox1
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
    python Lime/output_extract.py \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/${datasets}/pyfb/dev_${feat} \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/${datasets}/pyfb/test_${feat} \
      --nj 14 \
      --start-epochs 20 \
      --epochs 21 \
      --model ${model} \
      --embedding-size 128 \
      --sample-utt 5000 \
      --feat-dim 40 \
      --remove-vad \
      --check-path Data/checkpoint/${model}/${datasets}/${feat}_STAP/soft \
      --extract-path Data/gradient/${model}/${datasets}/${feat}_STAP/soft \
      --loss-type soft \
      --gpu-id 0
  done
fi

#stage=1000
if [ $stage -le 50 ]; then
  model=SiResNet34
  feat=fb40_wcmvn
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
    python Lime/output_extract.py \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/dev_fb64 \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/test_fb64 \
      --nj 14 \
      --start-epochs 21 \
      --epochs 21 \
      --model ${model} \
      --embedding-size 128 \
      --sample-utt 5000 \
      --feat-dim 64 \
      --kernel-size 3,3 \
      --stride 1 \
      --input-length fix \
      --remove-vad \
      --mvnorm \
      --check-path Data/checkpoint/SiResNet34/vox1/fb64_cmvn/soft \
      --extract-path Data/gradient/SiResNet34/vox1/fb64_cmvn/soft \
      --loss-type soft \
      --gpu-id 1
  done
fi

if [ $stage -le 60 ]; then
  model=LoResNet10
  feat=spect
  dataset=cnceleb
  for loss in soft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
    python Lime/output_extract.py \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/${dataset}/spect/dev \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/${dataset}/spect/eval \
      --nj 14 \
      --start-epochs 24 \
      --epochs 24 \
      --model ${model} \
      --embedding-size 128 \
      --sample-utt 2500 \
      --feat-dim 161 \
      --kernel-size 3,3 \
      --channels 64,128,256,256 \
      --resnet-size 18 \
      --check-path Data/checkpoint/LoResNet18/${dataset}/spect/${loss}_dp25 \
      --extract-path Data/gradient/LoResNet18/${dataset}/spect/${loss}_dp25 \
      --loss-type soft \
      --gpu-id 1
  done
fi

if [ $stage -le 61 ]; then
  model=LoResNet
  feat=spect
  dataset=timit
  lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification
  for loss in arcsoft; do
    echo -e "\033[31m==> Loss type: ${loss} \033[0m"
    python Lime/output_extract.py \
      --train-dir ${lstm_dir}/data/${dataset}/spect/train_log \
      --test-dir ${lstm_dir}/data/${dataset}/spect/test_log \
      --nj 12 \
      --start-epochs 12 \
      --epochs 12 \
      --model ${model} \
      --embedding-size 128 \
      --sample-utt 2500 \
      --feat-dim 161 \
      --kernel-size 5,5 \
      --channels 4,16,64 \
      --resnet-size 8 \
      --check-path Data/checkpoint/${model}8/${dataset}/spect_egs_log/${loss}_dp05 \
      --extract-path Data/gradient/${model}8/${dataset}/spect_egs_log/${loss}_dp05 \
      --loss-type ${loss} \
      --gpu-id 0
  done
fi

#stage=100
if [ $stage -le 62 ]; then
  dataset=timit
  for numframes in 1500; do
    echo -e "\033[31m==> num of frames per speaker : ${numframes} \033[0m"
    python Lime/fratio_extract.py \
      --extract-frames \
      --file-dir ${lstm_dir}/data/${dataset}/spect/train_power \
      --set-name {dataset} \
      --out-dir Data/fratio/${dataset}/dev_power \
      --nj 14 \
      --input-per-spks ${numframes} \
      --extract-frames \
      --feat-dim 161
  done
fi

if [ $stage -le 80 ]; then
  dataset=vox1
  for numframes in 15000; do
    echo -e "\033[31m==> num of frames per speaker : ${numframes} \033[0m"
    python Lime/fratio_extract.py \
      --extract-frames \
      --set-name {dataset} \
      --file-dir ${lstm_dir}/data/${dataset}/spect/dev_power \
      --out-dir Data/fratio/vox1/dev_power \
      --nj 14 \
      --input-per-spks ${numframes} \
      --extract-frames \
      --feat-dim 161
  done
fi


if [ $stage -le 100 ]; then
  model=LoResNet
  dataset=vox2
  train_set=vox2
  test_set=vox1
  feat_type=klsp
  feat=log
  loss=arcsoft
  resnet_size=8
  encoder_type=None
  embedding_size=256
  block_type=cbam
  kernel=5,5
  cam=grad_cam
  echo -e "\n\033[1;4;31m stage${stage} Training ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in gradient ;do
    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --start-epochs 61 \
      --epochs 61 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
      --train-set-name vox2 \
      --test-set-name vox1 \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test \
      --input-norm Mean \
      --kernel-size ${kernel} \
      --stride 2 \
      --channels 64,128,256 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --time-dim 1 \
      --avg-size 4 \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.1 \
      --check-path Data/checkpoint/LoResNet8/vox2/klsp_egs_baseline/arcsoft/Mean_cbam_None_dp01_alpha0_em256_var \
      --extract-path Data/gradient/LoResNet8/vox2/klsp_egs_baseline/arcsoft/Mean_cbam_None_dp01_alpha0_em256_var/epoch_61_var_${cam} \
      --gpu-id 1 \
      --margin 0.2 \
      --s 30 \
      --sample-utt 5994
    done
  exit
fi

if [ $stage -le 101 ]; then
  model=LoResNet
  dataset=cnceleb
  train_set=cnceleb
  test_set=cnceleb
  feat_type=klsp
  feat=log
  loss=arcsoft
  resnet_size=8
  encoder_type=None
  embedding_size=256
  block_type=cbam
  kernel=5,5
  cam=grad_cam
  echo -e "\n\033[1;4;31m stage${stage} Training ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in gradient ;do
    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --start-epochs 50 \
      --epochs 50 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev \
      --train-set-name cnc \
      --test-set-name cnc \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test \
      --input-norm Mean \
      --kernel-size ${kernel} \
      --stride 2 \
      --channels 64,128,256 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --time-dim 1 \
      --avg-size 4 \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.25 \
      --check-path Data/checkpoint/LoResNet8/cnceleb/klsp_egs_baseline/arcsoft_sgd_rop/Mean_cbam_AVG_dp25_alpha0_em256_wd5e4_var \
      --extract-path Data/gradient/LoResNet8/cnceleb/klsp_egs_baseline/arcsoft_sgd_rop/Mean_cbam_AVG_dp25_alpha0_em256_wd5e4_var/epoch_50_var_${cam} \
      --gpu-id 1 \
      --margin 0.2 \
      --s 30 \
      --sample-utt 1600
    done
  exit
fi


if [ $stage -le 200 ]; then
  model=TDNN_v5
  dataset=vox2
  train_set=vox2
  test_set=vox1
  feat_type=klfb
  feat=fb40
  loss=arcsoft
  resnet_size=8
  encoder_type=STAP
  embedding_size=512
  block_type=basic
  kernel=5,5
  cam=grad_cam


  echo -e "\n\033[1;4;31m Stage ${stage} Extracting ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in gradient ;do
    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --start-epochs 50 \
      --epochs 50 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40 \
      --train-set-name vox2 \
      --test-set-name vox1 \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_fb40 \
      --input-norm Mean \
      --input-dim 40 \
      --stride 1 \
      --channels 512,512,512,512,1500 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.0 \
      --check-path Data/checkpoint/TDNN_v5/vox2/klfb_egs_baseline/arcsoft_sgd_exp/inputMean_STAP_em512_wde4_var \
      --extract-path Data/gradient/TDNN_v5/vox2/klfb_egs_baseline/arcsoft_sgd_exp/inputMean_STAP_em512_wde4_var/epoch_50_var_${cam} \
      --gpu-id 1 \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --sample-utt 5994
    done
  exit
fi

if [ $stage -le 201 ]; then
  model=TDNN_v5
  dataset=cnceleb
  train_set=cnceleb
  test_set=cnceleb
  feat_type=klfb
  feat=fb40
  loss=arcsoft
  resnet_size=8
  encoder_type=STAP
  embedding_size=512
  block_type=basic
  kernel=5,5
  cam=grad_cam


  echo -e "\n\033[1;4;31m Stage ${stage} Extracting ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in gradient ;do
     python Lime/cam_extract.py \
       --model ${model} \
       --resnet-size ${resnet_size} \
       --cam ${cam} \
       --start-epochs 60 \
       --epochs 60 \
       --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev12_fb40 \
       --train-set-name cnce \
       --test-set-name cnce \
       --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_fb40 \
       --input-norm Mean \
       --input-dim 40 \
       --stride 1 \
       --channels 512,512,512,512,1500 \
       --encoder-type ${encoder_type} \
       --block-type ${block_type} \
       --embedding-size ${embedding_size} \
       --alpha 0 \
       --loss-type ${loss} \
       --dropout-p 0.0 \
       --check-path Data/checkpoint/TDNN_v5/cnceleb/klfb_egs12_baseline/arcsoft/Mean_STAP_em512_wd5e4_var \
       --extract-path Data/gradient/TDNN_v5/cnceleb/klfb_egs12_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/epoch_60_var_${cam} \
       --gpu-id 1 \
       --margin 0.2 \
       --s 30 \
       --remove-vad \
       --sample-utt 5600
     # done

    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --start-epochs 50 \
      --epochs 50 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40 \
      --train-set-name cnce \
      --test-set-name cnce \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_fb40 \
      --input-norm Mean \
      --input-dim 40 \
      --stride 1 \
      --channels 512,512,512,512,1500 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.0 \
      --check-path Data/checkpoint/TDNN_v5/cnceleb/klfb_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var \
      --extract-path Data/gradient/TDNN_v5/cnceleb/klfb_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/epoch_50_var_${cam} \
      --gpu-id 1 \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --sample-utt 3200
    done


  exit
fi

if [ $stage -le 202 ]; then
  model=TDNN_v5
  dataset=vox1
  train_set=vox1
  test_set=vox1
  feat_type=klfb
  feat=fb40
  loss=arcsoft
  resnet_size=8
  encoder_type=STAP
  embedding_size=512
  block_type=basic
  kernel=5,5
  cam=grad_cam


  echo -e "\n\033[1;4;31m Stage ${stage} Extracting ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in gradient ;do
    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --start-epochs 50 \
      --epochs 50 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40 \
      --train-set-name vox1 \
      --test-set-name vox1 \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_fb40 \
      --input-norm Mean \
      --input-dim 40 \
      --stride 1 \
      --channels 512,512,512,512,1500 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.0 \
      --check-path Data/checkpoint/TDNN_v5/vox1/klfb_egs_baseline/arcsoft/featfb40_inputMean_STAP_em512_wd5e4_var \
      --extract-path Data/gradient/TDNN_v5/vox1/klfb_egs_baseline/arcsoft/featfb40_inputMean_STAP_em512_wd5e4_var/epoch_50_var_${cam} \
      --gpu-id 1 \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --sample-utt 1211
    done
  exit
fi

if [ $stage -le 300 ]; then
  model=ThinResNet
  # dataset=vox1
  dataset=vox2

  train_set=vox2
  test_set=vox1
  feat_type=klfb
  feat=log
  loss=arcsoft
  resnet_size=34
  encoder_type=SAP2
  embedding_size=256
  block_type=basic
  kernel=5,5
  cam=gradient
  echo -e "\n\033[1;4;31m stage${stage} Training ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in gradient ;do
    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --start-epochs 60 \
      --epochs 60 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40 \
      --train-set-name ${train_set} \
      --test-set-name ${test_set} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_fb40 \
      --input-norm Mean \
      --kernel-size ${kernel} \
      --stride 2,1 \
      --channels 32,64,128,256 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --time-dim 1 \
      --avg-size 5 \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.1 \
      --check-path Data/checkpoint/${model}${resnet_size}/${train_set}/klfb_egs_baseline/arcsoft_sgd_rop/chn32_Mean_basic_downNone_none1_SAP2_dp01_alpha0_em256_wde4_var \
      --extract-path Data/gradient/${model}${resnet_size}/${train_set}/klfb_egs_baseline/arcsoft_sgd_rop/chn32_Mean_basic_downNone_none1_SAP2_dp01_alpha0_em256_wde4_var/epoch_60_var_${cam} \
      --gpu-id 1 \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --sample-utt 5994
    done
  exit
fi

if [ $stage -le 350 ]; then
  model=ThinResNet
  # dataset=vox1
#  dataset=cnceleb
  dataset=aishell2

  train_set=aishell2
  test_set=aishell2
  feat_type=klfb
  feat=log
  loss=arcsoft
  resnet_size=18
  encoder_type=SAP2
  embedding_size=256
  block_type=basic
  kernel=5,5
  cam=gradient
  downsample=k3
  echo -e "\n\033[1;4;31m stage${stage} Training ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in gradient ;do
    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --start-epochs 60 \
      --epochs 60 \
      --train-dir ${lstm_dir}/data/${dataset}/${feat_type}/dev_fb40 \
      --train-set-name ${train_set} \
      --test-set-name ${test_set} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test_fb40 \
      --input-norm Mean \
      --kernel-size ${kernel} \
      --stride 2,1 \
      --channels 16,32,64,128 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --downsample ${downsample} \
      --time-dim 1 \
      --avg-size 5 \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.1 \
      --check-path Data/checkpoint/${model}${resnet_size}/${train_set}/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em256_wd5e4_var \
      --extract-path Data/gradient/${model}${resnet_size}/${train_set}/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em256_wd5e4_var/epoch_60_var_${cam} \
      --gpu-id 0 \
      --margin 0.2 \
      --s 30 \
      --remove-vad \
      --sample-utt 4000
    done
  exit
fi

if [ $stage -le 351 ]; then
  model=ThinResNet
  datasets=vox1
#  dataset=cnceleb
#  dataset=aishell2
#  datasets=vox2
  train_set=vox1

  test_set=vox1
  feat_type=klsp
  mask_layer=rvec
  feat=log
  loss=arcsoft
  optimizer=sgd
  scheduler=rop
  resnet_size=34
  input_norm=Mean
  encoder_type=SAP2
  batch_size=256
  embedding_size=256
  block_type=basic
  kernel=5,5
  cam=gradient
  downsample=k1
  avg_str=avg5_
  fast=none1
  chn_str=
  alpha=0

  echo -e "\n\033[1;4;31m stage${stage} Training ${model}_${encoder_type} in ${train_set}_${test_set} with ${loss}\033[0m\n"
  for cam in grad_cam ;do
  for seed in 123456 123457 123458 ;do
    # vox1
    if [ $seed -le 123456 ];then
      epoch=27
    elif [ $seed -le 123457 ]; then
      epoch=31
    else
      epoch=19
    fi

  # vox2
#    if [ $seed -le 123456 ];then
#      epoch=41
#    elif [ $seed -le 123457 ]; then
#      epoch=40
#    else
#      epoch=53
#    fi

    model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${seed}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_down${downsample}_${avg_str}${encoder_type}_em${embedding_size}_dp01_alpha${alpha}_${fast}_${chn_str}wde4_var
    extract_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_down${downsample}_${avg_str}${encoder_type}_em${embedding_size}_dp01_alpha${alpha}_${fast}_${chn_str}wde4_var/${seed}
    python Lime/cam_extract.py \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --cam ${cam} \
      --steps 20 \
      --softmax \
      --start-epochs ${epoch} \
      --epochs ${epoch} \
      --train-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev \
      --train-set-name ${train_set} \
      --test-set-name ${test_set} \
      --test-dir ${lstm_dir}/data/${test_set}/${feat_type}/test \
      --input-norm Mean \
      --kernel-size ${kernel} \
      --fast ${fast} \
      --stride 2,2 \
      --channels 16,32,64,128 \
      --encoder-type ${encoder_type} \
      --block-type ${block_type} \
      --downsample ${downsample} \
      --time-dim 1 \
      --avg-size 5 \
      --embedding-size ${embedding_size} \
      --alpha 0 \
      --loss-type ${loss} \
      --dropout-p 0.1 \
      --check-path Data/checkpoint/${model_dir} \
      --extract-path Data/gradient/${extract_dir}/epoch_best_var_${cam}_softmax \
      --gpu-id 0 \
      --margin 0.2 \
      --s 30 \
      --sample-utt 4000
    done
    done
  exit
fi