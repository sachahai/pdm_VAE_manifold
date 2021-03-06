# @Author: Sacha Haidinger <sachahai>
# @Date:   2020-04-20T08:16:22+10:00
# @Email:  sacha.haidinger@epfl.ch
# @Project: Learning methods for Cell Profiling
# @Last modified by:   sachahai
# @Last modified time: 2020-08-26T16:58:12+10:00

'''File containing various functions to visualize latent representations learnt
from a model and to save / load model. '''

###############################
####### Imports ###############
###############################
import sys, os
import pandas as pd
import numpy as np
import itertools
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms
import matplotlib.colors
import matplotlib.cm
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline

import torch
from torch.autograd import Variable
from torch import nn
from torch import cuda
from torchvision.utils import save_image, make_grid

##############################################
######## Match Latent Code and Ground Truth
##############################################

def metadata_latent_space(model, infer_dataloader, train_on_gpu, GT_csv_path, save_csv=False, with_rawdata=False, csv_path='no_name_specified.csv'):
    '''
    Once a VAE model is trained, take its predictions (3D latent code) and store it in a csv
    file alongside the ground truth information. Useful for plots and downstream analyses.

    Params :
        - model (nn.Module) :  trained Pytorch VAE model that will produce latent codes of dataset
        - inder_dataloader (DataLoader) : Dataloader that iterates the dataset by batch
        - train_on_gpu (boolean) : Wheter infer latent codes on GPU or not.
        - GT_csv_path (string) : path to a csv file that contains all the ground truth information
                to keep alongside the latent codes. A column 'Unique_ID' (the name of the tiff files)
                needs to be present to match latent code and ground truth
        - save_csv (boolean) : If False, the new Panda DataFrame in only returned.
        - csv_path (string) : the path where to store a new csv file that contains the matched
                latent code and ground truth. Ignored if 'save_csv' is False
        - with_rawdata (boolean): If True, the raw data (images pixels) is also save in the csv file

    Return :
        - MetaData_csv (Pandas DataFrame) : DataFrame that contains both latent codes and ground truth, matched
    '''
    labels_list = []
    z_list = []
    id_list = []
    list_of_tensors = [] #Store raw_data for performance metrics

    if model.zdim > 3 :
        print(f'Latent space is >3D ({model.zdim} dimensional), no visualization is provided')
        return None

    ###### Iterate throughout inference dataset #####
    #################################################

    for i, (data, labels, file_names) in enumerate(infer_dataloader):
        #Extract unique cell id from file_names
        id_list.append([file_name for file_name in file_names])
        if train_on_gpu:
            # make sure this lives on the GPU
            data = data.cuda()
        with torch.no_grad():
            model.eval()
            if with_rawdata:
                raw_data = data.view(data.size(0),-1) #B x HxWxC
                list_of_tensors.append(raw_data.data.cpu().numpy())

            data = Variable(data, requires_grad=False)
            z, _ = model.encode(data)
            z = z.view(-1,model.zdim)
            z_list.append((z.data).cpu().numpy())
            labels_list.append(labels.numpy())

        print(f'In progress...{i*len(data)}/{len(infer_dataloader.dataset)}',end='\r')

    ###### Matching samples to metadata info #####
    #################################################

    unique_ids = list(itertools.chain.from_iterable(id_list))

    ###### Store raw data in a separate data frame #####
    if with_rawdata:
        raw_data = np.concatenate(list_of_tensors,axis=0)
        rawdata_frame = pd.DataFrame(data=raw_data[0:,0:],
                                index=[i for i in range(raw_data.shape[0])],
                               columns=['feature'+str(i) for i in range(raw_data.shape[1])])
        rawdata_frame['Unique_ID']=np.nan
        rawdata_frame.Unique_ID=unique_ids
        rawdata_frame = rawdata_frame.sort_values(by=['Unique_ID'])

    ##### Store latent code in a temporary dataframe #####
    z_points = np.concatenate(z_list,axis=0) # datasize x 3
    true_label = np.concatenate(labels_list,axis=0)

    temp_matching_df = pd.DataFrame(columns=['VAE_x_coord','VAE_y_coord','VAE_z_coord','Unique_ID'])
    temp_matching_df.VAE_x_coord = z_points[:,0]
    temp_matching_df.VAE_y_coord = z_points[:,1]
    if model.zdim == 3 :
        temp_matching_df.VAE_z_coord = z_points[:,2]
    else:
        temp_matching_df.VAE_z_coord = 0
    temp_matching_df.Unique_ID = unique_ids
    temp_matching_df = temp_matching_df.sort_values(by=['Unique_ID'])


    ##### Load Ground Truth information about the dataset #####
    MetaData_csv = pd.read_csv(GT_csv_path)
    MetaData_csv = MetaData_csv.sort_values(by=['Unique_ID'])

    ##### Match latent code information with ground truth info #####
    assert np.all(temp_matching_df.Unique_ID.values == MetaData_csv.Unique_ID.values), "Inference dataset doesn't match with csv metadata"
    MetaData_csv = MetaData_csv.join(temp_matching_df.set_index('Unique_ID'), on='Unique_ID')

    ##### Match raw data information with ground truth info #####
    if with_rawdata:
        assert np.all(rawdata_frame.Unique_ID.values == MetaData_csv.Unique_ID.values), "Inference dataset doesn't match with csv metadata"
        MetaData_csv = MetaData_csv.join(rawdata_frame.set_index('Unique_ID'), on='Unique_ID')

    #### Save Final CSV file #####
    if save_csv:
        MetaData_csv.to_csv(csv_path,index=False)
        print(f'Final CSV saved to : {csv_path}')

    return MetaData_csv


##############################################
######## Visualization
##############################################

def save_reconstruction(loader,VAE,save_path,train_on_gpu):
    ''' Show (and save) reconstruction produced by a trained VAE model of 4 random
    samples, alongside 8 newly generated samples, sampled from the prior dataset3_class_distribution

    Params :
        - loader (DataLoader) : Dataloader that iterates the dataset by batch
        - VAE (nn.Module) :  trained Pytorch VAE model that will produce latent codes of dataset
        - save_path (string) : path where to save figures
        - train_on_gpu (boolean) : Wheter infer latent codes on GPU or not.
    '''

    data, _, _ = next(iter(loader))
    if train_on_gpu:
        data = Variable(data,requires_grad=False).cuda()
    x_recon,_,_,_=VAE(data)
    img_grid = make_grid(torch.cat((data[:4,:3,:,:],nn.Sigmoid()(x_recon[:4,:3,:,:]))), nrow=4, padding=12, pad_value=1)

    pre,ext = os.path.splitext(save_path)

    plt.figure(figsize=(10,5))
    plt.imshow(img_grid.detach().cpu().permute(1,2,0))
    plt.axis('off')
    plt.title(f'Example data and its reconstruction')
    plt.savefig(pre+'reconstructions.png')

    samples = torch.randn(8, VAE.zdim, 1, 1)
    samples = Variable(samples,requires_grad=False).cuda()
    recon = VAE.decode(samples)
    img_grid = make_grid(nn.Sigmoid()(recon[:,:3,:,:]), nrow=4, padding=12, pad_value=1)

    plt.figure(figsize=(10,5))
    plt.imshow(img_grid.detach().cpu().permute(1,2,0))
    plt.axis('off')
    plt.title(f'Random generated samples')
    plt.savefig(pre+'generatedSamples.png')



def plot_from_csv(path_to_csv,low_dim_names=['VAE_x_coord','VAE_y_coord','VAE_z_coord'],dim=3,num_class=7,column=None,as_str=False):
    '''
    Plot on a plotly figure the latent space produced by any methods, already stored in a csv file.

    Params :
        - path_to_csv (string or pandas DataFrame) : path to a csv file or pandas DataFrame that contains the latent codes
                produced by a considered methods.
        - low_dim_names ([string]) : List of columns names that store the latent code to plot
        - dim (int) : Dimensionality of the latent code
        - num_class (int) : Number of different class. If a number is given, latent code will be color-coded based on the class
                identity (from 1 to num_class) given in the column 'GT_Label'
        - column (string) : Column name that store a ground truth that can be used to color-coded the latent space, rather
                than using the 'GT_Label' class identity
        - as_str (boolean) : If a 'column' name is given, and as_str is set to True, every unique value is considered as a
                class and will be colored by a different color. If set to False and values are int or float, a colorbar is used.

    Example :
    plot_from_csv(path_to_csv=...,low_dim_names=...,num_class=7) : Latent Codes color-coded based on int values (1-7) stored in 'GT_Label' column
    plot_from_csv(path_to_csv=...,low_dim_names=...,column='Shape_Factor',as_str=False) : Latent Codes color-coded based on a color bar that cover the range of ground truth 'Shape_Factor'
    '''
    if isinstance(path_to_csv,str):
        MetaData_csv = pd.read_csv(path_to_csv)
    else:
        MetaData_csv = path_to_csv

    if dim == 3:
        if column==None:
        ##### Fig 1 : Plot each single cell in latent space with GT cluster labels
            traces = []
            for i in range(num_class):
                scatter = go.Scatter3d(x=MetaData_csv[MetaData_csv['GT_label']==i+1][low_dim_names[0]].values,y=MetaData_csv[MetaData_csv['GT_label']==i+1][low_dim_names[1]].values,
                    z=MetaData_csv[MetaData_csv['GT_label']==i+1][low_dim_names[2]].values, mode='markers',
                    marker=dict(size=3, opacity=1),
                    name=f'Cluster {i+1}')
                traces.append(scatter)
            layout= dict(title='Latent Representation, colored by GT clustered')
            fig_3d_1 = go.Figure(data=traces, layout=layout)
            fig_3d_1.update_layout(margin=dict(l=0,r=0,b=0,t=0),showlegend=True,legend=dict(y=-.1))

            return fig_3d_1
        else :
            #Color from the info store in 'column' pass in argument
            if as_str:
                MetaData_csv[column]=MetaData_csv[column].astype(str)
            fig = px.scatter_3d(MetaData_csv,x=low_dim_names[0],y=low_dim_names[1],z=low_dim_names[2],color=column,color_discrete_sequence=px.colors.qualitative.T10+px.colors.qualitative.Alphabet)
            fig.update_traces(marker=dict(size=3))
            return fig

    if dim == 2:

        traces = []
        MS = MetaData_csv
        for i in range(num_class):
            scatter = go.Scatter(x=MS[MetaData_csv['GT_label']==i+1][low_dim_names[0]].values,y=MS[MetaData_csv['GT_label']==i+1][low_dim_names[1]].values,
                mode='markers',
                marker=dict(size=3, opacity=0.8),
                name=f'Cluster {i+1}')
            traces.append(scatter)
        layout= dict(title='Latent Representation, colored by GT clustered')
        fig_2d_1 = go.Figure(data=traces, layout=layout)
        fig_2d_1.update_layout(margin=dict(l=0,r=0,b=0,t=0),showlegend=True)

        return fig_2d_1



def plot_train_result(history, best_epoch=None,save_path=None, infoMAX = False):
    """Display training and validation loss evolution over epochs

    Params
    -------
    history : DataFrame
        Panda DataFrame containing train and valid losses
    best_epoch : int
        If early stopping is used, display the last saved model
    save_path : string
        Path to save the figure
    infoMax : boolean
        If True, an additional loss composant (Mutual Information) is plotted

    Return a matplotlib Figure
    --------
    """

    if  not(infoMAX):
        fig = plt.figure(figsize=(10,10))
        ax1 = fig.add_subplot(2,1,1) #Frist full row
        ax2 = fig.add_subplot(2,2,3) # bottom left on 4x4 grid
        ax3 = fig.add_subplot(2,2,4) # bottom right on a 4x4 grid
        ax1.plot(history['global_VAE_loss'][1:],color='dodgerblue',label='train')
        ax1.plot(history['global_VAE_loss_val'][1:],color='lightsalmon',label='test')
        ax1.set_title('Global VAE Loss')
        if best_epoch != None:
            ax1.axvline(best_epoch, linestyle='--', color='r',label='Early stopping')
        ax2.plot(history['recon_loss'][1:],color='dodgerblue',label='train')
        ax2.plot(history['recon_loss_val'][1:],color='lightsalmon',label='test')
        ax2.set_title('Reconstruction Loss')
        ax3.plot(history['kl_loss'][1:],color='dodgerblue',label='train')
        ax3.plot(history['kl_loss_val'][1:],color='lightsalmon',label='test')
        ax3.set_title('Fit to Prior')
        ax1.legend()
        ax2.legend()
        ax3.legend()


    if  infoMAX:
        fig, ((ax1 ,ax2),(ax3 ,ax4)) = plt.subplots(2,2,figsize=(10, 10))
        ax1.plot(history['global_VAE_loss'][1:],color='dodgerblue',label='train')
        ax1.plot(history['global_VAE_loss_val'][1:],color='lightsalmon',label='test')
        ax1.set_title('Global VAE Loss')
        if best_epoch != None:
            ax1.axvline(best_epoch, linestyle='--', color='r',label='Early stopping')
        ax2.plot(history['MI_estimation'][1:],color='dodgerblue',label='train')
        ax2.plot(history['MI_estimation_val'][1:],color='lightsalmon',label='test')
        ax2.set_title('Mutual Information')
        ax3.plot(history['recon_loss'][1:],color='dodgerblue',label='train')
        ax3.plot(history['recon_loss_val'][1:],color='lightsalmon',label='test')
        ax3.set_title('Reconstruction Loss')
        ax4.plot(history['kl_loss'][1:],color='dodgerblue',label='train')
        ax4.plot(history['kl_loss_val'][1:],color='lightsalmon',label='test')
        ax4.set_title('Fit to Prior')
        ax1.legend()
        ax2.legend()
        ax3.legend()
        ax4.legend()

    if save_path != None:
        plt.savefig(save_path+'los_evolution.png')

    return fig



############################
######## SAVING & STOPPING
############################

class EarlyStopping:
    """Early stops the training if validation loss doesn't improve after a given patience.
    This class is obtained from Bjarten Implementation (GitHub open source), thanks to him"""
    def __init__(self, patience=7, verbose=False, delta=0, path='checkpoint.pt'):
        """
        Args:
            patience (int): How long to wait after last time validation loss improved.
                            Default: 7
            verbose (bool): If True, prints a message for each validation loss improvement.
                            Default: False
            delta (float): Minimum change in the monitored quantity to qualify as an improvement.
                            Default: 0
            path (str): Path for the models to be saved to.
                            Default: 'checkpoint.pt'
        """
        self.patience = patience
        self.verbose = verbose
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.stop_epoch = 0
        self.val_loss_min = np.Inf
        self.delta = delta
        self.path = path

    def __call__(self, val_loss, VAE, MLP=None):

        score = -val_loss

        if self.best_score is None:
            self.best_score = score
            self.save_model(val_loss, VAE, MLP)
        elif score < self.best_score + self.delta:
            self.counter += 1
            print(f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.save_model(val_loss, VAE, MLP)
            self.counter = 0

    def save_model(self, val_loss, VAE, MLP):
        '''Saves model when validation loss decrease.'''
        self.stop_epoch = VAE.epochs
        if self.verbose:
            print(f'Validation loss decreased ({self.val_loss_min:.6f} --> {val_loss:.6f}).  Saving model ...')
        #Save both models
        pre, ext = os.path.splitext(self.path)
        save_brute(VAE,pre+f'_VAE_.pth')
        if MLP != None:
            save_brute(MLP,pre+f'_MLP_.pth')
        #torch.save(model.state_dict(), self.path)
        self.val_loss_min = val_loss


def save_checkpoint(model, path):
    """Save a NN model to path.

    Params
    --------
        model (PyTorch model): model to save
        path (str): location to save model. must end in '.pth'

    Returns
    --------
        None, save the `model` to `path`

    """
    # Basic details, as mapping id to classe and number of epochs already trained
    checkpoint = {
        'epochs': model.epochs,
        'zdim' : model.zdim,
        'channels' : model.channels,
        'layer_count' : model.layer_count,
        'base' : model.base,
        'loss' : model.loss,
        'input_size' : model.input_size,
        'model_type' : model.model_type
    }
    checkpoint['state_dict'] = model.state_dict() #Weights

    # Add the optimizer
    checkpoint['optimizer'] = model.optimizer
    checkpoint['optimizer_state_dict'] = model.optimizer.state_dict()

    # Save the data to the path
    torch.save(checkpoint, path)

def save_brute(model, path):
    '''Save the entire model
    For fast development purpose only'''

    torch.save(model,path)

def load_brute(path):
    '''To reload entire model
    For fast development purpose only'''

    return torch.load(path)

def load_checkpoint(path):
    """Load a VAE network, pre-trained on single cell images

    Params
    --------
        path (str): saved model checkpoint. Must end in '.pth'

    Returns
    --------
        None, load the `model` from `path`

    """
    # Load in checkpoint
    train_on_gpu = cuda.is_available()
    if train_on_gpu:
        checkpoint = torch.load(path)
    else :
        checkpoint = torch.load(path,map_location='cpu')  #If saved from GPU, need to be reload on GPU as well !

    if checkpoint['model_type'] == 'VAE_CNN_vanilla' :
        model = VAE(zdim=checkpoint['zdim'],channels=checkpoint['channels'],base=checkpoint['base'],loss=checkpoint['loss'],layer_count=checkpoint['layer_count'],input_size=checkpoint['input_size'])

    # Load in the state dict
    model.load_state_dict(checkpoint['state_dict'])

    total_params = sum(p.numel() for p in model.parameters())
    print(f'{total_params:,} total parameters.')
    total_trainable_params = sum(
        p.numel() for p in model.parameters() if p.requires_grad)
    print(f'{total_trainable_params:,} total gradient parameters.')

    if train_on_gpu:
        model = model.to('cuda')

    model.epochs = checkpoint['epochs']

    # Optimizer
    optimizer = checkpoint['optimizer']
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

    return model, optimizer


#######################################
######## Old visualization Function
#######################################

def plot_latent_space(model, dataloader, train_on_gpu):
    '''
    Simple plot of the latent representation. To plot every XXX epochs during training for instance
    '''

    labels_list = []
    z_list = []

    if model.zdim > 3 :
        print(f'Latent space is >3D ({model.zdim} dimensional), no visualization is provided')
        return None, None, None, None

    # TODO: Use a dataloader which do not 'drop last' for inference
    for i, (data, labels) in enumerate(dataloader):
        if train_on_gpu:
            # make sure this lives on the GPU
            data = data.cuda()
        with torch.no_grad():
            model.eval()

            data = Variable(data, requires_grad=False)

            #The mean can be taken as the most likely z
            z, _ = model.encode(data)
            z = z.view(-1,model.zdim)
            z_list.append((z.data).cpu().numpy())
            labels_list.append(labels.numpy())

        print(f'In progress...{i*len(data)}/{len(dataloader.dataset)}',end='\r')

    z_points = np.concatenate(z_list,axis=0) # datasize x 3
    true_label = np.concatenate(labels_list,axis=0)

    if model.zdim == 3:
        fig = plt.figure(figsize=(10,10))
        #ax = Axes3D(fig)
        ax=plt.axes(projection='3d')

        cmap1 = plt.get_cmap('tab20')
        colors1 = cmap1(np.linspace(0,1.0,20))
        cmap2 = plt.get_cmap('Set3')
        colors2 = cmap2(np.linspace(0,1.0,10))
        colors = np.concatenate((colors1,colors2),0)
        zorder = 100
        for i in np.unique(true_label):
            zorder -= 10
            if i+1 == 7: #Do not plot process 7 for more readability
                continue
            ax.scatter3D(z_points[true_label==i,0],z_points[true_label==i,1],z_points[true_label==i,2],s=5,color=colors[i],zorder=zorder, label=f'Process_{i+1}')
        ax.legend()
        return fig, ax, fig, ax

    if model.zdim == 2:
        fig = plt.figure(figsize=(12,12))
        ax = plt.subplot(111)

        #if 2D plot a separated plot with confidence ellipse
        fig2, ax_ellipse = plt.subplots(figsize=(12,12))

        cmap1 = plt.get_cmap('tab20')
        colors1 = cmap1(np.linspace(0,1.0,20))
        cmap2 = plt.get_cmap('Set3')
        colors2 = cmap2(np.linspace(0,1.0,10))
        colors = np.concatenate((colors1,colors2),0)

        zorder = 100
        for i in np.unique(true_label):
            zorder -= 10
            ax.scatter(z_points[true_label==i,0],z_points[true_label==i,1],s=5,color=colors[i],zorder=zorder, label=f'Process_{i+1}')

            mu_1 = np.mean(z_points[true_label==i,0])
            mu_2 = np.mean(z_points[true_label==i,1])

            confidence_ellipse(z_points[true_label==i,0], z_points[true_label==i,1], ax_ellipse,n_std=0.7,
                alpha=0.5,facecolor=colors[i], edgecolor=colors[i] , zorder=0)
            ax_ellipse.scatter(mu_1, mu_2,marker='X', s=50, color=colors[i],zorder=zorder,label=f'Process_{i+1}')

        ax.legend()
        ax_ellipse.legend()
        return fig, ax, fig2, ax_ellipse


def confidence_ellipse(x, y, ax, n_std=3.0, facecolor='none', **kwargs):
    """
    Create a plot of the covariance confidence ellipse of `x` and `y`

    Parameters
    ----------
    x, y : array_like, shape (n, )
        Input data.

    ax : matplotlib.axes.Axes
        The axes object to draw the ellipse into.

    n_std : float
        The number of standard deviations to determine the ellipse's radiuses.

    Returns
    -------
    matplotlib.patches.Ellipse

    Other parameters
    ----------------
    kwargs : `~matplotlib.patches.Patch` properties
    """
    if x.size != y.size:
        raise ValueError("x and y must be the same size")

    cov = np.cov(x, y)
    pearson = cov[0, 1]/np.sqrt(cov[0, 0] * cov[1, 1])
    # Using a special case to obtain the eigenvalues of this
    # two-dimensionl dataset.
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0),
        width=ell_radius_x * 2,
        height=ell_radius_y * 2,
        facecolor=facecolor,
        **kwargs)

    # Calculating the stdandard deviation of x from
    # the squareroot of the variance and multiplying
    # with the given number of standard deviations.
    scale_x = np.sqrt(cov[0, 0]) * n_std
    mean_x = np.mean(x)

    # calculating the stdandard deviation of y ...
    scale_y = np.sqrt(cov[1, 1]) * n_std
    mean_y = np.mean(y)

    transf = transforms.Affine2D() \
        .rotate_deg(45) \
        .scale(scale_x, scale_y) \
        .translate(mean_x, mean_y)

    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


def show(img, train_on_gpu):
    if train_on_gpu:
        npimg = img.cpu().numpy()
    else:
        npimg = img.numpy()
    plt.figure(figsize=(10,10))
    plt.imshow(np.transpose(npimg, (1,2,0)), interpolation='nearest')
