#!/usr/bin/env bash

stage=0
waited=0
while [ `ps 88761 | wc -l` -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done
#stage=10

lstm_dir=/home/work2020/yangwenhao/project/lstm_speaker_verification

if [ $stage -le 0 ]; then
  model=ThinResNet
  datasets=aidata feat_type=klfb
  encod=SAP2 embedding_size=256
  input_dim=40 input_norm=Mean
  loss=arcsoft lr_ratio=0 loss_ratio=10
  subset=
  activation=leakyrelu
  scheduler=cyclic optimizer=adam
  stat_type=margin1 #margin1sum
  m=1.0
  seed=123457
  # _lrr${lr_ratio}_lsr${loss_ratio}
  # CUDA_VISIBLE_DEVICES=0,1 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs_dist.py --train-config=TrainAndTest/Fbank/ResNets/vox1_aug/vox1_clsaug5.yaml --seed=${seed}

  # seed=123456
  for lamda_beta in 0.2 ; do
  for seed in 123457 123458 ; do
   for dim in 80 ; do
   echo -e "\n\033[1;4;31m Stage ${stage}: Training ${model}_${encod} in ${datasets}_${feat} with ${loss}\033[0m\n"
    # CUDA_VISIBLE_DEVICES=0,1 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_egs_dist.py --train-config=TrainAndTest/wav/resnet/aidata_float.yaml --seed=${seed}
    # sleep 5
    # CUDA_VISIBLE_DEVICES=0,1 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_egs_dist.py --train-config=TrainAndTest/wav/resnet/aidata_int.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,1 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/aidata_int_original.yaml --seed=${seed}
    # CUDA_VISIBLE_DEVICES=0,1 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/fbank/ResNets/aidata_cm.yaml --seed=${seed}
    # CUDA_VISIBLE_DEVICES=0,1 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/vox1_int_original.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/ecapa/vox2_int_brain_trans.yaml --seed=${seed}
# 
    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/cnc1_int_sparse.yaml --seed=${seed}
    # sleep 5
    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/cnc1_int_original.yaml --seed=${seed}
    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/vox1_int_baseline.yaml --seed=${seed}

    # sleep 5
    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/vox1_int_frl.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/frl/vox1_int_ftrl${dim}.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/vox2_resnet.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/v2/vox2_resnet_student.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/a2/aishell2_int_baseline.yaml --seed=${seed}
    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/v2/vox2_resnet_frl.yaml --seed=${seed}
    # sleep 5
    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/v2/vox2_resnet_frl2.yaml --seed=${seed}

    CUDA_VISIBLE_DEVICES=0,6 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/frl/vox1_int_student.yaml --seed=${seed}

    sleep 5
    CUDA_VISIBLE_DEVICES=0,6 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/frl/vox1_int_drop3.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/frl/vox1_int_drop3_scale5.yaml --seed=${seed}
    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/v2/vox2_resnet.yaml --seed=${seed}
    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/v2/vox2_resnet_student.yaml --seed=${seed}

    # sleep 5
    # CUDA_VISIBLE_DEVICES=0,4 OMP_NUM_THREADS=12 torchrun --nproc_per_node=2 --master_port=41725 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/a2/aishell2_int_frl.yaml --seed=${seed}

    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/vox1_int_baseline_spect.yaml --seed=${seed}

    # sleep 5
    # CUDA_VISIBLE_DEVICES=0,1 OMP_NUM_THREADS=12 python -m torch.distributed.launch --nproc_per_node=2 TrainAndTest/train_egs/train_dist.py --train-config=TrainAndTest/wav/resnet/vox1_int_frl_spect.yaml --seed=${seed}
    # python Light/main.py --config-yaml=TrainAndTest/wav/resnet/vox1_int_light.yaml --seed=${seed} --gpus=0,1


  done
  done
  done
  exit
fi
