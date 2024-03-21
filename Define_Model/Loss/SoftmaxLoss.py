#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: SoftmaxLoss.py
@Time: 2019/8/5 下午5:29
@Overview:
"AngleLinear" and "AngleSoftmaxLoss" Fork from
https://github.com/woshildh/a-softmax_pytorch/blob/master/a_softmax.py.

"AMSoftmax" Fork from
https://github.com/CoinCheung/pytorch-loss/blob/master/amsoftmax.py

"AngularSoftmax" is completed based on the two loss.

"Center Loss" is based on https://github.com/KaiyangZhou/pytorch-center-loss/blob/master/center_loss.py
"""
import math
import pdb
from random import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable

from Define_Model.Loss.LossFunction import LabelSmoothing, FocalLoss

__all__ = ["AngleLinear", "AngleSoftmaxLoss"]

from Define_Model.Loss.LossFunction import LabelSmoothing


class AngleLinear(nn.Module):  # 定义最后一层
    def __init__(self, in_features, out_features, m=3, phiflag=True):  # 输入特征维度，输出特征维度，margin超参数
        super(AngleLinear, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(torch.Tensor(
            in_features, out_features))  # 本层权重
        # 初始化权重，在第一维度上做normalize
        self.weight.data.uniform_(-1, 1).renorm_(2, 1, 1e-5).mul_(1e5)
        self.m = m
        self.phiflag = phiflag

    def forward(self, x):  # 前向过程，输入x
        # ww = w.renorm(2, 1, 1e-5).mul(1e5)#方向0上做normalize
        x_modulus = x.norm(p=2, dim=1, keepdim=True)
        w_modulus = self.weight.norm(p=2, dim=0, keepdim=True)

        # x_len = x.pow(2).sum(1).pow(0.5)
        # w_len = ww.pow(2).sum(0).pow(0.5)

        cos_theta = x.mm(self.weight)
        cos_theta = cos_theta / x_modulus / w_modulus
        cos_theta = cos_theta.clamp(-1, 1)

        if self.phiflag:
            cos_m_theta = self.mlambda[self.m](
                cos_theta)  # 由m和/cos(/theta)得到cos_m_theta
            theta = Variable(cos_theta.data.acos())
            k = (self.m*theta/3.14159265).floor()
            n_one = k*0.0 - 1
            phi_theta = (n_one**k) * cos_m_theta - 2*k  # 得到/phi(/theta)
        else:
            theta = cos_theta.acos()  # acos得到/theta
            phi_theta = self.myphi(theta, self.m)  # 得到/phi(/theta)
            phi_theta = phi_theta.clamp(-1*self.m, 1)  # 控制在-m和1之间

        cos_theta = cos_theta * w_modulus * x_modulus
        phi_theta = phi_theta * w_modulus * x_modulus
        output = [cos_theta, phi_theta]  # 返回/cos(/theta)和/phi(/theta)
        return output

    def __repr__(self):
        return "AngleLinear(m=%f, in=%d, out=%d)" % (self.m, self.in_features, self.out_features)


class AngleSoftmaxLoss(nn.Module):
    def __init__(self, m=3, lambda_min=5.0, lambda_max=1500.0, gamma=0, it=0, phiflag=True):
        super(AngleSoftmaxLoss, self).__init__()
        self.gamma = gamma
        self.m = m
        self.it = it
        self.lambda_min = lambda_min
        self.lambda_max = lambda_max
        self.phiflag = phiflag

        self.mlambda = [
            lambda x: x ** 0,
            lambda x: x ** 1,
            lambda x: 2 * x ** 2 - 1,
            lambda x: 4 * x ** 3 - 3 * x,
            lambda x: 8 * x ** 4 - 8 * x ** 2 + 1,
            lambda x: 16 * x ** 5 - 20 * x ** 3 + 5 * x
        ]  # 匿名函数,用于得到cos_m_theta

    @staticmethod
    def myphi(x, m):
        x = x * m
        return 1 - x ** 2 / math.factorial(2) + x ** 4 / math.factorial(4) - x ** 6 / math.factorial(6) + \
            x ** 8 / math.factorial(8) - x ** 9 / math.factorial(9)

    def forward(self, costh, label):
        '''
        x:
            cos_x: [batch, classes_num]
            phi_x: [batch, classes_num]
        y:
            target: LongTensor,[batch]
        return:
            loss:scalar
        '''
        self.it += 1
        # cos_theta, phi_theta = x #output包括上面的[cos_theta, phi_theta]
        if self.phiflag:
            cos_m_theta = self.mlambda[self.m](
                costh)  # 由m和/cos(/theta)得到cos_m_theta
            theta = Variable(costh.data.acos())
            k = (self.m * theta / 3.14159265).floor()
            n_one = k * 0.0 - 1
            phi_theta = (n_one ** k) * cos_m_theta - 2 * k  # 得到/phi(/theta)
        else:
            theta = costh.acos()  # acos得到/theta
            phi_theta = self.myphi(theta, self.m)  # 得到/phi(/theta)
            phi_theta = phi_theta.clamp(-1 * self.m, 1)  # 控制在-m和1之间

        y = label.view(-1, 1)

        index = costh.data * 0.0
        index.scatter_(1, y.data.view(-1, 1), 1)  # 将label存成稀疏矩阵
        index = index.to(dtype=torch.bool)
        index = Variable(index)

        # set lamb, change the rate of softmax and A-softmax
        # 动态调整lambda，来调整cos(\theta)和\phi(\theta)的比例
        lamb = max(self.lambda_min, self.lambda_max / (1 + 0.1 * self.it))
        output = costh * 1.0
        output[index] -= costh[index] * \
            (1.0 + 0) / (1 + lamb)  # 减去目标\cos(\theta)的部分
        output[index] += phi_theta[index] * \
            (1.0 + 0) / (1 + lamb)  # 加上目标\phi(\theta)的部分

        logpt = F.log_softmax(output)
        logpt = logpt.gather(1, y)
        logpt = logpt.view(-1)
        pt = Variable(logpt.data.exp())

        loss = -1 * (1 - pt) ** self.gamma * logpt
        loss = loss.mean()

        return loss


class AdditiveMarginLinear(nn.Module):
    def __init__(self, feat_dim, num_classes, normalize=True, use_gpu=False):
        super(AdditiveMarginLinear, self).__init__()
        self.feat_dim = feat_dim
        self.num_classes = num_classes
        self.normalize = normalize
        self.W = torch.nn.Parameter(torch.randn(
            feat_dim, num_classes), requires_grad=True)
        if use_gpu:
            self.W.cuda()
        nn.init.xavier_normal_(self.W, gain=1)

    def forward(self, x):
        # assert x.size()[0] == label.size()[0]
        assert x.size()[1] == self.feat_dim

        # pdb.set_trace()
        # x_norm = torch.norm(x, p=2, dim=1, keepdim=True).clamp(min=1e-12)
        # x_norm = torch.div(x, x_norm)

        x_norm = F.normalize(x, dim=1)
        # torch.norm(self.W, p=2, dim=0, keepdim=True).clamp(min=1e-12)
        w_norm = F.normalize(self.W, dim=0)
        costh = torch.mm(x_norm, w_norm)  # .clamp_(min=-1., max=1.)
        # x = x.unsqueeze(-1).repeat(1, 1, self.num_classes)
        # w = self.W.unsqueeze(0).repeat(x.shape[0], 1, 1)
        # # w_norm = torch.div(self.W, w_norm)
        # costh = torch.cosine_similarity(x, w, dim=1)
        # costh = torch.mm(x_norm, w_norm)  # .clamp_(min=-1., max=1.)

        return costh  # .clamp(min=-1.0, max=1.)

    def __repr__(self):
        return "AdditiveMarginLinear(feat_dim=%f, num_classes=%d)" % (self.feat_dim, self.num_classes)


class SubMarginLinear(nn.Module):
    def __init__(self, feat_dim, num_classes, num_center=3, output_subs=False):
        super(SubMarginLinear, self).__init__()
        self.feat_dim = feat_dim
        self.num_classes = num_classes
        self.num_center = num_center
        self.output_subs = output_subs

        self.W = torch.nn.Parameter(torch.randn(
            feat_dim, num_classes, num_center), requires_grad=True)

        nn.init.xavier_normal(self.W, gain=1)

    def forward(self, x):
        # assert x.size()[0] == label.size()[0]
        assert x.size()[1] == self.feat_dim

        x = x.unsqueeze(-1).unsqueeze(-1).repeat(1, 1,
                                                 self.num_classes, self.num_center)
        w = self.W.unsqueeze(0).repeat(x.shape[0], 1, 1, 1)

        # # w_norm = torch.div(self.W, w_norm)
        costh = torch.cosine_similarity(x, w, dim=1)
        # costh = torch.max(costh, dim=-1).values
        # if not self.training:
        #     # not self.output_subs:
        #     costh = torch.max(costh, dim=-1).values

        return costh  # .clamp(min=-1.0, max=1.)

    def __repr__(self):
        return "SubMarginLinear(feat_dim=%f, num_classes=%d, num_center=%d)" % (self.feat_dim, self.num_classes, self.num_center)


class AMSoftmaxLoss(nn.Module):
    def __init__(self, margin=0.3, s=15, all_iteraion=0):
        super(AMSoftmaxLoss, self).__init__()
        self.s = s
        self.margin = margin
        self.ce = nn.CrossEntropyLoss()
        self.iteraion = 0
        # self.all_iteraion = all_iteraion

    def forward(self, costh, label):
        lb_view = label.view(-1, 1)

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()

        delt_costh = torch.zeros(costh.size()).scatter_(
            1, lb_view.data, self.margin)

        if costh.is_cuda:
            delt_costh = Variable(delt_costh.cuda())

        costh_m = costh - delt_costh
        costh_m_s = self.s * costh_m

        # if self.iteraion < 1000:
        #     costh_m_s = 0.5 + costh + 0.5 * costh_m_s
        #     self.iteraion += 1

        loss = self.ce(costh_m_s, label)

        return loss

    def __repr__(self):
        return "AMSoftmaxLoss(margin=%f, s=%d)" % (self.margin, self.s)


class DAMSoftmaxLoss(nn.Module):
    def __init__(self, margin=0.3, s=15, lamda=2,
                 dynamic_s=False):
        super(DAMSoftmaxLoss, self).__init__()
        self.s = s
        self.margin = margin
        self.ce = nn.CrossEntropyLoss()
        self.lamda = lamda
        self.dynamic_s = dynamic_s

    def forward(self, costh, label):
        lb_view = label.view(-1, 1)

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()

        delt_costh = torch.zeros(costh.size()).scatter_(
            1, lb_view.data, self.margin)

        if costh.is_cuda:
            delt_costh = Variable(delt_costh.cuda())

        costh_m_target = costh.gather(1, label.reshape(-1, 1))
        costh_m_target = torch.exp(1 - costh_m_target) / self.lamda

        delt_costh = delt_costh * costh_m_target
        costh_m = costh - delt_costh
        costh_m_s = self.s * costh_m

        loss = self.ce(costh_m_s, label)

        return loss

    def __repr__(self):
        return "DAMSoftmaxLoss(margin=%f, s=%d)" % (self.margin, self.s)


class ArcSoftmaxLoss(nn.Module):

    def __init__(self, margin=0.5, s=64, iteraion=0, all_iteraion=0,
                 smooth_ratio=0, class_weight=None, focal=False, dynamic_s=False):
        super(ArcSoftmaxLoss, self).__init__()
        self.s = s
        self.margin = margin
        self.focal = focal
        self.dynamic_s = dynamic_s
        self.reduction = 'mean'

        if smooth_ratio > 0:
            self.ce = LabelSmoothing(smooth_ratio)
        elif focal:
            self.ce = FocalLoss(weight=class_weight)
        else:
            self.ce = nn.CrossEntropyLoss(weight=class_weight)

        self.iteraion = iteraion
        self.all_iteraion = all_iteraion
        self.smooth_ratio = smooth_ratio

    def forward(self, costh, label, lamda_beta=1, weight_margin=None):
        self.iteraion += 1

        lb_view = label.view(-1, 1)
        theta = costh.acos()
        # print('theta is ', theta.max())

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()

        if isinstance(lamda_beta, torch.Tensor):
            if len(lamda_beta.shape) == 1:
                lamda_beta = lamda_beta.unsqueeze(1).cpu()
        
        delt_theta =  lamda_beta * torch.zeros(costh.size()).scatter_(1, lb_view.data, 1)
        if costh.is_cuda:
            delt_theta = Variable(delt_theta.cuda())

        if weight_margin == None or self.iteraion <= 12075:
            delt_theta = delt_theta * self.margin
        else:
            # weight_margin = weight_margin.detach()
            weight_margin = torch.nn.functional.sigmoid(weight_margin - weight_margin.mean()).detach()
            delt_theta = (0.1 * weight_margin + self.margin-0.05) * delt_theta

        # pdb.set_trace()
        if costh.is_cuda:
            delt_theta = Variable(delt_theta.cuda())
            # print('delt_theta max is ', delt_theta.max())
            # print('theta + delt_theta max is ', (theta + delt_theta).max())

        costh_m = (theta + delt_theta).cos()
        # print('costh_m max is ', costh_m.max())
        # if self.iteraion < self.all_iteraion:
        #     self.iteraion += 1

        costh_m_s = self.s * costh_m
        if self.dynamic_s:
            max_cos = costh.max(dim=1, keepdim=True).values
            costh_m_s = costh_m_s * torch.exp(-max_cos*max_cos*max_cos*max_cos)
        # print('costh_m_s max is ', costh_m_s.max())
        self.ce.reduction = self.reduction

        loss = self.ce(costh_m_s, label)

        return loss

    def __repr__(self):
        return "ArcSoftmaxLoss(margin=%f, s=%d, iteration=%d, all_iteraion=%s, focal=%s)" % (self.margin,
                                                                                             self.s, self.iteraion,
                                                                                             self.all_iteraion,
                                                                                             self.focal)


class SubArcSoftmaxLoss(nn.Module):

    def __init__(self, margin=0.5, s=64, iteraion=0, all_iteraion=0, smooth_ratio=0, class_weight=None):
        super(SubArcSoftmaxLoss, self).__init__()
        self.s = s
        self.margin = margin

        self.ce = LabelSmoothing(
            smooth_ratio) if smooth_ratio > 0 else nn.CrossEntropyLoss(weight=class_weight)
        self.iteraion = iteraion
        self.all_iteraion = all_iteraion
        self.smooth_ratio = smooth_ratio

    def forward(self, costh, label):
        lb_view = label.view(-1, 1)
        cos_max = costh.max(dim=-1).values
        cos_min = costh.min(dim=-1).values

        min_costh = torch.zeros(cos_max.size()).scatter_(
            1, label.view(-1, 1).cpu(), 1)
        max_costh = torch.zeros(cos_max.size()).scatter_(
            1, label.view(-1, 1).cpu(), -1) + 1

        if lb_view.is_cuda:
            min_costh = min_costh.cuda()
            max_costh = max_costh.cuda()

        costh = cos_max * max_costh + cos_min * min_costh

        theta = costh.acos()
        # print('theta is ', theta.max())

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()

        delt_theta = torch.zeros(costh.size()).scatter_(
            1, lb_view.data, self.margin)

        # pdb.set_trace()
        if costh.is_cuda:
            delt_theta = Variable(delt_theta.cuda())
            # print('delt_theta max is ', delt_theta.max())
            # print('theta + delt_theta max is ', (theta + delt_theta).max())

        costh_m = (theta + delt_theta).cos()
        # print('costh_m max is ', costh_m.max())
        if self.iteraion < self.all_iteraion:
            costh_m = 0.5 * costh + 0.5 * costh_m
            self.iteraion += 1

        costh_m_s = self.s * costh_m
        # print('costh_m_s max is ', costh_m_s.max())

        loss = self.ce(costh_m_s, label)

        return loss

    def __repr__(self):
        return "SubArcSoftmaxLoss(margin=%f, s=%d, iteration=%d, all_iteraion=%s, smooth_ratio=%s)" % (self.margin,
                                                                                                       self.s,
                                                                                                       self.iteraion,
                                                                                                       self.all_iteraion,
                                                                                                       self.smooth_ratio)


class MinArcSoftmaxLoss(nn.Module):

    def __init__(self, margin=0.5, s=64, iteraion=0, all_iteraion=0):
        super(MinArcSoftmaxLoss, self).__init__()
        self.s = s
        self.margin = margin
        self.ce = nn.CrossEntropyLoss()
        self.iteraion = iteraion
        self.all_iteraion = all_iteraion

    def forward(self, costh, label):
        lb_view = label.view(-1, 1)
        theta = costh.acos()
        # print('theta is ', theta.max())

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()
        # pdb.set_trace()
        positive_theta = theta.gather(dim=1, index=label.view(-1, 1))
        center_mean = positive_theta.mean().cpu()
        center_std = positive_theta.std().cpu()

        delt_theta = torch.normal(
            float(center_mean), float(center_std), size=costh.size())
        # np.random.uniform(0,1)
        delt_theta = delt_theta.scatter_(1, lb_view.data, 0)

        # pdb.set_trace()
        if costh.is_cuda:
            delt_theta = Variable(delt_theta.cuda())

        costh_mm = (theta - delt_theta).cos()

        delt_theta = torch.zeros(costh.size()).scatter_(
            1, lb_view.data, self.margin)

        if costh.is_cuda:
            delt_theta = Variable(delt_theta.cuda())

        costh_pm = (theta + delt_theta).cos()
        # print('costh_m max is ', costh_m.max())
        # if self.iteraion < self.all_iteraion:
        costh_m = (0.1 * costh_mm + costh_pm) / (1 + 0.1)
        # self.iteraion += 1

        costh_m_s = self.s * costh_m
        # print('costh_m_s max is ', costh_m_s.max())
        loss = self.ce(costh_m_s, label)

        return loss

    def __repr__(self):
        return "MinArcSoftmaxLoss(margin=%f, s=%d, iteration=%d, all_iteraion=%s)" % (self.margin,
                                                                                      self.s,
                                                                                      self.iteraion,
                                                                                      self.all_iteraion)


class MinArcSoftmaxLoss_v2(nn.Module):

    def __init__(self, margin=0.2, s=30, iteraion=0, all_iteraion=0, scale=0.1):
        super(MinArcSoftmaxLoss_v2, self).__init__()
        self.s = s
        self.margin = margin
        self.ce = nn.CrossEntropyLoss()
        self.iteraion = iteraion
        self.all_iteraion = all_iteraion
        self.scale = scale

    def forward(self, costh, label):
        lb_view = label.view(-1, 1)
        theta = costh.acos()
        # print('theta is ', theta.max())

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()
        # pdb.set_trace()
        positive_theta = theta.gather(
            dim=1, index=label.view(-1, 1)).clamp_min(0.)
        center_mean = positive_theta.mean().cpu()
        center_std = positive_theta.std().cpu()

        delt_theta = torch.normal(float(center_mean), float(
            center_std), size=costh.size())  # .clamp_max(self.margin)
        # delt_theta *= center_mean.cos() ** 4 * self.scale

        # np.random.uniform(0,1)
        neg_delt_theta = delt_theta.scatter_(1, lb_view.data, 0)

        delt_theta = torch.zeros(costh.size()).scatter_(
            1, lb_view.data, self.margin)
        delt_theta -= self.scale * neg_delt_theta

        if costh.is_cuda:
            delt_theta = Variable(delt_theta.cuda())

        costh_m = (theta + delt_theta).cos()
        # print('costh_m max is ', costh_m.max())
        # if self.iteraion < self.all_iteraion:
        # costh_m = (0.1 * costh_mm + costh_pm) / (1 + 0.1)
        # self.iteraion += 1

        costh_m_s = self.s * costh_m
        # print('costh_m_s max is ', costh_m_s.max())
        loss = self.ce(costh_m_s, label)

        return loss

    def __repr__(self):
        return "MinArcSoftmaxLoss_v2(margin=%f, s=%d, iteration=%d, all_iteraion=%s)" % (self.margin,
                                                                                         self.s,
                                                                                         self.iteraion,
                                                                                         self.all_iteraion)


class CenterLoss(nn.Module):
    """Center loss.

    Reference:
    Wen et al. A Discriminative Feature Learning Approach for Deep Face Recognition. ECCV 2016.

    Args:
        num_classes (int): number of classes.
        feat_dim (int): feature dimension.
    """

    def __init__(self, num_classes=10, feat_dim=2):
        super(CenterLoss, self).__init__()
        self.num_classes = num_classes
        self.feat_dim = feat_dim

        self.centers = nn.Parameter(
            torch.randn(self.num_classes, self.feat_dim))
        # 初始化权重，在第一维度上做normalize
        self.centers.data.uniform_(-1, 1).renorm_(2, 1, 1e-5).mul_(1e5)

    def forward(self, x, labels):
        """
        Args:
            x: feature matrix with shape (batch_size, feat_dim).
            labels: ground truth labels with shape (batch_size).
        """
        batch_size = x.size(0)
        distmat = torch.pow(x, 2).sum(dim=1, keepdim=True).expand(batch_size, self.num_classes) + \
            torch.pow(self.centers, 2).sum(dim=1, keepdim=True).expand(
                self.num_classes, batch_size).t()
        distmat.addmm_(1, -2, x, self.centers.t())

        classes = torch.arange(self.num_classes).long()
        #if self.use_gpu: classes = classes.cuda()
        if self.centers.is_cuda:
            classes = classes.cuda()

        labels = labels.unsqueeze(1).expand(batch_size, self.num_classes)
        mask = labels.eq(classes.expand(batch_size, self.num_classes))

        dist = distmat * mask.float()
        loss = dist.sum() / batch_size

        return loss

    def __repr__(self):
        return "CenterLoss(num_classes=%d, feat_dim=%d)" % (self.num_classes, self.feat_dim)


class GaussianLoss(nn.Module):
    """Center loss.

    Reference:
    Wen et al. A Discriminative Feature Learning Approach for Deep Face Recognition. ECCV 2016.

    Args:
        num_classes (int): number of classes.
        feat_dim (int): feature dimension.
    """

    def __init__(self, num_classes=10, feat_dim=2):
        super(GaussianLoss, self).__init__()
        self.num_classes = num_classes
        self.feat_dim = feat_dim

        norm_ceneters = F.normalize(torch.randn(
            self.num_classes, self.feat_dim), p=2, dim=0)
        self.means = nn.Parameter(norm_ceneters)

        # 初始化权重，在第一维度上做normalize
        # cov = torch.eye(self.feat_dim, self.feat_dim).unsqueeze(0).repeat(self.num_classes, 1, 1)
        # self.covs_invers = nn.Parameter(cov)

    def forward(self, x, labels):
        """
        Args:
            x: feature matrix with shape (batch_size, feat_dim).
            labels: ground truth labels with shape (batch_size).
        """
        batch_size = x.size(0)
        x_expand = x.unsqueeze(1).expand(
            batch_size, self.num_classes, self.feat_dim)
        x_expand_mean = x_expand - self.means
        # log_pro = np.log((2 * np.pi) ** self.feat_dim) + x_expand_mean.unsqueeze(2).matmul(
        #     x_expand_mean.unsqueeze(3)).squeeze()
        log_pro = x_expand_mean.unsqueeze(2).matmul(
            x_expand_mean.unsqueeze(3)).squeeze()

        # distmat = torch.pow(x, 2).sum(dim=1, keepdim=True).expand(batch_size, self.num_classes) + \
        #           torch.pow(self.centers, 2).sum(dim=1, keepdim=True).expand(self.num_classes, batch_size).t()
        # distmat.addmm_(1, -2, x, self.centers.t())
        classes = torch.arange(self.num_classes).long()
        # if self.use_gpu: classes = classes.cuda()
        if self.means.is_cuda:
            classes = classes.cuda()

        labels = labels.unsqueeze(1).expand(batch_size, self.num_classes)
        mask = labels.eq(classes.expand(batch_size, self.num_classes))

        dist = log_pro * mask.float()
        loss = dist.sum() / batch_size

        return loss


class PrototypicalLinear(nn.Module):
    def __init__(self, feat_dim, n_classes=1000):
        super(PrototypicalLinear, self).__init__()
        self.feat_dim = feat_dim
        self.center = torch.nn.Parameter(torch.randn(feat_dim, n_classes))

        nn.init.xavier_normal(self.center, gain=1)

    def forward(self, x):
        # assert x.size()[0] == label.size()[0]
        assert x.size()[1] == self.feat_dim

        # pdb.set_trace()
        x_norm = torch.norm(x, p=2, dim=1, keepdim=True).clamp(min=1e-12)
        x_norm = torch.div(x, x_norm)

        w_norm = torch.norm(self.center, p=2, dim=0,
                            keepdim=True).clamp(min=1e-12)
        w_norm = torch.div(self.center, w_norm)

        costh = torch.mm(x_norm, w_norm)

        return costh


class APrototypicalLinear(nn.Module):
    def __init__(self, feat_dim, n_classes=1000):
        super(APrototypicalLinear, self).__init__()
        self.feat_dim = feat_dim
        self.center = nn.Parameter(torch.randn(feat_dim, n_classes))
        self.w = nn.Parameter(torch.ones(1))
        self.b = nn.Parameter(torch.zeros(1))

        nn.init.xavier_normal(self.center, gain=1)

    def forward(self, x):
        # assert x.size()[0] == label.size()[0]
        assert x.size()[1] == self.feat_dim

        # pdb.set_trace()
        x_norm = torch.norm(x, p=2, dim=1, keepdim=True).clamp(min=1e-12)
        x_norm = torch.div(x, x_norm)

        w_norm = torch.norm(self.center, p=2, dim=0,
                            keepdim=True).clamp(min=1e-12)
        w_norm = torch.div(self.center, w_norm)

        costh = self.w * torch.mm(x_norm, w_norm) + self.b

        return costh


class EVMClassifier(nn.Module):
    def __init__(self, feat_dim, n_classes=1000, use_gpu=False):
        super(EVMClassifier, self).__init__()
        self.feat_dim = feat_dim
        self.n_classes = n_classes
        self.centers = torch.nn.Parameter(torch.randn(feat_dim, n_classes) + 1 / math.sqrt(feat_dim),
                                          requires_grad=True)
        self.lamda = torch.nn.Parameter(
            torch.randn(n_classes) + 1, requires_grad=True)
        self.k = torch.nn.Parameter(torch.randn(
            n_classes) + 2, requires_grad=True)

        # if use_gpu:
        #     self.center.cuda()
        #     self.lamda.cuda()
        #     self.k.cuda()

        # nn.init.xavier_normal(self.W, gain=1)

    def forward(self, x):
        # assert x.size()[0] == label.size()[0]
        batch_size = x.size(0)
        distmat = torch.pow(x, 2).sum(dim=1, keepdim=True).expand(batch_size, self.n_classes) + \
            torch.pow(self.centers, 2).sum(
                dim=0, keepdim=True).expand(batch_size, self.n_classes)
        distmat.addmm_(1, -2, x, self.centers)

        l1_distmat = torch.sqrt(distmat) / torch.abs(self.k)
        # probabilities = torch.exp(-torch.pow(l1_distmat, self.k))
        probabilities = -torch.pow(l1_distmat, self.k)

        return probabilities
# Testing those Loss Classes
# a = Variable(torch.Tensor([[1., 1., 3.],
#                   [1., 2., 0.],
#                   [1., 4., 3.],
#                   [5., 0., 3.]]).cuda())
#
# a_label = Variable(torch.LongTensor([2, 1, 1, 0]).cuda())
#
# linear = AngleLinear(in_planes=3, out_planes=3, m=4)
# Asoft = AngleSoftmaxLoss()
# a_linear = linear(a)
# a_asoft = Asoft(a_linear, a_label)
# print("axsoftmax loss is {}".format(a_asoft))
#
# asoft = AngularSoftmax(in_feats=3, num_classes=3)
# a_loss = asoft(a, a_label)
# print("amsoftmax loss is {}".format(a_loss))
#
# amsoft = AMSoftmax(in_feats=3)
# am_a = amsoft(a, a_label)
# print("amsoftmax loss is {}".format(am_a))


class MarginLinearDummy(nn.Module):
    def __init__(self, feat_dim, num_classes, dummy_classes=1):
        super(MarginLinearDummy, self).__init__()
        self.feat_dim = feat_dim
        self.num_classes = num_classes
        self.dummy_classes = dummy_classes
        self.W = torch.nn.Parameter(torch.randn(
            feat_dim, num_classes + dummy_classes), requires_grad=True)

        nn.init.xavier_normal_(self.W, gain=1)

    def forward(self, x):
        # assert x.size()[0] == label.size()[0]
        assert x.shape[1] == self.feat_dim

        x_norm = F.normalize(x, dim=1)
        # torch.norm(self.W, p=2, dim=0, keepdim=True).clamp(min=1e-12)
        w_norm = F.normalize(self.W, dim=0)
        costh = torch.mm(x_norm, w_norm)  # .clamp_(min=-1., max=1.)

        if self.dummy_classes > 1:
            # pdb.set_trace() # costh.max()=0.2746 costh.min()=-0.2572
            costh_dummy = torch.max(
                costh[:, -self.dummy_classes:], dim=1, keepdim=True)[0]
            costh = torch.cat(
                [costh[:, :-self.dummy_classes], costh_dummy], dim=1)

        return costh  # .clamp(min=-1.0, max=1.)

    def __repr__(self):
        return "MarginLinearDummy(feat_dim=%f, num_classes=%d, dummy_classes=%d)" % (
            self.feat_dim, self.num_classes, self.dummy_classes)


class ProserLoss(nn.Module):

    def __init__(self, margin=0.2, s=64, smooth_ratio=0, class_weight=None,
                 beta_alpha=0.2, gamma=0.01, beta=1.0):
        super(ProserLoss, self).__init__()
        self.s = s
        self.margin = margin
        # self.dummy_classes = dummy_classes
        self.beta_alpha = beta_alpha
        self.gamma = gamma
        self.beta = beta

        self.ce = LabelSmoothing(
            smooth_ratio) if smooth_ratio > 0 else nn.CrossEntropyLoss(weight=class_weight)
        self.smooth_ratio = smooth_ratio

    def forward(self, costh, label, half_batch_size):

        lb_view = label.view(-1, 1)

        # half_batch_size = int(costh.shape[0] / 2)
        theta = costh.acos()

        if lb_view.is_cuda:
            lb_view = lb_view.cpu()

        delt_theta = torch.zeros(costh.size()).scatter_(
            1, lb_view.data, self.margin)

        # pdb.set_trace()
        if costh.is_cuda:
            delt_theta = Variable(delt_theta.cuda())

        costh_sm = self.s * (theta + delt_theta).cos()

        loss = self.ce(costh_sm[:half_batch_size], label[:half_batch_size])

        half_a_costh_m = costh_sm[:half_batch_size].clone()
        half_b_costh_m = costh_sm[half_batch_size:].clone()

        last_a_label = torch.LongTensor(
            [costh.shape[1] - 1 for i in range(half_batch_size)])
        last_b_label = torch.LongTensor(
            [costh.shape[1] - 1 for i in range(len(costh) - half_batch_size)])
        if costh.is_cuda:
            last_a_label = last_a_label.cuda()
            last_b_label = last_b_label.cuda()
            lb_view = lb_view.cuda()

        # pdb.set_trace()
        loss = loss + self.beta * self.ce(half_a_costh_m.clone().scatter_(1, lb_view[:half_batch_size], 0),
                                          last_a_label)
        loss += self.gamma * \
            self.ce(half_b_costh_m.scatter_(
                1, lb_view[half_batch_size:], 0), last_b_label)

        return loss

    def __repr__(self):
        return "ProserLoss(margin=%f, s=%d, smooth_ratio=%s, beta_alpha=%s, gamma=%s)" % (
            self.margin, self.s, self.smooth_ratio,
            self.beta_alpha, self.gamma)


class MixupLoss(nn.Module):

    def __init__(self, loss, gamma=1, margin_lamda=False):
        super(MixupLoss, self).__init__()
        self.loss = loss
        self.gamma = gamma
        self.margin_lamda = margin_lamda

    def forward(self, costh, label, half_batch_size=0, lamda_beta=0):
        margin_lamda = lamda_beta if self.margin_lamda else 1
        if half_batch_size > 0 :
            loss = self.loss(costh[:half_batch_size], label[:half_batch_size])

            loss = loss + self.gamma * (
                lamda_beta * self.loss(costh[-half_batch_size:],
                                    label[half_batch_size:int(2 * half_batch_size)], lamda_beta=margin_lamda)
                        + (1 - lamda_beta) * self.loss(costh[-half_batch_size:], label[-half_batch_size:], lamda_beta=margin_lamda))

            return loss / (1 + self.gamma)
        else:
            loss = self.loss(costh, label)
            return loss

    def __repr__(self):
        return "MixupLoss(loss=%s)" % (self.loss)