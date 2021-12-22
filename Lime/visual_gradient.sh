#!/usr/bin/env bash

stage=203
if [ $stage -le 0 ]; then
  for model in LoResNet10; do
    python Lime/visual_gradient.py \
      --extract-path Data/gradient/LoResNet10/timit/spect_161/soft_var/LoResNet10/soft_dp0.00/epoch_15 \
      --feat-dim 161
  done
fi

#stage=10
if [ $stage -le 1 ]; then
  for model in LoResNet10; do
    #    python Lime/visual_gradient.py \
    #      --extract-path Data/gradient/LoResNet10/timit/spect/soft_fix/epoch_15 \
    #      --feat-dim 161

    python Lime/visual_gradient.py \
      --extract-path Data/gradient/LoResNet10/timit/spect/soft_var/epoch_15 \
      --feat-dim 161
  done
fi

#stage=200
if [ $stage -le 2 ]; then
  for model in LoResNet10; do
    python Lime/visual_gradient.py \
      --extract-path Data/gradient/LoResNet10/timit/spect/soft_fix/LoResNet10/soft_dp0.00/epoch_15 \
      --feat-dim 161
  done
fi

if [ $stage -le 5 ]; then
  #Data/gradient/LoResNet10/libri/spect/soft_128_0.25/epoch_15/
  for model in LoResNet10; do
    #    python Lime/visual_gradient.py \
    #      --extract-path Data/gradient/LoResNet10/libri/spect/soft/epoch_15 \
    #      --feat-dim 161

    python Lime/visual_gradient.py \
      --extract-path Data/gradient/LoResNet10/libri/spect_noc/soft/epoch_15 \
      --feat-dim 161
    #    python Lime/visual_gradient.py \
    #      --extract-path Data/gradient/LoResNet10/center_dp0.00/epoch_36 \
    #      --feat-dim 161
  done
fi
#stage=100
if [ $stage -le 10 ]; then
  python Lime/visual_gradient.py \
    --extract-path Data/gradient/LoResNet10/vox1/spect/soft_wcmvn/epoch_24 \
    --feat-dim 161

#  for loss in soft amsoft center ; do
#    python Lime/visual_gradient.py \
#      --extract-path Data/gradient/LoResNet10/spect/${loss}_wcmvn/epoch_38 \
#      --feat-dim 161
#  done
fi
#stage=100

if [ $stage -le 20 ]; then
  python Lime/visual_gradient.py \
    --extract-path Data/gradient/ResNet20/vox1/spect_256_wcmvn/soft_wcmvn/epoch_24 \
    --feat-dim 257
fi

#stage=100
if [ $stage -le 30 ]; then
  #    python Lime/visual_gradient.py \
  #      --extract-path Data/gradient/ExResNet34/vox1/fb64_wcmvn/soft_var/epoch_30 \
  #      --feat-dim 64 \
  #      --acoustic-feature fbank

  python Lime/visual_gradient.py \
    --extract-path Data/gradient/SiResNet34/vox1/fb64_wcmvn/soft_fix/epoch_40 \
    --feat-dim 64 \
    --acoustic-feature fbank

fi
#stage=100
if [ $stage -le 40 ]; then
  python Lime/visual_gradient.py \
    --extract-path Data/gradient/SiResNet34/vox1/fb64_kaldi/soft_fix/epoch_26 \
    --feat-dim 64 \
    --acoustic-feature fbank

#    python Lime/visual_gradient.py \
#      --extract-path Data/gradient/TDNN/fb40_wcmvn/soft/epoch_18 \
#      --feat-dim 40 \
#      --acoustic-feature fbank

fi
if [ $stage -le 50 ]; then
  python Lime/visual_gradient.py \
    --extract-path Data/gradient/SiResNet34/vox1/fb64_cmvn/soft/epoch_21 \
    --feat-dim 64 \
    --acoustic-feature fbank

#    python Lime/visual_gradient.py \
#      --extract-path Data/gradient/TDNN/fb40_wcmvn/soft/epoch_18 \
#      --feat-dim 40 \
#      --acoustic-feature fbank

fi

if [ $stage -le 60 ]; then
  python Lime/visual_gradient.py \
    --extract-path Data/gradient/LoResNet18/cnceleb/spect/soft_dp25/epoch_24 \
    --feat-dim 161 \
    --acoustic-feature spectrogram

#    python Lime/visual_gradient.py \
#      --extract-path Data/gradient/TDNN/fb40_wcmvn/soft/epoch_18 \
#      --feat-dim 40 \
#      --acoustic-feature fbank

fi

if [ $stage -le 61 ]; then
  #    python Lime/visual_gradient.py \
  #      --extract-path Data/gradient/GradResNet8/timit/spect_egs_v2/soft_dp05/epoch_12 \
  #      --feat-dim 161 \
  #      --acoustic-feature spectrogram

  #    python Lime/visual_gradient.py \
  #      --extract-path Data/gradient/GradResNet8/timit/spect_egs_v2/asoft_dp05/epoch_12 \
  #      --feat-dim 161 \
  #      --acoustic-feature spectrogram

  #    python Lime/visual_gradient.py \
  #      --extract-path Data/gradient/LoResNet8/timit/spect_egs_log/soft_dp05/epoch_12 \
  #      --feat-dim 161 \
  #      --acoustic-feature spectrogram

  python Lime/visual_gradient.py \
    --extract-path Data/gradient/LoResNet8/timit/spect_egs_log/arcsoft_dp05/epoch_12 \
    --feat-dim 161 \
    --acoustic-feature spectrogram

#    python Lime/visual_gradient.py \
#      --extract-path Data/gradient/TDNN/fb40_wcmvn/soft/epoch_18 \
#      --feat-dim 40 \
#      --acoustic-feature fbank

fi

if [ $stage -le 80 ]; then

  #    python Lime/visual_gradient.py \
  #      --extract-path Data/gradient/TDNN/vox1/fb40_STAP/soft/epoch_20 \
  #      --feat-dim 40 \
  #      --acoustic-feature fbank
  python Lime/visual_gradient.py \
    --extract-path Data/gradient/ThinResNet34/vox1/fb64_None/soft/epoch_22 \
    --feat-dim 64 \
    --acoustic-feature fbank

fi

if [ $stage -le 100 ]; then

  python Lime/Plot/visual_gradient.py \
    --extract-path Data/gradient/LoResNet8/vox2/spect_egs/arcsoft/None_cbam_dp05_em256_k57/epoch_40 \
    --feat-dim 161 \
    --acoustic-feature spectrogram

fi

if [ $stage -le 110 ]; then

  python Lime/Plot/visual_gradient.py \
    --extract-path Data/gradient/LoResNet8/vox2/klsp_egs_baseline/arcsoft/Mean_cbam_None_dp01_alpha0_em256_var/epoch_50_var_50/epoch_50 \
    --feat-dim 161 \
    --acoustic-feature spectrogram

fi
if [ $stage -le 111 ]; then
  for s in dev dev_aug_com;do
    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/LoResNet8/vox1/klsp_egs_baseline/arcsoft/None_cbam_em256_alpha0_dp25_wd5e4_${s}_var/epoch_40_var_40/epoch_40 \
      --feat-dim 161 \
      --acoustic-feature spectrogram
  done
fi


if [ $stage -le 112 ]; then
  for s in dev ;do
    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/TDNN_v5/vox2/klfb_egs_baseline/arcsoft_sgd_exp/inputMean_STAP_em512_wde4_var/epoch_50_var_gradient/epoch_50 \
      --feat-dim 40 \
      --acoustic-feature fbank
  done
fi

if [ $stage -le 113 ]; then
  for s in dev ;do
#    python Lime/Plot/visual_gradient.py \
#      --extract-path Data/gradient/TDNN_v5/cnceleb/klfb_egs12_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/epoch_60_var_gradient/epoch_60 \
#      --feat-dim 40 \
#      --acoustic-feature fbank

    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/TDNN_v5/cnceleb/klfb_egs_baseline/arcsoft/Mean_STAP_em512_wd5e4_var/epoch_50_var_gradient/epoch_50 \
      --feat-dim 40 \
      --acoustic-feature fbank
  done
  exit
fi

if [ $stage -le 114 ]; then
  for s in dev ;do
    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/TDNN_v5/vox1/klfb_egs_baseline/arcsoft/featfb40_inputMean_STAP_em512_wd5e4_var/epoch_50_var_gradient/epoch_50 \
      --feat-dim 40 \
      --acoustic-feature fbank
  done
fi

if [ $stage -le 200 ]; then
  for s in dev ;do
    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/ThinResNet34/vox1/klfb_egs_baseline/arcsoft_sgd_rop/Mean_basic_none1_SAP2_dp125_alpha0_em256_wd5e4_var/epoch_50_var_gradient/epoch_50 \
      --feat-dim 40 \
      --acoustic-feature fbank
  done
  exit
fi

if [ $stage -le 201 ]; then
  for s in dev ;do
    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/ThinResNet34/vox2/klfb_egs_baseline/arcsoft_sgd_rop/chn32_Mean_basic_downNone_none1_SAP2_dp01_alpha0_em256_wde4_var/epoch_60_var_gradient/epoch_60 \
      --feat-dim 40 \
      --acoustic-feature fbank
  done
  exit
fi

if [ $stage -le 202 ]; then
  for s in dev ;do
    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/ThinResNet18/cnceleb/klfb_egs_baseline/arcsoft_sgd_rop/Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em256_wd5e4_var/epoch_60_var_gradient/epoch_60 \
      --feat-dim 40 \
      --acoustic-feature fbank
  done
  exit
fi

if [ $stage -le 203 ]; then
  for s in dev ;do
    python Lime/Plot/visual_gradient.py \
      --extract-path Data/gradient/ThinResNet18/cnceleb/klfb_egs12_baseline/arcsoft_sgd_rop/chn32_Mean_batch256_basic_downk3_none1_SAP2_dp01_alpha0_em256_wde4_var/epoch_73_var_gradient/epoch_73 \
      --feat-dim 40 \
      --acoustic-feature fbank
  done
  exit
fi