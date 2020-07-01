# @Author: Sacha Haidinger <sachahai>
# @Date:   2020-06-22T09:36:50+10:00
# @Email:  sacha.haidinger@epfl.ch
# @Project: Learning methods for Cell Profiling
# @Last modified by:   sachahai
# @Last modified time: 2020-06-30T11:58:35+10:00

'''
From a hyper optimization run, go over each model that has been trained and compute
all the different qualitative and quantitative metrics
'''

import os
from r_LCMC import compute_coranking, unsupervised_score
from performance_metrics import classifier_performance
from sklearn import metrics
from MINE_net import compute_MI
import pandas as pd
import numpy as np
from matplotlib.colors import LogNorm
import matplotlib.pyplot as plt


path_to_run = 'optimization/InfoMAX_VAE/Dataset1/run2_MIupgrade_alpha-beta_2020-06-27'+'/'

all_model_folder = [f for f in os.listdir(path_to_run) if not f.startswith('.')]

counter=1
for model_i in all_model_folder:
    if os.path.isdir(path_to_run+model_i):

        print(f'Starting metrics computation for model {counter} out of {len(all_model_folder)-1}')

        model_folder = f'{path_to_run}{model_i}/'

        feature_size = 64*64*3

        metadata_csv = ''
        path_to_VAE = ''

        all_files = [f for f in os.listdir(model_folder) if not f.startswith('.')]
        for file_i in all_files:
            if file_i.endswith('metedata.csv'):
                metadata_csv = model_folder+file_i
            if file_i.endswith('VAE_.pth'):
                path_to_VAE = model_folder+file_i

        #Create a 'metrics' folder if it doesn't already exists
        save_folder = f'{model_folder}metrics/'
        try:
            os.mkdir(save_folder)
        except FileExistsError as e:
            pass



        ###################################################
        ###### Unsupervised Metric and Local Quality Score
        ###################################################

        # #Compute CoRanking Matrice and Save it
        # Q_final = compute_coranking(metadata_csv, feature_size, save_matrix=True, saving_path=save_folder)
        # print('Coranking Matrix computed and saved')
        #
        # #compute unsupervised score from coranking matrix
        # trust, cont, lcmc = unsupervised_score(Q_final)
        # print('Unsupervised score were computed for 20 different Neighborhood size (1-20% of N)')
        #
        # aggregate_score = np.mean(np.stack([trust,cont,lcmc],axis=0),axis=0)
        # x=range(20)
        # trust_AUC = metrics.auc(x,trust)
        # cont_AUC = metrics.auc(x,cont)
        # lcmc_AUC = metrics.auc(x,lcmc)
        # aggregate_AUC = metrics.auc(x,aggregate_score)
        #
        # fig, (ax1,ax2,ax3) = plt.subplots(3,1,sharex=True,figsize=(12,12))
        # ax1.plot(trust,label=f'Model1 - AUC : {trust_AUC:.2f}')
        # ax1.set_title('Trustworthiness')
        # ax1.legend()
        # ax3.set_xlabel('Neighborhood size - % of total datasize')
        # ax3.set_xticks(range(0,20))
        # ax3.set_xticklabels(range(1,21))
        # ax2.plot(cont,label=f'Model1 - AUC : {cont_AUC:.2f}')
        # ax2.set_title('Continuity')
        # ax2.legend()
        # ax3.plot(lcmc,label=f'Model1 - AUC : {lcmc_AUC:.2f}')
        # ax3.set_title('LCMC')
        # ax3.legend()
        # fig.suptitle('Unsupervised evaluation of projection at different scale')
        # plt.savefig(save_folder+'unsup_score_plot.png')
        # plt.close()
        #
        # unsup_score_df = pd.DataFrame({'trust':trust,'cont':cont,
        #     'lcmc':lcmc,'aggregate_score':aggregate_score,
        #     'trust_AUC':trust_AUC,'cont_AUC':cont_AUC,
        #     'lcmc_AUC':lcmc_AUC,'aggregate_AUC':aggregate_AUC})
        # #Save the unsupervised_score to a CSV file
        # unsup_score_df.to_csv(f'{save_folder}unsupervised_score.csv')
        #
        # #Save CoRanking plot Image
        # plt.figure(figsize=(6,6))
        # plt.imshow(Q_final[:800,:800], cmap=plt.cm.gnuplot2_r, norm=LogNorm())
        # plt.title('First 800 Ranks - Coranking Matrix')
        # plt.savefig(save_folder+'coranking_plot.png')
        # plt.close()
        # plt.figure(figsize=(6,6))
        # plt.imshow(Q_final, cmap=plt.cm.gnuplot2_r, norm=LogNorm())
        # plt.title('Full Coranking Matrix')
        # plt.savefig(save_folder+'coranking_plot_zoom.png')
        # plt.close()


        ###################################################
        ###### Mutual Information Score Estimation
        ###################################################

        # print('Computation of MI Score')
        #
        # MI_score = compute_MI(metadata_csv,save_path=save_folder,batch_size=2048,alpha_logit=-4.5,bound_type='infoNCE')
        # MI_score_df = pd.DataFrame({'MI_score':MI_score},index=[0])
        # MI_score_df.to_csv(f'{save_folder}MI_score.csv')
        # plt.close('all')


        ###################################################
        ###### Classifer test accuracy score
        ###################################################

        num_iter=8
        print(f'Computation of classifier accuracy ({num_iter} iterations)')

        print('Metric 1...')
        #Metric 1 : Acc on all test single cells except uniform cluster 7
        _, test_accuracies_m1, _ = classifier_performance(metadata_csv,Metrics=[True,False,False],num_iteration=num_iter)

        print('Metric 2...')
        #Metric 2 : Acc on all strong phenotypical change test single cells except uniform cluster 7
        _, test_accuracies_m2, _ = classifier_performance(metadata_csv,Metrics=[False,True,False],num_iteration=num_iter)

        print('Metric 3...')
        #Metric 3 : Acc on all strong phenotypical change + META_CLUSTER (1&2, 3&4 and 5&6 grouped) test single cells except uniform cluster 7
        _, test_accuracies_m3, _ = classifier_performance(metadata_csv,Metrics=[False,False,True],num_iteration=num_iter)

        mean_acc_m1 = np.mean(test_accuracies_m1)
        std_acc_m1 = np.std(test_accuracies_m1)
        mean_acc_m2 = np.mean(test_accuracies_m2)
        std_acc_m2 = np.std(test_accuracies_m2)
        mean_acc_m3 = np.mean(test_accuracies_m3)
        std_acc_m3 = np.std(test_accuracies_m3)

        accuracy_df = pd.DataFrame({'test_accuracies_m1':test_accuracies_m1,'test_accuracies_m2':test_accuracies_m2,
            'test_accuracies_m3':test_accuracies_m3,'mean_acc_m1':mean_acc_m1,
            'std_acc_m1':std_acc_m1,'mean_acc_m2':mean_acc_m2,
            'std_acc_m2':std_acc_m2,'mean_acc_m3':mean_acc_m3,'std_acc_m3':std_acc_m3})
        accuracy_df.to_csv(f'{save_folder}classifier_acc_score.csv')


        counter += 1




#Run 5h37 min for unsupervised metrics computation
#Run 13h40 min for MI 220 epoch LR 0.0003 BS 2048. A bit unstable need to go less aggressive
#Run 1h4 min for 3 classifier accuracy metrics
