import torch
import numpy as np
import matplotlib.pyplot as plt
import yaml
import itertools
import sys
import time
from tqdm import tqdm

from func import load_hyper_param, short_test, visualize_performance, log_output_test_reward_pretty, current_time_str, Logger, load_model_rewards, load_model_policy
from POMDP_model import initialize_model_reward
from BVVI import BVVI

def main(Alg:str,
         config_filename='hyper_param_naive',
         model_true=None,
         reward_true=None,
         model_load=None,
         policy_load=None,
         output_to_log_file=False,
         log_episode_filename='log_episode_naive',
         prt_progress=True,
         prt_policy_normalization=True,
         true_weight_output_parent_directory='real_env',
         weight_output_parent_directory='learnt\\naive'
         ):
    '''
    model_true if None, then randomly initialize one.
    '''
    # load hyper parameters
    hyper_param= load_hyper_param('config\\'+config_filename+'.yaml')    # can delete the naive
    nS,nO,nA,H,K,nF,delta,gamma,iota =hyper_param

    # initialize true model and/or rewards if necessary
    if model_true ==None:
        print(f"no model_true input, initialize a new one")
        model_true,_=initialize_model_reward(nS,nO,nA,H,model_init_type='random_homogeneous', reward_init_type='random_homogeneous')
    if model_true==None:
        raise(ValueError)
    
    if reward_true ==None:
        print(f"no reward_true input, initialize a new one")
        _, reward_true=initialize_model_reward(nS,nO,nA,H,model_init_type='random_homogeneous', reward_init_type='random_homogeneous')
    if reward_true==None:
        raise(ValueError)
    
    # [Evaluation] Reset the parameter errors and accumulated returns tested in the true envirnoemt of each iteration.
    mu_err=np.zeros([K])
    T_err=np.zeros([K])
    O_err=np.zeros([K])
    tested_returns=np.zeros([K])
    evaluation_metrics=(mu_err, T_err, O_err, tested_returns)

    # start the algorithm and logging instructions.
    if output_to_log_file:
        print(f"Will output log information to both the file:{'console_output.log'} and the console.")
        old_stdout = sys.stdout
        log_file = open("log\console_output.log","w")
        sys.stdout = Logger() #sys.stdout = log_file
        print(f"Start BVVI test. Current time={current_time_str()}")
        time.sleep(3)

    print('%'*100)
    print('Test Algorithm.')
    print('%'*100)
    print('hyper parameters:{}')
    with open('config\\'+config_filename+'.yaml') as hyp_file:  # can remove naive.
        content=hyp_file.read()
    print(content)
    print('%'*100)
    print('Call function beta_vector_value_iteration...')

    with open('log\\'+log_episode_filename+'.txt',mode='w') as log_episode_file:
        # log_episode_file.write(f"\n\nTest BVVI. Current time={current_time_str()}")   #real_env_kernels reward_fix
        if Alg=='BVVI':
            (policy_learnt, model_learnt, evaluation_results)=BVVI(\
                hyper_param=hyper_param,\
                    model_true=model_true,\
                        reward_true=reward_true,\
                            model_load=model_load,\
                                policy_load=policy_load,\
                                    evaluation_metrics=evaluation_metrics,\
                                        log_episode_file=log_episode_file,\
                                            true_weight_output_parent_directory=true_weight_output_parent_directory,\
                                                weight_output_parent_directory=weight_output_parent_directory,\
                                                    prt_progress=prt_progress,\
                                                        prt_policy_normalization=prt_policy_normalization)
        elif Alg=='RSVI2':
            from RSVI2 import RSVI2
            (policy_learnt, model_learnt, evaluation_results)=RSVI2(\
                hyper_param=hyper_param,\
                    model_true=model_true,\
                        reward_true=reward_true)
        else:
            raise(NotImplementedError)
        # log_episode_file.write(f"\n\nEnd Testing BVVI. Current time={current_time_str()}")
        log_episode_file.close()
    episode_data=np.loadtxt('log\\'+log_episode_filename+'.txt', dtype=np.float64)
    print('beta_vector_value_iteration...returned.')
    print(f"End BVVI test. Current time={current_time_str()}")
    print('%'*100)
    print('Call function visualize_performance...')

    visualize_performance(evaluation_results,H)

    print('visualize_performance...returned.')
    print('%'*100)
    print('Beta Vector Value Iteration test complete.')
    print('%'*100)
    
    if output_to_log_file is True:
        sys.stdout = old_stdout
        log_file.close()
    return policy_learnt

def test_with_medium_random_env(from_scratch=False):
    if from_scratch:
        model_true, reward_true=(None,None)
        model_load, policy_load=(None,None)
    else:
        model_true, reward_true=load_model_rewards(parent_directory='real_env\medium_real')
        model_load, policy_load=load_model_policy(parent_directory='learnt\medium')
    policy_learnt=main(config_filename= 'hyper_param_medium',
                        model_true=None,
                        reward_true=None,
                        model_load=None,
                        policy_load=None,
                        output_to_log_file=True,
                        log_episode_filename= 'log_episode_medium',
                        prt_progress=False,
                        prt_policy_normalization=False,
                        true_weight_output_parent_directory='real_env\medium_real',
                        weight_output_parent_directory='learnt\medium'
                        )
    
def manual_initialization(H:int):
    from func import Normalize_T
    # Initial Distribution
    mu_true=torch.tensor([1,0,0])

    # Transition
    stochastic_transition=True
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
    identity_emission=True              #False
    if identity_emission==False:
        O_true=torch.stack([torch.tensor([[0.4,0.2,0.4],[0.3,0.5,0.2],[0.2,0.7,0.1]]).transpose(0,1).repeat(1,1) for _ in range(H+1)])
    else:
        O_true=torch.eye(3).unsqueeze(0).repeat(H+1,1,1)

    # Rewards
    peaky_reward=True
    # peacky rewards (much easier than 0/1)
    if peaky_reward:
        R_true=torch.tensor([[1,-10],[-10,1],[1,-10]]).unsqueeze(0).repeat(H,1,1)
    else:
        R_true=torch.tensor([[1,0],[0,1],[1,0]]).unsqueeze(0).repeat(H,1,1)

    return (mu_true,T_true,O_true,R_true)

def test_with_naive_env(config_filename, log_episode_filename):
    
    nS,nO,nA,H,K,nF,delta,gamma,iota =load_hyper_param('config\\'+config_filename+'.yaml')    # can delete the naive

    mu_true, T_true, O_true,R_true=manual_initialization(H)
    
    model_true=(mu_true, T_true, O_true)
    reward_true=R_true

    policy_learnt=main(config_filename= config_filename,
                        model_true=model_true,
                        reward_true=reward_true,
                        model_load=None,
                        policy_load=None,
                        output_to_log_file=True,
                        log_episode_filename= log_episode_filename,
                        prt_progress=False,
                        prt_policy_normalization=False,
                        true_weight_output_parent_directory='real_env\\naive_real_id',      #'real_env\\naive_real'
                        weight_output_parent_directory='learnt\\naive_id'                      #'learnt\\naive' 
                        )
    
    # if we are training from naive params, also run this line:
    # Note: this only works for gamma=1. otherwise change
    log_output_test_reward_pretty(H=H,K_end=300,gamma=1.0, plot_optimal_policy=True, optimal_value=1/gamma*np.exp(gamma*H),
                                  log_episode_file_name='log_episode_naive')

    print('%'*100)
    print("short test of policy")
    short_test(policy_learnt,mu_true,T_true,O_true,R_true,only_reward=False)
    # print(policy_learnt)

def naive_train_and_plot(train_from_scratch=False):
    config_filename='hyper_param_naive'
    log_episode_file_name='log_episode_naive'

    nS,nO,nA,H,K,nF,delta,gamma,iota =load_hyper_param('config\\'+config_filename+'.yaml')

    # train again on the naive dataset.
    if train_from_scratch:
        test_with_naive_env(config_filename=config_filename,log_episode_filename=log_episode_file_name)

    K_end=200
    optimal_value=1/gamma*np.exp(gamma*H)
    log_file_directory='log\\'+log_episode_file_name+'.txt'

    with open(log_file_directory,mode='r') as log_episode_file:
        averge_risk_measure_of_each_episode=np.loadtxt(log_file_directory)[0:K_end+1,0]
        '''
        Plot regret, suppose that we know the optimal value funciton.
        '''

        plot_type='regret'   # other options: 'risk_average', 'risk_each'

        risk_measure_smooth=np.cumsum(averge_risk_measure_of_each_episode)/(1+np.arange(len(averge_risk_measure_of_each_episode)))

        regret_curve=optimal_value-averge_risk_measure_of_each_episode

        regret_curve_smooth=np.cumsum(regret_curve)/(1+np.arange(len(regret_curve)))
        
        indices=np.arange(regret_curve_smooth.shape[0])

        if plot_type=='regret':
            plot_curve=regret_curve_smooth
        elif plot_type=='risk_average':
            plot_curve=risk_measure_smooth
        elif plot_type=='risk_each':
            plot_curve=averge_risk_measure_of_each_episode
        plt.plot(indices, plot_curve,label='BVVI(ours)')
        
        # upper and lower bounds of the accumulated risk measure.

        plt.ylim((min(plot_curve)*0.4,max(plot_curve)*1.2))

        plt.title(f'Performance of Output Policies')   # . Horizon H={H}
        
        plt.xlabel(f'Episode $k$')    # H transitions per iteration.   Samples N (=iteration $K$ * {H})
        
        if plot_type=='regret':
            plt.ylabel(f'Average Regret')
        elif plot_type=='risk_average':
            plt.ylabel(f'Average Risk Measure')
        elif plot_type=='risk_each':
            plt.ylabel(f'Risk Measure of Each Episode')
       
        # plt.ylabel( r'$\frac{1}{k}\sum_{t=1}^{k} \frac{1}{\gamma} \mathbb{E}^{\pi^k} \sum_{h=1}^H e^{\gamma r_h(S_h,A_h)}$')

        plt.legend(loc='upper right')

        plt.savefig('plots/Reward'+current_time_str()+'.jpg')

        plt.show()

if __name__ == "__main__":
    naive_train_and_plot(train_from_scratch=True)

