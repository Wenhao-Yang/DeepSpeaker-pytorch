#!/usr/bin/env bash

stage=90
waited=0
while [ $(ps 103374 | wc -l) -eq 2 ]; do
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
      --resume Data/checkpoint/${model}/fbank80/soft/checkpoint_1.pth
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
  lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification
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
  model=TDNN_v4
  datasets=vox1
  feat=log
  feat_type=spect
  loss=soft
  encod=STAP
  embedding_size=512

  for model in TDNN_v4; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
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

if [ $stage -le 80 ]; then
  model=TDNN_v4
  datasets=vox2
  feat=fb40
  feat_type=pyfb
  loss=soft
  encod=STAP
  embedding_size=512

  for model in ETDNN_v5 FTDNN; do
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

if [ $stage -le 81 ]; then
  model=DTDNN
  datasets=vox2
  feat=log
  feat_type=spect
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_norm=Mean

  for model in TDNN_v5; do
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
      --epochs 3 \
      --patience 2 \
      --milestones 10,20,30 \
      --model ${model} \
      --scheduler rop \
      --weight-decay 0.0001 \
      --lr 0.00001 \
      --alpha 0 \
      --feat-format kaldi \
      --embedding-size ${embedding_size} \
      --batch-size 128 \
      --accu-steps 1 \
      --input-dim 161 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}_v2/${loss}_100ce/emsize${embedding_size}_input${input_norm} \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}_v2/${loss}_100ce/emsize${embedding_size}_input${input_norm}/checkpoint_53.pth \
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

if [ $stage -le 82 ]; then
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

if [ $stage -le 90 ]; then
  model=RET
  datasets=vox2
  feat=log
  feat_type=spect
  loss=arcsoft
  encod=STAP
  embedding_size=512
  input_norm=None
  batch_size=256

  for block_type in Basic Basic_v6 ; do
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
      --epochs 1 \
      --patience 2 \
      --milestones 10,20,30 \
      --model ${model} \
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
      --channels 512,512,512,512,512,1500 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}_v2/${loss}_100ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size} \
      --resume Data/checkpoint/${model}/${datasets}/${feat_type}_${encod}_v2/${loss}_100ce/em${embedding_size}_input${input_norm}_${block_type}_bs${batch_size}/checkpoint_21.pth \
      --cos-sim \
      --dropout-p 0.0 \
      --veri-pairs 9600 \
      --gpu-id 0,1 \
      --num-valid 2 \
      --loss-type ${loss} \
      --margin 0.25 \
      --s 30 \
      --all-iteraion 500 \
      --log-interval 10
  done
fi
