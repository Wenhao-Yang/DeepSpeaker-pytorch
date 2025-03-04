#!/usr/bin/env bash

stage=21
waited=0
while [ `ps 99278 | wc -l` -eq 2 ]; do
  sleep 60
  waited=$(expr $waited + 1)
  echo -en "\033[1;4;31m Having waited for ${waited} minutes!\033[0m\r"
done
#stage=10

lstm_dir=/home/yangwenhao/project/lstm_speaker_verification


if [ $stage -le 0 ]; then
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1
    for model_name in ecapa_aug53 ecapa_aug53_dp111 ecapa_aug53_attenoise10100 ecapa_aug53_attenoise10100_prob08 ecapa_aug53_pattenoise10100_prob08 ecapa_aug53_noise10100_prob08 ecapa_aug53_burr10 ecapa_aug53_inspecaug05 ecapa_aug53_dp111_attenoise10100 ecapa_aug53_radionoise1010 ecapa_aug53_radionoise10100; do
    echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
        for seed in 1234 1235 1236 ; do
            if [[ $model_name == ecapa_aug53 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53/${seed}
            elif [[ $model_name == ecapa_aug53_dp111 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_dp111/${seed}
            elif [[ $model_name == ecapa_aug53_burr10 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_burr1210/${seed}
            elif [[ $model_name == ecapa_aug53_magdp111 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_mag111/${seed}
            elif [[ $model_name == ecapa_aug53_dp111_before ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_dp111_before/${seed}
            elif [[ $model_name == ecapa_aug53_multilayer10 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_attenoise_multilayers1/${seed}
            elif [[ $model_name == ecapa_aug53_inspecaug05 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_inspecaug05/${seed}
            elif [[ $model_name == ecapa_aug53_noise10100_prob08 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_noise10100_prob08/${seed}
            elif [[ $model_name == ecapa_aug53_attenoise10100_prob08 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_attenoise10100_prob08/${seed}
            elif [[ $model_name == ecapa_aug53_pattenoise10100_prob08 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_pattenoise10100_prob08/${seed}
            elif [[ $model_name == ecapa_aug53_dp111_attenoise10100 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_dp111_attenoise10100/${seed}
            elif [[ $model_name == ecapa_aug53_attenoise10100 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_attenoise10100/${seed}
            elif [[ $model_name == ecapa_aug53_radionoise1010 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_radionoise/${seed}
            elif [[ $model_name == ecapa_aug53_radionoise10100 ]];then
                model_dir=${common_path}/wave_fb80_dist_aug53_radionoise10100/${seed}
            fi
            
            python -W ignore TrainAndTest/train_egs/average_model.py \
                --check-path Data/checkpoint/${model_dir}
        done
    done
 exit
fi

if [ $stage -le 10 ]; then
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_half_aug53
    for model_name in noise1010 attenoise1010 noise0110 noise0210 noise2010 noise10010 noise1001 noise1002 noise1020 noise10100 noise10100 noise1010 noise1010_magnitude noise1010_time noise1010_frequency; do
    echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
        for seed in 1234 1235 1236 ; do
            if [[ $model_name == baseline ]];then
                model_dir=${common_path}/${seed}
            elif [[ $model_name == channel_dropout ]];then
                model_dir=${common_path}_dp111/${seed}
            elif [[ $model_name == noise1010_magnitude ]];then
                model_dir=${common_path}_noise1010_prob10_magnitude/${seed}
            elif [[ $model_name == noise1010_time ]];then
                model_dir=${common_path}_noise1010_prob10_time/${seed}
            elif [[ $model_name == noise1010_frequency ]];then
                model_dir=${common_path}_noise1010_prob10_frequency/${seed}
            else
                model_dir=${common_path}_${model_name}_prob10/${seed}
            fi
            
            python -W ignore TrainAndTest/train_egs/average_model.py \
                --check-path Data/checkpoint/${model_dir}
        done
    done
 exit
fi

if [ $stage -le 20 ]; then
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53
    # for model_name in baseline ; do
    # echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
    #     for seed in 1234 1235 1236 ; do
    #         if [[ $model_name == baseline ]];then
    #             model_dir=${common_path}/${seed}
    #         elif [[ $model_name == noise1010_frequency ]];then
    #             model_dir=${common_path}_noise1010_prob10_frequency/${seed}
    #         else
    #             model_dir=${common_path}_${model_name}_prob10/${seed}
    #         fi
            
    #         python -W ignore TrainAndTest/train_egs/average_model.py \
    #             --check-path Data/checkpoint/${model_dir}
    #     done
    # done

    # common_path=ECAPA_brain/Mean_batch48_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mix
    # common_path=ECAPA_brain/Mean_batch48_SASP2_em192_chn384_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mix
    # common_path=ECAPA_brain/Mean_batch48_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mixgrl
    # for model_name in baseline ; do
    # echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
    #     for seed in 1234 ; do
    #         if [[ $model_name == baseline ]];then
    #             model_dir=${common_path}/${seed}
    #         elif [[ $model_name == sep ]];then
    #             model_dir=${common_path}sep/${seed}
    #         elif [[ $model_name == wasse ]];then
    #             model_dir=${common_path}wasse1/${seed}
    #         elif [[ $model_name == fix ]];then
    #             model_dir=${common_path}wasse1fix/${seed}
    #         elif [[ $model_name == cosine ]];then
    #             model_dir=${common_path}cosine1/${seed}
    #         fi
            
    #         python -W ignore TrainAndTest/train_egs/average_model.py \
    #             --check-path Data/checkpoint/${model_dir}
    #     done
    # done

    # common_path=ECAPA_brain/Mean_batch48_SASP2_em192_chn384_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mix
    # common_path=ECAPA_brain/Mean_batch48_inbn_SASP2_em192_chn384_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug53_mix
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_aug53
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_radsnr05_aug53
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_radsnr05_aug53
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/cnceleb/wave_fb80_inst2_aug53
    # common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/cnceleb/wave_fb80_inst2_radsnr05_aug53
    for model in baseline band aug_fine aug aug_band aug_band_fine ; do
    if [[ $model == band ]];then
        # band
        common_path=ECAPA_brain/Mean_batch192_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_band05
        assigned_epoch=24,33,30
    elif [[ $model == baseline ]];then
        # aug+fine
        common_path=ECAPA_brain/Mean_batch192_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist
        assigned_epoch=12,11,23
    elif [[ $model == aug_fine ]];then
        # aug+fine
        common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug64fine16
        assigned_epoch=12,13
    elif [[ $model == aug ]];then
        # aug
        common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug64
        assigned_epoch=11,12
    elif [[ $model == aug_band ]];then
        # aug+band
        common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug64band
        assigned_epoch=41,29
    elif [[ $model == aug_band_fine ]];then
        # aug+band+fine
        common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug64band_fine16
        assigned_epoch=50,44
    fi

    for model_name in baseline ; do
    echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
        for seed in 123456 ; do
            if [[ $model_name == baseline ]];then
                model_dir=${common_path}/${seed}
            elif [[ $model_name == shuffle ]];then
                model_dir=${common_path}_shuffle/${seed}
            elif [[ $model_name == warm ]];then
                model_dir=${common_path}warm/${seed}
            elif [[ $model_name == hidden ]];then
                model_dir=${common_path}warmhidden/${seed}
            elif [[ $model_name == fix ]];then
                model_dir=${common_path}wasse1fix/${seed}
            elif [[ $model_name == cosine ]];then
                model_dir=${common_path}cosine1/${seed}
            elif [[ $model_name == inbn05 ]];then
                model_dir=${common_path}_inbn05/${seed}
            elif [[ $model_name == mfa ]];then
                model_dir=${common_path}crossentropy_mfa_STAP/${seed}
            elif [[ $model_name == concat ]];then
                model_dir=${common_path}crossentropy_concat_STAP/${seed}
            elif [[ $model_name == wassmfafix ]];then
                model_dir=${common_path}wasse0.1_mfa_STAPfix/${seed}
            elif [[ $model_name == bp ]];then
                model_dir=${common_path}dp/${seed}
            fi
            
            python -W ignore TrainAndTest/train_egs/average_model.py \
                --check-path Data/checkpoint/${model_dir} \
                --assigned-epoch ${assigned_epoch}
        done
    done
    done
    exit
fi

if [ $stage -le 21 ]; then
    common_path=ECAPA_brain/Mean_batch96_SASP2_em192_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_aug53
    # common_path=ECAPA_brain/Mean_batch64_SASP2_em192_chn1024_official_2s/arcsoft_adam_cyclic/vox2/wave_fb80_inst2_aug53
    for model_name in both band02 ; do
    echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
        for seed in 1234 ; do
            if [[ $model_name == baseline ]];then
                model_dir=${common_path}/${seed}
            elif [[ $model_name == b* ]];then
                model_dir=${common_path}_${model_name}/${seed}
            elif [[ $model_name == noise1010_frequency ]];then
                model_dir=${common_path}_noise1010_prob10_frequency/${seed}
            else
                model_dir=${common_path}_${model_name}_prob10/${seed}
            fi
            
            python -W ignore TrainAndTest/train_egs/average_model.py \
                --check-path Data/checkpoint/${model_dir}
                # --assigned-epoch 11,12
        done
    done
 exit
fi

if [ $stage -le 22 ]; then
    common_path=ECAPA_brain/Mean_batch48_SASP2_em192_official_2sesmix8/arcsoft_adam_cyclic/vox2/wave_fb80_dist_aug64fine #162_ada
    for model_name in 162_adaparallel-1_layer5_scale166464 162_adaparallel-1_layer5_scale16128128 322_adaparallel-1_layer5_scale166464 322_adaparallel-1_layer5_scale16128128 ; do #parallel0.1_layer5_scale163248 parallel0.25_layer5_scale163248 parallel0.1_layer5_scale326448
    assigned_epoch=15,16
    echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
        for seed in 123456 ; do
            model_dir=${common_path}${model_name}/${seed}            
        
            python -W ignore TrainAndTest/train_egs/average_model.py \
                --check-path Data/checkpoint/${model_dir} \
                --assigned-epoch ${assigned_epoch}
        done
    done
 exit
fi


if [ $stage -le 23 ]; then
    embedding_size=256 #192
    common_path=ECAPA_brain/Mean_batch96_SASP2_em${embedding_size}_official_2s/arcsoft_adam_cyclic/vox1/wave_fb80_inst_aug74
    for model_name in style2 ; do #mixup
    echo -e "\n\033[1;4;31m Stage${stage}: Average model: ${model_name} \033[0m\n"
        for seed in 1234 ; do
            if [[ $model_name == baseline ]];then
                model_dir=${common_path}/${seed}
            elif [[ $model_name == mixup ]];then
                model_dir=${common_path}_remix_mixup0_lamda0.2_mixrt1.00/${seed}
            elif [[ $model_name == mixup08 ]];then
                model_dir=${common_path}_remix_mixup08_lamda0.2_mixrt1.00/${seed}
            elif [[ $model_name == margin_mixup08 ]];then
                model_dir=${common_path}_remix_margin_mixup08_lamda0.2_mixrt1.00/${seed}
            elif [[ $model_name == style2 ]];then
                model_dir=${common_path}_remix_style2_lamda0.2_mixrt1.00/${seed}
            else
                model_dir=${common_path}_${model_name}_prob10/${seed}
            fi
            
            python -W ignore TrainAndTest/train_egs/average_model.py \
                --check-path Data/checkpoint/${model_dir}
        done
    done
 exit
fi