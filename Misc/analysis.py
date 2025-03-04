#!/usr/bin/env python
# encoding: utf-8

"""
@Author: yangwenhao
@Contact: 874681044@qq.com
@Software: PyCharm
@File: analysis.py
@Time: 2022/12/20 下午4:14
@Overview:
"""
import os
import numpy as np
import h5py

def read_hdf5(reader, key):
    with h5py.File(reader, 'r') as r:
        data_flat = r.get(key)[:]
        return data_flat
    
def format_eer_file(file_path):
    assert os.path.exists(file_path)
    eer = []
    mindcf01 = []
    mindcf001 = []
    model_str = ''
    with open(file_path, 'r') as f:
        for l in f.readlines():
            ls = l.split()
            if len(ls) ==0:
                continue
            elif len(ls)< 10:
                model_str = "-".join(ls[1:])
                # print("-".join(ls[1:]))
                test_set=''
                eer = []
                mindcf01 = []
                mindcf001 = []

            elif len(ls)>= 10:
                eer.append(float(ls[3]))
                mindcf01.append(float(ls[7]))
                mindcf001.append(float(ls[9]))
                test_set=ls[1]

            if len(eer)==3:
                print("#|{: ^19s}".format(test_set)+"|  {:>5.2f}±{:<.2f}  |".format(np.mean(eer), np.std(eer)), end=' ')
                print("%.4f±%.4f"%(np.mean(mindcf01), np.std(mindcf01)), end=' ')
                print("| %.4f±%.4f | %s"%(np.mean(mindcf001), np.std(mindcf001), model_str)) 
                
                eer = []
                mindcf01 = []
                mindcf001 = []
                
def format_eer_file_train(file_path):
    assert os.path.exists(file_path)
    eer = []
    mindcf01 = []
    mindcf001 = []
    mix2 = []
    mix3 = []
    model_str = ''
    with open(file_path, 'r') as f:
        for l in f.readlines():
            ls = l.split()
            if len(ls) ==0:
                continue
            elif len(ls)< 10:
                model_str = "-".join(ls[1:])
                # print("-".join(ls[1:]))
                test_set=''
                eer = []
                mindcf01 = []
                mindcf001 = []

            elif len(ls)>= 10:
                eer.append(float(ls[2].rstrip('%,')))
                mindcf01.append(float(ls[6].rstrip(',')))
                mindcf001.append(float(ls[8].rstrip(',')))
                mix2.append(float(ls[10].rstrip(',')))
                mix3.append(float(ls[11].rstrip('.')))
                test_set=''# ls[1]

            if len(eer)==3:
                print("#| {:>5.2f}±{:<.2f} |".format(np.mean(eer), np.std(eer)), end=' ')
                print("%.4f±%.4f"%(np.mean(mindcf01), np.std(mindcf01)), end=' ')
                print("| %.4f±%.4f"%(np.mean(mindcf001), np.std(mindcf001)), end=' ') 
                print("| %.4f±%.4f"%(np.mean(mix2), np.std(mix2)), end=' ') 
                print("| %.4f±%.4f | %s"%(np.mean(mix3), np.std(mix3), model_str)) 
                
                eer = []
                mindcf01 = []
                mindcf001 = []

def format_eer_file_eval(file_path, log=True):
    assert os.path.exists(file_path)
    results = []
    with open(file_path, 'r') as f:
        eer = []
        mindcf01 = []
        mindcf001 = []
        mix2 = []
        mix3 = []
        model_str = ''
        result = []
        
        for l in f.readlines():
            ls = l.split()
            if len(ls) ==0:
                continue
            elif len(ls)< 10:
                model_str = "-".join(ls[1:])
                result.append(model_str)
                
                # print("-".join(ls[1:]))
                test_set=''
                eer = []
                mindcf01 = []
                mindcf001 = []

            elif len(ls)>= 10:
                eer.append(float(ls[1]))
                mindcf01.append(float(ls[5]))
                mindcf001.append(float(ls[7]))
                
                mix2.append(float(ls[1])*float(ls[7]))
                mix3.append(float(ls[1])*float(ls[7])*float(ls[5]))
                test_set=''# ls[1]

            if len(eer)==3:
                if log:
                    print("#| {:>5.2f}±{:<.2f} |".format(np.mean(eer), np.std(eer)), end=' ')
                    print("%.4f±%.4f"%(np.mean(mindcf01), np.std(mindcf01)), end=' ')
                    print("| %.4f±%.4f"%(np.mean(mindcf001), np.std(mindcf001)), end=' ')    
                    print("| %.4f±%.4f"%(np.mean(mix2), np.std(mix2)), end=' ') 
                    print("| %.4f±%.4f | %s"%(np.mean(mix3), np.std(mix3), model_str)) 
                
                result.extend([np.mean(eer), np.std(eer), 
                               np.mean(mindcf01), np.std(mindcf01), 
                               np.mean(mindcf001), np.std(mindcf001),
                               np.mean(mix2), np.std(mix2),
                               np.mean(mix3), np.std(mix3)])
                results.append(result)
                              
                result = []             
                eer = []
                mindcf01 = []
                mindcf001 = []
        
        return results

                
def read_eer_file(file_path):
    assert os.path.exists(file_path)
    eer = []
    mindcf01 = []
    mindcf001 = []

    result_lst = []
    result_idx = []
    with open(file_path, 'r') as f:
        for l in f.readlines():
            ls = l.split()
            if len(ls) ==0:
                continue
            elif len(ls)>= 10:
                eer.append(float(ls[3]))
                mindcf01.append(float(ls[7]))
                mindcf001.append(float(ls[9]))
                test_set=int(ls[1].split(',')[1])-1 #vox1-test-0,1

            if len(eer)==3:
                result_idx.append(test_set)
                result_lst.append([np.mean(eer), np.mean(mindcf01), np.mean(mindcf001)])
                eer = []
                mindcf01 = []
                mindcf001 = []
                
    result_lst = np.array(result_lst)
    result_idx = np.array(result_idx)
    
    return result_idx, result_lst
