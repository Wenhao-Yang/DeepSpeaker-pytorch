#!/usr/bin/env python
# encoding: utf-8
'''
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: VS Code
@File: common.py
@Time: 2023/02/23 18:23
@Overview:
'''
import time
import numpy as np
import torch.nn as nn
import torch
import os
import pdb
from kaldiio import WriteHelper
from pytorch_lightning import LightningModule
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from Define_Model.Loss.LossFunction import CenterLoss, Wasserstein_Loss, MultiCenterLoss, CenterCosLoss, RingLoss, \
    VarianceLoss, DistributeLoss, MMD_Loss, aDCFLoss
from Define_Model.Loss.SoftmaxLoss import AngleSoftmaxLoss, AMSoftmaxLoss, ArcSoftmaxLoss, DAMSoftmaxLoss, \
    GaussianLoss, MinArcSoftmaxLoss, MinArcSoftmaxLoss_v2, MixupLoss
import Process_Data.constants as C

from TrainAndTest.common_func import AverageMeter
from Define_Model.Optimizer import create_optimizer, create_scheduler
from Eval.eval_metrics import evaluate_kaldi_eer, evaluate_kaldi_mindcf


class SpeakerLoss(nn.Module):

    def __init__(self, config_args):
        super().__init__()

        self.config_args = {}
        self.lncl = True if 'lncl' in config_args and config_args['lncl'] == True else False
        iteration = 0

        self.reduction = 'mean'
        ce_criterion = nn.CrossEntropyLoss()
        loss_type = set(['soft', 'asoft', 'center', 'variance', 'gaussian', 'coscenter', 'mulcenter',
                         'amsoft', 'subam',  'damsoft', 'subdam',
                         'arcsoft', 'subarc', 'minarcsoft', 'minarcsoft2', 'wasse', 'mmd', 'ring', 'arcdist',
                         'aDCF', ])

        self.config_args['loss_type'] = config_args['loss_type']

        if config_args['loss_type'] == 'soft':
            xe_criterion = None
        elif config_args['loss_type'] == 'asoft':
            ce_criterion = AngleSoftmaxLoss(
                lambda_min=config_args['lambda_min'], lambda_max=config_args['lambda_max'])
            xe_criterion = None
        elif config_args['loss_type'] == 'variance':
            xe_criterion = VarianceLoss(
                num_classes=config_args['num_classes'], feat_dim=config_args['embedding_size'])
        elif config_args['loss_type'] == 'gaussian':
            xe_criterion = GaussianLoss(
                num_classes=config_args['num_classes'], feat_dim=config_args['embedding_size'])
        elif config_args['loss_type'] == 'coscenter':
            xe_criterion = CenterCosLoss(
                num_classes=config_args['num_classes'], feat_dim=config_args['embedding_size'])
        elif config_args['loss_type'] == 'mulcenter':
            xe_criterion = MultiCenterLoss(num_classes=config_args['num_classes'], feat_dim=config_args['embedding_size'],
                                           num_center=config_args['num_center'])
        elif config_args['loss_type'] in ['amsoft', 'subam']:
            ce_criterion = None
            xe_criterion = AMSoftmaxLoss(
                margin=config_args['margin'], s=config_args['s'])
        elif config_args['loss_type'] in ['damsoft', 'subdam']:
            ce_criterion = None
            xe_criterion = DAMSoftmaxLoss(
                margin=config_args['margin'], s=config_args['s'])
        elif config_args['loss_type'] in ['aDCF']:
            ce_criterion = None
            xe_criterion = aDCFLoss(alpha=config_args['s'],
                                    beta=(1 - config_args['smooth_ratio']),
                                    gamma=config_args['smooth_ratio'],
                                    omega=config_args['margin'])

        elif config_args['loss_type'] in ['arcsoft', 'subarc']:
            ce_criterion = None
            if 'class_weight' in config_args and config_args['class_weight'] == 'cnc1':
                class_weight = torch.tensor(C.CNC1_WEIGHT)
                if len(class_weight) != config_args['num_classes']:
                    class_weight = None
            else:
                class_weight = None
            if 'dynamic_s' in config_args:
                dynamic_s = config_args['dynamic_s']
            else:
                dynamic_s = False

            all_iteraion = 0 if 'all_iteraion' not in config_args else config_args[
                'all_iteraion']
            smooth_ratio = 0 if 'smooth_ratio' not in config_args else config_args[
                'smooth_ratio']
            xe_criterion = ArcSoftmaxLoss(margin=config_args['margin'], s=config_args['s'], iteraion=iteration,
                                          all_iteraion=all_iteraion, smooth_ratio=smooth_ratio,
                                          class_weight=class_weight, dynamic_s=dynamic_s)

        elif config_args['loss_type'] == 'minarcsoft':
            ce_criterion = None
            xe_criterion = MinArcSoftmaxLoss(margin=config_args['margin'], s=config_args['s'], iteraion=iteration,
                                             all_iteraion=config_args['all_iteraion'])
        elif config_args['loss_type'] == 'minarcsoft2':
            ce_criterion = None
            xe_criterion = MinArcSoftmaxLoss_v2(margin=config_args['margin'], s=config_args['s'], iteraion=iteration,
                                                all_iteraion=config_args['all_iteraion'])
        elif config_args['loss_type'] == 'wasse':
            xe_criterion = Wasserstein_Loss(
                source_cls=config_args['source_cls'])
        elif config_args['loss_type'] == 'mmd':
            xe_criterion = MMD_Loss()
            # args.alpha = 0.0


        if 'second_loss' in config_args:
            if config_args['second_loss'] == 'center':
                ce_criterion = CenterLoss(num_classes=config_args['num_classes'],
                                      feat_dim=config_args['embedding_size'],
                                      alpha=config_args['center_alpha'] if 'center_alpha' in config_args else 0)
            elif config_args['second_loss'] == 'ring':
                ce_criterion = RingLoss(ring=config_args['ring'])
            elif config_args['second_loss'] == 'dist':
                ce_criterion = DistributeLoss(stat_type=config_args['stat_type'],
                                            margin=config_args['m'])
            elif config_args['second_loss'] == 'gender':
                ce_criterion = nn.CrossEntropyLoss()
            elif config_args['second_loss'] == 'wasse':
                metric = 'cosine' if 'second_metric' not in config_args else config_args['second_metric']  
                ce_criterion = Wasserstein_Loss(source_cls=0, metric=metric)
            
            self.second_loss = config_args['second_loss']
        
        else:
            self.second_loss = 'none'

        self.softmax = nn.Softmax(dim=1)
        self.ce_criterion = ce_criterion
        if 'mixup_type' in config_args and config_args['mixup_type'] != '':
            if 'margin_lamda' in config_args:
                margin_lamda = config_args['margin_lamda']
            else:
                margin_lamda = False

            xe_criterion = MixupLoss(
                xe_criterion, gamma=config_args['proser_gamma'], margin_lamda=margin_lamda)

        self.xe_criterion = xe_criterion
        self.loss_ratio = config_args['loss_ratio']

    def forward(self, outputs, label,
                second_label=None, batch_weight=None, epoch=0,
                half_data=0, lamda_beta=0, other=False):
        
        if isinstance(outputs, tuple):
            classfier, feats = outputs
        else:
            classfier = outputs

        other_loss = 0.

        if self.config_args['loss_type'] in ['soft', 'asoft']:
            loss = self.ce_criterion(classfier, label)
        elif self.config_args['loss_type'] in ['amsoft', 'arcsoft', 'minarcsoft', 'minarcsoft2', 'subarc', ]:
            if isinstance(self.xe_criterion, MixupLoss):
                loss = self.xe_criterion(
                    classfier, label, half_batch_size=half_data, lamda_beta=lamda_beta)
            else:
                self.xe_criterion.reduction = self.reduction
                loss = self.xe_criterion(classfier, label)

            if batch_weight != None:
                loss = loss * batch_weight
                loss = loss.mean()
                self.xe_criterion.ce.reduction = 'mean'

            if self.ce_criterion != None:
                if self.second_loss == 'gender' and second_label != None:
                    loss_cent = self.loss_ratio * self.ce_criterion(feats, second_label)
                    other_loss += float(loss_cent)
                    loss = loss + loss_cent
                elif self.second_loss in ['dist', 'ring', 'center', 'wasse']:
                    loss_cent = self.loss_ratio * self.ce_criterion(feats, label)
                    other_loss += float(loss_cent)
                    loss = loss + loss_cent

        # if self.lncl:
        #     predicted_labels = self.softmax(classfier.clone())
        #     predicted_one_labels = torch.max(predicted_labels, dim=1)[1]

        #     if config_args['loss_type'] in ['amsoft', 'damsoft', 'arcsoft', 'minarcsoft', 'minarcsoft2',
        #                                     'aDCF', 'subarc', 'arcdist']:
        #         predict_loss = self.xe_criterion(
        #             classfier, predicted_one_labels)
        #     else:
        #         predict_loss = self.ce_criterion(
        #             classfier, predicted_one_labels)

        #     alpha_t = np.clip(
        #         config_args['alpha_t'] * (epoch / config_args['epochs']) ** 2, a_min=0, a_max=1)
        #     mp = predicted_labels.mean(dim=0) * predicted_labels.shape[1]

        #     loss = (1 - alpha_t) * loss + alpha_t * predict_loss + \
        #         config_args['beta'] * torch.mean(-torch.log(mp))
        if other:
            return loss, other_loss
        else:
            return loss


def get_trials(trials):

    trials_pairs = []

    with open(trials, 'r') as t:

        for line in t.readlines():
            pair = line.split()
            pair_true = False if pair[2] in ['nontarget', '0'] else True
            trials_pairs.append((pair[0], pair[1], pair_true))

    return trials_pairs


class SpeakerModule(LightningModule):

    def __init__(self, config_args) -> None:
        super().__init__()

        self.config_args = config_args
        # self.train_dir = train_dir
        self.encoder = config_args['embedding_model']
        self.encoder.classifier = config_args['classifier']
        self.softmax = nn.Softmax(dim=1)

        self.loss = SpeakerLoss(config_args)
        self.batch_size = config_args['batch_size']
        self.test_trials = get_trials(config_args['train_trials_path'])
        self.mean_vector = True
        # self.optimizer = optimizer

    def on_train_epoch_start(self) -> None:
        self.train_accuracy = AverageMeter()
        self.train_loss = AverageMeter()

        return super().on_train_epoch_start()

    def on_after_batch_transfer(self, batch: Any, dataloader_idx: int) -> Any:
        # self.print('transfer:, ', time.time() - self.stop_time)
        # self.stop_time = time.time()
        # # return super().on_after_batch_transfer(batch, dataloader_idx)
        return batch

    def training_step(self, batch, batch_idx):
        # training_step defines the train loop.
        # it is independent of forward
        data, label = batch
        logits, embeddings = self.encoder(data)
        loss, other_loss = self.loss(logits, embeddings, label)

        predicted_one_labels = self.softmax(logits)
        predicted_one_labels = torch.max(predicted_one_labels, dim=1)[1]
        batch_correct = (predicted_one_labels == label).sum().item()

        train_batch_accuracy = 100. * batch_correct / len(predicted_one_labels)
        self.train_accuracy.update(
            float(train_batch_accuracy), embeddings.size(0))
        self.train_loss.update(float(loss), embeddings.size(0))

        self.log("Train/All_Loss", float(loss))
        self.log("Train/ALL_Accuracy", train_batch_accuracy)

        return loss

    def on_train_epoch_end(self) -> None:
        self.print("Epoch {:>2d} Loss: {:>7.4f} Accuracy: {:>6.2f}%".format(
            self.current_epoch, self.train_loss.avg, self.train_accuracy.avg))
        return super().on_train_epoch_end()

    def on_validation_epoch_start(self) -> None:
        self.valid_xvectors = []
        self.valid_total_loss = AverageMeter()
        # self.valid_other_loss = AverageMeter()
        self.valid_accuracy = AverageMeter()

        return super().on_validation_epoch_start()

    def validation_step(self, batch, batch_idx, dataloader_idx):
        # this is the validation loop
        data, label = batch
        if data.shape[1] != 1:
            data_shape = data.shape
            data = data.reshape(-1, 1, data_shape[2], data_shape[3])

        logits, embeddings = self.encoder(data)
        # logits = self.decoder(embeddings)

        if isinstance(label[0], str):
            self.valid_xvectors.append((embeddings, label))
            return embeddings, label
        else:
            val_loss, _ = self.loss(logits, embeddings, label)

            predicted_one_labels = self.softmax(logits)
            predicted_one_labels = torch.max(predicted_one_labels, dim=1)[1]
            batch_correct = (predicted_one_labels == label).sum().item()

            self.valid_total_loss.update(
                float(val_loss.item()), predicted_one_labels.size(0))
            self.valid_accuracy.update(
                float(batch_correct / len(predicted_one_labels)), predicted_one_labels.size(0))

            return val_loss

    def on_validation_epoch_end(self) -> None:
        torch.distributed.barrier()
        valid_xvectors = [None for _ in range(
            torch.distributed.get_world_size())]

        torch.distributed.all_gather_object(
            valid_xvectors, self.valid_xvectors)
        uid2embedding = {}
        for v_dict in valid_xvectors:
            if v_dict == None:
                print('None exist.')
            for embedding, uid in v_dict:
                uid2embedding[uid[0]] = embedding

        distances, labels = [], []
        list_a, list_b = [], []
        dist = nn.CosineSimilarity(dim=1)

        for i, (a_uid, b_uid, l) in enumerate(self.test_trials):

            a = uid2embedding[a_uid].cpu()[0]
            b = uid2embedding[b_uid].cpu()[0]

            list_a.append(a/a.norm(2))
            list_b.append(b/b.norm(2))
            labels.append(l)

            if len(list_a) == 256 or i+1 == len(self.test_trials):
                dists = dist.forward(torch.stack(
                    list_a), torch.stack(list_b)).cpu().numpy()
                distances.extend(dists)
                list_a, list_b = [], []

        eer, eer_threshold, accuracy = evaluate_kaldi_eer(distances, labels,
                                                          cos=True, re_thre=True)
        mindcf_01, mindcf_001 = evaluate_kaldi_mindcf(
            distances, labels)
        # pdb.set_trace()
        self.valid_xvectors = []

        self.log("Test/EER", eer*100,  sync_dist=True)
        self.log("Test/threshold", eer_threshold,  sync_dist=True)
        self.log("Test/mindcf_01", mindcf_01,  sync_dist=True)
        self.log("Test/mindcf_001", mindcf_001,  sync_dist=True)

        self.log("Test/mix2", eer*100*mindcf_001,  sync_dist=True)
        self.log("Test/mix8", eer*100*mindcf_01,  sync_dist=True)
        self.log("Test/mix3", eer*100*mindcf_01*mindcf_001,  sync_dist=True)

        self.log("Valid/Loss", self.valid_total_loss.avg, sync_dist=True)
        self.log("Valid/Accuracy",
                 self.validvalid_accuracy_total_loss.avg, sync_dist=True)

        return super().on_validation_epoch_end()

    def on_test_epoch_start(self) -> None:
        self.test_input = self.config_args['test_input']
        self.test_xvector_dir = "%s/Test/epoch_%s" % (
            self.config_args['check_path'].replace('checkpoint', 'xvector'), self.current_epoch)

        self.test_xvectors = []
        if self.test_input == 'fix':
            self.this_test_data = []
            self.this_test_seg = [0]
            self.this_test_uids = []

        return super().on_test_epoch_start()


    def test_step(self, batch, batch_idx):
        # this is the test loop
        data, uid = batch
        vec_shape = data.shape

        if self.test_input == 'fix':
            if vec_shape[1] != 1:
                data = data.reshape(
                    vec_shape[0] * vec_shape[1], 1, vec_shape[2], vec_shape[3])

            self.this_test_data.append(data)
            self.this_test_seg.append(self.this_test_seg[-1] + len(data))
            self.this_test_uids.append(uid)

            batch_size = self.batch_size
            test_length = len(self.trainer.test_dataloaders)

            if torch.cat(self.this_test_data, dim=0).shape[0] >= batch_size or batch_idx + 1 >= test_length-4:
                data = torch.cat(self.this_test_data, dim=0)
                if data.shape[0] > (3 * batch_size):
                    i = 0
                    out = []
                    while i < data.shape[0]:
                        data_part = data[i:(i + batch_size)]
                        model_out = self.encoder(data_part)
                        if isinstance(model_out, tuple):
                            try:
                                _, out_part, _, _ = model_out
                            except:
                                _, out_part = model_out
                        else:
                            out_part = model_out

                        out.append(out_part)
                        i += batch_size

                    out = torch.cat(out, dim=0)
                else:
                    model_out = self.encoder(data)

                    if isinstance(model_out, tuple):
                        try:
                            _, out, _, _ = model_out
                        except:
                            _, out = model_out
                    else:
                        out = model_out

                # out = out.data.cpu().float().numpy()
                # print(out.shape)
                if len(out.shape) == 3:
                    out = out.squeeze(0)

                for i, u in enumerate(self.this_test_uids):
                    uid_vec = out[self.this_test_seg[i]                                  :self.this_test_seg[i + 1]]
                    if self.mean_vector:
                        uid_vec = uid_vec.mean(axis=0, keepdim=True)
                    self.test_xvectors.append((u, uid_vec))

                self.this_test_data = []
                self.this_test_seg = [0]
                self.this_test_uids = []
        else:
            model_out = self.encoder(data)
            if isinstance(model_out, tuple):
                try:
                    _, out, _, _ = model_out
                except:
                    _, out = model_out
            else:
                out = model_out

            self.test_xvectors.append((uid, out))

    def on_test_epoch_end(self) -> None:
        test_xvectors = [None for _ in range(
            torch.distributed.get_world_size())]

        torch.distributed.all_gather_object(
            test_xvectors, self.test_xvectors)

        if torch.distributed.get_rank() == 0:
            uid2embedding = {}

            for v_dict in test_xvectors:
                if v_dict == None:
                    print('None exist.')

                for uid, embedding in v_dict:
                    uid2embedding[uid[0]] = embedding

            distances, labels = [], []
            list_a, list_b = [], []
            dist = nn.CosineSimilarity(dim=1)
            for i, (a_uid, b_uid, l) in enumerate(self.test_trials):

                a = uid2embedding[a_uid].cpu()[0]
                b = uid2embedding[b_uid].cpu()[0]

                list_a.append(a/a.norm(2))
                list_b.append(b/b.norm(2))
                labels.append(l)

                if len(list_a) == 256 or i+1 == len(self.test_trials):
                    dists = dist.forward(torch.stack(
                        list_a), torch.stack(list_b)).cpu().numpy()
                    distances.extend(dists)

                    list_a, list_b = [], []

            eer, eer_threshold, accuracy = evaluate_kaldi_eer(distances, labels,
                                                              cos=True, re_thre=True)
            mindcf_01, mindcf_001 = evaluate_kaldi_mindcf(
                distances, labels)

            result_str = 'For cosine distance, %d pairs:\n' % (
                len(self.test_trials))
            result_str += '\33[91m'
            result_str += '+-------------------+-------------+-------------+---------------+---------------+-------------------+\n'
            result_str += '|{: ^19s}|{: ^13s}|{: ^13s}|{: ^15s}|{: ^15s}|{: ^19s}|\n'.format('Test Set',
                                                                                             'EER (%)',
                                                                                             'Threshold',
                                                                                             'MinDCF-0.01',
                                                                                             'MinDCF-0.001',
                                                                                             'Date')
            result_str += '+-------------------+-------------+-------------+---------------+---------------+-------------------+\n'
            eer = '{:.4f}'.format(eer * 100.)
            threshold = '{:.4f}'.format(eer_threshold)
            mindcf_01 = '{:.4f}'.format(mindcf_01)
            mindcf_001 = '{:.4f}'.format(mindcf_001)
            date = time.strftime("%Y%m%d %H:%M:%S", time.localtime())
            test_set_name = '-'.join(
                self.config_args['train_trials_path'].split('/')[-3:-1])
            result_str += '|{: ^19s}|{: ^13s}|{: ^13s}|{: ^15s}|{: ^15s}|{: ^19s}|'.format(test_set_name,
                                                                                           eer,
                                                                                           threshold,
                                                                                           mindcf_01,
                                                                                           mindcf_001,
                                                                                           date)
            result_str += '\n+-------------------+-------------+-------------+---------------+---------------+-------------------+\n'
            result_str += '\33[0m'

            self.print(result_str)

        # if torch.distributed.get_rank() == 0:
            xvector_dir = self.test_xvector_dir
            if not os.path.exists(xvector_dir):
                os.makedirs(xvector_dir)

            scp_file = xvector_dir + '/xvectors.scp'
            ark_file = xvector_dir + '/xvectors.ark'
            writer = WriteHelper('ark,scp:%s,%s' % (ark_file, scp_file))

            for uid in uid2embedding:
                uid_vec = uid2embedding[uid]
                writer(str(uid), uid_vec.detach().cpu().numpy())

        return super().on_test_epoch_end()

    def configure_optimizers(self):
        config_args = self.config_args

        opt_kwargs = {'lr': config_args['lr'],
                      'lr_decay': config_args['lr_decay'],
                      'weight_decay': config_args['weight_decay'],
                      'dampening': config_args['dampening'],
                      'momentum': config_args['momentum'],
                      'nesterov': config_args['nesterov']}

        optimizer = create_optimizer(
            self.parameters(), config_args['optimizer'], **opt_kwargs)
        scheduler = create_scheduler(optimizer, config_args)

        # torch.optim.Adam(self.parameters(), lr=1e-3)
        # return ({'optimizer': optimizer, 'scheduler': scheduler, 'monitor': 'val_loss'},)
        if 'scheduler_interval' in config_args:
            interval = config_args['scheduler_interval']
        else:
            interval = 'step' if isinstance(
                scheduler, torch.optim.lr_scheduler.CyclicLR) else 'epoch'

        return ({'optimizer': optimizer,
                 'lr_scheduler': {
                     "scheduler": scheduler,
                     "monitor": "Valid/Loss",
                     "interval": interval,
                 }, })
