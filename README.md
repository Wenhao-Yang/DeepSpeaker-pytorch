<h1 align="center">
  <br>
  <br>
  Deep Speaker Recognition - Pytorch Implementation
  <br>
</h1>

<p align="center">
  <a href="">
    <img src="https://img.shields.io/badge/python-3.x-blue"
         alt="Gitter">
  </a>
  <a href="https://github.com/ryanvolz/radioconda"><img src="https://img.shields.io/badge/kaldi-blue"></a>
  <a href="https://github.com/ryanvolz/radioconda"><img src="https://img.shields.io/badge/speechbrain-green"></a>
  <a href="https://github.com/ryanvolz/radioconda"><img src="https://img.shields.io/badge/geomloss-green"></a>
  <a href="https://github.com/ryanvolz/radioconda"><img src="https://img.shields.io/badge/captum-green"></a>
  

  </a>
</p>

<p align="center">
  <a href="#how-to-use">Install</a> •
  <a href="#key-features">Features</a> •
  <a href="#dataset">Dataset</a> •
  <a href="#neural-networks">Neural Networks</a> •
  <!-- <a href="#credits">Credits</a> • -->
  <a href="#related">Related</a> •
  <a href="#license">License</a>
</p>

This is the respository for investigation of deep speaker recognition. The implementation is based on Pytorch with kaldi audio processing. 


## How To Install

```shell
# Clone this respository
git clone https://github.com/Wenhao-Yang/SpeakerVerifiaction-pytorch

# Install dependencies
pip install -r requirements.txt
```

## Key-Features

> - Knowledge Distillation
> - Mixup-based Augmentation
> - Domain Adversarial Learning

## Datasets

Prepare data in [kaldi](https://github.com/kaldi-asr/kaldi) way, make features in Process_Data and store shuffled features with random length in egs. Other stages are processed in this [resposity]().

- Development & Test:

> Voxceleb1、Voxceleb2、Aishell1&2、CN-celeb1&2、aidatatang_200zh、MAGICDATA、TAL_CSASR
> ChiME5、VOiCES、CommonVoice、AMI、SITW、Librispeech、TIMIT

- Augmentation:
  
> MUSAN、RIRS


#### Pre-Processing

> - Resample
> - Butter Bandpass Filtering
> - Augmentation
> - LMS Filtering ( Defected )

#### Accoustic Features

> - MFCC
> - Fbank
> - Spectrogram

# Neural-Networks

#### TDNN-based models

The TDNN_v2 is implemented from 'https://github.com/cvqluu/TDNN/blob/master/tdnn.py'. The TDNN_v4 layer is implemented using nn.Conv2d. The TDNN_v5 layer implemented using nn.Conv1d

> - ETDNN
> - FTDNN
> - DTDNN
> - Aggregated-Residual TDNN
> - ECAPA-TDNN
> - LSTM

#### ResNet-based models

> - ResNet34
> - ResCNN

### Loss Type

#### Discriminative

> - A-Softmax
> - AM-Softmax
> - AAM-Softmax
> - Center Loss
> - Ring Loss

#### End-to-End

> - Generalized End-to-End Loss
> - Triplet Loss
> - Contrastive Loss
> - Prototypical Loss
> - Angular Prototypical Loss

### Pooling Type

> - Self-Attention
> - Statistic Pooling
> - Attention Statistic Pooling
> - GhostVALD Pooling

### Score with Normalization

> - Cosine
> - PLDA
> - DET
> - t-sne

<!-- ### Disrization
- Hierarchical Agglomerative Clustering -->

### Class Activation Mapping Analysis

> - Gradient
> - Grad-CAM
> - Grad-CAM++
> - Full-Grad
> - Integrated Gradients

### To do list

- [ ] Self-supervised Pre-Trained Speech Representation Models

### X. Miscellaneous

#### Mixed precision training test

1.Result:
1.1 torch with one 2080ti ThinResNet for one epoch

```text
Normal torch
> Running 10.9361 minutes for Epoch  1, GPU Memory-3799M: 
> Train Accuracy: 17.641670%, Avg loss: 4.453071.
  Valid Accuracy: 24.607762%, Avg loss: 3.693921.
  Train EER: 14.4528%, Threshold: 0.5362, mindcf-0.01: 0.8898, mindcf-0.001: 0.9166. 
  Test  ERR: 12.7572%, Threshold: 0.5246, mindcf-0.01: 0.8408, mindcf-0.001: 0.9176.

Nvidia Apex
> Running 9.1049 minutes for Epoch  1, GPU Memory-3799M: 
> Train Accuracy: 17.752310%, Avg loss: 4.443472.
  Valid Accuracy: 23.905863%, Avg loss: 3.808081.
  Train EER: 13.8477%, Threshold: 0.5310, mindcf-0.01: 0.8706, mindcf-0.001: 0.9282. 
  Test  ERR: 12.7784%, Threshold: 0.5301, mindcf-0.01: 0.8184, mindcf-0.001: 0.8848. 

Torch amp
> Running 8.9960 minutes for Epoch  1, GPU Memory-3729M: 
> Train Accuracy: 17.992458%, Avg loss: 4.410025.
  Valid Accuracy: 30.470685%, Avg loss: 3.432679.
  Train EER: 14.8058%, Threshold: 0.4383, mindcf-0.01: 0.9010, mindcf-0.001: 0.9551. 
  Test  ERR: 12.8420%, Threshold: 0.4092, mindcf-0.01: 0.7864, mindcf-0.001: 0.8909.
```

Work accomplished so far:

- [x] Models implementation
- [x] Data pipeline implementation - "Voxceleb"
- [x] Project structure cleanup.
- [ ] Trained simple ResNet10 with softmax+triplet loss for pre-training 10 batch and triplet loss for 18 epoch ,
  resulted in accuracy ???
- [x] DET curve

### Timeline

- [x] Extract x-vectors from trained Neural Network in 20190626
- [x] Code cleanup (factory model creation) 20200725
- [x] Modified preprocessing
- [x] Modified model for ResNet34,50,101 in 20190625
- [x] Added cosine distance in Triplet Loss(The previous distance is l2) in 20190703
- [ ] Adding scoring for identification
- [ ] Fork plda method for classification in python from: https://github.com/RaviSoji/plda/blob/master/plda/

### 5. Performance

#### 5.1 Baseline

|   Group  |      Model   |  epoch  |    Loss Type   |       Loss      |    Train/Test   |    Accuracy (%)  |  EER (%) |
|:--------:|:------------:|:-------:|:--------------:|:---------------:|:----------------:|:----------------:|:--------:|
|1         | Resnet-10    |  1:22   |    Triplet     |  6.6420:0.0113  |  0.8553/0.8431  |    ...   |
|          | ResNet-34    |   1:8   |  CrossEntropy  |  8.0285:0.0301  |  0.8360/0.8302  |    ...   |
|2         | TDNN         |    40   |  CrossEntropy  |  3.1716:0.0412  |  vox1 dev/test  | 99.9994/99.5871  | 1.6700/5.4030 |
|2         | TDNN         |    40   |  CrossEntropy  |  3.0382:0.2196  | vox2 dev/vox1 test | 98.5265/98.2733 | 3.0800/3.0859 |
| | ETDNN         |....| Softmax | 8.0285:0.0301 | 0.8360/0.8302  | ... | |
| | FTDNN         |....| Softmax | 8.0285:0.0301 | 0.8360/0.8302  | ... | |
| | DTDNN         |....| Softmax | 8.0285:0.0301 | 0.8360/0.8302  | ... | |
| | ARETDNN         |....| Softmax | 8.0285:0.0301 | 0.8360/0.8302  | ... | |
|3| LSTM         |....|     ...   |        ...        |   ...  | ... | |
| | LSTM         |....| Softmax | 8.0285:0.0301 | 0.8360/0.8302  | ... | |
| | LSTM         |....| Softmax | 8.0285:0.0301 | 0.8360/0.8302  | ... | |
|2| ...          |....|    ...    | ...   |   ...   | ... |
|2| TDNN         |....| Softmax | 8.0285:0.0301 | 0.8360/0.8302  | ... | |

- TDNN_v5, Training set: voxceleb 2 161-dimensional spectrogram, Loss: arcosft, Cosine Similarity

  |   Test Set      |    EER ( % )  |   Threshold   |  MinDCF-0.01   |   MinDCF-0.01  |     Date     |
  |:---------------:|:-------------:|:-------------:|:--------------:|:--------------:|:------------:|
  |   vox1 test     |    2.3542%    |   0.2698025   |    0.2192      |     0.2854     |   20210426   |
  |   sitw dev      |    2.8109%    |   0.2630014   |    0.2466      |     0.4026     |   20210515   |
  |   sitw eval     |    3.2531%    |   0.2642460   |    0.2984      |     0.4581     |   20210515   |
  |  cnceleb test   |   16.8276%    |   0.2165570   |    0.6923      |     0.8009     |   20210515   |
  |  aishell2 test  |   10.8300%    |   0.2786811   |    0.8212      |     0.9527     |   20210515   |
  |   aidata test   |   10.0972%    |   0.2952531   |    0.7859      |     0.9520     |   20210515   |

<!-- #### 5.2 Baseline -->


# Related 

At the beginning, this project was forked and started from
the [qqueing/DeepSpeaker-pytorch](https://github.com/qqueing/DeepSpeaker-pytorch).

## Reference

> [1] D. Snyder, D. Garcia-Romero, G. Sell, D. Povey and S. Khudanpur, "X-Vectors: Robust DNN Embeddings for Speaker Recognition," 2018 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP), Calgary, AB, Canada, 2018, pp. 5329-5333
> [2] Cai, Weicheng, Jinkun Chen, and Ming Li. "Analysis of Length Normalization in End-to-End Speaker Verification System.." conference of the international speech communication association (2018): 3618-3622.
>
> [2] ...













