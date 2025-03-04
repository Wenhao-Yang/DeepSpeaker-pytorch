#!/usr/bin/env bash

<<<<<<< HEAD
stage=20
=======
stage=50
>>>>>>> Server/Server
waited=0
while [ `ps 75486 | wc -l` -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done
#stage=10


if [ $stage -le 0 ]; then
#  for loss in soft asoft ; do
  model=ExResNet
  datasets=vox1
  feat=power_257
  loss=soft
#  for encod in None ; do
#    echo -e "\n\033[1;4;31m Training ${model}_${encod} with ${loss}\033[0m\n"
#    python -W ignore TrainAndTest/Fbank/ResNets/train_exres_kaldi.py \
#      --train-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/vox1/pydb/dev_${feat} \
#      --test-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/vox1/pydb/test_${feat} \
#      --nj 10 \
#      --epochs 30 \
#      --milestones 12,19,25 \
#      --model ${model} \
#      --resnet-size 34 \
#      --stride 2 \
#      --feat-format kaldi \
#      --embedding-size 128 \
#      --batch-size 128 \
#      --accu-steps 1 \
#      --feat-dim 64 \
#      --remove-vad \
#      --time-dim 1 \
#      --avg-size 4 \
#      --kernel-size 5,5 \
#      --test-input-per-file 4 \
#      --lr 0.1 \
#      --encoder-type ${encod} \
#      --check-path Data/checkpoint/${model}34/${datasets}_${encod}/${feat}/${loss} \
#      --resume Data/checkpoint/${model}34/${datasets}_${encod}/${feat}/${loss}/checkpoint_100.pth \
#      --input-per-spks 384 \
#      --veri-pairs 9600 \
#      --gpu-id 0 \
#      --num-valid 2 \
#      --loss-type soft
#  done

  for encod in STAP ; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Fbank/ResNets/train_exres_kaldi.py \
      --train-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/vox1/spect/dev_${feat} \
      --test-dir /home/work2020/yangwenhao/project/lstm_speaker_verification/data/vox1/spect/test_${feat} \
      --nj 12 \
      --epochs 25 \
      --milestones 10,15,20 \
      --model ${model} \
      --resnet-size 34 \
      --stride 2 \
      --inst-norm \
      --filter \
      --feat-format kaldi \
      --embedding-size 128 \
      --batch-size 128 \
      --accu-steps 1 \
      --feat-dim 64 \
      --time-dim 8 \
      --avg-size 1 \
      --kernel-size 5,5 \
      --test-input-per-file 4 \
      --lr 0.1 \
      --loss-ratio 0.1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}34_filter/${datasets}_${encod}/${feat}/${loss}_mean \
      --resume Data/checkpoint/${model}34_filter/${datasets}_${encod}/${feat}/${loss}_mean/checkpoint_100.pth \
      --input-per-spks 384 \
      --veri-pairs 9600 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type soft

  done
fi
#stage=100

if [ $stage -le 1 ]; then
#  for loss in center amsoft ; do/
  for loss in center asoft; do
    echo -e "\n\033[1;4;31m Finetuning ${model} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Fbank/ResNets/train_exres_kaldi.py \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb64/dev_noc \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb64/test_noc \
      --nj 4 \
      --model ExResNet34 \
      --resnet-size 34 \
      --feat-dim 64 \
      --stride 1 \
      --kernel-size 3,3 \
      --batch-size 64 \
      --check-path Data/checkpoint/${model}/spect/${loss} \
      --resume Data/checkpoint/${model}/spect/soft/checkpoint_30.pth \
      --input-per-spks 192 \
      --loss-type ${loss} \
      --lr 0.01 \
      --loss-ratio 0.01 \
      --milestones 5,9 \
      --num-valid 2 \
      --epochs 12
  done

fi

if [ $stage -le 10 ]; then
#  for loss in soft asoft ; do
  model=ExResNet34
  datasets=vox1
  feat=fb64_wcmvn
  for loss in soft ; do
    echo -e "\n\033[1;4;31m Training ${model} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Fbank/ResNets/train_exres_kaldi.py \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/dev_fb64_wcmvn \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/test_fb64_wcmvn \
      --nj 14 \
      --epochs 20 \
      --milestones 8,12,16 \
      --model ${model} \
      --resnet-size 34 \
      --embedding-size 128 \
      --feat-dim 64 \
      --remove-vad \
      --stride 1 \
      --time-dim 1 \
      --avg-size 1 \
      --kernel-size 3,3 \
      --batch-size 64 \
      --test-batch-size 32 \
      --test-input-per-file 2 \
      --lr 0.1 \
      --check-path Data/checkpoint/${model}/${datasets}/${feat}/${loss}_fix \
      --resume Data/checkpoint/${model}/${datasets}/${feat}/${loss}_fix/checkpoint_1.pth \
      --input-per-spks 192 \
      --veri-pairs 9600 \
      --gpu-id 1 \
      --num-valid 2 \
      --loss-type ${loss}
  done
fi

if [ $stage -le 15 ]; then
#  for loss in soft asoft ; do
  model=SiResNet34
  datasets=vox1
  feat=fb64_cmvn
  for loss in soft ; do
    echo -e "\n\033[1;4;31m Training ${model} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Fbank/ResNets/train_exres_kaldi.py \
      --train-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/dev_fb64 \
      --test-dir /home/yangwenhao/local/project/lstm_speaker_verification/data/Vox1_pyfb/test_fb64 \
      --nj 16 \
      --epochs 13 \
      --milestones 1,5,10 \
      --model ${model} \
      --resnet-size 34 \
      --embedding-size 128 \
      --feat-dim 64 \
      --remove-vad \
      --stride 1 \
      --time-dim 1 \
      --avg-size 1 \
      --kernel-size 3,3 \
      --batch-size 64 \
      --test-batch-size 4 \
      --test-input-per-file 4 \
      --lr 0.1 \
      --check-path Data/checkpoint/${model}/${datasets}/${feat}/${loss} \
      --resume Data/checkpoint/${model}/${datasets}/${feat}/${loss}/checkpoint_9.pth \
      --input-per-spks 192 \
      --veri-pairs 9600 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type ${loss}
  done
fi

if [ $stage -le 20 ]; then
  lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification
  model=ExResNet
  datasets=vox1
  feat=power_257
  loss=soft

  for encod in STAP ; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/vox1/egs/spect/dev_${feat} \
      --valid-dir ${lstm_dir}/data/vox1/egs/spect/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/spect/test_${feat} \
      --nj 10 \
      --epochs 22 \
      --milestones 8,13,18 \
      --model ${model} \
      --resnet-size 34 \
      --stride 2 \
      --inst-norm \
      --filter \
      --feat-format kaldi \
      --embedding-size 128 \
      --batch-size 128 \
      --accu-steps 1 \
      --feat-dim 64 \
      --input-dim 257 \
      --time-dim 8 \
      --avg-size 1 \
      --kernel-size 5,5 \
      --test-input-per-file 4 \
      --lr 0.1 \
      --loss-ratio 0.1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}34_filter/${datasets}_${encod}/${feat}/${loss}_mean_0.5_0.05 \
      --resume Data/checkpoint/${model}34_filter/${datasets}_${encod}/${feat}/${loss}_mean_0.5_0.05/checkpoint_100.pth \
      --input-per-spks 384 \
      --cos-sim \
      --veri-pairs 9600 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type soft

  done
<<<<<<< HEAD
=======
fi

if [ $stage -le 40 ]; then
  lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification
  model=ThinResNet
  resnet_size=34
  datasets=vox1
  feat=fb64
#  loss=soft
  encod=STAP

  for loss in soft ; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/vox1/egs/pyfb/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/pyfb/dev_${feat}/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox1/egs/pyfb/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/pyfb/test_${feat} \
      --nj 10 \
      --epochs 22 \
      --milestones 8,13,18 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --stride 1 \
      --feat-format kaldi \
      --embedding-size 128 \
      --batch-size 128 \
      --accu-steps 1 \
      --feat-dim 64 \
      --time-dim 1 \
      --fast \
      --dropout-p 0.25 \
      --avg-size 1 \
      --kernel-size 5,5 \
      --lr 0.1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat}_${encod}/${loss}_dp25_fast \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat}_${encod}/${loss}_dp25_fast/checkpoint_22.pth \
      --input-per-spks 384 \
      --cos-sim \
      --veri-pairs 9600 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type ${loss} \
      --remove-vad

  done
fi

#stage=1000
if [ $stage -le 50 ]; then
  lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification
  model=ThinResNet
  resnet_size=34
  datasets=vox2
  feat=fb40
#  loss=soft
  encod=STAP

  for loss in soft ; do
    echo -e "\n\033[1;4;31m Training ${model}_${encod} with ${loss}\033[0m\n"
    python -W ignore TrainAndTest/Spectrogram/train_egs.py \
      --train-dir ${lstm_dir}/data/vox2/egs/pyfb/dev_${feat} \
      --train-test-dir ${lstm_dir}/data/vox1/pyfb/dev_fb40/trials_dir \
      --train-trials trials_2w \
      --valid-dir ${lstm_dir}/data/vox2/egs/pyfb/valid_${feat} \
      --test-dir ${lstm_dir}/data/vox1/pyfb/test_${feat} \
      --nj 10 \
      --epochs 22 \
      --milestones 8,13,18 \
      --model ${model} \
      --resnet-size ${resnet_size} \
      --stride 1 \
      --fast \
      --feat-format kaldi \
      --embedding-size 128 \
      --batch-size 256 \
      --accu-steps 1 \
      --feat-dim 40 \
      --time-dim 1 \
      --dropout-p 0.25 \
      --avg-size 1 \
      --kernel-size 5,5 \
      --lr 0.1 \
      --encoder-type ${encod} \
      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat}_${encod}/${loss}_dp25_fast \
      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat}_${encod}/${loss}_dp25_fast/checkpoint_22.pth \
      --input-per-spks 384 \
      --cos-sim \
      --veri-pairs 9600 \
      --gpu-id 0 \
      --num-valid 2 \
      --loss-type ${loss} \
      --remove-vad

  done
>>>>>>> Server/Server
fi