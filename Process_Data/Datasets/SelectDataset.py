#!/usr/bin/env python
# encoding: utf-8
'''
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: VS Code
@File: SelectDataset.py
@Time: 2024/01/09 16:08
@Overview: 
'''

from typing import Any
import torch
import copy
import os
import pandas as pd
import random
import numpy as np
from tqdm import tqdm
from torch.nn.parallel import DistributedDataParallel

def main_process():
    if (torch.distributed.is_initialized() and torch.distributed.get_rank() == 0) or not torch.distributed.is_initialized():
        return True

    return False

class SelectSubset(object):
    def __init__(self, train_dir, args, fraction=0.5,
                 random_seed=None, save_dir='',**kwargs) -> None:
        if fraction <= 0.0 or fraction > 1.0:
            raise ValueError("Illegal Coreset Size.")
        
        self.train_dir = train_dir
        self.num_classes = len(train_dir.speakers)
        self.save_dir = save_dir
        if self.save_dir != '' and not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        
        self.fraction = fraction
        self.random_seed = random_seed
        self.index = []
        self.args = args

        self.n_train = len(train_dir)
        self.coreset_size = round(self.n_train * fraction)
        self.iteration = 0

    def before_run(self):
        if isinstance(self.model, DistributedDataParallel):
            self.model = self.model.module

    def select(self, **kwargs):
        return
    
    def save_subset(self, top_examples):
        if self.save_dir != '' and main_process():
            sub_utts = [self.train_dir.base_utts[t] for t in top_examples]
            train_utts = pd.DataFrame(sub_utts, columns=['uid', 'start', 'end'])
            train_utts.to_csv(os.path.join(self.save_dir, 'subtrain.{}.csv'.format(self.iteration)),
                              index=None)
    

class GraNd(SelectSubset):
    def __init__(self, train_dir, args, fraction=0.5,
                 random_seed=1234, repeat=4, select_aug=False,
                 save_dir='',
                 model=None, balance=False, **kwargs):
        
        super(GraNd, self).__init__(train_dir, args, fraction, random_seed, save_dir)
        
        # self.epochs = epochs
        self.model = model
        self.repeat = repeat
        self.balance = balance
        self.select_aug = select_aug
        self.device = model.device        

        self.random_seed += torch.distributed.get_rank()

    def while_update(self, outputs, loss, targets, epoch, batch_idx, batch_size):
        if batch_idx % self.args.print_freq == 0:
            print('| Epoch [%3d/%3d] Iter[%3d/%3d]\t\tLoss: %.4f' % (
                epoch, self.epochs, batch_idx + 1, (self.n_train // batch_size) + 1, loss.item()))

    def before_run(self):
        if isinstance(self.model, DistributedDataParallel):
            self.model = self.model.module

    def run(self):
        # seeding
        torch.manual_seed(self.random_seed)
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)
        
        batch_size = self.args['batch_size'] // 2 if not self.select_aug else self.args['batch_size'] // 4
        num_classes = self.args['num_classes']

        # self.model.embedding_recorder.record_embedding = True  # recording embedding vector
        self.model.eval()

        embedding_dim = self.model.embedding_size #get_last_layer().in_features
        batch_loader = torch.utils.data.DataLoader(
            self.train_dir, batch_size=batch_size, num_workers=self.args['nj'])
        sample_num = self.n_train

        if torch.distributed.get_rank() == 0 :
            pbar = tqdm(enumerate(batch_loader), total=len(batch_loader), ncols=50)
        else:
            pbar = enumerate(batch_loader)

        for i, (data, label) in pbar:
            # self.model_optimizer.zero_grad()
            if self.select_aug:
                with torch.no_grad():
                    wavs_aug_tot = []
                    labels_aug_tot = []
                    wavs_aug_tot.append(data.cuda()) # data_shape [batch, 1,1,time]
                    labels_aug_tot.append(label.cuda())

                    wavs = data.squeeze().cuda()
                    wav_label = label.squeeze().cuda()

                    for augment in self.args['augment_pipeline']:
                        # Apply augment
                        wavs_aug = augment(wavs, torch.tensor([1.0]*len(wavs)).cuda())
                        # Managing speed change
                        if wavs_aug.shape[1] > wavs.shape[1]:
                            wavs_aug = wavs_aug[:, 0 : wavs.shape[1]]
                        else:
                            zero_sig = torch.zeros_like(wavs)
                            zero_sig[:, 0 : wavs_aug.shape[1]] = wavs_aug
                            wavs_aug = zero_sig

                        if 'concat_augment' in self.args and self.args['concat_augment']:
                            wavs_aug_tot.append(wavs_aug.unsqueeze(1).unsqueeze(1))
                            labels_aug_tot.append(wav_label)
                        else:
                            wavs = wavs_aug
                            wavs_aug_tot[0] = wavs_aug.unsqueeze(1).unsqueeze(1)
                            labels_aug_tot[0] = wav_label
                    
                    data = torch.cat(wavs_aug_tot, dim=0)
                    label = torch.cat(labels_aug_tot)

            classfier, embedding = self.model(data.to(self.device))
            # outputs = self.model(input)
            # loss    = self.criterion(outputs.requires_grad_(True),
            #                       targets.to(self.args.device)).sum()
            loss, _ = self.model.loss(classfier, label.to(self.device),
                                        batch_weight=None, other=True)
            
            batch_num = classfier.shape[0]
            with torch.no_grad():
                bias_parameters_grads = torch.autograd.grad(loss, classfier)[0]
                grad_norm = torch.norm(torch.cat([bias_parameters_grads, (
                        embedding.view(batch_num, 1, embedding_dim).repeat(1,
                                             num_classes, 1) * bias_parameters_grads.view(
                                             batch_num, num_classes, 1).repeat(1, 1, embedding_dim)).
                                             view(batch_num, -1)], dim=1), dim=1, p=2)
                
                if self.select_aug:
                    grad_norm = grad_norm.reshape(len(self.args['augment_pipeline']), -1)
                    grad_norm = grad_norm.mean(dim=0)

                self.norm_matrix[i * batch_size:min((i + 1) * batch_size, sample_num),
                self.cur_repeat] = grad_norm
                
            # if i > 100: 
            #     break
        # self.model.train()
        # self.model.embedding_recorder.record_embedding = False

    def select(self, model, **kwargs):
        self.model = model
        self.before_run()
        
        # Initialize a matrix to save norms of each sample on idependent runs
        self.train_indx = np.arange(self.n_train)
        self.norm_matrix = torch.zeros([self.n_train, self.repeat],
                                       requires_grad=False).to(self.device)

        for self.cur_repeat in range(self.repeat):
            self.run()
            self.random_seed = self.random_seed + 5

        norm_mean = torch.mean(self.norm_matrix, dim=1).cpu().detach().numpy()

        torch.distributed.barrier()
        norm_means = [None for _ in range(torch.distributed.get_world_size())]
        torch.distributed.all_gather_object(norm_means, norm_mean)
        norm_mean = np.mean(norm_means, axis=0)
        self.norm_mean = norm_mean

        if not self.balance:
            top_examples = self.train_indx[np.argsort(self.norm_mean)][::-1][:self.coreset_size]
        else:
            top_examples = np.array([], dtype=np.int64)
            uids = [utts[0] for utts in self.train_dir.base_utts]
            sids = [self.train_dir.utt2spk_dict[uid] for uid in uids]
            label = np.array([self.train_dir.spk_to_idx[sid] for sid in sids])
            
            for c in range(self.num_classes):
                c_indx = self.train_indx[label == c]
                budget = round(self.fraction * len(c_indx))
                top_examples = np.append(top_examples, c_indx[np.argsort(self.norm_mean[c_indx])[::-1][:budget]])

        self.save_subset(top_examples)
        # subtrain_dir = copy.deepcopy(self.train_dir)
        subtrain_dir = torch.utils.data.Subset(self.train_dir, top_examples)
        self.iteration += 1

        return subtrain_dir


class LossSelect(SelectSubset):
    def __init__(self, train_dir, args, fraction=0.5,
                 random_seed=1234, repeat=4, select_aug=False,
                 save_dir='',
                 model=None, balance=False, **kwargs):
        
        super(LossSelect, self).__init__(train_dir, args, fraction, random_seed,
                                        save_dir)
        
        # self.epochs = epochs
        self.model = model
        self.repeat = repeat
        self.balance = balance
        self.select_aug = select_aug
        self.device = model.device        

        self.random_seed += torch.distributed.get_rank()

    def while_update(self, outputs, loss, targets, epoch, batch_idx, batch_size):
        if batch_idx % self.args.print_freq == 0:
            print('| Epoch [%3d/%3d] Iter[%3d/%3d]\t\tLoss: %.4f' % (
                epoch, self.epochs, batch_idx + 1, (self.n_train // batch_size) + 1, loss.item()))

    def before_run(self):
        if isinstance(self.model, DistributedDataParallel):
            self.model = self.model.module

    def run(self):
        # seeding
        torch.manual_seed(self.random_seed)
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)
        
        batch_size = self.args['batch_size'] // 2 if not self.select_aug else self.args['batch_size'] // 4
        num_classes = self.args['num_classes']

        # self.model.embedding_recorder.record_embedding = True  # recording embedding vector
        self.model.eval()
        previous_reduction = self.model.loss.reduction
        self.model.loss.reduction = 'none'

        embedding_dim = self.model.embedding_size #get_last_layer().in_features
        batch_loader = torch.utils.data.DataLoader(
            self.train_dir, batch_size=batch_size, num_workers=self.args['nj'])
        sample_num = self.n_train

        if torch.distributed.get_rank() == 0 :
            pbar = tqdm(enumerate(batch_loader), total=len(batch_loader), ncols=50)
        else:
            pbar = enumerate(batch_loader)

        for i, (data, label) in pbar:
            # self.model_optimizer.zero_grad()
            if self.select_aug:
                with torch.no_grad():
                    wavs_aug_tot = []
                    labels_aug_tot = []
                    wavs_aug_tot.append(data.cuda()) # data_shape [batch, 1,1,time]
                    labels_aug_tot.append(label.cuda())

                    wavs = data.squeeze().cuda()
                    wav_label = label.squeeze().cuda()

                    for augment in self.args['augment_pipeline']:
                        # Apply augment
                        wavs_aug = augment(wavs, torch.tensor([1.0]*len(wavs)).cuda())
                        # Managing speed change
                        if wavs_aug.shape[1] > wavs.shape[1]:
                            wavs_aug = wavs_aug[:, 0 : wavs.shape[1]]
                        else:
                            zero_sig = torch.zeros_like(wavs)
                            zero_sig[:, 0 : wavs_aug.shape[1]] = wavs_aug
                            wavs_aug = zero_sig

                        if 'concat_augment' in self.args and self.args['concat_augment']:
                            wavs_aug_tot.append(wavs_aug.unsqueeze(1).unsqueeze(1))
                            labels_aug_tot.append(wav_label)
                        else:
                            wavs = wavs_aug
                            wavs_aug_tot[0] = wavs_aug.unsqueeze(1).unsqueeze(1)
                            labels_aug_tot[0] = wav_label
                    
                    data = torch.cat(wavs_aug_tot, dim=0)
                    label = torch.cat(labels_aug_tot)

            with torch.no_grad():
                classfier, _ = self.model(data.to(self.device))
                loss, _ = self.model.loss(classfier, label.to(self.device),
                                            batch_weight=None, other=True)
            
                self.norm_matrix[i * batch_size:min((i + 1) * batch_size, sample_num),
                self.cur_repeat] = loss
        
        self.model.loss.reduction = previous_reduction

    def select(self, model, **kwargs):
        self.model = model
        self.before_run()
        
        # Initialize a matrix to save norms of each sample on idependent runs
        self.train_indx = np.arange(self.n_train)
        self.norm_matrix = torch.zeros([self.n_train, self.repeat],
                                       requires_grad=False).to(self.device)

        for self.cur_repeat in range(self.repeat):
            self.run()
            self.random_seed = self.random_seed + 5

        norm_mean = torch.mean(self.norm_matrix, dim=1).cpu().detach().numpy()

        torch.distributed.barrier()
        norm_means = [None for _ in range(torch.distributed.get_world_size())]
        torch.distributed.all_gather_object(norm_means, norm_mean)
        norm_mean = np.mean(norm_means, axis=0)
        self.norm_mean = norm_mean

        if not self.balance:
            top_examples = self.train_indx[np.argsort(self.norm_mean)][::-1][:self.coreset_size]
        else:
            top_examples = np.array([], dtype=np.int64)
            uids = [utts[0] for utts in self.train_dir.base_utts]
            sids = [self.train_dir.utt2spk_dict[uid] for uid in uids]
            label = [self.train_dir.spk_to_idx[sid] for sid in sids] 
            
            for c in range(self.num_classes):
                c_indx = self.train_indx[label == c]
                budget = round(self.fraction * len(c_indx))
                top_examples = np.append(top_examples, c_indx[np.argsort(self.norm_mean[c_indx])[::-1][:budget]])

        self.save_subset(top_examples)
        # subtrain_dir = copy.deepcopy(self.train_dir)
        subtrain_dir = torch.utils.data.Subset(self.train_dir, top_examples)
        self.iteration += 1

        return subtrain_dir
        # return {"indices": top_examples, "scores": self.norm_mean}


class GradMatch(SelectSubset):
    def __init__(self, train_dir, args, fraction=0.5, 
                 random_seed=None, repeat=4, 
                 save_dir='',
                 epochs=200, model=None, select_aug=False,
                 balance=True, dst_val=None, lam: float = 1., **kwargs):
        
        super(GradMatch, self).__init__(train_dir, args, fraction, random_seed)
        self.balance = balance
        self.dst_val = dst_val

    def num_classes_mismatch(self):
        raise ValueError("num_classes of pretrain dataset does not match that of the training dataset.")

    def while_update(self, outputs, loss, targets, epoch, batch_idx, batch_size):
        if batch_idx % self.args.print_freq == 0:
            print('| Epoch [%3d/%3d] Iter[%3d/%3d]\t\tLoss: %.4f' % (
                epoch, self.epochs, batch_idx + 1, (self.n_pretrain_size // batch_size) + 1, loss.item()))

    def orthogonal_matching_pursuit(self, A, b, budget: int, lam: float = 1.):
        '''approximately solves min_x |x|_0 s.t. Ax=b using Orthogonal Matching Pursuit
        Acknowlegement to:
        https://github.com/krishnatejakk/GradMatch/blob/main/GradMatch/selectionstrategies/helpers/omp_solvers.py
        Args:
          A: design matrix of size (d, n)
          b: measurement vector of length d
          budget: selection budget
          lam: regularization coef. for the final output vector
        Returns:
           vector of length n
        '''
        with torch.no_grad():
            d, n = A.shape
            if budget <= 0:
                budget = 0
            elif budget > n:
                budget = n

            x = np.zeros(n, dtype=np.float32)
            resid = b.clone()
            indices = []
            boolean_mask = torch.ones(n, dtype=bool, device="cuda")
            all_idx = torch.arange(n, device='cuda')

            for i in range(budget):
                if i % self.args.print_freq == 0:
                    print("| Selecting [%3d/%3d]" % (i + 1, budget))
                projections = torch.matmul(A.T, resid)
                index = torch.argmax(projections[boolean_mask])
                index = all_idx[boolean_mask][index]

                indices.append(index.item())
                boolean_mask[index] = False

                if indices.__len__() == 1:
                    A_i = A[:, index]
                    x_i = projections[index] / torch.dot(A_i, A_i).view(-1)
                    A_i = A[:, index].view(1, -1)
                else:
                    A_i = torch.cat((A_i, A[:, index].view(1, -1)), dim=0)
                    temp = torch.matmul(A_i, torch.transpose(A_i, 0, 1)) + lam * torch.eye(A_i.shape[0], device="cuda")
                    x_i, _ = torch.lstsq(torch.matmul(A_i, b).view(-1, 1), temp)
                resid = b - torch.matmul(torch.transpose(A_i, 0, 1), x_i).view(-1)
            if budget > 1:
                x_i = nnls(temp.cpu().numpy(), torch.matmul(A_i, b).view(-1).cpu().numpy())[0]
                x[indices] = x_i
            elif budget == 1:
                x[indices[0]] = 1.
        return x

    def orthogonal_matching_pursuit_np(self, A, b, budget: int, lam: float = 1.):
        '''approximately solves min_x |x|_0 s.t. Ax=b using Orthogonal Matching Pursuit
        Acknowlegement to:
        https://github.com/krishnatejakk/GradMatch/blob/main/GradMatch/selectionstrategies/helpers/omp_solvers.py
        Args:
          A: design matrix of size (d, n)
          b: measurement vector of length d
          budget: selection budget
          lam: regularization coef. for the final output vector
        Returns:
           vector of length n
        '''
        d, n = A.shape
        if budget <= 0:
            budget = 0
        elif budget > n:
            budget = n

        x = np.zeros(n, dtype=np.float32)
        resid = np.copy(b)
        indices = []
        boolean_mask = np.ones(n, dtype=bool)
        all_idx = np.arange(n)

        for i in range(budget):
            if i % self.args.print_freq == 0:
                print("| Selecting [%3d/%3d]" % (i + 1, budget))
            projections = A.T.dot(resid)
            index = np.argmax(projections[boolean_mask])
            index = all_idx[boolean_mask][index]

            indices.append(index.item())
            boolean_mask[index] = False

            if indices.__len__() == 1:
                A_i = A[:, index]
                x_i = projections[index] / A_i.T.dot(A_i)
            else:
                A_i = np.vstack([A_i, A[:, index]])
                x_i = lstsq(A_i.dot(A_i.T) + lam * np.identity(A_i.shape[0]), A_i.dot(b))[0]
            resid = b - A_i.T.dot(x_i)
        if budget > 1:
            x_i = nnls(A_i.dot(A_i.T) + lam * np.identity(A_i.shape[0]), A_i.dot(b))[0]
            x[indices] = x_i
        elif budget == 1:
            x[indices[0]] = 1.
        return x

    def calc_gradient(self, index=None, val=False):
        self.model.eval()
        if val:
            batch_loader = torch.utils.data.DataLoader(
                self.dst_val if index is None else torch.utils.data.Subset(self.dst_val, index),
                batch_size=self.args.selection_batch, num_workers=self.args.workers)
            sample_num = len(self.dst_val.targets) if index is None else len(index)
        else:
            batch_loader = torch.utils.data.DataLoader(
                self.train_dir if index is None else torch.utils.data.Subset(self.train_dir, index),
                batch_size=self.args.selection_batch, num_workers=self.args.workers)
            sample_num = self.n_train if index is None else len(index)

        self.embedding_dim = self.model.get_last_layer().in_features
        gradients = torch.zeros([sample_num, self.args.num_classes * (self.embedding_dim + 1)],
                                requires_grad=False, device=self.args.device)

        for i, (input, targets) in enumerate(batch_loader):
            self.model_optimizer.zero_grad()
            outputs = self.model(input.to(self.args.device)).requires_grad_(True)
            loss = self.criterion(outputs, targets.to(self.args.device)).sum()
            batch_num = targets.shape[0]
            with torch.no_grad():
                bias_parameters_grads = torch.autograd.grad(loss, outputs, retain_graph=True)[0].cpu()
                weight_parameters_grads = self.model.embedding_recorder.embedding.cpu().view(batch_num, 1,
                                                    self.embedding_dim).repeat(1,self.args.num_classes,1) *\
                                                    bias_parameters_grads.view(batch_num, self.args.num_classes,
                                                    1).repeat(1, 1, self.embedding_dim)
                gradients[i * self.args.selection_batch:min((i + 1) * self.args.selection_batch, sample_num)] =\
                    torch.cat([bias_parameters_grads, weight_parameters_grads.flatten(1)], dim=1)

        return gradients

    def select(self, model, **kwargs):
        self.model = model
        self.before_run()

        self.model.no_grad = True
        with self.model.embedding_recorder:
            if self.dst_val is not None:
                val_num = len(self.dst_val.targets)

            if self.balance:
                selection_result = np.array([], dtype=np.int64)
                weights = np.array([], dtype=np.float32)
                for c in range(self.args.num_classes):
                    class_index = np.arange(self.n_train)[self.dst_train.targets == c]
                    cur_gradients = self.calc_gradient(class_index)
                    if self.dst_val is not None:
                        # Also calculate gradients of the validation set.
                        val_class_index = np.arange(val_num)[self.dst_val.targets == c]
                        cur_val_gradients = torch.mean(self.calc_gradient(val_class_index, val=True), dim=0)
                    else:
                        cur_val_gradients = torch.mean(cur_gradients, dim=0)
                    if self.args.device == "cpu":
                        # Compute OMP on numpy
                        cur_weights = self.orthogonal_matching_pursuit_np(cur_gradients.numpy().T,
                                                                          cur_val_gradients.numpy(),
                                                                        budget=round(len(class_index) * self.fraction))
                    else:
                        cur_weights = self.orthogonal_matching_pursuit(cur_gradients.to(self.args.device).T,
                                                                       cur_val_gradients.to(self.args.device),
                                                                       budget=round(len(class_index) * self.fraction))
                    selection_result = np.append(selection_result, class_index[np.nonzero(cur_weights)[0]])
                    weights = np.append(weights, cur_weights[np.nonzero(cur_weights)[0]])
            else:
                cur_gradients = self.calc_gradient()
                if self.dst_val is not None:
                    # Also calculate gradients of the validation set.
                    cur_val_gradients = torch.mean(self.calc_gradient(val=True), dim=0)
                else:
                    cur_val_gradients = torch.mean(cur_gradients, dim=0)
                if self.args.device == "cpu":
                    # Compute OMP on numpy
                    cur_weights = self.orthogonal_matching_pursuit_np(cur_gradients.numpy().T,
                                                                      cur_val_gradients.numpy(),
                                                                      budget=self.coreset_size)
                else:
                    cur_weights = self.orthogonal_matching_pursuit(cur_gradients.T, cur_val_gradients,
                                                                   budget=self.coreset_size)
                selection_result = np.nonzero(cur_weights)[0]
                weights = cur_weights[selection_result]
        self.model.no_grad = False
        return {"indices": selection_result, "weights": weights}

    def select(self, **kwargs):
        selection_result = self.run()
        return selection_result

class RandomSelect(SelectSubset):
    def __init__(self, train_dir, args, fraction=0.5,
                 random_seed=1234, repeat=4,
                 model=None, balance=False, **kwargs):
        
        super().__init__(train_dir, args, fraction, random_seed, model)
        
        self.model = model
        self.repeat = repeat
        self.balance = balance
        
    def select(self, **kwargs):
        
        torch.manual_seed(self.random_seed)
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)
        self.random_seed = self.random_seed + 5
        
        # Initialize a matrix to save norms of each sample on idependent runs
        self.train_indx = np.arange(self.n_train)
        norm_mean = np.random.uniform(0, 1, self.n_train)

        torch.distributed.barrier()
        norm_means = [None for _ in range(torch.distributed.get_world_size())]
        torch.distributed.all_gather_object(norm_means, norm_mean)
        norm_mean = np.mean(norm_means, axis=0)
        self.norm_mean = norm_mean
        
        # if not self.balance:
        #     random.shuffle(self.train_indx)
        #     top_examples = self.train_indx[:self.coreset_size]
        # else:
        #     top_examples = np.array([], dtype=np.int64)
        #     uids = [utts[0] for utts in self.train_dir.base_utts]
        #     sids = [self.train_dir.utt2spk_dict[uid] for uid in uids]
        #     label = [self.train_dir.spk_to_idx[sid] for sid in sids] 
        
        #     for c in range(self.num_classes):
        #         c_indx = self.train_indx[label == c]
        #         random.shuffle(c_indx)
                
        #         budget = round(self.fraction * len(c_indx))
        #         top_examples = np.append(top_examples, c_indx[:budget])
        if not self.balance:
            top_examples = self.train_indx[np.argsort(self.norm_mean)][::-1][:self.coreset_size]
        else:
            top_examples = np.array([], dtype=np.int64)
            uids = [utts[0] for utts in self.train_dir.base_utts]
            sids = [self.train_dir.utt2spk_dict[uid] for uid in uids]
            label = [self.train_dir.spk_to_idx[sid] for sid in sids] 
            
            for c in range(self.num_classes):
                c_indx = self.train_indx[label == c]
                budget = round(self.fraction * len(c_indx))
                top_examples = np.append(top_examples, c_indx[np.argsort(self.norm_mean[c_indx])[::-1][:budget]])
                
        # subtrain_dir = copy.deepcopy(self.train_dir)
        # original_utts = subtrain_dir.base_utts
        # sub_utts = [original_utts[i] for i in top_examples]
        # random.shuffle(sub_utts)
        # subtrain_dir.base_utts = sub_utts
        
        subtrain_dir = torch.utils.data.Subset(self.train_dir, top_examples)

        return subtrain_dir
    
        # return {"indices": top_examples, "scores": self.norm_mean}
