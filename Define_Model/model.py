#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: model.py
@Overview: The deep speaker model is not entirely the same as ResNets, as there are convolutional layers between blocks.
"""

import math

import torch
import torch.nn as nn
import torchaudio.transforms
from torch.autograd import Function
from torch.autograd import Variable
from torch.nn import CosineSimilarity

from Define_Model.FilterLayer import FreqTimeReweightLayer, FrequencyReweightLayer, MeanStd_Norm, Mean_Norm, Inst_Norm, SlideMean_Norm, SparseFbankLayer, SpectrogramLayer, fDLR, MelFbankLayer
from Define_Model.Loss.SoftmaxLoss import AngleLinear
from Define_Model.FilterLayer import TimeMaskLayer, FreqMaskLayer, SqueezeExcitation, GAIN, fBLayer, fBPLayer, fLLayer, \
    RevGradLayer, DropweightLayer, DropweightLayer_v2, DropweightLayer_v3, GaussianNoiseLayer, MusanNoiseLayer, \
    AttentionweightLayer, TimeFreqMaskLayer, \
    AttentionweightLayer_v2, AttentionweightLayer_v3, AttentionweightLayer_v0

def get_layer_param(model):
    return sum([torch.numel(param) for param in model.parameters()])


def get_activation(activation):
    if activation == 'relu':
        nonlinearity = nn.ReLU
    elif activation in ['leakyrelu', 'leaky_relu']:
        nonlinearity = nn.LeakyReLU
    elif activation == 'prelu':
        nonlinearity = nn.PReLU

    return nonlinearity


def get_filter_layer(filter: str, input_dim: int, sr: int, feat_dim: int, exp: bool, filter_fix: bool,
                     stretch_ratio: list = [1.0], init_weight: str = 'mel', win_length=int(0.025*16000),
                     nfft=512):
    if filter == 'fDLR':
        filter_layer = fDLR(input_dim=input_dim, sr=sr, num_filter=feat_dim, exp=exp, filter_fix=filter_fix)
    elif filter == 'fBLayer':
        filter_layer = fBLayer(input_dim=input_dim, sr=sr, num_filter=feat_dim, exp=exp, filter_fix=filter_fix)
    elif filter == 'fBPLayer':
        filter_layer = fBPLayer(input_dim=input_dim, sr=sr, num_filter=feat_dim, exp=exp,
                                filter_fix=filter_fix)
    elif filter == 'fLLayer':
        filter_layer = fLLayer(input_dim=input_dim, num_filter=feat_dim, exp=exp)
    elif filter == 'Avg':
        filter_layer = nn.AvgPool2d(kernel_size=(1, 7), stride=(1, 3))
    elif filter == 'fbank':
        filter_layer = MelFbankLayer(sr=sr, num_filter=feat_dim, stretch_ratio=stretch_ratio)
    elif filter == 'spect':
        filter_layer = SpectrogramLayer(sr=sr, stretch_ratio=stretch_ratio, 
                                        win_length=win_length, n_fft=nfft)
    elif filter == 'sparse':
        filter_layer = SparseFbankLayer(sr=sr, num_filter=feat_dim, stretch_ratio=stretch_ratio,
                                        init_weight=init_weight)
    else:
        filter_layer = None

    return filter_layer


def get_input_norm(input_norm: str, input_dim=None):
    if input_norm == 'Mean':
        inst_layer = Mean_Norm()
    elif input_norm == 'SMean':
        inst_layer = SlideMean_Norm()
    elif input_norm == 'Mstd':
        inst_layer = MeanStd_Norm()
    elif input_norm == 'Inst':
        inst_layer = Inst_Norm(dim=input_dim)
    else:
        inst_layer = None

    return inst_layer


def get_mask_layer(mask: str, mask_len: list, input_dim: int, init_weight: str,
                   weight_p: float, scale: float, weight_norm: str):
    if mask == "time":
        maks_layer = TimeMaskLayer(mask_len=mask_len[0])
    elif mask == "freq":
        maks_layer = FreqMaskLayer(mask_len=mask_len[0])
    elif mask == "both":
        mask_layer = TimeFreqMaskLayer(mask_len=mask_len)
    elif mask == "time_freq":
        mask_layer = nn.Sequential(
            TimeMaskLayer(mask_len=mask_len[0]),
            FreqMaskLayer(mask_len=mask_len[1])
        )
    elif mask == 'attention0':
        mask_layer = AttentionweightLayer_v0(input_dim=input_dim, weight=init_weight,
                                             weight_norm=weight_norm)
    elif mask == 'attention':
        mask_layer = AttentionweightLayer(input_dim=input_dim, weight=init_weight,
                                          weight_norm=weight_norm)
    elif mask == 'attention2':
        mask_layer = AttentionweightLayer_v2(input_dim=input_dim, weight=init_weight,
                                             weight_norm=weight_norm)
    elif mask == 'attention3':
        mask_layer = AttentionweightLayer_v3(input_dim=input_dim, weight=init_weight)
    elif mask == 'drop':
        mask_layer = DropweightLayer(input_dim=input_dim, dropout_p=weight_p,
                                     weight=init_weight, scale=scale)
    elif mask == 'drop2':
        mask_layer = DropweightLayer_v2(input_dim=input_dim, dropout_p=weight_p,
                                        weight=init_weight, scale=scale)
    elif mask == 'drop3':
        mask_layer = DropweightLayer_v3(input_dim=input_dim, dropout_p=weight_p,
                                        weight=init_weight, scale=scale)
    elif mask == 'frl':
        mask_layer = FrequencyReweightLayer(input_dim=input_dim)
    elif mask == 'frrl':
        mask_layer = FreqTimeReweightLayer(input_dim=input_dim)
    else:
        mask_layer = None

    return mask_layer


class ReLU20(nn.Hardtanh):

    def __init__(self, inplace=False):
        super(ReLU20, self).__init__(0, 20, inplace)

    def __repr__(self):
        inplace_str = 'inplace' if self.inplace else ''
        return self.__class__.__name__ + ' (' \
               + inplace_str + ')'

def conv3x3(in_planes, out_planes, stride=1):
    "3x3 convolution with padding"
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)

class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = ReLU20(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class myResNet(nn.Module):

    def __init__(self, block, layers, num_classes=1000):

        super(myResNet, self).__init__()

        self.relu = ReLU20(inplace=True)
        self.inplanes = 64
        self.conv1 = nn.Conv2d(1, 64, kernel_size=5, stride=2, padding=2,bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, layers[0])

        self.inplanes = 128
        self.conv2 = nn.Conv2d(64, 128, kernel_size=5, stride=2, padding=2,bias=False)
        self.bn2 = nn.BatchNorm2d(128)
        self.layer2 = self._make_layer(block, 128, layers[1])
        self.inplanes = 256
        self.conv3 = nn.Conv2d(128, 256, kernel_size=5, stride=2, padding=2,bias=False)
        self.bn3 = nn.BatchNorm2d(256)
        self.layer3 = self._make_layer(block, 256, layers[2])
        self.inplanes = 512
        self.conv4 = nn.Conv2d(256, 512, kernel_size=5, stride=2, padding=2,bias=False)
        self.bn4 = nn.BatchNorm2d(512)
        self.layer4 = self._make_layer(block, 512, layers[3])

        
        self.avgpool = nn.AdaptiveAvgPool2d((4, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):

        layers = []
        layers.append(block(self.inplanes, planes, stride))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
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
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x


class DeepSpeakerModel(nn.Module):
    def __init__(self, resnet_size, embedding_size, num_classes, feature_dim=64):
        super(DeepSpeakerModel, self).__init__()
        resnet_type = {10:[1, 1, 1, 1],
                       18:[2, 2, 2, 2],
                       34:[3, 4, 6, 3],
                       50:[3, 4, 6, 3],
                       101:[3, 4, 23, 3]}
        self.embedding_size = embedding_size
        self.resnet_size = resnet_size
        self.num_classes = num_classes

        self.model = myResNet(BasicBlock, resnet_type[resnet_size])
        if feature_dim == 64:
            self.model.fc = nn.Linear(512 * 4, self.embedding_size)
        elif feature_dim == 40:
            self.model.fc = nn.Linear(256 * 5, self.embedding_size)

        #self.model.classifier = nn.Linear(self.embedding_size, num_classes)
        #self.norm = nn.BatchNorm1d(512)
        self.model.classifier = nn.Linear(self.embedding_size, num_classes)

    def l2_norm(self,input):
        input_size = input.size()
        buffer = torch.pow(input, 2)

        normp = torch.sum(buffer, 1).add_(1e-10)
        norm = torch.sqrt(normp)

        _output = torch.div(input, norm.view(-1, 1).expand_as(input))

        output = _output.view(input_size)

        return output

    def forward(self, x):

        x = self.model.conv1(x)
        x = self.model.bn1(x)
        x = self.model.relu(x)
        x = self.model.layer1(x)

        x = self.model.conv2(x)
        x = self.model.bn2(x)
        x = self.model.relu(x)
        x = self.model.layer2(x)

        x = self.model.conv3(x)
        x = self.model.bn3(x)
        x = self.model.relu(x)
        x = self.model.layer3(x)

        x = self.model.conv4(x)
        x = self.model.bn4(x)
        x = self.model.relu(x)
        x = self.model.layer4(x)

        # print(x.shape)
        x = self.model.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.model.fc(x)
        x = self.l2_norm(x)

        # Multiply by alpha = 10 as suggested in https://arxiv.org/pdf/1703.09507.pdf
        alpha = 10
        features = x * alpha

        # x = x.resize(int(x.size(0) / 17),17 , 512)
        # self.features =torch.mean(x,dim=1)
        # x = self.model.classifier(features)

        return features

    def forward_classifier(self, x):
        res = self.model.classifier(x)
        return res

class ResSpeakerModel(nn.Module):
    """
    Define the ResNets model with A-softmax and AM-softmax loss.
    """
    def __init__(self, resnet_size, embedding_size, num_classes, feature_dim=64):
        super(ResSpeakerModel, self).__init__()
        resnet_type = {10:[1, 1, 1, 1],
                       18:[2, 2, 2, 2],
                       34:[3, 4, 6, 3],
                       50:[3, 4, 6, 3],
                       101:[3, 4, 23, 3]}
        self.embedding_size = embedding_size

        self.resnet_size = resnet_size
        self.num_classes = num_classes

        self.model = myResNet(BasicBlock, resnet_type[resnet_size])
        if feature_dim == 64:
            self.model.fc = nn.Linear(512 * 4, self.embedding_size)
        elif feature_dim == 40:
            self.model.fc = nn.Linear(256 * 5, self.embedding_size)
        elif feature_dim == 257:
            self.model.fc = nn.Linear(256 * 5, self.embedding_size)

        self.model.classifier = nn.Linear(self.embedding_size, self.num_classes)

        # TAP Encoding Layer
        self.model.encodinglayer = nn.AdaptiveAvgPool2d((1, 512))

        # TODO: SAP, LDE Encoding Layer after the embedding layers
        # SAP Encoding Layer


        self.model.W = torch.nn.Parameter(torch.randn(self.embedding_size, num_classes))
        nn.init.xavier_normal(self.model.W, gain=1)

        # self.model.classifier = nn.Softmax(self.embedding_size, num_classes)
        # self.model.classifier = AngleLinear(self.embedding_size, num_classes)

        # Parameters for a-softmax
        self.gamma = 0
        self.it = 0
        self.LambdaMin = 5.0
        self.LambdaMax = 1500.0
        self.lamb = 1500.0

        # default 4, based on the voxceleb 1, set to 3
        self.m = 4
        self.ce = nn.CrossEntropyLoss()

        # cos(2thera) = 2cos(theta)**2 - 1
        # cos(3thera) = 4cos(theta)**2 - 3cos(theta)
        # cos(4thera) = 8cos(theta)**4 - 2cos(theta)**2 - 1
        self.cos_function = [
            lambda x: x ** 0,
            lambda x: x ** 1,
            lambda x: 2 * x ** 2 - 1,
            lambda x: 4 * x ** 3 - 3 * x,
            lambda x: 8 * x ** 4 - 8 * x ** 2 + 1,
            lambda x: 16 * x ** 5 - 20 * x ** 3 + 5 * x,
        ]

        # Parameters for am-softmax
        # default 0.4, based on the voxceleb1, set to 0.3
        self.margin = 0.4
        self.s = 30

    def l2_norm(self,input):
        input_size = input.size()
        buffer = torch.pow(input, 2)

        normp = torch.sum(buffer, 1).add_(1e-10)
        norm = torch.sqrt(normp)

        _output = torch.div(input, norm.view(-1, 1).expand_as(input))

        output = _output.view(input_size)

        return output

    def forward(self, x):
        # pdb.set_trace()

        x = self.model.conv1(x)
        x = self.model.bn1(x)
        x = self.model.relu(x)
        x = self.model.layer1(x)

        x = self.model.conv2(x)
        x = self.model.bn2(x)
        x = self.model.relu(x)
        x = self.model.layer2(x)

        x = self.model.conv3(x)
        x = self.model.bn3(x)
        x = self.model.relu(x)
        x = self.model.layer3(x)

        x = self.model.conv4(x)
        x = self.model.bn4(x)
        x = self.model.relu(x)
        x = self.model.layer4(x)

        # print(x.s)
        x = self.model.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.model.fc(x)
        self.features = self.l2_norm(x)

        # Multiply by alpha = 10 as suggested in https://arxiv.org/pdf/1703.09507.pdf
        # alpha=10
        # self.features = self.features * alpha
        return self.features

    def forward_classifier(self, x):
        # x = self.forward(x)
        # x = self.encodinglayer(x)
        res = x.mm(self.model.W)
        # res = self.model.classifier(features)
        return res

    def encodinglayer(self, x):
        features = self.model.encodinglayer(x)
        return features

    def AngularSoftmaxLoss(self, x, label):

        self.it += 1
        assert x.size()[0] == label.size()[0]
        # assert features.size()[1] == self.in_feats

        w = self.model.W.renorm(2, 1, 1e-5).mul(1e5)  # [batch, out_planes]
        x_modulus = x.pow(2).sum(1).pow(0.5)  # [batch]
        w_modulus = w.pow(2).sum(0).pow(0.5)  # [out_planes]

        # get w@x=||w||*||x||*cos(theta)
        # w = w.cuda()
        inner_wx = x.mm(w)  # [batch,out_planes]
        cos_theta = (inner_wx / x_modulus.view(-1, 1)) / w_modulus.view(1, -1)
        cos_theta = cos_theta.clamp(-1, 1)

        # get cos(m*theta)
        # TODO: cos_m_theta isn't correct.
        cos_m_theta = self.cos_function[self.m](cos_theta)
        theta = Variable(cos_theta.data.acos())

        # get k, theta is in [ k*pi/m , (k+1)*pi/m ]
        k = (self.m * theta / math.pi).floor()
        minus_one = k * 0 - 1

        # get phi_theta = -1^k*cos(m*theta)-2*k
        phi_theta = (minus_one ** k) * cos_m_theta - 2 * k

        # get cos_x and phi_x
        # cos_x = cos(theta)*||x||
        # phi_x = phi(theta)*||x||
        cos_x = cos_theta * x_modulus.view(-1, 1)
        phi_x = phi_theta * x_modulus.view(-1, 1)

        target = label.view(-1, 1)

        # get one_hot mat
        index = cos_x.data * 0.0  # size=(B,Classnum)
        index.scatter_(1, target.data.view(-1, 1), 1)
        index = index.byte()
        index = Variable(index)

        # set lamb, change the rate of softmax and A-softmax
        self.lamb = max(self.LambdaMin, self.LambdaMax / (1 + 0.1 * self.it))

        # get a-softmax and softmax mat
        output = cos_x * 1
        # output[index] -= cos_x[index]
        # output[index] += phi_x[index]
        output[index] -= (cos_x[index] * 1.0 / (+self.lamb))
        output[index] += (phi_x[index] * 1.0 / (self.lamb))

        # pdb.set_trace()
        # get loss, which is equal to Cross Entropy.
        # logpt = F.log_softmax(output, dim=1)  # [batch,classes_num]
        # logpt = logpt.gather(1, target)  # [batch]
        # pt = logpt.data.exp()
        # torch.mm()
        # loss = -1 * logpt * (1 - pt) ** self.gamma
        # loss = loss.mean()
        loss = self.ce(output, label)

        return loss

    def AMSoftmaxLoss(self, x, label):

        assert x.size()[0] == label.size()[0]
        #assert x.size()[1] == self.in_feats

        # pdb.set_trace()
        x_norm = torch.norm(x, p=2, dim=1, keepdim=True).clamp(min=1e-12)
        x_norm = torch.div(x, x_norm)
        w_norm = torch.norm(self.model.W, p=2, dim=0, keepdim=True).clamp(min=1e-12)
        w_norm = torch.div(self.model.W, w_norm)
        costh = torch.mm(x_norm, w_norm)
        lb_view = label.view(-1, 1)

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()
        delt_costh = torch.zeros(costh.size()).scatter_(1, lb_view.data, self.margin)

        if x.is_cuda:
            delt_costh = Variable(delt_costh.cuda())

        costh_m = costh - delt_costh
        costh_m_s = self.s * costh_m

        loss = self.ce(costh_m_s, label)

        return loss

class ResCNNSpeaker(nn.Module):
    """
    Define the ResNets model with A-softmax and AM-softmax loss.
    Added dropout as https://github.com/nagadomi/kaggle-cifar10-torch7 after average pooling and fc layer.
    """
    def __init__(self, resnet_size, embedding_size, num_classes, block=BasicBlock, feature_dim=64, dropout=False):
        super(ResCNNSpeaker, self).__init__()
        resnet_type = {10:[1, 1, 1, 1],
                       18:[2, 2, 2, 2],
                       34:[3, 4, 6, 3],
                       50:[3, 4, 6, 3],
                       101:[3, 4, 23, 3]}

        layers = resnet_type[resnet_size]

        self.embedding_size = embedding_size
        self.relu = ReLU20(inplace=True)

        self.in_planes = 64
        self.conv1 = nn.Conv2d(1, 64, kernel_size=5, stride=2, padding=2, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, layers[0])

        self.in_planes = 128
        self.conv2 = nn.Conv2d(64, 128, kernel_size=5, stride=2, padding=2, bias=False)
        self.bn2 = nn.BatchNorm2d(128)
        self.layer2 = self._make_layer(block, 128, layers[1])

        self.in_planes = 256
        self.conv3 = nn.Conv2d(128, 256, kernel_size=5, stride=2, padding=2, bias=False)
        self.bn3 = nn.BatchNorm2d(256)
        self.layer3 = self._make_layer(block, 256, layers[2])

        self.in_planes = 512
        self.conv4 = nn.Conv2d(256, 512, kernel_size=5, stride=2, padding=2, bias=False)
        self.bn4 = nn.BatchNorm2d(512)
        self.layer4 = self._make_layer(block, 512, layers[3])

        # self.avg_pool = nn.AdaptiveAvgPool2d([4, 1])
        self.avg_pool = nn.AdaptiveAvgPool2d((4, 1))

        self.fc = nn.Sequential(
            nn.Linear(self.in_planes * 4, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )
        self.classifier = nn.Linear(self.embedding_size, num_classes)

        for m in self.modules():  # 对于各层参数的初始化
            if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm1d):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()

        # self.weight = nn.Parameter(torch.Tensor(embedding_size, num_classes))  # 本层权重
        # self.weight.data.uniform_(-1, 1).renorm_(2, 1, 1e-5).mul_(1e5)  # 初始化权重，在第一维度上做normalize

    def l2_norm(self,input):
        input_size = input.size()
        buffer = torch.pow(input, 2)

        normp = torch.sum(buffer, 1).add_(1e-10)
        norm = torch.sqrt(normp)

        _output = torch.div(input, norm.view(-1, 1).expand_as(input))
        output = _output.view(input_size)

        return output

    def _make_layer(self, block, planes, blocks, stride=1):
        layers = [block(self.in_planes, planes, stride)]
        self.in_planes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.in_planes, planes))
        return nn.Sequential(*layers)


    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.layer1(x)

        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.layer2(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        x = self.layer3(x)

        x = self.conv4(x)
        x = self.bn4(x)
        x = self.relu(x)
        x = self.layer4(x)

        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        x = self.l2_norm(x)
        # Multiply by alpha = 10 as suggested in https://arxiv.org/pdf/1703.09507.pdf
        alpha = 10
        feature = x * alpha

        # ww = self.weight.renorm(2, 1, 1e-5).mul(1e5)  # 方向0上做normalize
        # x_len = feature.pow(2).sum(1).pow(0.5)
        # w_len = ww.pow(2).sum(0).pow(0.5)
        # cos_theta = feature.mm(ww) / x_len.view(-1, 1) / w_len.view(1, -1)
        logits = self.classifier(feature)

        # res = self.model.classifier(features)
        return logits, feature

class SuperficialResCNN(nn.Module):  # 定义resnet
    def __init__(self, embedding_size, layers=[1, 1, 1, 0], block=BasicBlock, n_classes=1000,
                 m=3):  # block类型，embedding大小，分类数，maigin大小
        super(SuperficialResCNN, self).__init__()

        self.embedding_size = embedding_size
        self.relu = ReLU(inplace=True)

        self.in_planes = 64
        self.conv1 = nn.Conv2d(1, 64, kernel_size=5, stride=2, padding=2, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, layers[0])

        self.in_planes = 128
        self.conv2 = nn.Conv2d(64, 128, kernel_size=5, stride=2, padding=2, bias=False)
        self.bn2 = nn.BatchNorm2d(128)
        self.layer2 = self._make_layer(block, 128, layers[1])

        self.in_planes = 256
        self.conv3 = nn.Conv2d(128, 256, kernel_size=5, stride=2, padding=2, bias=False)
        self.bn3 = nn.BatchNorm2d(256)
        self.layer3 = self._make_layer(block, 256, layers[2])

        # self.in_planes = 512
        # self.conv4 = nn.Conv2d(256, 512, kernel_size=5, stride=2, padding=2, bias=False)
        # self.bn4 = nn.BatchNorm2d(512)
        # self.layer4 = self._make_layer(block, 512, layers[3])

        # self.avg_pool = nn.AdaptiveAvgPool2d([4, 1])
        self.avg_pool = nn.AdaptiveAvgPool2d((4, 1))

        self.fc = nn.Sequential(
            nn.Linear(self.in_planes * 4, embedding_size),
            nn.BatchNorm1d(embedding_size)
        )

        # self.W = torch.nn.Parameter(torch.randn(self.embedding_size, n_classes))
        # self.W.data.uniform_(-1, 1).renorm_(2, 1, 1e-5).mul_(1e5)
        # nn.init.xavier_normal(self.W, gain=1)

        self.angle_linear = AngleLinear(in_features=embedding_size, out_features=n_classes, m=m)

        for m in self.modules():  # 对于各层参数的初始化
            if isinstance(m, nn.Conv2d):  # 以2/n的开方为标准差，做均值为0的正态分布
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm1d):  # weight设置为1，bias为0
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        layers = [block(self.in_planes, planes, stride)]
        self.in_planes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.in_planes, planes))
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.layer1(x)

        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.layer2(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        x = self.layer3(x)

        # x = self.conv4(x)
        # x = self.bn4(x)
        # x = self.relu(x)
        # x = self.layer4(x)

        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        # x = x * self.alpha

        logit = self.angle_linear(x)
        return logit, x  # 返回倒数第二层


# convert dict attribute to object attribute
class AttrDict(dict):
    """Dict as attribute trick.
    """

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
        for key in self.__dict__:
            value = self.__dict__[key]
            if isinstance(value, dict):
                self.__dict__[key] = AttrDict(value)
            elif isinstance(value, list):
                if isinstance(value[0], dict):
                    self.__dict__[key] = [AttrDict(item) for item in value]
                else:
                    self.__dict__[key] = value

    def yaml(self):
        """Convert object to yaml dict and return.
        """
        yaml_dict = {}
        for key in self.__dict__:
            value = self.__dict__[key]
            if isinstance(value, AttrDict):
                yaml_dict[key] = value.yaml()
            elif isinstance(value, list):
                if isinstance(value[0], AttrDict):
                    new_l = []
                    for item in value:
                        new_l.append(item.yaml())
                    yaml_dict[key] = new_l
                else:
                    yaml_dict[key] = value
            else:
                yaml_dict[key] = value
        return yaml_dict

    def __repr__(self):
        """Print all variables.
        """
        ret_str = []
        for key in self.__dict__:
            value = self.__dict__[key]
            if isinstance(value, AttrDict):
                ret_str.append('{}:'.format(key))
                child_ret_str = value.__repr__().split('\n')
                for item in child_ret_str:
                    ret_str.append('    ' + item)
            elif isinstance(value, list):
                if isinstance(value[0], AttrDict):
                    ret_str.append('{}:'.format(key))
                    for item in value:
                        # treat as AttrDict above
                        child_ret_str = item.__repr__().split('\n')
                        for item in child_ret_str:
                            ret_str.append('    ' + item)
                else:
                    ret_str.append('{}: {}'.format(key, value))
            else:
                ret_str.append('{}: {}'.format(key, value))
        return '\n'.join(ret_str)
