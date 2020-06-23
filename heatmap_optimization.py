# @Author: Sacha Haidinger <sachahai>
# @Date:   2020-06-22T15:07:55+10:00
# @Email:  sacha.haidinger@epfl.ch
# @Project: Learning methods for Cell Profiling
# @Last modified by:   sachahai
# @Last modified time: 2020-06-23T11:09:19+10:00


'''
From a folder containing several models trained in a grid-search optimization manner,
plot results of various metrics to assess quality of the learnt latent representation on
a heatmap.
'''

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import pickle as pkl

path_to_run = 'optimization/InfoMAX_VAE/Dataset1/run1_alpha-beta_2020-06-21/'

all_model_folder = [f for f in os.listdir(path_to_run) if not f.startswith('.')]

trust_hm = np.zeros((6,6))
cont_hm = np.zeros((6,6))
lcmc_hm = np.zeros((6,6))
aggregate_hm = np.zeros((6,6))


alpha_list = np.array([0,5,20,100,500,1000])
beta_list = np.array([0,1,5,20,100,500])


for model_i in all_model_folder:
    if os.path.isdir(path_to_run+model_i):

        alpha = int(model_i.split('_')[-3])
        beta = int(model_i.split('_')[-1])
        col = np.where(alpha_list==alpha)[0]
        row = np.where(beta_list==beta)[0]

        score_df = pd.read_csv(path_to_run+model_i+'/'+'metrics/'+'unsupervised_score.csv')

        trust_AUC = score_df.trust_AUC.values[0]
        cont_AUC = score_df.cont_AUC.values[0]
        lcmc_AUC = score_df.lcmc_AUC.values[0]
        aggregate_AUC = score_df.aggregate_AUC.values[0]

        trust_hm[row,col] = trust_AUC
        cont_hm[row,col] = cont_AUC
        lcmc_hm[row,col] = lcmc_AUC
        aggregate_hm[row,col] = aggregate_AUC


list_map = [trust_hm,cont_hm,lcmc_hm,aggregate_hm]
list_name = ['trustworthiness','continuity','lcmc','aggregate_score']

for i, map in enumerate(list_map):

    ind_max = np.unravel_index(np.argmax(map),(6,6))

    fig, ax = plt.subplots(1,1,figsize=(8,8))
    im = ax.imshow(map,interpolation='bilinear',origin='lower',cmap='viridis')
    ax.set_xticks(np.arange(len(alpha_list)))
    ax.set_yticks(np.arange(len(beta_list)))
    ax.set_xticklabels(alpha_list)
    ax.set_yticklabels(beta_list)
    ax.set_xlim(0,len(alpha_list)-1)
    ax.set_ylim(0,len(beta_list)-1)
    ax.set_xlabel('alpha')
    ax.set_ylabel('beta')
    x,y=np.meshgrid(np.arange(len(alpha_list)),np.arange(len(beta_list)))
    ax.scatter(x,y,c='r',marker='.',s=100,clip_on=False)
    ax.scatter(ind_max[1],ind_max[0],marker='X',s=300,c='purple',clip_on=False)

    ax.set_title(f'Grid Search on alpha & beta parameters, metric : {list_name[i]}')
    fig.colorbar(im)
    plt.savefig(path_to_run+f'{list_name[i]}_heatmap.png')

    name_pkl = path_to_run+f'{list_name[i]}_heatmap.pkl'
    with open(name_pkl, 'wb') as f:
        pkl.dump(map, f, protocol=pkl.HIGHEST_PROTOCOL)






results = np.array([[1,1,1],[370,41,5],[6,7,8]])
np.argmax(results)
np.unravel_index(3,(3,3))

# #results = np.array([[1,2],[3,4],[6,7]])
#
# a = [1,5,100] # Alpha will be on COLUMN from left to right
# b = [1,10,100] # Beta will be on ROW from bottom to top
#
# fig, ax = plt.subplots(1,1,figsize=(8,8))
# im = ax.imshow(results,interpolation='bilinear',origin='lower',cmap='magma')
# ax.set_xticks(np.arange(len(a)))
# ax.set_yticks(np.arange(len(b)))
# ax.set_xticklabels(a)
# ax.set_yticklabels(b)
# ax.set_xlim(0,len(a)-1)
# ax.set_ylim(0,len(b)-1)
# ax.set_xlabel('alpha')
# ax.set_ylabel('beta')
# x,y=np.meshgrid(np.arange(len(a)),np.arange(len(b)))
# ax.scatter(x,y,c='r',marker='.',s=100,clip_on=False)
# ax.set_title('Grid Search on alpha & beta parameters')
# fig.colorbar(im)