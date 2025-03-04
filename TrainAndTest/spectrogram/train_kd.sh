#!/usr/bin/env bash

stage=20
waited=0
while [ $(ps 27253 | wc -l) -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done
#stage=10
lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification

#if [ $stage -le 0 ]; then
#
#fi

if [ $stage -le 0 ]; then
  datasets=vox1
  feat_type=klsp
  model=LoResNet resnet_size=8
  encoder_type=AVG embedding_size=256
  block_type=cbam
  kernel=5,5
  loss=arcsoft
  alpha=0
  input_norm=Mean
  mask_layer=baseline weight=clean
  scheduler=rop optimizer=sgd
  nj=8
  chn=16

  teacher_dir=Data/checkpoint/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var
  label_dir=Data/label/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var

  kd_type=attention #em_l2 vanilla
  kd_ratio=1000
  kd_loss=
  attention_type=freq norm_type=input_weight
#  _${weight}
  for kd_type in attention ; do
  for norm_type in input_weight ; do
  for chn in 16 ; do
  for seed in 123456 1234567 123458; do

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

    if [[ $kd_type == attention ]];then
        kd_ratio=1000
        if [[ $norm_type == input_weight ]]; then
          kd_ratio=40
        fi
        kd_str=_${kd_type}${kd_ratio}${kd_loss}_${attention_type}_${norm_type}
      else
        kd_ratio=0.4
        kd_str=_${kd_type}${kd_ratio}${kd_loss}
      fi

    model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_kd_${mask_layer}/${seed}/${loss}_${optimizer}_${scheduler}/${input_norm}_${block_type}_${encoder_type}_dp${dp_str}_alpha${alpha}_em${embedding_size}_wd5e4_chn${chn}_var${kd_str}
#           --kd-loss ${kd_loss} \

     echo -e "\n\033[1;4;31m Stage${stage}: Training ${model}${resnet_size} in ${datasets}_egs with ${loss} with ${input_norm} normalization \033[0m\n"
     python TrainAndTest/train_egs_kd.py \
       --model ${model} --resnet-size ${resnet_size} \
       --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
       --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev/trials_dir \
       --train-trials trials_2w \
       --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
       --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test \
       --feat-format kaldi \
       --seed $seed \
       --random-chunk 200 400 \
       --input-norm ${input_norm} \
       --nj ${nj} --shuffle \
       --epochs 50 --batch-size 128 \
       --optimizer ${optimizer} --scheduler ${scheduler} \
       --lr 0.1 --base-lr 0.000006 \
       --mask-layer ${mask_layer} \
       --init-weight ${weight} \
       --milestones 10,20,30,40 \
       --check-path Data/checkpoint/${model_dir} \
       --resume Data/checkpoint/${model_dir}/checkpoint_50.pth \
       --kernel-size ${kernel} \
       --channels ${channels} \
       --stride 2 \
       --block-type ${block_type} \
       --embedding-size ${embedding_size} \
       --time-dim 1 --avg-size 4 \
       --encoder-type ${encoder_type} \
       --num-valid 2 \
       --alpha ${alpha} \
       --margin 0.2 --s 30 \
       --weight-decay 0.0005 \
       --dropout-p ${dp} \
       --gpu-id 0,1 \
       --extract --cos-sim \
       --all-iteraion 0 \
       --loss-type ${loss} \
       --kd-type ${kd_type} --attention-type ${attention_type} --norm-type ${norm_type} \
       --distil-weight 0.5 --kd-ratio ${kd_ratio} \
       --teacher-model-yaml ${teacher_dir}/model.2022.01.05.yaml \
       --teacher-resume ${teacher_dir}/checkpoint_40.pth \
       --temperature 20
   done
   done
   done
   done
  exit
fi

if [ $stage -le 5 ]; then
  datasets=vox1
  feat_type=klsp
  model=LoResNet resnet_size=8
  encoder_type=AVG embedding_size=256
  block_type=cbam
  kernel=5,5
  loss=arcsoft
  alpha=0
  input_norm=Mean
  mask_layer=attention weight=clean
  scheduler=rop optimizer=sgd
  nj=8
  chn=16

  teacher_dir=Data/checkpoint/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var
  label_dir=Data/label/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var

  for seed in 123457 123458 ;do
    for encoder_type in AVG ; do
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

      if [[ $mask_layer == attention* ]];then
        at_str=_${weight}
      else
        at_str=
      fi

      echo -e "\n\033[1;4;31m Stage${stage}: Training ${model}${resnet_size} in ${datasets}_egs with ${loss} with ${input_norm} normalization \033[0m\n"
      model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_kd2_${mask_layer}/${seed}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_down${downsample}_avg${avg_size}_${encoder_type}_em${embedding_size}_dp02_alpha${alpha}${at_str}_${chn_str}wd5e4_var

      python TrainAndTest/train_egs_kd2.py \
       --model ${model} --resnet-size ${resnet_size} \
       --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
       --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev/trials_dir \
       --train-trials trials_2w \
       --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
       --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test \
       --feat-format kaldi \
       --random-chunk 200 400 \
       --input-norm ${input_norm} \
       --nj ${nj} --shuffle \
       --epochs 50 --batch-size 128 \
       --optimizer ${optimizer} --scheduler ${scheduler} \
       --lr 0.1 --base-lr 0.000006 \
       --mask-layer ${mask_layer} --init-weight ${weight} \
       --milestones 10,20,30,40 \
       --check-path Data/checkpoint/${model_dir} \
       --resume Data/checkpoint/${model_dir}/checkpoint_50.pth \
       --kernel-size ${kernel} --stride 2 \
       --channels ${channels} \
       --block-type ${block_type} \
       --time-dim 1 --avg-size 4 \
       --encoder-type ${encoder_type} --embedding-size ${embedding_size} \
       --num-valid 2 \
       --alpha ${alpha} \
       --loss-type ${loss} --margin 0.2 --s 30 \
       --weight-decay 0.0005 \
       --dropout-p ${dp} \
       --gpu-id 0,1 \
       --extract --cos-sim \
       --all-iteraion 0 \
       --distil-weight 0.5 \
       --teacher-model-yaml ${teacher_dir}/model.2022.01.05.yaml \
       --teacher-resume ${teacher_dir}/checkpoint_40.pth \
       --label-dir ${label_dir} \
       --temperature 20
   done

   done

#  weight=vox2
#  scale=0.2
#
#  for mask_layer in drop; do
##    mask_layer=baseline
#    echo -e "\n\033[1;4;31m Stage${stage}: Training ${model}${resnet_size} in ${datasets}_egs_${mask_layer} with ${loss} with ${input_norm} normalization \033[0m\n"
#    python TrainAndTest/train_egs.py \
#      --model ${model} --resnet-size ${resnet_size} \
#      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
#      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
#      --train-trials trials_2w \
#      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
#      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
#      --feat-format kaldi \
#      --random-chunk 200 400 \
#      --input-norm ${input_norm} \
#      --nj ${nj} \
#      --epochs 50 --batch-size 128 \
#      --shuffle \
#      --optimizer ${optimizer} --scheduler ${scheduler} \
#      --lr 0.1 --base-lr 0.000005 \
#      --mask-layer ${mask_layer} --init-weight ${weight} --scale ${scale} \
#      --milestones 10,20,30,40 \
#      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_${block_type}_${encoder_type}_dp01_alpha${alpha}_em${embedding_size}_${weight}_wd5e4_var \
#      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_${block_type}_${encoder_type}_dp01_alpha${alpha}_em${embedding_size}_${weight}_wd5e4_var/checkpoint_50.pth \
#      --kernel-size ${kernel} --stride 2 \
#      --channels 64,128,256 \
#      --block-type ${block_type} \
#      --embedding-size ${embedding_size} \
#      --time-dim 1 --avg-size 4 \
#      --encoder-type ${encoder_type} \
#      --num-valid 2 \
#      --alpha ${alpha} \
#      --margin 0.2 --s 30 \
#      --weight-decay 0.0005 \
#      --dropout-p 0.1 \
#      --gpu-id 0,1 \
#      --extract --cos-sim \
#      --all-iteraion 0 \
#      --loss-type ${loss}
#  done

  exit
fi

if [ $stage -le 10 ]; then
  datasets=vox1
  feat_type=klsp
  model=LoResNet resnet_size=8
  encoder_type=AVG
  embedding_size=256
  block_type=cbam
  kernel=5,5
  loss=arcsoft
  alpha=0
  input_norm=Mean
  mask_layer=attention weight=vox2
  scheduler=rop optimizer=sgd
  nj=8

  teacher_dir=Data/checkpoint/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var

   for encoder_type in AVG ; do
     echo -e "\n\033[1;4;31m Stage${stage}: Extracting labels from ${teacher_dir} in ${datasets}_egs with ${loss} with ${input_norm} normalization \033[0m\n"
     python Extraction/extract_egs_label.py \
       --model ${model} \
       --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
       --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/dev/trials_dir \
       --train-trials trials_2w \
       --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
       --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test \
       --feat-format kaldi \
       --random-chunk 200 400 \
       --input-norm ${input_norm} \
       --nj ${nj} \
       --shuffle \
       --batch-size 128 \
       --check-path ${teacher_dir} \
       --gpu-id 0,1 \
       --extract \
       --teacher-model-yaml ${teacher_dir}/model.2022.01.05.yaml \
       --teacher-resume ${teacher_dir}/checkpoint_40.pth \
       --temperature 20
   done

#  weight=vox2
#  scale=0.2
#
#  for mask_layer in drop; do
##    mask_layer=baseline
#    echo -e "\n\033[1;4;31m Stage${stage}: Training ${model}${resnet_size} in ${datasets}_egs_${mask_layer} with ${loss} with ${input_norm} normalization \033[0m\n"
#    python TrainAndTest/train_egs.py \
#      --model ${model} --resnet-size ${resnet_size} \
#      --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev \
#      --train-test-dir ${lstm_dir}/data/vox1/${feat_type}/dev/trials_dir \
#      --train-trials trials_2w \
#      --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_valid \
#      --test-dir ${lstm_dir}/data/vox1/${feat_type}/test \
#      --feat-format kaldi \
#      --random-chunk 200 400 \
#      --input-norm ${input_norm} \
#      --nj ${nj} \
#      --epochs 50 \
#      --batch-size 128 \
#      --shuffle \
#      --optimizer ${optimizer} --scheduler ${scheduler} \
#      --lr 0.1 \
#      --base-lr 0.000005 \
#      --mask-layer ${mask_layer} \
#      --init-weight ${weight} \
#      --scale ${scale} \
#      --milestones 10,20,30,40 \
#      --check-path Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_${block_type}_${encoder_type}_dp01_alpha${alpha}_em${embedding_size}_${weight}_wd5e4_var \
#      --resume Data/checkpoint/${model}${resnet_size}/${datasets}/${feat_type}_egs_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_${block_type}_${encoder_type}_dp01_alpha${alpha}_em${embedding_size}_${weight}_wd5e4_var/checkpoint_50.pth \
#      --kernel-size ${kernel} \
#      --channels 64,128,256 \
#      --stride 2 \
#      --block-type ${block_type} \
#      --embedding-size ${embedding_size} \
#      --time-dim 1 --avg-size 4 \
#      --encoder-type ${encoder_type} \
#      --num-valid 2 \
#      --alpha ${alpha} \
#      --margin 0.2 \
#      --s 30 \
#      --weight-decay 0.0005 \
#      --dropout-p 0.1 \
#      --gpu-id 0,1 \
#      --extract \
#      --cos-sim \
#      --all-iteraion 0 \
#      --loss-type ${loss}
#  done

  exit
fi

if [ $stage -le 20 ]; then
  datasets=vox1
  feat_type=klfb input_dim=40
  model=ThinResNet resnet_size=10
  encoder_type=ASTP2 embedding_size=256
  block_type=seblock downsample=k3 red_ratio=2

  kernel=5,5
  loss=arcsoft
  alpha=0
  input_norm=Mean
  mask_layer=baseline weight=clean
  scheduler=rop optimizer=sgd
  nj=8
  chn=16
  fast=none1
  avg_size=5 dp_str=01 dp=0.1
  batch_size=256

  teacher_dir=Data/checkpoint/ThinResNet34/vox1/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_seblock_red2_downk3_avg5_ASTP2_em256_dp01_alpha0_none1_wd5e4_vares_bashuf/123457
#  label_dir=Data/label/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_dev_var

  kd_type=attention #em_l2 vanilla
  kd_ratio=1000
  kd_loss=

  attention_type=both
  norm_type=input_mean
#  _${weight}
  for attention_type in freq time ; do
  for norm_type in feat ; do
  for chn in 16 ; do
  for seed in 123456 123457 123458 ; do

    if [ $resnet_size -le 34 ];then
      expansion=1
      exp_str=
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

    if [[ $kd_type == attention ]];then
        kd_ratio=1000
        if [[ $norm_type == input ]]; then
          kd_str=_${kd_type}${kd_ratio}${kd_loss}
        else
#          kd_ratio=40
          kd_str=_${kd_type}${kd_ratio}${kd_loss}_${attention_type}_${norm_type}
        fi
      else
        kd_ratio=0.4
        kd_str=_${kd_type}${kd_ratio}${kd_loss}
      fi

    model_dir=${model}${resnet_size}/${datasets}/${feat_type}_egs_kd_${mask_layer}/${loss}_${optimizer}_${scheduler}/${input_norm}_batch${batch_size}_${block_type}_red${red_ratio}${exp_str}_down${downsample}_avg${avg_size}_${encoder_type}_em${embedding_size}_dp01_alpha${alpha}_${fast}${at_str}_${chn_str}wd5e4_var${kd_str}_bashuf/${seed}
#           --kd-loss ${kd_loss} \

     echo -e "\n\033[1;4;31m Stage${stage}: Training ${model}${resnet_size} in ${datasets}_egs with ${loss} with ${input_norm} normalization \033[0m\n"
     python TrainAndTest/train_egs_kd.py \
       --model ${model} --resnet-size ${resnet_size} \
       --train-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/dev_fb${input_dim} \
       --train-test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_fb${input_dim} \
       --train-trials trials \
       --valid-dir ${lstm_dir}/data/${datasets}/egs/${feat_type}/valid_fb${input_dim} \
       --test-dir ${lstm_dir}/data/${datasets}/${feat_type}/test_fb${input_dim} \
       --feat-format kaldi \
       --seed $seed --nj ${nj} --shuffle --batch-shuffle \
       --random-chunk 200 400 \
       --input-norm ${input_norm} --input-dim ${input_dim} \
       --epochs 50 --batch-size ${batch_size} \
       --early-stopping --early-patience 15 --early-delta 0.0001 --early-meta EER \
       --optimizer ${optimizer} --scheduler ${scheduler} \
       --lr 0.1 --base-lr 0.000001 \
       --mask-layer ${mask_layer} --init-weight ${weight} \
       --milestones 10,20,30,40 \
       --check-path Data/checkpoint/${model_dir} \
       --resume Data/checkpoint/${model_dir}/checkpoint_50.pth \
       --kernel-size ${kernel} --channels ${channels} \
       --stride 2,1 --fast ${fast} \
       --block-type ${block_type} --red-ratio ${red_ratio} --downsample ${downsample} --expansion ${expansion} \
       --embedding-size ${embedding_size} \
       --time-dim 1 --avg-size ${avg_size} --encoder-type ${encoder_type} \
       --num-valid 2 \
       --alpha ${alpha} \
       --loss-type ${loss} --margin 0.2 --s 30 --all-iteraion 0 \
       --weight-decay 0.0005 --dropout-p ${dp} \
       --gpu-id 0,1 \
       --extract --cos-sim \
       --kd-type ${kd_type} --attention-type ${attention_type} --norm-type ${norm_type} \
       --distil-weight 0.5 --kd-ratio ${kd_ratio} --temperature 20 \
       --teacher-model-yaml ${teacher_dir}/model.2022.09.11.yaml \
       --teacher-resume ${teacher_dir}/best.pth \
       --remove-vad
   done
   done
   done
   done
  exit
fi