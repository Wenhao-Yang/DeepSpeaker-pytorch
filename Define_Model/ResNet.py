#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: ResNet.py
@Time: 2019/10/10 下午5:09
@Overview: Deep Speaker using Resnet with CNN, which is not ordinary Resnet.
This file define resnet in 'Deep Residual Learning for Image Recognition'

For all model, the pre_forward function is for extract vectors and forward for classification.
"""
import pdb
import random

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
# from torchvision.models.resnet import BasicBlock
# from torchvision.models.resnet import Bottleneck
from torchvision.models.densenet import _DenseBlock
from torchvision.models.shufflenetv2 import InvertedResidual
from Define_Model.FilterLayer import FreqTimeReweightLayer, FrequencyGenderReweightLayer5, FrequencyNormReweightLayer, FrequencyReweightLayer, FrequencyReweightLayer2, TimeMaskLayer, FreqMaskLayer, SqueezeExcitation, GAIN, TimeReweightLayer, fBLayer, fBPLayer, fLLayer, \
    RevGradLayer, DropweightLayer, DropweightLayer_v2, DropweightLayer_v3, GaussianNoiseLayer, MusanNoiseLayer, \
    AttentionweightLayer, TimeFreqMaskLayer, \
    AttentionweightLayer_v2, AttentionweightLayer_v3, ReweightLayer, AttentionweightLayer_v0
from Define_Model.FilterLayer import fDLR, GRL, L2_Norm, Mean_Norm, Inst_Norm, MeanStd_Norm, CBAM
from Define_Model.MixStyle import SinkhornDistance
from Define_Model.Pooling import SelfAttentionPooling, AttentionStatisticPooling, StatisticPooling, AdaptiveStdPool2d, \
    SelfVadPooling, GhostVLAD_v2, AttentionStatisticPooling_v2, SelfAttentionPooling_v2, SelfAttentionPooling_v3

from typing import Type, Any, Callable, Union, List, Optional
from torch import Tensor

from Define_Model.FilterLayer import get_input_norm, get_mask_layer, get_filter_layer


def conv1x1(in_planes, out_planes, stride=1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


def conv3x3(in_planes, out_planes, stride=1, groups: int = 1, dilation: int = 1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, padding=1,
                     stride=stride, groups=groups, bias=False, dilation=dilation)


def conv5x5(in_planes, out_planes, stride=2, groups: int = 1, dilation: int = 1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=5, padding=2,
                     stride=stride, bias=False, groups=groups, dilation=dilation)


class BasicBlock(nn.Module):
    expansion: int = 1

    def __init__(self, inplanes: int, planes: int, stride: int = 1, downsample: Optional[nn.Module] = None,
                 groups: int = 1, base_width: int = 64, dilation: int = 1,
                 norm_layer: Optional[Callable[..., nn.Module]] = None, **kwargs) -> None:
        super(BasicBlock, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError(
                'BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError(
                "Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class Bottleneck(nn.Module):
    # Bottleneck in torchvision places the stride for downsampling at 3x3 convolution(self.conv2)
    # while original implementation places the stride at the first 1x1 convolution(self.conv1)
    # according to "Deep residual learning for image recognition"https://arxiv.org/abs/1512.03385.
    # This variant is also known as ResNet V1.5 and improves accuracy according to
    # https://ngc.nvidia.com/catalog/model-scripts/nvidia:resnet_50_v1_5_for_pytorch.

    expansion: int = 4

    def __init__(self, inplanes: int, planes: int, stride: int = 1, downsample: Optional[nn.Module] = None,
                 groups: int = 1, base_width: int = 64, dilation: int = 1,
                 norm_layer: Optional[Callable[..., nn.Module]] = None, **kwargs) -> None:
        super(Bottleneck, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        width = int(planes * (base_width / 64.)) * groups
        # Both self.conv2 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv1x1(inplanes, width)
        self.bn1 = norm_layer(width)
        self.conv2 = conv3x3(width, width, stride, groups, dilation)
        self.bn2 = norm_layer(width)
        self.conv3 = conv1x1(width, planes * self.expansion)
        self.bn3 = norm_layer(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class SEBasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None, reduction_ratio=4, **kwargs):
        super(SEBasicBlock, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError(
                'BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError(
                "Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride
        self.reduction_ratio = reduction_ratio

        # Squeeze-and-Excitation
        self.se_layer = SqueezeExcitation(
            inplanes=planes, reduction_ratio=reduction_ratio)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out = self.se_layer(out)

        out += identity
        out = self.relu(out)

        return out


class SEBottleneck(nn.Module):
    # Bottleneck in torchvision places the stride for downsampling at 3x3 convolution(self.conv2)
    # while original implementation places the stride at the first 1x1 convolution(self.conv1)
    # according to "Deep residual learning for image recognition"https://arxiv.org/abs/1512.03385.
    # This variant is also known as ResNet V1.5 and improves accuracy according to
    # https://ngc.nvidia.com/catalog/model-scripts/nvidia:resnet_50_v1_5_for_pytorch.

    expansion: int = 4

    def __init__(self, inplanes: int, planes: int, stride: int = 1, downsample: Optional[nn.Module] = None,
                 groups: int = 1, base_width: int = 64, dilation: int = 1,
                 norm_layer: Optional[Callable[..., nn.Module]] = None, reduction_ratio: int = 4, **kwargs) -> None:
        super(SEBottleneck, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        width = int(planes * (base_width / 64.)) * groups
        # Both self.conv2 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv1x1(inplanes, width)
        self.bn1 = norm_layer(width)
        self.conv2 = conv3x3(width, width, stride, groups, dilation)
        self.bn2 = norm_layer(width)
        self.conv3 = conv1x1(width, planes * self.expansion)
        self.bn3 = norm_layer(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride
        self.reduction_ratio = reduction_ratio

        # Squeeze-and-Excitation
        self.se_layer = SqueezeExcitation(
            inplanes=planes * self.expansion, reduction_ratio=reduction_ratio)

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        out = self.se_layer(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out
    

class SEBottleneck_v2(nn.Module):
    # Bottleneck in torchvision places the stride for downsampling at 3x3 convolution(self.conv2)
    # while original implementation places the stride at the first 1x1 convolution(self.conv1)
    # according to "Deep residual learning for image recognition"https://arxiv.org/abs/1512.03385.
    # This variant is also known as ResNet V1.5 and improves accuracy according to
    # https://ngc.nvidia.com/catalog/model-scripts/nvidia:resnet_50_v1_5_for_pytorch.

    expansion: int = 4

    def __init__(self, inplanes: int, planes: int, stride: int = 1, downsample: Optional[nn.Module] = None,
                 groups: int = 1, base_width: int = 64, dilation: int = 1,
                 norm_layer: Optional[Callable[..., nn.Module]] = None, reduction_ratio: int = 4, **kwargs) -> None:
        super(SEBottleneck_v2, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        width = int(planes * (base_width / 64.)) * groups
        # Both self.conv2 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv1x1(inplanes, width)
        self.bn1 = norm_layer(width)

        if stride == 1:
            self.conv2 = conv3x3(width, width, stride, groups, dilation)
        elif stride == 2:
            self.conv2 = conv5x5(width, width, stride, groups, dilation)

        self.bn2 = norm_layer(width)
        self.conv3 = conv1x1(width, planes * self.expansion)
        self.bn3 = norm_layer(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride
        self.reduction_ratio = reduction_ratio

        # Squeeze-and-Excitation
        self.se_layer = SqueezeExcitation(
            inplanes=planes * self.expansion, reduction_ratio=reduction_ratio)

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        out = self.se_layer(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class SEBasicBlock_v2(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None, reduction_ratio=2, **kwargs):
        super(SEBasicBlock_v2, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError(
                'BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError(
                "Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        if stride == 1:
            self.conv1 = conv3x3(inplanes, planes, stride)
        elif stride == 2:
            self.conv1 = conv5x5(inplanes, planes, stride)

        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride
        self.reduction_ratio = reduction_ratio

        # Squeeze-and-Excitation
        self.se_layer = SqueezeExcitation(
            inplanes=planes, reduction_ratio=reduction_ratio)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out = self.se_layer(out)

        out += identity
        out = self.relu(out)

        return out


class CBAMBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None, reduction_ratio=16, **kwargs):
        super(CBAMBlock, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError(
                'BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError(
                "Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride
        self.reduction_ratio = reduction_ratio

        # Squeeze-and-Excitation
        self.CBAM_layer = CBAM(planes, planes)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out = self.CBAM_layer(out)

        out += identity
        out = self.relu(out)

        return out


class CBAMBlock_v2(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None, reduction_ratio=2, **kwargs):
        super(CBAMBlock_v2, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError(
                'BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError(
                "Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        if stride == 1:
            self.conv1 = conv3x3(inplanes, planes, stride)
        elif stride == 2:
            self.conv1 = conv5x5(inplanes, planes, stride)

        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride
        self.reduction_ratio = reduction_ratio

        # Squeeze-and-Excitation
        self.CBAM_layer = CBAM(planes, planes)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out = self.CBAM_layer(out)

        out += identity
        out = self.relu(out)

        return out


class Conv1dReLUBn(nn.Module):
    def __init__(self, kernel_size=3, input_channels=80, output_channels=64, stride=1,
                dilation=1):
        super(Conv1dReLUBn, self).__init__()
        padding = kernel_size//2 * dilation
        self.conv1 = nn.Conv1d(in_channels=input_channels, out_channels=output_channels, 
                               kernel_size=kernel_size, dilation=dilation,
                               stride=stride, padding=padding)
        self.relu = nn.ReLU()
        self.bn = nn.BatchNorm1d(output_channels)
        
    def forward(self, x):
        if x.shape[1] == 1:
            x = x.squeeze(1)

        x = x.transpose(1,2)
        
        x = self.conv1(x)
        x = self.relu(x)
        x = self.bn(x)
        
        return x.transpose(1,2)
    
class ResidualConv1dReLUBn(nn.Module):
    def __init__(self, kernel_size=3, output_channels=64, stride=1,
                dilation=1):
        super(ResidualConv1dReLUBn, self).__init__()
        padding = kernel_size//2 * dilation
        self.conv1 = nn.Conv1d(in_channels=output_channels, out_channels=output_channels, 
                               kernel_size=kernel_size, dilation=dilation,
                               stride=stride, padding=padding)
        self.relu = nn.ReLU()
        self.bn = nn.BatchNorm1d(output_channels)
        
    def forward(self, x):    
        x0 = x.transpose(1,2)
        
        x = self.conv1(x0)
        x = self.relu(x)
        x = self.bn(x) + x0
        
        return x.transpose(1,2)
    
class Res2Conv2dReluBn(nn.Module):
    '''
    in_channels == out_channels == channels
    '''

    def __init__(self, channels, kernel_size=1, padding=0, dilation=1, stride=1, bias=False, scale=4):
        super().__init__()
        assert channels % scale == 0, "{} % {} != 0".format(channels, scale)
        self.scale = scale
        self.width = channels // scale
        self.nums = scale if scale == 1 else scale - 1

        self.convs = []
        self.bns = []
        for i in range(self.nums):
            self.convs.append(nn.Conv2d(self.width, self.width,
                              kernel_size, stride, padding, dilation, bias=bias))
            self.bns.append(nn.BatchNorm2d(self.width))
        self.convs = nn.ModuleList(self.convs)
        self.bns = nn.ModuleList(self.bns)

    def forward(self, x):
        out = []
        spx = torch.split(x, self.width, 1)
        for i in range(self.nums):
            if i == 0:
                sp = spx[i]
            else:
                sp = sp + spx[i]
            # Order: conv -> relu -> bn
            sp = self.convs[i](sp)
            sp = self.bns[i](F.relu(sp))
            out.append(sp)
        if self.scale != 1:
            out.append(spx[self.nums])
        out = torch.cat(out, dim=1)
        return out


class Res2Conv2dBnRelu(nn.Module):
    '''
    in_channels == out_channels == channels
    '''

    def __init__(self, channels, kernel_size=1, padding=0, dilation=1, stride=1, bias=False, scale=4):
        super().__init__()
        assert channels % scale == 0, "{} % {} != 0".format(channels, scale)
        self.scale = scale
        self.width = channels // scale
        self.nums = scale if scale == 1 else scale - 1

        self.convs = []
        self.bns = []
        for i in range(self.nums):
            self.convs.append(nn.Conv2d(self.width, self.width,
                              kernel_size, stride, padding, dilation, bias=bias))
            self.bns.append(nn.BatchNorm2d(self.width))
        self.convs = nn.ModuleList(self.convs)
        self.bns = nn.ModuleList(self.bns)

    def forward(self, x):
        out = []
        spx = torch.split(x, self.width, 1)
        for i in range(self.nums):
            if i == 0:
                sp = spx[i]
            else:
                sp = sp + spx[i]
            # Order: conv -> relu -> bn
            sp = self.convs[i](sp)
            sp = F.relu(self.bns[i](sp))

            out.append(sp)
        if self.scale != 1:
            out.append(spx[self.nums])
        out = torch.cat(out, dim=1)
        return out
    
class Res2Conv2dBn(nn.Module):
    '''
    in_channels == out_channels == channels
    '''

    def __init__(self, channels, kernel_size=1, padding=0, dilation=1, stride=1, bias=False, scale=4):
        super().__init__()
        assert channels % scale == 0, "{} % {} != 0".format(channels, scale)
        self.scale = scale
        self.width = channels // scale
        self.nums = scale if scale == 1 else scale - 1

        self.convs = []
        self.bns = []
        for i in range(self.nums):
            self.convs.append(nn.Conv2d(self.width, self.width,
                              kernel_size, stride, padding, dilation, bias=bias))
            self.bns.append(nn.BatchNorm2d(self.width))
        self.convs = nn.ModuleList(self.convs)
        self.bns = nn.ModuleList(self.bns)

    def forward(self, x):
        out = []
        spx = torch.split(x, self.width, 1)
        for i in range(self.nums):
            if i == 0:
                sp = spx[i]
            else:
                sp = sp + spx[i]
            # Order: conv -> relu -> bn
            sp = self.convs[i](sp)
            sp = self.bns[i](sp)
            out.append(sp)
        if self.scale != 1:
            out.append(spx[self.nums])
        out = torch.cat(out, dim=1)
        return out


class Conv2dReluBn(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=1, stride=1, padding=0, dilation=1, bias=False):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels,
                              kernel_size, stride, padding, dilation, bias=bias)
        self.bn = nn.BatchNorm2d(out_channels)

    def forward(self, x):
        return self.bn(F.relu(self.conv(x)))


''' SE-Res2Block.
    Note: residual connection is implemented in the ECAPA_TDNN model, not here.
'''


class SE_Res2Bottleneck(nn.Module):

    def __init__(self, inplanes, planes, kernel_size=3, padding=1, stride=1, dilation=1,
                 scale=8, reduction_ratio=2, downsample=None, **kwargs):
        super(SE_Res2Bottleneck, self).__init__()
        self.scale = scale
        self.stride = stride

        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.downsample = downsample
        self.conv1 = Conv2dReluBn(
            inplanes, planes, kernel_size=1, stride=stride, padding=0)
        self.conv2 = Res2Conv2dReluBn(
            planes, kernel_size, padding, dilation, stride=1, scale=scale)
        self.conv3 = Conv2dReluBn(
            planes, planes, kernel_size=1, stride=1, padding=0)

        # Squeeze-and-Excitation
        self.se_layer = SqueezeExcitation(
            inplanes=planes, reduction_ratio=reduction_ratio)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.conv2(out)
        out = self.conv3(out)

        out = self.se_layer(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = F.relu(out)

        return out

class SE_Res2Block(nn.Module):
    expansion: int = 1

    def __init__(self, inplanes, planes, kernel_size=3, padding=1, stride=1, dilation=1,
                 scale=8, reduction_ratio=2, downsample=None, **kwargs):
        super(SE_Res2Block, self).__init__()
        self.scale = scale
        self.stride = stride

        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.downsample = downsample
        # self.conv1 = Res2Conv2dBnRelu(
        #     inplanes, kernel_size, padding, dilation, stride=stride, scale=scale)
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)

        self.conv2 = Res2Conv2dBn(
            channels=planes, kernel_size=kernel_size, padding=1, dilation=1, stride=1, scale=scale)

        # Squeeze-and-Excitation
        self.se_layer = SqueezeExcitation(
            inplanes=planes, reduction_ratio=reduction_ratio)

    def forward(self, x):
        identity = x

        # out = self.conv1(x)
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)

        if self.downsample is not None:
            identity = self.downsample(x)
        out = self.se_layer(out)

        out += identity
        out = F.relu(out)

        return out

class Res2Block(nn.Module):

    def __init__(self, inplanes, planes, kernel_size=3, padding=1, stride=1, dilation=1,
                 scale=4, reduction_ratio=2, downsample=None, **kwargs):
        super(Res2Block, self).__init__()
        self.scale = scale
        self.stride = stride

        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.downsample = downsample
        self.conv1 = Res2Conv2dBnRelu(
            inplanes, kernel_size, padding, dilation, stride=stride, scale=scale)
        self.conv2 = Res2Conv2dBn(
            planes=planes, kernel_size=3, padding=1, dilation=1, stride=1, scale=scale)

        # Squeeze-and-Excitation
        # self.se_layer = SqueezeExcitation(inplanes=planes, reduction_ratio=reduction_ratio)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.conv2(out)

        # out = self.se_layer(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = F.relu(out)

        return out
    
class Res2Bottleneck(nn.Module):

    def __init__(self, inplanes, planes, kernel_size=3, padding=1, stride=1, dilation=1,
                 scale=8, reduction_ratio=2, downsample=None, **kwargs):
        super(Res2Bottleneck, self).__init__()
        self.scale = scale
        self.stride = stride

        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.downsample = downsample
        self.conv1 = Conv2dReluBn(
            inplanes, planes, kernel_size=1, stride=stride, padding=0)
        self.conv2 = Res2Conv2dReluBn(
            planes, kernel_size, padding, dilation, stride=1, scale=scale)
        self.conv3 = Conv2dReluBn(
            planes, planes, kernel_size=1, stride=1, padding=0)

        # Squeeze-and-Excitation
        # self.se_layer = SqueezeExcitation(inplanes=planes, reduction_ratio=reduction_ratio)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.conv2(out)
        out = self.conv3(out)

        # out = self.se_layer(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = F.relu(out)

        return out


class Block3x3(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, **kwargs):
        super(Block3x3, self).__init__()
        self.conv1 = conv3x3(inplanes, planes)
        self.bn1 = nn.BatchNorm2d(planes)

        self.conv2 = conv3x3(planes, planes, stride)
        self.bn2 = nn.BatchNorm2d(planes)

        self.conv3 = conv3x3(planes, planes)
        self.bn3 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)

        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class InstBlock3x3(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(InstBlock3x3, self).__init__()
        self.conv1 = conv3x3(inplanes, planes)
        self.bn1 = nn.InstanceNorm2d(planes)

        self.conv2 = conv3x3(planes, planes, stride)
        self.bn2 = nn.InstanceNorm2d(planes)

        self.conv3 = conv3x3(planes, planes)
        self.bn3 = nn.InstanceNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)

        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class VarSizeConv(nn.Module):

    def __init__(self, inplanes, planes, stride=1, kernel_size=[3, 5, 9]):
        super(VarSizeConv, self).__init__()
        self.stide = stride

        self.conv1 = nn.Conv2d(
            inplanes, planes, kernel_size=kernel_size[0], stride=stride, padding=1)
        self.bn1 = nn.InstanceNorm2d(planes)

        self.conv2 = nn.Conv2d(
            inplanes, planes, kernel_size=kernel_size[1], stride=stride, padding=2)
        self.bn2 = nn.InstanceNorm2d(planes)

        self.conv3 = nn.Conv2d(
            inplanes, planes, kernel_size=kernel_size[2], stride=stride, padding=4)
        self.bn3 = nn.InstanceNorm2d(planes)

        self.avg = nn.AvgPool2d(kernel_size=int(
            stride * 2 + 1), stride=stride, padding=stride)

    def forward(self, x):
        x1 = self.conv1(x)
        x1 = self.bn1(x1)

        x2 = self.conv2(x)
        x2 = self.bn2(x2)

        x3 = self.conv3(x)
        x3 = self.bn3(x3)

        if self.stide != 1:
            x = self.avg(x)

        return torch.cat([x, x1, x2, x3], dim=1)
        # return torch.cat([x, x1, x2, x3], dim=1)


class SimpleResNet(nn.Module):

    def __init__(self, block=BasicBlock,
                 num_classes=1000,
                 embedding_size=128,
                 zero_init_residual=False,
                 groups=1,
                 width_per_group=64,
                 replace_stride_with_dilation=None,
                 norm_layer=None, **kwargs):
        super(SimpleResNet, self).__init__()
        layers = [3, 4, 6, 3]
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        self._norm_layer = norm_layer
        self.embedding_size = embedding_size
        self.inplanes = 16
        self.dilation = 1
        num_filter = [16, 32, 64, 128]

        if replace_stride_with_dilation is None:
            # each element in the tuple indicates if we should replace
            # the 2x2 stride with a dilated convolution instead
            replace_stride_with_dilation = [False, False, False]
        if len(replace_stride_with_dilation) != 3:
            raise ValueError("replace_stride_with_dilation should be None "
                             "or a 3-element tuple, got {}".format(replace_stride_with_dilation))
        self.groups = groups
        self.base_width = width_per_group
        self.conv1 = nn.Conv2d(
            1, num_filter[0], kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = norm_layer(num_filter[0])
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=1, padding=1)

        # num_filter = [16, 32, 64, 128]

        self.layer1 = self._make_layer(block, num_filter[0], layers[0])
        self.layer2 = self._make_layer(
            block, num_filter[1], layers[1], stride=2)
        self.layer3 = self._make_layer(
            block, num_filter[2], layers[2], stride=2)
        self.layer4 = self._make_layer(
            block, num_filter[3], layers[3], stride=2)

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc1 = nn.Linear(128 * block.expansion, embedding_size)
        # self.norm = self.l2_norm(num_filter[3])
        self.alpha = 12

        self.fc2 = nn.Linear(embedding_size, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                # nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                nn.init.normal(m.weight, mean=0., std=1.)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant(m.weight, 1)
                nn.init.constant(m.bias, 0)

        # Zero-initialize the last BN in each residual branch,
        # so that the residual branch starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, Bottleneck):
                    nn.init.constant(m.bn3.weight, 0)
                elif isinstance(m, BasicBlock):
                    nn.init.constant(m.bn2.weight, 0)

    def l2_norm(self, input):
        input_size = input.size()
        buffer = torch.pow(input, 2)

        normp = torch.sum(buffer, 1).add_(1e-10)
        norm = torch.sqrt(normp)

        _output = torch.div(input, norm.view(-1, 1).expand_as(input))
        output = _output.view(input_size)

        return output

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def _forward(self, x):
        # pdb.set_trace()
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        # print(x.shape)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        # pdb.set_trace()
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc1(x)

        x = self.l2_norm(x)
        embeddings = x * self.alpha

        x = self.fc2(embeddings)

        return x, embeddings

    # Allow for accessing forward method in a inherited class
    forward = _forward


# Analysis of Length Normalization in End-to-End Speaker Verification System
# https://arxiv.org/abs/1806.03209

class BasicBlock_v2(nn.Module):
    expansion: int = 1

    def __init__(
            self,
            inplanes: int,
            planes: int,
            stride: int = 1,
            downsample: Optional[nn.Module] = None,
            groups: int = 1,
            base_width: int = 64,
            dilation: int = 1,
            norm_layer: Optional[Callable[..., nn.Module]] = None
    ) -> None:
        super(BasicBlock_v2, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError(
                'BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError(
                "Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        if stride == 1:
            self.conv1 = conv3x3(inplanes, planes, stride)
        elif stride == 2:
            self.conv1 = conv5x5(inplanes, planes, stride)
        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class Bottleneck_v2(nn.Module):
    # Bottleneck in torchvision places the stride for downsampling at 3x3 convolution(self.conv2)
    # while original implementation places the stride at the first 1x1 convolution(self.conv1)
    # according to "Deep residual learning for image recognition"https://arxiv.org/abs/1512.03385.
    # This variant is also known as ResNets V1.5 and improves accuracy according to
    # https://ngc.nvidia.com/catalog/model-scripts/nvidia:resnet_50_v1_5_for_pytorch.

    expansion: int = 4

    def __init__(
            self,
            inplanes: int,
            planes: int,
            stride: int = 1,
            downsample: Optional[nn.Module] = None,
            groups: int = 1,
            base_width: int = 64,
            dilation: int = 1,
            norm_layer: Optional[Callable[..., nn.Module]] = None
    ) -> None:
        super(Bottleneck_v2, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        width = int(planes * (base_width / 64.)) * groups
        # Both self.conv2 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv1x1(inplanes, width)
        self.bn1 = norm_layer(width)

        if stride == 1:
            self.conv2 = conv3x3(width, width, stride, groups, dilation)
            # self.conv2 = conv3x3(inplanes, planes, stride)
        elif stride == 2:
            self.conv2 = conv5x5(width, width, stride, groups, dilation)

        self.bn2 = norm_layer(width)
        self.conv3 = conv1x1(width, planes * self.expansion)
        self.bn3 = norm_layer(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x: Tensor) -> Tensor:
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class ThinResNet(nn.Module):
    def __init__(self, resnet_size=34, num_classes=1000, 
                 input_norm='', input_len=300, inst_norm=True, input_dim=257, gain_axis='both',
                 filter=None, feat_dim=64, sr=16000, stretch_ratio=[1.0], win_length=int(0.025*16000),
                 nfft=512, exp=False, filter_fix=False,
                 kernel_size=5, stride=1, padding=2, first_bias=True, 
                 block_type='None', expansion=1, channels=[16, 32, 64, 128], fast='None', downsample=None, 
                 red_ratio=8,
                 zero_init_residual=False, groups=1, width_per_group=64, replace_stride_with_dilation=None, 
                 dropout_p=0.0, 
                 encoder_type='STAP', time_dim=1, avg_size=4, embedding_size=128, 
                 alpha=0,
                 norm_layer=None, 
                 mask='None', mask_len=[5, 10], init_weight='mel', scale=0.2, weight_p=0.1, weight_norm='max',
                 mix='mixup', mask_ckp='',
                 gain_layer=False, **kwargs):
        
        super(ThinResNet, self).__init__()
        resnet_type = {8: [1, 1, 1, 0],
                       10: [1, 1, 1, 1],
                       14: [2, 2, 2, 0],
                       18: [2, 2, 2, 2],
                       34: [3, 4, 6, 3],
                       50: [3, 4, 6, 3],
                       101: [3, 4, 23, 3]}

        layers = resnet_type[resnet_size]
        freq_dim = avg_size  # default 4
        time_dim = time_dim  # default 1
        self.input_len = input_len
        self.input_dim = input_dim
        self.inst_norm = inst_norm
        self.filter = filter
        self._norm_layer = nn.BatchNorm2d
        self.embedding_size = embedding_size
        self.dropout_p = dropout_p
        self.gain_layer = gain_layer
        self.gain_axis = gain_axis
        self.mask = mask
        self.scale = scale
        self.weight_p = weight_p
        self.weight_norm = weight_norm

        self.dilation = 1
        self.fast = str(fast)
        self.num_filter = channels  # [16, 32, 64, 128]
        self.inplanes = self.num_filter[0]
        self.downsample = str(downsample)

        self.mix_type = mix
        mix_types = {
            "mixup": self.mixup,
            "manifold": self.mixup,
            "addup": self.addup,
            "style": self.mixstyle,
            "align": self.alignmix,
            "style_time": self.mixstyle_time,
            "style_base": self.mixbase,
            "cutmix": self.cutmix,
            "cutmixstyle": self.cutmixstylebase,
        }
        self.mix = mix_types[mix]

        if block_type == "seblock":
            block = SEBasicBlock if resnet_size < 50 else SEBottleneck
            # block.reduction_ratio = red_ratio
        elif block_type == "seblock_v2":
            block = SEBasicBlock_v2 if resnet_size < 50 else SEBottleneck_v2
        elif block_type == 'cbam':
            block = CBAMBlock
        elif block_type == 'cbam_v2':
            block = CBAMBlock_v2
        elif block_type in ['basic', 'None']:
            block = BasicBlock if resnet_size < 50 else Bottleneck
        elif block_type == 'basic_v2':
            block = BasicBlock_v2 if resnet_size < 50 else Bottleneck_v2
        elif block_type == 'se2block':
            block = SE_Res2Block if resnet_size < 50 else SE_Res2Bottleneck
        elif block_type == 'res2block':
            block = Res2Block if resnet_size < 50 else Res2Bottleneck

        block.expansion = expansion
        # num_filter = [32, 64, 128, 256]

        if replace_stride_with_dilation is None:
            # each element in the tuple indicates if we should replace
            # the 2x2 stride with a dilated convolution instead
            replace_stride_with_dilation = [False, False, False]
        if len(replace_stride_with_dilation) != 3:
            raise ValueError("replace_stride_with_dilation should be None "
                             "or a 3-element tuple, got {}".format(replace_stride_with_dilation))
        self.groups = groups
        self.base_width = width_per_group
        self.input_norm = input_norm

        input_mask = []
        filter_layer = get_filter_layer(filter=filter, input_dim=input_dim, sr=sr, feat_dim=feat_dim,
                                        exp=exp, filter_fix=filter_fix,
                                        stretch_ratio=stretch_ratio, win_length=win_length, nfft=nfft)
        if filter_layer != None:
            input_mask.append(filter_layer)
            input_dim = feat_dim

        norm_layer = get_input_norm(input_norm, input_dim)
        if norm_layer != None:
            input_mask.append(norm_layer)
        mask_layer = get_mask_layer(mask=mask, mask_len=mask_len, input_dim=input_dim,
                                    init_weight=init_weight, weight_p=weight_p,
                                    scale=scale, weight_norm=weight_norm, mask_ckp=mask_ckp)

        if mask_layer != None:
            input_mask.append(mask_layer)

        self.input_mask = nn.Sequential(*input_mask)

        self.conv1 = nn.Conv2d(1, self.num_filter[0], kernel_size=kernel_size, stride=stride, padding=padding)
        self.bn1 = self._norm_layer(self.num_filter[0])
        self.relu = nn.ReLU(inplace=True)

        if self.fast.startswith('avp'):
            self.maxpool = nn.AvgPool2d(kernel_size=(
                3, 3), stride=(1, 2), padding=(1, 1))
        elif self.fast.startswith('av1p'):
            self.maxpool = nn.AvgPool2d(kernel_size=(
                1, 2), stride=(1, 2), padding=(0, 0))
        elif self.fast.startswith('mxp'):
            self.maxpool = nn.MaxPool2d(kernel_size=(
                3, 3), stride=(1, 2), padding=(1, 1))
        else:
            self.maxpool = None

        self.layer1 = self._make_layer(
            block, self.num_filter[0], layers[0], red_ratio=red_ratio, input_dim=int(np.ceil(input_dim/self.conv1.stride[1])))
        self.layer2 = self._make_layer(
            block, self.num_filter[1], layers[1], stride=2, red_ratio=red_ratio, input_dim=int(np.ceil(input_dim/self.conv1.stride[1]/2)))
        self.layer3 = self._make_layer(
            block, self.num_filter[2], layers[2], stride=2, red_ratio=red_ratio)

        last_stride = 1 if self.fast in [
            'avp1', 'mxp1', 'none1', 'av1p1', 'av1p'] else 2
        self.layer4 = self._make_layer(
            block, self.num_filter[3], layers[3], stride=last_stride, red_ratio=red_ratio)

        self.gain = GAIN(time=self.input_len,
                         freq=self.input_dim) if self.gain_layer else None
        self.dropout = nn.Dropout(self.dropout_p)

        last_channel = self.num_filter[3] if layers[3] > 0 else self.num_filter[2]
        # [64, 128, 37, 8]
        if freq_dim > 0:
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            encode_input_dim = int(freq_dim * last_channel * block.expansion)
        else:
            self.avgpool = None
            encode_input_dim = int(
                np.ceil(input_dim / self.conv1.stride[1] / 4 / last_stride) * last_channel * block.expansion)

        if encoder_type == 'SAP':
            self.encoder = SelfAttentionPooling(
                input_dim=encode_input_dim, hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim

        elif encoder_type == 'SAP2':
            self.encoder = SelfAttentionPooling_v2(input_dim=encode_input_dim,
                                                   hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim

        elif encoder_type in ['ASTP', 'SASP']:
            self.encoder = AttentionStatisticPooling(input_dim=encode_input_dim,
                                                     hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim * 2
        elif encoder_type in ['ASTP2', 'SASP2']:
            self.encoder = AttentionStatisticPooling_v2(
                input_dim=encode_input_dim, hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim * 2
        elif encoder_type == 'STAP':
            self.encoder = StatisticPooling(input_dim=encode_input_dim)
            self.encoder_output = encode_input_dim * 2
        else:
            self.encoder = nn.AdaptiveAvgPool2d((time_dim, None))
            self.encoder_output = encode_input_dim * time_dim

        self.fc1 = nn.Sequential(
            nn.Linear(self.encoder_output, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )

        self.alpha = alpha
        if self.alpha:
            self.l2_norm = L2_Norm(self.alpha)
        self.classifier = nn.Linear(embedding_size, num_classes)
        self.return_embeddings = True

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                # nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                nn.init.normal_(m.weight, mean=0., std=1.)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        # Zero-initialize the last BN in each residual branch, so that the residual branch
        # starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, Bottleneck):
                    nn.init.constant_(m.bn3.weight, 0)
                elif isinstance(m, BasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)

    def _make_layer(self, block, planes, blocks, stride=1, red_ratio=2, input_dim=None):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            if self.downsample in ['None', 'k1']:
                downsample = nn.Sequential(
                    conv1x1(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k1avg':
                downsample = nn.Sequential(
                    nn.AvgPool2d(kernel_size=3, stride=stride, padding=1),
                    conv1x1(self.inplanes, planes * block.expansion, 1),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k3':
                downsample = nn.Sequential(
                    conv3x3(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k5':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k5r':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                    nn.ReLU()
                )
            elif self.downsample == 'k51':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion,
                            stride, groups=self.inplanes),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k52':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion,
                            stride, groups=int(self.inplanes / 2)),
                    nn.BatchNorm2d(planes * block.expansion),
                )

        layers = []
        if blocks > 0:
            layers.append(block(self.inplanes, planes, stride=stride,
                          downsample=downsample, reduction_ratio=red_ratio))
            self.inplanes = planes * block.expansion
            for _ in range(1, blocks):
                layers.append(block(self.inplanes, planes,
                              reduction_ratio=red_ratio))

        if self.mask == 'frl' and input_dim != None:
            layers.append(FrequencyReweightLayer(input_dim=input_dim))
        elif self.mask in ['frl2', 'fgrl4frl2'] and input_dim != None:
            layers.append(FrequencyReweightLayer2(input_dim=input_dim))
        elif self.mask == 'fnrl' and input_dim != None:
            layers.append(FrequencyNormReweightLayer(input_dim=input_dim))
        elif self.mask in ['fgrl52', 'fgrl42'] and input_dim != None:
            layers.append(FrequencyGenderReweightLayer5(input_dim=input_dim))
        elif self.mask == 'trl' and input_dim != None:
            layers.append(TimeReweightLayer(input_dim=input_dim))
        elif self.mask == 'ftrl' and input_dim != None:
            layers.append(FreqTimeReweightLayer(input_dim=input_dim))

        return nn.Sequential(*layers)

    def _forward(self, x, feature_map='', proser=None, label=None,
                 lamda_beta=0.2, mixup_alpha=-1):

        if isinstance(mixup_alpha, float) or isinstance(mixup_alpha, int):
            layer_mix = mixup_alpha
        elif isinstance(mixup_alpha, list):
            layer_mix = random.choice(mixup_alpha)

        if proser != None and layer_mix == 0:
            x = self.mix(x, proser, lamda_beta)

        x = self.input_mask(x)
        if proser != None and layer_mix == 1:
            x = self.mix(x, proser, lamda_beta)

        x = self.relu(self.bn1(self.conv1(x)))
        if self.maxpool != None:
            x = self.maxpool(x)

        if proser != None and layer_mix == 2:
            x = self.mix(x, proser, lamda_beta)

        # print(x.shape)
        group1 = self.layer1(x)
        if proser != None and layer_mix == 3:
            group1 = self.mix(group1, proser, lamda_beta)

        group2 = self.layer2(group1)
        if proser != None and layer_mix == 4:
            group2 = self.mix(group2, proser, lamda_beta)

        group3 = self.layer3(group2)
        if proser != None and layer_mix == 5:
            group3 = self.mix(group3, proser, lamda_beta)

        group4 = self.layer4(group3)
        if proser != None and layer_mix == 6:
            group4 = self.mix(group4, proser, lamda_beta)

        if self.dropout_p > 0:
            group4 = self.dropout(group4)

        if feature_map == 'last':
            embeddings = group4
        elif feature_map == 'attention':
            embeddings = (group1, group2, group3, group4)

        if self.avgpool != None:
            group4 = self.avgpool(group4)

        if self.encoder != None:
            x = self.encoder(group4)

        if proser != None and layer_mix == 7:
            x = self.mix(x, proser, lamda_beta)
        x = x.view(x.size(0), -1)

        x = self.fc1(x)
        if self.alpha:
            x = self.l2_norm(x)

        if proser != None and layer_mix == 8:
            x = self.mix(x, proser, lamda_beta)

        if feature_map == 'last':
            return embeddings, x

        if proser != None and label != None:
            half_batch_size = int(x.shape[0] / 2)
            half_feats = x[-half_batch_size:]
            # half_label = label[-half_batch_size:]

            # half_idx = [i for i in range(half_batch_size)]
            # half_idx_ten = torch.LongTensor(half_idx)
            # random.shuffle(half_idx)
            # pdb.set_trace()
            shuf_half_idx_ten = proser
            select_bool = label[:, 0, 0, 0]
            select_bool = select_bool.reshape(
                -1, 1).repeat_interleave(self.embedding_size, dim=1)
            select_bool = select_bool.to(device=half_feats.device)
            # torch.repeat_interleave()
            half_a_feat = torch.masked_select(
                half_feats, mask=select_bool).reshape(-1, self.embedding_size)

            # print(half_feats[shuf_half_idx_ten], select_bool)
            half_b_feat = torch.masked_select(half_feats[shuf_half_idx_ten], mask=select_bool).reshape(-1,
                                                                                                       self.embedding_size)

            # half_b_label = torch.masked_select(half_label, mask=select_bool[:, 0])
            # pdb.set_trace()
            lamda_beta = np.random.beta(lamda_beta, lamda_beta)
            half_feat = lamda_beta * half_a_feat + \
                (1 - lamda_beta) * half_b_feat
            # print(x[:half_batch_size].shape, half_feat.shape)
            x = torch.cat([x[:half_batch_size], half_feat], dim=0)

        if proser != None and layer_mix == 9:
            x = self.mix(x, proser, lamda_beta)

        logits = "" if self.classifier == None else self.classifier(x)

        if feature_map == 'attention':
            return logits, embeddings

        if self.return_embeddings:
            return logits, x
        else:
            return logits

    def xvector(self, x, embedding_type='near'):
        # pdb.set_trace()
        # print(x.shape)
        if self.filter_layer != None:
            x = self.filter_layer(x)

        if self.inst_layer != None:
            x = self.inst_layer(x)

        if self.mask_layer != None:
            x = self.mask_layer(x)

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        if self.maxpool != None:
            x = self.maxpool(x)

        # print(x.shape)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        # print(x.shape)

        if self.dropout_p > 0:
            x = self.dropout(x)

        if self.avgpool != None:
            x = self.avgpool(x)

        if self.encoder != None:
            x = self.encoder(x)

        x = x.view(x.size(0), -1)
        if embedding_type == 'near':
            embeddings = self.fc1[0](x)
        else:
            embeddings = self.fc1(x)

        return embeddings

    def mixup(self, x, shuf_half_idx_ten, lamda_beta):
        mix_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-mix_size:]
        x = torch.cat(
            [x[:-mix_size], lamda_beta * half_feats +
                (1 - lamda_beta) * half_feats[shuf_half_idx_ten]],
            dim=0)

        return x

    def mixstyle(self, x, shuf_half_idx_ten, lamda_beta):
        mix_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-mix_size:]

        mu = half_feats.mean(dim=[2, 3], keepdim=True)
        var = half_feats.var(dim=[2, 3], keepdim=True)
        sig = (var + 1e-6).sqrt()
        mu, sig = mu.detach(), sig.detach()
        x_normed = (half_feats - mu) / sig

        mu2, sig2 = mu[shuf_half_idx_ten], sig[shuf_half_idx_ten]
        mu_mix = mu*lamda_beta + mu2 * (1-lamda_beta)
        sig_mix = sig*lamda_beta + sig2 * (1-lamda_beta)

        x = torch.cat(
            [x[:-mix_size], x_normed*sig_mix + mu_mix],
            dim=0)

        return x
    
    def mixbase(self, x, shuf_half_idx_ten, lamda_beta):
        mix_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-mix_size:]

        mu = half_feats.mean(dim=[1], keepdim=True)
        var = half_feats.var(dim=[1], keepdim=True)
        sig = (var + 1e-6).sqrt()
        mu, sig = mu.detach(), sig.detach()

        x_normed = (half_feats - mu) / sig
        x_normed2 = x_normed[shuf_half_idx_ten].detach()

        mu2, sig2 = mu[shuf_half_idx_ten], sig[shuf_half_idx_ten]
        
        # mu_mix = mu*lamda_beta + mu2 * (1-lamda_beta)
        # sig_mix = sig*lamda_beta + sig2 * (1-lamda_beta)

        x_normed2 = x_normed*lamda_beta + x_normed2 * (1-lamda_beta)

        x = torch.cat(
            [x[:-mix_size], x_normed2*sig2 + mu2],
            dim=0)

        return x
    
    def cutmix(self, x, shuf_half_idx_ten, lamda_beta):
        mix_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-mix_size:]

        lam_t = int(np.ceil(half_feats.shape[2] * np.sqrt(lamda_beta)))
        lam_f = int(np.ceil(half_feats.shape[3] * np.sqrt(lamda_beta)))
        t_start = np.random.randint(0, half_feats.shape[2])
        f_start = np.random.randint(0, half_feats.shape[3])

        half_feats_shuf = half_feats[shuf_half_idx_ten].clone().detach()
        if lam_t > 0:
            end_t = t_start + lam_t
            half_feats[:, :, t_start:end_t] = half_feats_shuf[:, :,t_start:end_t]

        if lam_f > 0:
            end_f = f_start + lam_f
            half_feats[:, :, :, f_start:end_f] = half_feats_shuf[:, :,:, f_start:end_f]

        x = torch.cat(
            [x[:-mix_size], half_feats],
            dim=0)

        return x
    
    def cutmixstylebase(self, x, shuf_half_idx_ten, lamda_beta):
        mix_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-mix_size:]

        mu = half_feats.mean(dim=[1], keepdim=True)
        var = half_feats.var(dim=[1], keepdim=True)

        lam_t = int(np.ceil(mu.shape[2] * np.sqrt(lamda_beta)))
        lam_f = int(np.ceil(mu.shape[3] * np.sqrt(lamda_beta)))
        t_start = np.random.randint(0, mu.shape[2])
        f_start = np.random.randint(0, mu.shape[3])

        sig = (var + 1e-6).sqrt()
        mu, sig = mu.detach(), sig.detach()

        x_normed = (half_feats - mu) / sig
        x_normed2 = x_normed[shuf_half_idx_ten].detach()

        mu2, sig2 = mu[shuf_half_idx_ten], sig[shuf_half_idx_ten]

        # mu_mix = mu*lamda_beta + mu2 * (1-lamda_beta)
        # sig_mix = sig*lamda_beta + sig2 * (1-lamda_beta)
        if lam_t > 0:
            end_t = t_start + lam_t
            x_normed[:, :, t_start:end_t] = x_normed2[:, :,t_start:end_t]

        if lam_f > 0:
            end_f = f_start + lam_f
            x_normed[:, :, :, f_start:end_f] = x_normed2[:, :,:, f_start:end_f]

        x = torch.cat(
            [x[:-mix_size], x_normed*sig2 + mu2],
            dim=0)

        return x

    def mixstyle_time(self, x, shuf_half_idx_ten, lamda_beta):
        mix_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-mix_size:]

        mu = half_feats.mean(dim=2, keepdim=True)
        var = half_feats.var(dim=2, keepdim=True)
        sig = (var + 1e-6).sqrt()
        mu, sig = mu.detach(), sig.detach()
        x_normed = (half_feats - mu) / sig

        mu2, sig2 = mu[shuf_half_idx_ten], sig[shuf_half_idx_ten]
        mu_mix = mu*lamda_beta + mu2 * (1-lamda_beta)
        sig_mix = sig*lamda_beta + sig2 * (1-lamda_beta)

        x = torch.cat(
            [x[:-mix_size], x_normed*sig_mix + mu_mix],
            dim=0)

        return x

    def alignmix(self, x, shuf_half_idx_ten, lamda_beta):
        mix_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-mix_size:]
        half_feats_shape = half_feats.shape # 128 x 128 x 38 x 5
        # print(half_feats.shape)
        # out shape = batch_size x 512 x 4 x 4 (cifar10/100)
        # batch_size x 512 x 16
        feat1 = half_feats.view(half_feats_shape[0], self.num_filter[-1], -1)
        feat2 = half_feats[shuf_half_idx_ten].view(
            half_feats_shape[0], self.num_filter[-1], -1)

        sinkhorn = SinkhornDistance(eps=0.1, max_iter=100, reduction=None)

        P = sinkhorn(feat1.permute(0, 2, 1),
                     feat2.permute(0, 2, 1)).detach()  # optimal plan batch x 16 x 16
        # P = P*(half_feats_shape[2]*half_feats_shape[3]) # assignment matrix
        P = P*(feat1.shape[-1]) # assignment matrix

        # uniformly choose at random, which alignmix to perform
        align_mix = random.randint(0, 1)
        if (align_mix == 0):
            # \tilde{A} = A'R^{T}
            f1 = torch.matmul(feat2, P.permute(0, 2, 1).cuda()).view(
                half_feats_shape) # batch_tf*channel x tf*channel_tf*channel
            final = feat1.view(half_feats_shape)*lamda_beta + f1*(1-lamda_beta)

        elif (align_mix == 1):
            # \tilde{A}' = AR
            f2 = torch.matmul(feat1, P.cuda()).view(half_feats_shape).cuda()
            final = f2*lamda_beta + feat2.view(half_feats_shape)*(1-lamda_beta)

        x = torch.cat([x[:-mix_size], final], dim=0)

        return x

    def addup(self, x, shuf_half_idx_ten, lamda_beta):
        half_batch_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-half_batch_size:]
        x = torch.cat(
            [x[:-half_batch_size], -lamda_beta * half_feats +
                (1 + lamda_beta) * half_feats[shuf_half_idx_ten]],
            dim=0)

        return x

    # Allow for accessing forward method in a inherited class
    forward = _forward


class RepeatResNet(nn.Module):
    def __init__(self, resnet_size=34, block_type='None', expansion=1, channels=[16, 32, 64, 128],
                 input_len=300, inst_norm=True, input_dim=257, sr=16000, gain_axis='both',
                 first_bias=True, kernel_size=5, stride=1, padding=2,
                 dropout_p=0.0, exp=False, filter_fix=False, feat_dim=64, filter=None,
                 num_classes=1000, embedding_size=128, fast='None', time_dim=1, avg_size=4,
                 alpha=12, encoder_type='STAP', zero_init_residual=False, groups=1, width_per_group=64,
                 replace_stride_with_dilation=None, norm_layer=None, downsample=None,
                 mask='None', mask_len=[5, 10], red_ratio=8,
                 init_weight='mel', scale=0.2, weight_p=0.1, weight_norm='max',
                 input_norm='', gain_layer=False, **kwargs):
        super(RepeatResNet, self).__init__()
        resnet_type = {8: [1, 1, 1, 0],
                       10: [1, 1, 1, 1],
                       14: [2, 2, 2, 0],
                       18: [2, 2, 2, 2],
                       34: [3, 4, 6, 3],
                       50: [3, 4, 6, 3],
                       101: [3, 4, 23, 3]}

        layers = resnet_type[resnet_size]
        freq_dim = avg_size  # default 4
        time_dim = time_dim  # default 1
        self.input_len = input_len
        self.input_dim = input_dim
        self.inst_norm = inst_norm
        self.filter = filter
        self._norm_layer = nn.BatchNorm2d
        self.embedding_size = embedding_size
        self.dropout_p = dropout_p
        self.gain_layer = gain_layer
        self.gain_axis = gain_axis
        self.mask = mask
        self.scale = scale
        self.weight_p = weight_p
        self.weight_norm = weight_norm

        self.dilation = 1
        self.fast = str(fast)
        self.num_filter = channels  # [16, 32, 64, 128]
        self.inplanes = self.num_filter[0]
        self.downsample = str(downsample)

        if block_type == "seblock":
            block = SEBasicBlock if resnet_size < 50 else SEBottleneck
            # block.reduction_ratio = red_ratio
        elif block_type == "seblock_v2":
            block = SEBasicBlock_v2
        elif block_type == 'cbam':
            block = CBAMBlock
        elif block_type == 'cbam_v2':
            block = CBAMBlock_v2
        elif block_type in ['basic', 'None']:
            block = BasicBlock if resnet_size < 50 else Bottleneck
        elif block_type == 'basic_v2':
            block = BasicBlock_v2 if resnet_size < 50 else Bottleneck_v2
        elif block_type == 'se2block':
            block = SE_Res2Block
        elif block_type == 'res2block':
            block = Res2Block

        block.expansion = expansion
        # num_filter = [32, 64, 128, 256]

        if replace_stride_with_dilation is None:
            # each element in the tuple indicates if we should replace
            # the 2x2 stride with a dilated convolution instead
            replace_stride_with_dilation = [False, False, False]
        if len(replace_stride_with_dilation) != 3:
            raise ValueError("replace_stride_with_dilation should be None "
                             "or a 3-element tuple, got {}".format(replace_stride_with_dilation))
        self.groups = groups
        self.base_width = width_per_group
        self.input_norm = input_norm

        input_mask = []
        filter_layer = get_filter_layer(filter=filter, input_dim=input_dim, sr=sr, feat_dim=feat_dim,
                                        exp=exp, filter_fix=filter_fix)
        if filter_layer != None:
            input_mask.append(filter_layer)

        norm_layer = get_input_norm(input_norm)
        if norm_layer != None:
            input_mask.append(norm_layer)
        mask_layer = get_mask_layer(mask=mask, mask_len=mask_len, input_dim=input_dim,
                                    init_weight=init_weight, weight_p=weight_p,
                                    scale=scale, weight_norm=weight_norm)

        if mask_layer != None:
            input_mask.append(mask_layer)

        self.input_mask = nn.Sequential(*input_mask)

        self.conv1 = nn.Conv2d(1, self.num_filter[0], kernel_size=kernel_size, stride=stride, padding=padding,
                               bias=first_bias)
        self.bn1 = self._norm_layer(self.num_filter[0])
        self.relu = nn.ReLU(inplace=True)

        if self.fast.startswith('avp'):
            # self.maxpool = nn.MaxPool2d(kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
            self.maxpool = nn.AvgPool2d(kernel_size=(
                3, 3), stride=(1, 2), padding=(1, 1))
        elif self.fast.startswith('av1p'):
            # self.maxpool = nn.MaxPool2d(kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
            self.maxpool = nn.AvgPool2d(kernel_size=(
                1, 3), stride=(1, 2), padding=(0, 1))
        elif self.fast.startswith('mxp'):
            self.maxpool = nn.MaxPool2d(kernel_size=(
                3, 3), stride=(1, 2), padding=(1, 1))
        else:
            self.maxpool = None

        self.layer1 = self._make_layer(
            block, self.num_filter[0], layers[0], red_ratio=red_ratio)
        self.layer2 = self._make_layer(
            block, self.num_filter[1], layers[1], stride=2, red_ratio=red_ratio)
        self.layer3 = self._make_layer(
            block, self.num_filter[2], layers[2], stride=2, red_ratio=red_ratio)

        last_stride = 1 if self.fast in [
            'avp1', 'mxp1', 'none1', 'av1p1'] else 2
        self.layer4 = self._make_layer(
            block, self.num_filter[3], layers[3], stride=last_stride, red_ratio=red_ratio)

        self.gain = GAIN(time=self.input_len,
                         freq=self.input_dim) if self.gain_layer else None
        self.dropout = nn.Dropout(self.dropout_p)

        last_channel = self.num_filter[3] if layers[3] > 0 else self.num_filter[2]
        # [64, 128, 37, 8]
        if freq_dim > 0:
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            encode_input_dim = int(freq_dim * last_channel * block.expansion)
        else:
            self.avgpool = None

            encode_input_dim = int(
                np.ceil(input_dim / self.conv1.stride[1] / 4 / last_stride) * last_channel * block.expansion)

        if encoder_type == 'SAP':
            self.encoder = SelfAttentionPooling(
                input_dim=encode_input_dim, hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim

        elif encoder_type == 'SAP2':
            self.encoder = SelfAttentionPooling_v2(input_dim=encode_input_dim,
                                                   hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim

        elif encoder_type in ['ASTP', 'SASP']:
            self.encoder = AttentionStatisticPooling(input_dim=encode_input_dim,
                                                     hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim * 2

        elif encoder_type in ['ASTP2', 'SASP2']:
            self.encoder = AttentionStatisticPooling_v2(
                input_dim=encode_input_dim, hidden_dim=int(embedding_size / 2))
            self.encoder_output = encode_input_dim * 2

        elif encoder_type == 'STAP':
            self.encoder = StatisticPooling(input_dim=encode_input_dim)
            self.encoder_output = encode_input_dim * 2
        else:
            self.encoder = nn.AdaptiveAvgPool2d((time_dim, None))
            self.encoder_output = encode_input_dim * time_dim

        self.fc1 = nn.Sequential(
            nn.Linear(self.encoder_output, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )

        self.alpha = alpha
        if self.alpha:
            self.l2_norm = L2_Norm(self.alpha)

        self.classifier = nn.Linear(embedding_size, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                # nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                nn.init.normal_(m.weight, mean=0., std=1.)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        # Zero-initialize the last BN in each residual branch, so that the residual branch
        # starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, Bottleneck):
                    nn.init.constant_(m.bn3.weight, 0)
                elif isinstance(m, BasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)

    def _make_layer(self, block, planes, blocks, stride=1, red_ratio=2):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            if self.downsample in ['None', 'k1']:
                downsample = nn.Sequential(
                    conv1x1(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k1avg':
                downsample = nn.Sequential(
                    nn.AvgPool2d(kernel_size=3, stride=stride, padding=1),
                    conv1x1(self.inplanes, planes * block.expansion, 1),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k3':
                downsample = nn.Sequential(
                    conv3x3(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k5':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k5r':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                    nn.ReLU()
                )
            elif self.downsample == 'k51':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion,
                            stride, groups=self.inplanes),
                    nn.BatchNorm2d(planes * block.expansion),
                )
            elif self.downsample == 'k52':
                downsample = nn.Sequential(
                    conv5x5(self.inplanes, planes * block.expansion,
                            stride, groups=int(self.inplanes / 2)),
                    nn.BatchNorm2d(planes * block.expansion),
                )

        layers = []
        if blocks > 0:
            layers.append(block(self.inplanes, planes, stride=stride,
                          downsample=downsample, reduction_ratio=red_ratio))
            self.inplanes = planes * block.expansion
            for _ in range(1, blocks):
                layers.append(block(self.inplanes, planes,
                              reduction_ratio=red_ratio))

        return nn.Sequential(*layers)

    def _forward(self, x, feature_map='', proser=None, label=None,
                 lamda_beta=0.2, mixup_alpha=-1):
        # pdb.set_trace()
        # print(x.shape)
        # if self.filter_layer != None:
        #     x = self.filter_layer(x)
        #
        # if self.inst_layer != None:
        #     x = self.inst_layer(x)
        #
        # if self.mask_layer != None:
        #     x = self.mask_layer(x)
        if isinstance(mixup_alpha, float) or isinstance(mixup_alpha, int):
            # layer_mix = random.randint(0, 2)
            layer_mix = mixup_alpha
        elif isinstance(mixup_alpha, list):
            layer_mix = random.choice(mixup_alpha)

        if proser != None and layer_mix == 0:
            x = self.mixup(x, proser, lamda_beta)

        x = self.input_mask(x)
        if proser != None and layer_mix == 1:
            x = self.mixup(x, proser, lamda_beta)

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        if self.maxpool != None:
            x = self.maxpool(x)

        if proser != None and layer_mix == 2:
            x = self.mixup(x, proser, lamda_beta)

        # print(x.shape)
        group1 = self.layer1(x)
        group1 = self.layer1[-1:](group1)

        if proser != None and layer_mix == 3:
            group1 = self.mixup(group1, proser, lamda_beta)

        group2 = self.layer2(group1)
        group2 = self.layer2[-1:](group2)

        if proser != None and layer_mix == 4:
            group2 = self.mixup(group2, proser, lamda_beta)

        group3 = self.layer3(group2)
        group3 = self.layer3[-1:](group3)

        if proser != None and layer_mix == 5:
            group3 = self.mixup(group3, proser, lamda_beta)

        group4 = self.layer4(group3)
        group4 = self.layer4[-1:](group4)
        # group4 = self.layer4(group4)
        if proser != None and layer_mix == 6:
            group4 = self.mixup(group4, proser, lamda_beta)

        if self.dropout_p > 0:
            group4 = self.dropout(group4)

        if feature_map == 'last':
            embeddings = group4
        elif feature_map == 'attention':
            embeddings = (group1, group2, group3, group4)

        if self.avgpool != None:
            x = self.avgpool(group4)

        if self.encoder != None:
            x = self.encoder(x)

        x = x.view(x.size(0), -1)
        # if proser != None and layer_mix == 7:
        #     x = self.mixup(x, proser, lamda_beta)
        x = self.fc1(x)
        if self.alpha:
            x = self.l2_norm(x)

        if feature_map == 'last':
            return embeddings, x

        if proser != None and label != None:
            half_batch_size = int(x.shape[0] / 2)
            half_feats = x[-half_batch_size:]
            # half_label = label[-half_batch_size:]

            # half_idx = [i for i in range(half_batch_size)]
            # half_idx_ten = torch.LongTensor(half_idx)
            # random.shuffle(half_idx)
            # pdb.set_trace()
            shuf_half_idx_ten = proser
            select_bool = label[:, 0, 0, 0]
            select_bool = select_bool.reshape(
                -1, 1).repeat_interleave(self.embedding_size, dim=1)
            select_bool = select_bool.to(device=half_feats.device)
            # torch.repeat_interleave()
            half_a_feat = torch.masked_select(
                half_feats, mask=select_bool).reshape(-1, self.embedding_size)

            # print(half_feats[shuf_half_idx_ten], select_bool)
            half_b_feat = torch.masked_select(half_feats[shuf_half_idx_ten], mask=select_bool).reshape(-1,
                                                                                                       self.embedding_size)

            # half_b_label = torch.masked_select(half_label, mask=select_bool[:, 0])
            # pdb.set_trace()
            lamda_beta = np.random.beta(lamda_beta, lamda_beta)
            # lamda_beta = max(0.2, lamda_beta)
            # lamda_beta = min(0.8, lamda_beta)

            half_feat = lamda_beta * half_a_feat + \
                (1 - lamda_beta) * half_b_feat
            # print(x[:half_batch_size].shape, half_feat.shape)
            x = torch.cat([x[:half_batch_size], half_feat], dim=0)

        if proser != None and layer_mix == 7:
            x = self.mixup(x, proser, lamda_beta)

        logits = "" if self.classifier == None else self.classifier(x)

        if feature_map == 'attention':
            return logits, embeddings

        return logits, x

    def xvector(self, x, embedding_type='near'):
        # pdb.set_trace()
        # print(x.shape)
        if self.filter_layer != None:
            x = self.filter_layer(x)

        if self.inst_layer != None:
            x = self.inst_layer(x)

        if self.mask_layer != None:
            x = self.mask_layer(x)

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        if self.maxpool != None:
            x = self.maxpool(x)

        # print(x.shape)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        # print(x.shape)

        if self.dropout_p > 0:
            x = self.dropout(x)

        if self.avgpool != None:
            x = self.avgpool(x)

        if self.encoder != None:
            x = self.encoder(x)

        x = x.view(x.size(0), -1)
        if embedding_type == 'near':
            embeddings = self.fc1[0](x)
        else:
            embeddings = self.fc1(x)

        return embeddings

    def mixup(self, x, shuf_half_idx_ten, lamda_beta):
        half_batch_size = shuf_half_idx_ten.shape[0]
        half_feats = x[-half_batch_size:]
        x = torch.cat(
            [x[:-half_batch_size], lamda_beta * half_feats +
                (1 - lamda_beta) * half_feats[shuf_half_idx_ten]],
            dim=0)

        return x

    # Allow for accessing forward method in a inherited class
    forward = _forward


class ResNet(nn.Module):

    def __init__(self, resnet_size=18, embedding_size=512, block=BasicBlock,
                 channels=[64, 128, 256, 512], num_classes=1000,
                 avg_size=4, zero_init_residual=False, **kwargs):
        super(ResNet, self).__init__()

        resnet_layer = {10: [1, 1, 1, 1],
                        18: [2, 2, 2, 2],
                        34: [3, 4, 6, 3],
                        50: [3, 4, 6, 3],
                        101: [3, 4, 23, 3]}

        layers = resnet_layer[resnet_size]
        self.layers = layers

        self.avg_size = avg_size
        self.channels = channels
        self.inplanes = self.channels[0]
        self.conv1 = nn.Conv2d(
            1, self.channels[0], kernel_size=5, stride=2, padding=2, bias=False)
        self.bn1 = nn.BatchNorm2d(self.channels[0])
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.layer1 = self._make_layer(block, self.channels[0], layers[0])
        self.layer2 = self._make_layer(
            block, self.channels[1], layers[1], stride=2)
        self.layer3 = self._make_layer(
            block, self.channels[2], layers[2], stride=2)
        self.layer4 = self._make_layer(
            block, self.channels[3], layers[3], stride=2)

        self.avgpool = nn.AdaptiveAvgPool2d((1, avg_size))

        if self.layers[3] == 0:
            self.fc1 = nn.Sequential(
                nn.Linear(self.channels[2] * avg_size, embedding_size),
                nn.BatchNorm1d(embedding_size)
            )
        else:
            self.fc1 = nn.Sequential(
                nn.Linear(self.channels[3] * avg_size, embedding_size),
                nn.BatchNorm1d(embedding_size)
            )

        self.classifier = nn.Linear(embedding_size, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(
                    m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        # Zero-initialize the last BN in each residual branch, so that the residual
        # branch starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, Bottleneck):
                    nn.init.constant_(m.bn3.weight, 0)
                elif isinstance(m, BasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)

        if self.layers[3] != 0:
            x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)

        feat = self.fc1(x)
        logits = self.classifier(feat)

        return logits, feat


# M. Hajibabaei and D. Dai, “Unified hypersphere embedding for speaker recognition,”
# arXiv preprint arXiv:1807.08312, 2018.
class ResNet20(nn.Module):
    def __init__(self, num_classes=1000, embedding_size=128, dropout_p=0.0,
                 block=BasicBlock, input_frames=300, **kwargs):
        super(ResNet20, self).__init__()
        self.dropout_p = dropout_p
        self.inplanes = 1
        self.layer1 = self._make_layer(Block3x3, planes=64, blocks=1, stride=2)

        self.inplanes = 64
        self.layer2 = self._make_layer(
            Block3x3, planes=128, blocks=1, stride=2)

        self.inplanes = 128
        self.layer3 = self._make_layer(BasicBlock, 128, 1)

        self.inplanes = 128
        self.layer4 = self._make_layer(
            Block3x3, planes=256, blocks=1, stride=2)

        self.inplanes = 256
        self.layer5 = self._make_layer(BasicBlock, 256, 3)

        self.inplanes = 256
        self.layer6 = self._make_layer(
            Block3x3, planes=512, blocks=1, stride=2)

        self.inplanes = 512
        self.avgpool = nn.AdaptiveAvgPool2d((1, None))
        self.dropout = nn.Dropout(p=dropout_p)
        self.fc1 = nn.Sequential(
            nn.Linear(17 * self.inplanes, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )
        self.classifier = nn.Linear(embedding_size, num_classes)

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        x = self.layer6(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)

        if self.dropout_p != 0:
            x = self.dropout(x)

        feat = self.fc1(x)

        logits = self.classifier(feat)

        return logits, feat


class LocalResNet(nn.Module):
    """
    Define the ResNet model with A-softmax and AM-softmax loss.
    Added dropout as https://github.com/nagadomi/kaggle-cifar10-torch7 after average pooling and fc layer.
    """

    def __init__(self, embedding_size, num_classes, 
                 resnet_size=8, block_type='basic', red_ratio=2,
                 input_dim=161, input_len=300, gain_layer=False,
                 exp=False, filter_fix=False, feat_dim=64,
                 sr=16000, stretch_ratio=[1.0], win_length=int(0.025*16000), nfft=512,
                 relu_type='relu', channels=[64, 128, 256], dropout_p=0.,
                 encoder_type='None',
                 input_norm=None, alpha=12, stride=2, transform=False, time_dim=1, fast='None',
                 avg_size=4, kernal_size=5, padding=2, filter=None, mask='None', mask_len=[5, 5],
                 init_weight='mel', weight_norm='max', scale=0.2, weight_p=0.1, mask_ckp='',
                 **kwargs):

        super(LocalResNet, self).__init__()
        resnet_type = {8: [1, 1, 1, 0],
                       10: [1, 1, 1, 1],
                       14: [2, 2, 2, 0],
                       18: [2, 2, 2, 2],
                       34: [3, 4, 6, 3],
                       50: [3, 4, 6, 3],
                       101: [3, 4, 23, 3]}

        layers = resnet_type[resnet_size]

        if block_type == "seblock":
            block = SEBasicBlock
        elif block_type == 'cbam':
            block = CBAMBlock
        elif block_type == "se2block":
            block = SE_Res2Block if resnet_size < 50 else SE_Res2Bottleneck
        else:
            block = BasicBlock

        self.input_len = input_len
        self.input_dim = input_dim

        self.alpha = alpha
        self.layers = layers
        self.dropout_p = dropout_p
        self.transform = transform
        self.fast = fast
        self.mask = mask
        self.relu_type = relu_type
        self.embedding_size = embedding_size
        self.gain_layer = gain_layer
        #
        if self.relu_type == 'relu6':
            self.relu = nn.ReLU6(inplace=True)
        elif self.relu_type == 'leakyrelu':
            self.relu = nn.LeakyReLU()
        elif self.relu_type == 'relu':
            self.relu = nn.ReLU(inplace=True)

        self.input_norm = input_norm
        self.input_len = input_len
        self.filter = filter

        input_mask = []
        filter_layer = get_filter_layer(filter=filter, input_dim=input_dim, sr=sr, feat_dim=feat_dim,
                                        exp=exp, filter_fix=filter_fix,
                                        stretch_ratio=stretch_ratio, win_length=win_length, nfft=nfft)
        if filter_layer != None:
            input_mask.append(filter_layer)
            input_dim = feat_dim

        norm_layer = get_input_norm(input_norm, input_dim)
        if norm_layer != None:
            input_mask.append(norm_layer)
        mask_layer = get_mask_layer(mask=mask, mask_len=mask_len, input_dim=input_dim,
                                    init_weight=init_weight, weight_p=weight_p,
                                    scale=scale, weight_norm=weight_norm, mask_ckp=mask_ckp)

        if mask_layer != None:
            input_mask.append(mask_layer)

        self.input_mask = nn.Sequential(*input_mask)

        self.inplanes = channels[0]
        self.conv1 = nn.Conv2d(
            1, channels[0], kernel_size=kernal_size, stride=stride, padding=padding)
        self.bn1 = nn.BatchNorm2d(channels[0])
        if self.fast.startswith('avp'):
            # self.maxpool = nn.MaxPool2d(kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
            # self.maxpool = nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
            self.maxpool = nn.Sequential(
                nn.Conv2d(channels[0], channels[0], kernel_size=1, stride=1),
                nn.ReLU(),
                nn.BatchNorm2d(channels[0]),
                nn.AvgPool2d(kernel_size=3, stride=2)
            )
        else:
            self.maxpool = None
        # self.maxpool = nn.MaxPool2d(kernel_size=(3, 1), stride=(2, 1), padding=(1, 0))
        self.layer1 = self._make_layer(block, channels[0], layers[0])

        self.inplanes = channels[1]
        self.conv2 = nn.Conv2d(channels[0], channels[1], kernel_size=(5, 5), stride=2,
                               padding=padding, bias=False)
        self.bn2 = nn.BatchNorm2d(channels[1])
        self.layer2 = self._make_layer(block, channels[1], layers[1])

        self.inplanes = channels[2]
        self.conv3 = nn.Conv2d(channels[1], channels[2], kernel_size=(5, 5), stride=2,
                               padding=padding, bias=False)
        self.bn3 = nn.BatchNorm2d(channels[2])
        self.layer3 = self._make_layer(block, channels[2], layers[2])

        if layers[3] != 0:
            assert len(channels) == 4
            self.inplanes = channels[3]
            if self.fast in ['avp1', 'mxp1', 'none1', 'av1p1']:
                stride = 1 
            elif self.fast in ['none21']:
                stride = [2, 1] 
            else:
                stride = 2

            self.conv4 = nn.Conv2d(channels[2], channels[3], kernel_size=(5, 5), stride=stride,
                                   padding=padding, bias=False)
            self.bn4 = nn.BatchNorm2d(channels[3])
            self.layer4 = self._make_layer(
                block=block, planes=channels[3], blocks=layers[3])

        self.gain = GAIN(time=self.input_len,
                         freq=self.input_dim) if self.gain_layer else None
        self.dropout = nn.Dropout(self.dropout_p)

        last_conv_chn = channels[-1]
        freq_dim = avg_size

        if encoder_type == 'SAP':
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            self.encoder = SelfAttentionPooling(
                input_dim=last_conv_chn * freq_dim, hidden_dim=int(embedding_size / 2))
            self.encoder_output = last_conv_chn * freq_dim
        elif encoder_type == 'SAP2':
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            self.encoder = SelfAttentionPooling_v2(input_dim=last_conv_chn * freq_dim,
                                                   hidden_dim=int(embedding_size / 2))
            self.encoder_output = last_conv_chn * freq_dim
        elif encoder_type == 'SAP3':
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            self.encoder = SelfAttentionPooling_v3(input_dim=last_conv_chn * freq_dim,
                                                   hidden_dim=int(embedding_size / 2))
            self.encoder_output = last_conv_chn * freq_dim
        elif encoder_type == 'SASP':
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            self.encoder = AttentionStatisticPooling(
                input_dim=last_conv_chn, hidden_dim=int(embedding_size / 2))
            self.encoder_output = last_conv_chn * 2 * freq_dim
        elif encoder_type == 'SASP2':
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            self.encoder = AttentionStatisticPooling_v2(
                input_dim=last_conv_chn, hidden_dim=int(embedding_size / 2))
            self.encoder_output = last_conv_chn * 2 * freq_dim
        elif encoder_type == 'STAP':
            self.avgpool = nn.AdaptiveAvgPool2d((None, freq_dim))
            self.encoder = StatisticPooling(input_dim=last_conv_chn * freq_dim)
            self.encoder_output = last_conv_chn * freq_dim * 2
        elif encoder_type == 'ASTP':
            self.avgpool = AdaptiveStdPool2d((time_dim, freq_dim))
            self.encoder = None
            self.encoder_output = last_conv_chn * freq_dim * time_dim
        else:
            self.avgpool = nn.AdaptiveAvgPool2d((time_dim, freq_dim))
            self.encoder = None
            self.encoder_output = last_conv_chn * freq_dim * time_dim

        # self.fc1 = nn.Sequential(
        #     nn.Linear(self.encoder_output, embedding_size),
        #     nn.ReLU(),
        #     nn.BatchNorm1d(embedding_size)
        # )

        # self.fc1 = nn.Sequential(
        #     nn.Linear(self.encoder_output, embedding_size),
        #     nn.BatchNorm1d(embedding_size)
        # )
        self.fc = nn.Sequential(
            nn.Linear(self.encoder_output, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )

        if self.transform == 'Linear':
            self.trans_layer = nn.Sequential(
                nn.Linear(embedding_size, embedding_size),
                nn.ReLU(),
                nn.BatchNorm1d(embedding_size)
            )
        elif self.transform == 'GhostVLAD':
            self.trans_layer = GhostVLAD_v2(
                num_clusters=8, gost=1, dim=embedding_size, normalize_input=True)
        else:
            self.trans_layer = None

        if self.alpha:
            self.l2_norm = L2_Norm(self.alpha)

        # self.fc = nn.Linear(self.inplanes * avg_size, embedding_size)
        self.classifier = nn.Linear(self.embedding_size, num_classes)

        for m in self.modules():  # 对于各层参数的初始化
            if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
                # n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                # m.weight.data.normal_(0, math.sqrt(2. / n))
                nn.init.kaiming_normal_(
                    m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.GroupNorm)):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1, red_ratio=2):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(inplanes=self.inplanes, planes=planes, stride=stride,
                            downsample=downsample, reduction_ratio=red_ratio))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x, feature_map='', proser=None, label=None,
                 lamda_beta=0.2, mixup_alpha=-1):
        
        x = self.input_mask(x)

        x = self.relu(self.bn1(self.conv1(x)))
        if self.maxpool != None:
            x = self.maxpool(x)

        group1 = self.layer1(x)

        x = self.relu(self.bn2(self.conv2(group1)))
        group2 = self.layer2(x)

        x = self.relu(self.bn3(self.conv3(group2)))
        group3 = self.layer3(x)

        groups = [group1, group2, group3]

        if self.layers[3] != 0:
            x = self.relu(self.bn4(self.conv4(group3)))
            group4 = self.layer4(x)
            groups.append(group4)

        if self.dropout_p > 0:
            groups[-1] = self.dropout(groups[-1])

        if feature_map == 'last':
            embeddings = groups[-1]
        elif feature_map == 'attention':
            embeddings = groups

        x = self.avgpool(groups[-1])
        if self.encoder != None:
            x = self.encoder(x)

        x = x.view(x.size(0), -1)
        # x = self.fc1(x)
        x = self.fc(x)

        if self.trans_layer != None:
            x = self.trans_layer(x)
            # x = t_x + x

        if self.alpha:
            x = self.l2_norm(x)

        if feature_map == 'last':
            return embeddings, x

        logits = "" if self.classifier == None else self.classifier(x)

        if feature_map == 'attention':
            return logits, embeddings

        return logits, x

    def xvector(self, x, embedding_type='near'):
        x = self.input_mask(x)

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        if self.fast:
            x = self.maxpool(x)
        x = self.layer1(x)

        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.layer2(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        x = self.layer3(x)

        if self.layers[3] != 0:
            x = self.conv4(x)
            x = self.bn4(x)
            x = self.relu(x)
            x = self.layer4(x)

        if self.dropout_p > 0:
            x = self.dropout(x)

        x = self.avgpool(x)
        if self.encoder != None:
            x = self.encoder(x)

        x = x.view(x.size(0), -1)
        # x = self.fc1(x)
        if embedding_type == 'near':
            embeddings = self.fc[0](x)
        else:
            embeddings = self.fc(x)

        return "", embeddings


# previoud version for test
# class LocalResNet(nn.Module):
#     """
#     Define the ResNets model with A-softmax and AM-softmax loss.
#     Added dropout as https://github.com/nagadomi/kaggle-cifar10-torch7 after average pooling and fc layer.
#     """
#
#     def __init__(self, embedding_size, num_classes,
#                  input_dim=161, block=BasicBlock,
#                  resnet_size=8, channels=[64, 128, 256], dropout_p=0.,
#                  inst_norm=False, alpha=12, stride=2, transform=False,
#                  avg_size=4, kernal_size=5, padding=2, **kwargs):
#
#         super(LocalResNet, self).__init__()
#         resnet_type = {8: [1, 1, 1, 0],
#                        10: [1, 1, 1, 1],
#                        18: [2, 2, 2, 2],
#                        34: [3, 4, 6, 3],
#                        50: [3, 4, 6, 3],
#                        101: [3, 4, 23, 3]}
#
#         layers = resnet_type[resnet_size]
#         self.alpha = alpha
#         self.layers = layers
#         self.dropout_p = dropout_p
#         self.transform = transform
#
#         self.embedding_size = embedding_size
#         # self.relu = nn.LeakyReLU()
#         self.relu = nn.ReLU(inplace=True)
#         self.inst_norm = inst_norm
#         self.inst_layer = nn.InstanceNorm1d(input_dim)
#
#         self.inplanes = channels[0]
#         self.conv1 = nn.Conv2d(1, channels[0], kernel_size=(5, 5), stride=stride, padding=(3, 2))
#         self.bn1 = nn.BatchNorm2d(channels[0])
#         self.maxpool = nn.MaxPool2d(kernel_size=(3, 1), stride=(2, 1), padding=(1, 0))
#
#         self.layer1 = self._make_layer(block, channels[0], layers[0])
#
#         self.inplanes = channels[1]
#         self.conv2 = nn.Conv2d(channels[0], channels[1], kernel_size=kernal_size, stride=2,
#                                padding=padding, bias=False)
#         self.bn2 = nn.BatchNorm2d(channels[1])
#         self.layer2 = self._make_layer(block, channels[1], layers[1])
#
#         self.inplanes = channels[2]
#         self.conv3 = nn.Conv2d(channels[1], channels[2], kernel_size=kernal_size, stride=2,
#                                padding=padding, bias=False)
#         self.bn3 = nn.BatchNorm2d(channels[2])
#         self.layer3 = self._make_layer(block, channels[2], layers[2])
#
#         if layers[3] != 0:
#             assert len(channels) == 4
#             self.inplanes = channels[3]
#             self.conv4 = nn.Conv2d(channels[2], channels[3], kernel_size=kernal_size, stride=2,
#                                    padding=padding, bias=False)
#             self.bn4 = nn.BatchNorm2d(channels[3])
#             self.layer4 = self._make_layer(block=block, planes=channels[3], blocks=layers[3])
#
#         self.dropout = nn.Dropout(self.dropout_p)
#         self.avg_pool = nn.AdaptiveAvgPool2d((1, avg_size))
#
#         self.fc = nn.Sequential(
#             nn.Linear(self.inplanes * avg_size, embedding_size),
#             nn.BatchNorm1d(embedding_size)
#         )
#
#         if self.transform:
#             self.trans_layer = nn.Sequential(
#                 nn.Linear(embedding_size, embedding_size, bias=False),
#                 nn.BatchNorm1d(embedding_size),
#                 nn.ReLU()
#             )
#
#         # self.fc = nn.Linear(self.inplanes * avg_size, embedding_size)
#         self.classifier = nn.Linear(self.embedding_size, num_classes)
#
#         for m in self.modules():  # 对于各层参数的初始化
#             if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
#                 # n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
#                 # m.weight.data.normal_(0, math.sqrt(2. / n))
#                 nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
#             elif isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.GroupNorm)):  # weight设置为1，bias为0
#                 m.weight.data.fill_(1)
#                 m.bias.data.zero_()
#
#     def l2_norm(self, input, alpha=1.0):
#         # alpha = log(p * ( class -2) / (1-p))
#         input_size = input.size()
#         buffer = torch.pow(input, 2)
#
#         normp = torch.sum(buffer, 1).add_(1e-12)
#         norm = torch.sqrt(normp)
#
#         _output = torch.div(input, norm.view(-1, 1).expand_as(input))
#         output = _output.view(input_size)
#         # # # input = input.renorm(p=2, dim=1, maxnorm=1.0)
#         # norm = input.norm(p=2, dim=1, keepdim=True).add(1e-14)
#         # output = input / norm
#
#         return output * alpha
#
#     def _make_layer(self, block, planes, blocks, stride=1):
#         downsample = None
#         if stride != 1 or self.inplanes != planes * block.expansion:
#             downsample = nn.Sequential(
#                 conv1x1(self.inplanes, planes * block.expansion, stride),
#                 nn.BatchNorm2d(planes * block.expansion),
#             )
#
#         layers = []
#         layers.append(block(self.inplanes, planes, stride, downsample))
#         self.inplanes = planes * block.expansion
#         for _ in range(1, blocks):
#             layers.append(block(self.inplanes, planes))
#
#         return nn.Sequential(*layers)
#
#     def forward(self, x):
#         if self.inst_norm:
#             x = x.squeeze(1).transpose(1, 2)
#             x = self.inst_layer(x)
#             x = x.transpose(1, 2).unsqueeze(1)
#
#             # x = x - torch.mean(x, dim=-2, keepdim=True)
#
#         x = self.conv1(x)
#         x = self.bn1(x)
#         x = self.relu(x)
#         x = self.maxpool(x)
#
#         x = self.layer1(x)
#
#         x = self.conv2(x)
#         x = self.bn2(x)
#         x = self.relu(x)
#         x = self.layer2(x)
#
#         x = self.conv3(x)
#         x = self.bn3(x)
#         x = self.relu(x)
#         x = self.layer3(x)
#
#         if self.layers[3] != 0:
#             x = self.conv4(x)
#             x = self.bn4(x)
#             x = self.relu(x)
#             x = self.layer4(x)
#
#         if self.dropout_p > 0:
#             x = self.dropout(x)
#
#         # if self.statis_pooling:
#         #     mean_x = self.avg_pool(x)
#         #     mean_x = mean_x.view(mean_x.size(0), -1)
#         #
#         #     std_x = self.std_pool(x)
#         #     std_x = std_x.view(std_x.size(0), -1)
#         #
#         #     x = torch.cat((mean_x, std_x), dim=1)
#         #
#         # else:
#         # print(x.shape)
#         x = self.avg_pool(x)
#         x = x.view(x.size(0), -1)
#
#         x = self.fc(x)
#         if self.transform == True:
#             x += self.trans_layer(x)
#             t_x = self.trans_layer(x)
#             x = t_x + x
#
#         if self.alpha:
#             x = self.l2_norm(x, alpha=self.alpha)
#
#         logits = self.classifier(x)
#
#         return logits, x


class DomainNet(nn.Module):
    """
    Define the ResNets model with A-softmax and AM-softmax loss.
    Added dropout as https://github.com/nagadomi/kaggle-cifar10-torch7 after average pooling and fc layer.
    """

    def __init__(self, model, embedding_size, num_classes_a, num_classes_b, **kwargs):

        super(DomainNet, self).__init__()

        self.xvectors = model
        self.embedding_size = embedding_size

        # self.grl = GRL(lambda_=0.)
        self.classifier_spk = nn.Linear(embedding_size, num_classes_a)
        self.classifier_dom = nn.Sequential(
            RevGradLayer(),
            nn.Linear(self.embedding_size, int(self.embedding_size / 2)),
            nn.ReLU(inplace=True),
            nn.BatchNorm1d(int(self.embedding_size / 2)),
            nn.Linear(int(self.embedding_size/2), num_classes_b),
        )

        for m in self.modules():  # 对于各层参数的初始化
            if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
                # n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                # m.weight.data.normal_(0, math.sqrt(2. / n))
                nn.init.kaiming_normal_(
                    m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.GroupNorm)):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def forward(self, x):
        return self.xvectors(x)

    def classifier(self, embeddings):
        spk_logits = self.classifier_spk(embeddings)
        dom_logits = self.classifier_dom(embeddings)

        return spk_logits, dom_logits


class GradResNet(nn.Module):
    """
    Define the ResNets model with A-softmax and AM-softmax loss.
    Added dropout as https://github.com/nagadomi/kaggle-cifar10-torch7 after average pooling and fc layer.
    """

    def __init__(self, embedding_size, num_classes, block=BasicBlock, input_dim=161,
                 resnet_size=8, channels=[64, 128, 256], dropout_p=0., ince=False, transform=False,
                 inst_norm=False, alpha=12, vad=False, avg_size=4, kernal_size=5, padding=2, **kwargs):

        super(GradResNet, self).__init__()
        resnet_type = {8: [1, 1, 1, 0],
                       10: [1, 1, 1, 1],
                       18: [2, 2, 2, 2],
                       34: [3, 4, 6, 3],
                       50: [3, 4, 6, 3],
                       101: [3, 4, 23, 3]}

        layers = resnet_type[resnet_size]
        self.ince = ince
        self.alpha = alpha
        self.layers = layers
        self.dropout_p = dropout_p
        self.transform = transform

        self.embedding_size = embedding_size
        # self.relu = nn.LeakyReLU()
        self.relu = nn.ReLU(inplace=True)
        self.vad = vad
        if self.vad:
            self.vad_layer = SelfVadPooling(input_dim)

        self.inst_norm = inst_norm
        # self.inst_layer = nn.InstanceNorm1d(input_dim)

        if self.ince:
            self.pre_conv = VarSizeConv(1, 1)
            self.conv1 = nn.Conv2d(
                4, channels[0], kernel_size=5, stride=2, padding=2)
        else:
            self.conv1 = nn.Conv2d(
                1, channels[0], kernel_size=5, stride=2, padding=2)

        self.bn1 = nn.BatchNorm2d(channels[0])
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.inplanes = channels[0]
        self.layer1 = self._make_layer(block, channels[0], layers[0])

        self.inplanes = channels[1]
        self.conv2 = nn.Conv2d(channels[0], channels[1], kernel_size=kernal_size,
                               stride=2, padding=padding, bias=False)
        self.bn2 = nn.BatchNorm2d(channels[1])
        self.layer2 = self._make_layer(block, channels[1], layers[1])

        self.inplanes = channels[2]
        self.conv3 = nn.Conv2d(channels[1], channels[2], kernel_size=kernal_size,
                               stride=2, padding=padding, bias=False)
        self.bn3 = nn.BatchNorm2d(channels[2])
        self.layer3 = self._make_layer(block, channels[2], layers[2])

        if layers[3] != 0:
            assert len(channels) == 4
            self.inplanes = channels[3]
            self.conv4 = nn.Conv2d(channels[2], channels[3], kernel_size=kernal_size, stride=2,
                                   padding=padding, bias=False)
            self.bn4 = nn.BatchNorm2d(channels[3])
            self.layer4 = self._make_layer(
                block=block, planes=channels[3], blocks=layers[3])

        self.dropout = nn.Dropout(self.dropout_p)
        self.avg_pool = nn.AdaptiveAvgPool2d((1, avg_size))

        if self.transform:
            self.trans_layer = nn.Sequential(
                nn.Linear(embedding_size, embedding_size, bias=False),
                nn.BatchNorm1d(embedding_size),
                nn.ReLU()
            )

        self.fc = nn.Sequential(
            nn.Linear(self.inplanes * avg_size, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )

        # self.fc = nn.Linear(self.inplanes * avg_size, embedding_size)
        self.classifier = nn.Linear(self.embedding_size, num_classes)

        for m in self.modules():  # 对于各层参数的初始化
            if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
                # n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                # m.weight.data.normal_(0, math.sqrt(2. / n))
                nn.init.kaiming_normal_(
                    m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.GroupNorm)):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def l2_norm(self, input, alpha=1.0):
        # alpha = log(p * (class -2) / (1-p))
        input_size = input.size()
        buffer = torch.pow(input, 2)

        normp = torch.sum(buffer, 1).add_(1e-12)
        norm = torch.sqrt(normp)

        _output = torch.div(input, norm.view(-1, 1).expand_as(input))
        output = _output.view(input_size)
        # # # input = input.renorm(p=2, dim=1, maxnorm=1.0)
        # norm = input.norm(p=2, dim=1, keepdim=True).add(1e-14)
        # output = input / norm

        return output * alpha

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        if self.vad:
            x = self.vad_layer(x)

        x = torch.log(x)

        if self.inst_norm:
            # x = self.inst_layer(x)
            x = x - torch.mean(x, dim=-2, keepdim=True)

        if self.ince:
            x = self.pre_conv(x)

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        # x = self.maxpool(x)

        x = self.layer1(x)

        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.layer2(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        x = self.layer3(x)

        if self.layers[3] != 0:
            x = self.conv4(x)
            x = self.bn4(x)
            x = self.relu(x)
            x = self.layer4(x)

        if self.dropout_p > 0:
            x = self.dropout(x)

        # if self.statis_pooling:
        #     mean_x = self.avg_pool(x)
        #     mean_x = mean_x.view(mean_x.size(0), -1)
        #
        #     std_x = self.std_pool(x)
        #     std_x = std_x.view(std_x.size(0), -1)
        #
        #     x = torch.cat((mean_x, std_x), dim=1)
        #
        # else:
        # print(x.shape)
        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)

        x = self.fc(x)
        if self.transform:
            t_x = self.trans_layer(x)
            x = t_x + x

        if self.alpha:
            x = self.l2_norm(x, alpha=self.alpha)

        logits = self.classifier(x)

        return logits, x


class TimeFreqResNet(nn.Module):
    """
    Define the ResNets model with A-softmax and AM-softmax loss.
    Added dropout as https://github.com/nagadomi/kaggle-cifar10-torch7 after average pooling and fc layer.
    """

    def __init__(self, embedding_size, num_classes, block=BasicBlock, input_dim=161,
                 resnet_size=8, channels=[64, 128, 256], dropout_p=0., ince=False,
                 inst_norm=False, alpha=12, vad=False, avg_size=4, kernal_size=5, padding=2, **kwargs):

        super(TimeFreqResNet, self).__init__()
        resnet_type = {8: [1, 1, 1, 0],
                       10: [1, 1, 1, 1],
                       18: [2, 2, 2, 2],
                       34: [3, 4, 6, 3],
                       50: [3, 4, 6, 3],
                       101: [3, 4, 23, 3]}

        layers = resnet_type[resnet_size]
        self.ince = ince
        self.alpha = alpha
        self.layers = layers
        self.dropout_p = dropout_p

        self.embedding_size = embedding_size
        # self.relu = nn.LeakyReLU()
        self.relu = nn.ReLU(inplace=True)
        self.vad = vad
        if self.vad:
            self.vad_layer = SelfVadPooling(input_dim)

        self.inst_norm = inst_norm
        # self.inst_layer = nn.InstanceNorm1d(input_dim)

        self.conv1 = nn.Sequential(nn.Conv2d(1, channels[0], kernel_size=(5, 1), stride=(2, 1), padding=(2, 0)),
                                   nn.BatchNorm2d(channels[0]),
                                   nn.Conv2d(channels[0], channels[0], kernel_size=(1, 5), stride=(1, 2),
                                             padding=(0, 2)),
                                   )

        self.bn1 = nn.BatchNorm2d(channels[0])
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.inplanes = channels[0]
        self.layer1 = self._make_layer(block, channels[0], layers[0])

        self.inplanes = channels[1]

        # self.conv2 = nn.Conv2d(channels[0], channels[1], kernel_size=kernal_size,
        #                        stride=2, padding=padding, bias=False)
        self.conv2 = nn.Sequential(
            nn.Conv2d(channels[0], channels[1], kernel_size=(
                5, 1), stride=(2, 1), padding=(2, 0)),
            nn.BatchNorm2d(channels[1]),
            nn.Conv2d(channels[1], channels[1], kernel_size=(1, 5), stride=(1, 2),
                      padding=(0, 2)),
        )

        self.bn2 = nn.BatchNorm2d(channels[1])
        self.layer2 = self._make_layer(block, channels[1], layers[1])

        self.inplanes = channels[2]
        # self.conv3 = nn.Conv2d(channels[1], channels[2], kernel_size=kernal_size,
        #                        stride=2, padding=padding, bias=False)
        self.conv3 = nn.Sequential(
            nn.Conv2d(channels[1], channels[2], kernel_size=(
                5, 1), stride=(2, 1), padding=(2, 0)),
            nn.BatchNorm2d(channels[2]),
            nn.Conv2d(channels[2], channels[2], kernel_size=(
                1, 5), stride=(1, 2), padding=(0, 2)),
        )

        self.bn3 = nn.BatchNorm2d(channels[2])
        self.layer3 = self._make_layer(block, channels[2], layers[2])

        if layers[3] != 0:
            assert len(channels) == 4
            self.inplanes = channels[3]
            self.conv4 = nn.Conv2d(channels[2], channels[3], kernel_size=kernal_size, stride=2,
                                   padding=padding, bias=False)
            self.bn4 = nn.BatchNorm2d(channels[3])
            self.layer4 = self._make_layer(
                block=block, planes=channels[3], blocks=layers[3])

        self.dropout = nn.Dropout(self.dropout_p)
        self.avg_pool = nn.AdaptiveAvgPool2d((1, avg_size))

        self.fc = nn.Sequential(
            nn.Linear(self.inplanes * avg_size, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )
        # self.fc = nn.Linear(self.inplanes * avg_size, embedding_size)
        self.classifier = nn.Linear(self.embedding_size, num_classes)

        for m in self.modules():  # 对于各层参数的初始化
            if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
                # n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                # m.weight.data.normal_(0, math.sqrt(2. / n))
                nn.init.kaiming_normal_(
                    m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.GroupNorm)):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def l2_norm(self, input, alpha=1.0):
        # alpha = log(p * (class -2) / (1-p))
        input_size = input.size()
        buffer = torch.pow(input, 2)

        normp = torch.sum(buffer, 1).add_(1e-12)
        norm = torch.sqrt(normp)

        _output = torch.div(input, norm.view(-1, 1).expand_as(input))
        output = _output.view(input_size)

        return output * alpha

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        if self.vad:
            x = self.vad_layer(x)

        x = torch.log(x)

        if self.inst_norm:
            # x = self.inst_layer(x)
            x = x - torch.mean(x, dim=-2, keepdim=True)

        if self.ince:
            x = self.pre_conv(x)

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        # x = self.maxpool(x)

        x = self.layer1(x)

        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.layer2(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        x = self.layer3(x)

        if self.layers[3] != 0:
            x = self.conv4(x)
            x = self.bn4(x)
            x = self.relu(x)
            x = self.layer4(x)

        if self.dropout_p > 0:
            x = self.dropout(x)

        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)

        x = self.fc(x)
        if self.alpha:
            x = F.self.l2_norm(x, alpha=self.alpha)

        logits = self.classifier(x)

        return logits, x


class MultiResNet(nn.Module):
    """
    Define the ResNets model with A-softmax and AM-softmax loss.
    Added dropout as https://github.com/nagadomi/kaggle-cifar10-torch7 after average pooling and fc layer.
    """

    def __init__(self, embedding_size, num_classes_a, num_classes_b, block=BasicBlock, input_dim=161,
                 resnet_size=8, channels=[64, 128, 256], dropout_p=0., stride=2, fast=False,
                 inst_norm=False, alpha=12, input_norm='None', transform=False,
                 avg_size=4, kernal_size=5, padding=2, mask='None', mask_len=25, **kwargs):

        super(MultiResNet, self).__init__()
        resnet_type = {8: [1, 1, 1, 0],
                       10: [1, 1, 1, 1],
                       18: [2, 2, 2, 2],
                       34: [3, 4, 6, 3],
                       50: [3, 4, 6, 3],
                       101: [3, 4, 23, 3]}

        layers = resnet_type[resnet_size]
        self.alpha = alpha
        self.layers = layers
        self.dropout_p = dropout_p
        self.embedding_size = embedding_size
        self.relu = nn.ReLU(inplace=True)
        self.transform = transform
        self.fast = fast
        self.input_norm = input_norm
        self.mask = mask

        if input_norm == 'Instance':
            self.inst_layer = nn.InstanceNorm1d(input_dim)
        elif input_norm == 'Mean':
            self.inst_layer = Mean_Norm()
        elif input_norm == 'MeanStd':
            self.inst_layer = MeanStd_Norm()
        else:
            self.inst_layer = None

        if self.mask == "time":
            self.maks_layer = TimeMaskLayer(mask_len=mask_len)
        elif self.mask == "freq":
            self.mask_layer = FreqMaskLayer(mask_len=mask_len)
        elif self.mask == "time_freq":
            self.mask_layer = nn.Sequential(
                TimeMaskLayer(mask_len=mask_len),
                FreqMaskLayer(mask_len=mask_len)
            )
        else:
            self.mask_layer = None

        self.inplanes = channels[0]
        self.conv1 = nn.Conv2d(
            1, channels[0], kernel_size=5, stride=stride, padding=2, bias=False)
        self.bn1 = nn.BatchNorm2d(channels[0])

        # fast v3
        if self.fast:
            self.maxpool = nn.Sequential(
                nn.Conv2d(channels[0], channels[0], kernel_size=1, stride=1),
                nn.ReLU(),
                nn.BatchNorm2d(channels[0]),
                nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
            )
        else:
            self.maxpool = None

        # self.maxpool = nn.MaxPool2d(kernel_size=(3, 1), stride=(2, 1), padding=1)
        self.layer1 = self._make_layer(block, channels[0], layers[0])

        self.inplanes = channels[1]
        self.conv2 = nn.Conv2d(channels[0], channels[1], kernel_size=kernal_size, stride=2,
                               padding=padding, bias=False)
        self.bn2 = nn.BatchNorm2d(channels[1])
        self.layer2 = self._make_layer(block, channels[1], layers[1])

        self.inplanes = channels[2]
        self.conv3 = nn.Conv2d(channels[1], channels[2], kernel_size=kernal_size, stride=2,
                               padding=padding, bias=False)
        self.bn3 = nn.BatchNorm2d(channels[2])
        self.layer3 = self._make_layer(block, channels[2], layers[2])

        if layers[3] != 0:
            assert len(channels) == 4
            self.inplanes = channels[3]
            self.conv4 = nn.Conv2d(channels[2], channels[3], kernel_size=kernal_size, stride=2,
                                   padding=padding, bias=False)
            self.bn4 = nn.BatchNorm2d(channels[3])
            self.layer4 = self._make_layer(
                block=block, planes=channels[3], blocks=layers[3])

        self.dropout = nn.Dropout(self.dropout_p)
        self.avg_pool = nn.AdaptiveAvgPool2d((1, avg_size))

        self.fc = nn.Sequential(
            nn.Linear(self.inplanes * avg_size, self.embedding_size),
            nn.BatchNorm1d(self.embedding_size)
        )
        if self.transform == 'Linear':
            self.trans_layer = nn.Sequential(
                nn.Linear(embedding_size, embedding_size),
                nn.ReLU(),
                nn.BatchNorm1d(embedding_size))
        elif self.transform == 'GhostVLAD':
            self.trans_layer = GhostVLAD_v2(
                num_clusters=8, gost=1, dim=embedding_size, normalize_input=True)
        else:
            self.trans_layer = None
        if self.alpha:
            self.l2_norm = L2_Norm(self.alpha)

        self.classifier_a = nn.Linear(self.embedding_size, num_classes_a)
        self.classifier_b = nn.Linear(self.embedding_size, num_classes_b)

        for m in self.modules():  # 对于各层参数的初始化
            if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
                # n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                # m.weight.data.normal_(0, math.sqrt(2. / n))
                nn.init.kaiming_normal_(
                    m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.GroupNorm)):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        tuple_input = False
        if isinstance(x, tuple):
            tuple_input = True
            size_a = len(x[0])
            x = torch.cat(x, dim=0)

        if self.inst_layer != None:
            x = self.inst_layer(x)

        if self.mask_layer != None:
            x = self.mask_layer(x)

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        if self.maxpool != None:
            x = self.maxpool(x)

        x = self.layer1(x)

        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.layer2(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        x = self.layer3(x)

        if self.layers[3] != 0:
            x = self.conv4(x)
            x = self.bn4(x)
            x = self.relu(x)
            x = self.layer4(x)

        if self.dropout_p > 0:
            x = self.dropout(x)

        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)

        embeddings = self.fc(x)

        if self.trans_layer != None:
            embeddings = self.trans_layer(embeddings)

        if self.alpha:
            embeddings = self.l2_norm(embeddings)
            # embeddings = self.l2_norm(embeddings, alpha=self.alpha)

        if tuple_input:
            embeddings_a = embeddings[:size_a]
            embeddings_b = embeddings[size_a:]

            logits_a = self.classifier_a(embeddings_a)
            logits_b = self.classifier_b(embeddings_b)

            return (logits_a, logits_b), (embeddings_a, embeddings_b)
        else:
            return '', embeddings

    # def cls_forward(self, a, b):
    #
    #     logits_a = self.classifier_a(a)
    #     logits_b = self.classifier_b(b)
    #
    #     return logits_a, logits_b
