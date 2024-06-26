
# mischellaneous functions
import numpy as np
import matplotlib.pyplot as plt
import yaml
import torch
import sys
import os

def make_all_dirs():
    write_current_time_str()
    os.makedirs(os.path.join('plots',current_time_str()), exist_ok=True)
    os.makedirs(os.path.join('./log',current_time_str()), exist_ok=True)
    os.makedirs(os.path.join('./log',current_time_str(),"various_risk"),exist_ok=True)


def init_manual(H:int,stochastic_transition:bool,
                identity_emission:bool,
                peaky_reward:bool):
    from utils import Normalize_T, Normalize_O

    # Initial Distribution
    mu_true=torch.tensor([1,0,0])

    # Transition
    if stochastic_transition==False:
        T_true=torch.stack([torch.tensor([[0,0,1],
                                        [1,0,0],
                                        [0,1,0]]).unsqueeze(-1).repeat(1,1,2) for _ in range(H)])
    else:
        # Stochastic Transition(much harder)
        T_true=torch.stack([torch.tensor([[0.03,0.04,0.89],
                                        [0.95,0.02,0.10],
                                        [0.02,0.94,0.01]]).to(torch.float64).unsqueeze(-1).repeat(1,1,2) for _ in range(H)])
        T_true=Normalize_T(T_true)

    # Emission
    if identity_emission==False:
        '''
        O_true=torch.stack([torch.tensor([[0.4,0.3,0.2],
                                          [0.2,0.5,0.7],
                                          [0.4,0.2,0.1]]).transpose(0,1).repeat(1,1) for _ in range(H+1)])
        '''
        O_true=torch.stack([torch.tensor([[0.83,0.05,0.02],
                                          [0.08,0.79,0.09],
                                          [0.09,0.06,0.89]]).to(torch.float64).transpose(0,1).repeat(1,1) for _ in range(H+1)])
        O_true=Normalize_O(O_true)
    else:
        O_true=torch.eye(3).unsqueeze(0).repeat(H+1,1,1)

    # Rewards
    # peacky rewards (much easier than 0/1)
    if peaky_reward==True:
        R_true=torch.tensor([[1,-10],[-10,1],[1,-10]]).unsqueeze(0).repeat(H,1,1)
    else:
        R_true=torch.tensor([[1,0],[0,1],[1,0]]).unsqueeze(0).repeat(H,1,1)

    return (mu_true,T_true,O_true,R_true)





def POMDP_smooth(POMDP_single_episode_rewards:np.array)->tuple:
    POMDP_episodic_smooth=smooth(POMDP_single_episode_rewards, window_len=2,window='max_pooling')
    POMDP_episodic_smooth=smooth(POMDP_episodic_smooth, window_len=3,window='hamming')
    indices=np.arange(POMDP_episodic_smooth.shape[0])
    return (indices, POMDP_episodic_smooth)


def POMDP_regret(optimal_value_POMDP, POMDP_single_episode_rewards):
    from scipy.optimize import curve_fit
    POMDP_regret=np.cumsum(optimal_value_POMDP-POMDP_single_episode_rewards)
    indices=np.arange(POMDP_regret.shape[0])
    scatter_size=np.ones_like(indices)*0.02
    def square_rt(x,a,b,d):
        return a*np.sqrt(b*x)+d
    print(POMDP_regret.shape[0])
    indices=np.arange(POMDP_regret.shape[0])
    fit_param, fit_curve = curve_fit(square_rt, indices, POMDP_regret)
    POMDP_regret_fit=square_rt(indices, *fit_param)

    return (indices, POMDP_regret, POMDP_regret_fit, scatter_size)

def POMDP_PAC(optimal_value_POMDP,POMDP_single_episode_rewards:np.array):
    from scipy.optimize import curve_fit

    POMDP_PAC_raw=optimal_value_POMDP-np.cumsum(POMDP_single_episode_rewards)/(1+np.arange(len(POMDP_single_episode_rewards)))
    indices=np.arange(POMDP_PAC_raw.shape[0])

    def inverse_sqrt(x,a,b,c,d):
        #print(b*x+c) cound be negative...causing errors...
        return a*(1/np.sqrt(1e-9+np.abs(b*x+c)))+d
    indices=np.arange(POMDP_PAC_raw.shape[0])
    fit_param, fit_curve = curve_fit(inverse_sqrt, indices, POMDP_PAC_raw)
    POMDP_PAC_fit=inverse_sqrt(indices, *fit_param)

    return (indices[10:],POMDP_PAC_raw[10:],POMDP_PAC_fit[10:])



def smooth(x:np.array,window_len=11,window='hanning'):
    import numpy as np
    """smooth the data using a window with requested size.
    
    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal 
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.
    
    input:
        x: the input signal 
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 
        'flat', 
        'hanning', 
        'hamming', 
        'bartlett', 
        'blackman'
        'max_pooling'
            flat window will produce a moving average smoothing.

    output:
        the smoothed signal
        
    example:

    t=linspace(-2,2,0.1)
    x=sin(t)+randn(len(t))*0.1
    y=smooth(x)
    
    see also: 
    
    numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    scipy.signal.lfilter
 
    TODO: the window parameter could be the window itself if an array instead of a string
    NOTE: length(output) != length(input), 
    to correct this: 
    return y[(window_len/2-1):-(window_len/2)] instead of just y.
    """

    # if x.ndim != 1:
    #     raise ValueError, "smooth only accepts 1 dimension arrays."
    #window_len=1
    if x.size < window_len:
        print("Input vector needs to be bigger than window size.")
        print(f"x={x}"+"size="+f"{x.size}")
        print(f"window size={window_len}")
        raise(ValueError)

    if window_len<3:
        return x
    
    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman','max_pooling']:
        print("Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")
        raise(ValueError)


    s=np.r_[x[window_len-1:0:-1],x,x[-2:-window_len-1:-1]]
    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    elif window !='max_pooling':
        w=eval('np.'+window+'(window_len)')
    else:
        y_max_pool=np.array([x[i:i+window_len].max() for i in range(x.size-window_len+1)])
        return y_max_pool
    y=np.convolve(w/w.sum(),s,mode='valid')
    return y  # y[(window_len/2-1):(window_len/2)]





def moving_average(time_series:np.array, window_width:int)->np.array:
    '''
    input an array of length L, with window width being W, then
    output array of length L-W+1.
    '''
    test = np.cumsum(time_series, dtype=float)
    test[window_width:] = test[window_width:] - test[:-window_width]
    return test[window_width - 1:] / window_width

def Normalize_T(T):
    shape=T.shape
    H=shape[0]
    nS=shape[1]
    nA=shape[3]
    for h in range(H):
        for s in range(nS):
            for a in range(nA):
                T[h][:,s,a]=T[h][:,s,a]/(torch.sum(T[h][:,s,a]))
    return T

def Normalize_O(O):
    shape=O.shape
    H=shape[0]
    nO=shape[1]
    nS=shape[2]
    for h in range(H):
        for o in range(nO):
            for s in range(nS):
                O[h][:,s]=O[h][:,s]/(torch.sum(O[h][:,s]))
    return O



# test normalization
def test_normalization_mu(mu:torch.Tensor):
    # check all elements non-negative
    positive=np.fabs((torch.sum(mu>=0)/mu.numel()).item()-1) <1e-6
    normalized=(np.fabs(sum(mu)-1) <1e-6).item()
    if positive==False:
        raise(ValueError)
        return False
    if normalized==False:
        raise(ValueError)
        return False
    return True

def test_normalization_T(T_hat:torch.Tensor,nS:int,nA:int,H:int):
    positive=np.fabs((torch.sum(T_hat>=0)/T_hat.numel()).item()-1) <1e-6
    if positive == False:
        raise(ValueError)
        return False
    normalized=True
    for h in range(H):
        for s in range(nS):
            for a in range(nA):
                if (np.fabs(sum(T_hat[h][:,s,a])-1)>1e-6):
                    print(f"T_hat[{h}][:,{s},{a}]={T_hat[h][:,s,a]}, sum={sum(T_hat[h][:,s,a]):.10f}")
                    raise(ValueError)
                    return False
    return True

def test_normalization_O(O_hat:torch.Tensor,nS:int,H:int):
    positive=np.fabs((torch.sum(O_hat>=0)/O_hat.numel()).item()-1) <1e-6
    if positive == False:
        raise(ValueError)
        return False
    normalized=True
    for h in range(H+1):
        for s in range(nS):
                if (np.fabs(sum(O_hat[h][:,s])-1)>1e-6):
                    print(f"O_hat[{h}][:,{s}]={O_hat[h][:,s]}, sum={sum(O_hat[h][:,s]):.10f}")
                    raise(ValueError)
                    return False
    return True

def test_model_normalized(model_being_tested:tuple, nS:int,nA:int,H:int):
    mu_hat, T_hat,O_hat = model_being_tested
    test_normalization_mu(mu_hat)
    test_normalization_T(T_hat,nS,nA,H)
    test_normalization_O(O_hat,nS,H)

# (x)^+ and (x)^- functions.
def negative_func(x:np.float64)->np.float64:
    return np.min(x,0)
def positive_func(x:np.float64)->np.float64:
    return np.max(x,0)

# obtain current time as a python string

def write_current_time_str():    
    import datetime
    crtm=str(datetime.datetime.now())[:-7].replace(' ', '-').replace(':', '-')
    crtm="2024-05-22-16-57-58"
    with open(os.path.join('./log','current_time.txt'),'w') as f:
        f.write(crtm)

def current_time_str()->str:
    with open(os.path.join('./log','current_time.txt'),'r') as f:
        crtm=f.read()
    crtm="2024-05-22-16-57-58"
    return crtm

# load hyper parameters from a yaml file.
def load_hyper_param(hyper_param_file_name:str)->tuple:
    ''''
    given hyper parameter file name, return the params.   
    
    '''
    # print(f"hyper_param_file_name={hyper_param_file_name}")
    with open(hyper_param_file_name, 'r') as file:
        hyper_param = yaml.safe_load(file)
    nA=hyper_param['sizes']['size_of_action_space']
    nS=hyper_param['sizes']['size_of_state_space']
    nO=hyper_param['sizes']['size_of_observation_space']
    H=hyper_param['sizes']['horizon_len']
    K=hyper_param['sizes']['num_episode']
    nF=pow((nO*nA),H) #size_of_history_space
    delta=hyper_param['sizes']['confidence_level']
    gamma=hyper_param['sizes']['risk_sensitivity_factor']
    iota =np.log(K*H*nS*nO*nA/delta)
    return (nS,nO,nA,H,K,nF,delta,gamma,iota)

# output loss curve.
def log_output_param_error(mu_err,T_err,O_err, H:int)->None:
    '''
    write and read Monte-Carlo erros and plot three curves on a graph. 
    '''
    import os
    log_filename=os.path.join('./log',current_time_str(),"log.txt")
    with open(log_filename,mode='w') as log_file:
        # log_file.write(f"\n\nTest BVVI. Current time={current_time_str()}")
        param_error=np.column_stack((mu_err,T_err,O_err))
        np.savetxt(log_filename,param_error)
        log_file.close()

    with open(log_filename,mode='r') as log_file:
        loss_curve=np.loadtxt(log_filename)
        # print(f"read in {loss_curve.shape[0]} items from File:{log_filename}" )
        indices=np.arange(loss_curve.shape[0])*H
        labels_plt=['Initial distribution $\mu(\cdot)$',\
                    'Transition matrices $\{\mathbb{T}_h(\cdot|s,a)\}_{h=1}^{H+1}$',\
                        'Emission matrices $\{\mathbb{O}_h(\cdot|s)\}_{h=1}^{H+1}$']
        for id in range(3):
            plt.plot(indices,loss_curve[:,id],label=labels_plt[id])
        plt.title(f'Average 2-norm Error of Monte-Carlo Simulation. Horizon H={H}')
        plt.xlabel(f'Samples N (=iteration $k$ * {H})')    # H transitions per iteration.
        plt.ylabel(r'$\frac{1}{d} \| \widehat{p}^k(\cdot)-p(\cdot) \|_2$')
        plt.legend(loc='upper right', labels=labels_plt)
        plt.tight_layout()
        plt.savefig(os.path.join('plots',current_time_str(),'single-MC'+'.jpg'))
        plt.show()

def log_output_tested_rewards(averge_risk_measure_of_each_episode:np.array,H:int)->None:
    loss_curve=averge_risk_measure_of_each_episode
    indices=np.arange(loss_curve.shape[0])  #*H
    labels_plt=['BVVI(ours)']
    # replace with these lines when we have multiple curves.
    # for id in range(3):
    #     plt.plot((indices),loss_curve[id],label=labels_plt[id])
    plt.plot((indices), loss_curve) #, labels_plt

    plt.title(f'Average Risk Measure of Policies. Horizon H={H}')
    plt.xlabel(f'Episode $k$')    # H transitions per iteration.   Samples N (=iteration $K$ * {H})
    plt.ylabel(f'Average Risk Measure')         # $\sum_{h=1}^{H}r_h(\mathbf{S}_h,\mathbf{A}_h)$
    
    plt.legend(loc='upper right', labels=labels_plt)
    plt.tight_layout()
    plt.savefig(os.path.join('plots',current_time_str(),'single-reward.jpg'))
    plt.show()

def log_output_test_reward_pretty(H:int,
                                  K_end:int,
                                  gamma:float,
                                  plot_optimal_policy=True,
                                  optimal_value=0.0,
                                  log_episode_file_name='log_episode_naive'
                                  ):
    log_file_directory=os.path.join('./log',current_time_str(),log_episode_file_name+'.txt')
    with open(log_file_directory,mode='r') as log_episode_file:
        averge_risk_measure_of_each_episode=np.loadtxt(log_file_directory)[0:K_end+1,0]

        loss_curve=averge_risk_measure_of_each_episode

        indices=np.arange(loss_curve.shape[0]) 

        plt.plot(indices, loss_curve,label='BVVI(ours)') 
        
        # optimal policy's performance (adjustable, optional)
        if plot_optimal_policy:
            plt.axhline(y=optimal_value, color='orange', linestyle='--',label='Optimal Policy')
        
        # upper and lower bounds of the accumulated risk measure.
        plt.ylim((0.0,H*1.2))

        plt.title(f'Accumulated Risk-Sensitive Reward of Policies')   # . Horizon H={H}
        
        plt.xlabel(f'Episode $k$')    # H transitions per iteration.   Samples N (=iteration $K$ * {H})
        plt.ylabel(f'Average Risk Measure')         # $\sum_{h=1}^{H}r_h(\mathbf{S}_h,\mathbf{A}_h)$
        
        plt.legend(loc='upper right')
        
        plt.tight_layout()
        plt.savefig(os.path.join('plots',current_time_str(),'single-Reward.jpg'))
        plt.close()
        plt.show()

def init_history_space(H:int, nO:int, nA:int)->list:
    '''
    inputs: horizon length H, sizes of observation space nO and action space nA.
    outputs: list of tensors. 
    '''
    observation_space=tuple(list(np.arange(nO)))
    action_space=tuple(list(np.arange(nA)))
    history_space=[None for _ in range(H+1)]
    for h in range(H+1):
        # Create the space of \mathcal{F}_h = (\mathcal{O}\times \mathcal{A})^{h-1}\times \mathcal{O}
        history_space[h]=[observation_space if i%2==0 else action_space for i in range(2*(h))]+[observation_space]
    return history_space

def init_value_representation(horizon_length:int,size_of_state_space:int, size_of_observation_space:int, size_of_action_space:int)->tuple:
    '''
    inputs: as the name suggests.
    output: a list of tensors, the series of (empirical) risk-sensitive beliefs   sigma :  \vec{\sigma}_{h,f_h} \in \R^{S}
    In the following loop, 
        "hist_coords" is the coordinates of all the possible histories in the history space of order h.
        This iterator traverses the history space of \mathcal{F}_h, which recordes all possible 
        observable histories up to step h. The order of traversal is identical to a binary search tree.
        Each element in the coordinate list "hist" is an OAOA...O tuple of size 2h-1.
        "hist" can be viewed as an encoding of f_h
        
        sigma[h][hist] is of shape torch.Size([nS])  is the vector \vec{sigma}_{h,f_h} \in \R^S        
        
        sigma[h-1][hist[0:-2]] is still of shape torch.Size([nS]) is the belief of previous history: \vec{sigma}_{h-1,f_{h-1}} \in \R^S   

        run these lines to check the shapes of the tensors:
            print(f"h={h}":)
            print(f"\thistory{hist} correspond to belief {sigma[h][hist].shape}")
            if h >=1:
                print(f"\t\twhose preivous history is {hist[0:-2]}, with previous belief {sigma[h-1][hist[0:-2]].shape}")
    '''
    risk_belief=[None for _ in range(horizon_length+1)]
    for h in range(horizon_length+1):
        risk_belief[h]=torch.zeros([size_of_observation_space if i%2==0 else size_of_action_space for i in range(2*(h))]+[size_of_observation_space] +[size_of_state_space], dtype=torch.float64)
    
    '''
    Create beta vectors, Q-values and value functions
    beta_vector:       tensor list of length H+1
        beta_vector[h][hist][s] is \widehat{\beta}_{h, f_h}^k(s_h)
    Q_function:     tensor list of length H
        each element Q_function[h].shape    torch.Size([nO, nA, nO, nA, nO, nA])
            is the Q function at step h. The last dimension is the action a_h, the rest are history coordinates.

        Q_function[h][history].shape: torch.Size([nA])
            is the Q function vector at step h, conditioned on history: Q_f(\cdot;f_h), with different actions

        Q_function[h][history][a] is Q_h(a;f_h)

    value_function: tensor list of length H
        each element value_function[h].shape :  torch.Size([4, 2, 4, 2, 4]) is the value function at step h.
    '''
    beta_vector=[torch.ones_like(risk_belief[h],dtype=torch.float64) for h in range(horizon_length+1)] 

    Q_function=[torch.zeros(risk_belief[h].shape[:-1]+(size_of_action_space,),dtype=torch.float64) for h in range(horizon_length)]

    value_function=[torch.zeros(risk_belief[h].shape[:-1],dtype=torch.float64) for h in range(horizon_length)]

    return (risk_belief, beta_vector, Q_function, value_function)


def init_occurrence_counters(H:int, nS:int, nO:int, nA:int)->tuple:
    ## for initial state estimation
    Ns_init=torch.zeros([nS])      # frequency of s0
    ## for transition estimation
    Nssa=torch.zeros([H,nS,nS,nA]) # frequency of s' given (s,a)
    Nssa_ones=torch.ones([1,nS,nA])# matrix of 1 of size N(s,a) 
    Nsa=torch.ones([H,nS,nA])      # frequency of (s,a) :           \widehat{N}_{h}(s_h,a_h) \vee 1  h=1,2,3,...H
    ## for emission estimation
    Nos=torch.zeros([H+1,nO,nS])   # frequency of o  given s
    Nos_ones=torch.ones([1,nS])    # matrix of 1 of size N(s)
    Ns=torch.ones([H+1,nS])        # frequency of s:                \widehat{N}_{h}(s_{h}) \vee 1    h=1,2,3,...H+1
    return (Ns_init, Nssa, Nssa_ones, Nsa, Nos, Nos_ones, Ns)


def test_policy_normalized(policy_test:list, size_obs:int, size_act:int)->bool:
    '''
    input policy
    output whether this policy is normalized
    '''
    import itertools
    normalized_flag=True
    horizon_len=len(policy_test)
    history_space=init_history_space(horizon_len,nO=size_obs,nA=size_act)
    for h in range(horizon_len):
        # retrieve the policy tensor at step h
        policy_step=policy_test[h]
        # traverse all history coordinates
        history_coordinates=list(itertools.product(*history_space[h]))
        for hist in history_coordinates:
            action_distribution=policy_step[hist]
            if torch.sum(action_distribution).item()!=1:
                normalized_flag=False
                raise(ValueError)
                return normalized_flag
    return True

def test_log_output():
    log_output_tested_rewards(averge_risk_measure_of_each_episode=np.array([1,3,2,4,7]), H=5)


def test_output_log_file(output_to_log_file=True):
    import sys
    if output_to_log_file:
        old_stdout = sys.stdout
        log_file = open(os.path.join('./log',current_time_str(),"console_output.log","w"))
        sys.stdout = log_file
    print('%'*100)
    print('test Beta Vector Value Iteration.')
    print('%'*100)
    print('hyper parameters=')
    with open(os.path.join("config","hyper_param.yaml")) as hyp_file:
        content=hyp_file.read()
    print(content)
    print('%'*100)
    print('Call function \'  beta_vector_value_iteration...\' ')
    
    print('\'  beta_vector_value_iteration...\' returned.')
    print('%'*100)
    print('Call function \'  visualize_performance...\' ')
    
    print('\'  visualize_performance...\' returned.')
    print('%'*100)
    print('Beta Vector Value Iteration test complete.')
    print('%'*100)
    if output_to_log_file is True:
        sys.stdout = old_stdout
        log_file.close()

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log =open("./log/"+current_time_str()+"/console_output.log", "a")
        
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass    

def save_model_rewards(kernels, reward_table, parent_directory):
    import os
    mu, T, O =kernels
    torch.save(mu,os.path.join(parent_directory,'mu.pt'))
    torch.save(T,os.path.join(parent_directory,'T.pt'))
    torch.save(O,os.path.join(parent_directory,'O.pt'))
    torch.save(reward_table,os.path.join(parent_directory,'R.pt'))

def load_model_rewards(parent_directory)->tuple:
    import os
    mu=torch.load(os.path.join(parent_directory,'mu.pt'))
    T=torch.load(os.path.join(parent_directory,'T.pt'))
    O=torch.load(os.path.join(parent_directory,'O.pt'))
    reward_table=torch.load(os.path.join(parent_directory,'R.pt'))
    kernels=(mu, T, O)
    return (kernels, reward_table)

def save_model_policy(kernels, policy, parent_directory):
    import os
    mu, T, O =kernels
    torch.save(mu,os.path.join(parent_directory,'mu.pt'))
    torch.save(T,os.path.join(parent_directory,'T.pt'))
    torch.save(O,os.path.join(parent_directory,'O.pt'))

    policy_dict={id:len for id, len in enumerate(policy)}
    torch.save(policy_dict,parent_directory+'\Policy.pt')

def load_model_policy(parent_directory):
    import os
    mu=torch.load(os.path.join(parent_directory,'mu.pt'))
    T=torch.load(os.path.join(parent_directory,'T.pt'))
    O=torch.load(os.path.join(parent_directory,'O.pt'))
    kernels=(mu, T, O)

    policy_dict = torch.load(os.path.join(parent_directory,'\Policy.pt'))
    policy=[policy_dict[id] for id in range(len(policy_dict))]
    return (kernels, policy)

def short_test(policy,mu_true,T_true,O_true,R_true,only_reward=False):
    from POMDP_model import sample_from, action_from_policy

    horizon=T_true.shape[0]
    model=(mu_true,T_true,O_true)
    reward=R_true
    output_reward=True

    print("\n")
    init_dist, trans_kernel, emit_kernel =model 

    full_traj=np.ones((3,horizon+1), dtype=int)*(-1)   
    if output_reward:
        sampled_reward=np.ones(horizon, dtype=np.float64)*(-1)

    # S_0
    full_traj[0][0]=sample_from(init_dist)
    # A single step of interactions
    for h in range(horizon+1):
        # S_h
        state=full_traj[0][h]
        # O_h \sim \mathbb{O}_h(\cdot|s_h)
        observation=sample_from(emit_kernel[h][:,state])
        full_traj[1][h]=observation
        # A_h \sim \pi_h(\cdot |f_h). We do not collect A_{H+1}, which is a[H]. We set a[H] as 0
        if h<horizon:
            action=action_from_policy(full_traj[1:3,:],h,policy)
            full_traj[2][h]=action
            # R_h = r_h(s_h,a_h)
            if output_reward:
                sampled_reward[h]=reward[h][state][action]
                print(f"(h,s,a,r)={h,state,action,sampled_reward[h]}")
        # S_h+1 \sim \mathbb{T}_{h}(\cdot|s_{h},a_{h})
        if h<horizon:  #do not record s_{H+1}
            new_state=sample_from(trans_kernel[h][:,state,action])
            full_traj[0][h+1]=new_state

    print(f"sampled_reward={sampled_reward}")
    print(f"full_traj=\n{full_traj}")
    if only_reward==True:
        return np.cumsum(sampled_reward) / np.arange(1, sampled_reward.shape[0]+1)
    #sampled_reward     accumulated_mean = 
    else:
        return full_traj

def visualize_performance(evaluation_results, H:int):
    # unpack
    mu_err,T_err,O_err, tested_risk_measure=evaluation_results

    # plot planning result.
    log_output_tested_rewards(tested_risk_measure,H)
    # log_output_test_reward_pretty(H=H,gamma=gamma, plot_optimal_policy=True, optimal_value=np.exp(3), log_episode_file_name='log_episode_naive')

    # plot parameter learning results
    log_output_param_error(mu_err,T_err,O_err, H)

# test_log_output()
