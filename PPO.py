###############################################################
#                                                             #
#    PPO - proximal policy optimization                       #
#    Оптимизация проксимальной политики для среды Cartpole    #
#                                                             #
###############################################################


import gym
import torch
import numpy as np
import pandas as pd
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from PPOconfig import PPOconfig
from PPOnetwork import Policy


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Agent(PPOconfig):
    def __init__(self):
        self.env = gym.make('CartPole-v0')
        self.action_size = self.env.action_space.n # 2
        if self.train_cartpole:
            self.policy_network = Policy(action_size=self.action_size).to(device)
        self.optimizer = optim.Adam(self.policy_network.parameters(), lr=self.learning_rate)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=self.k_epoch, gamma=0.999)
        self.loss = 0
        self.criterion = nn.MSELoss()
        self.memory = {'state': [], 'action': [], 'reward': [], 'next_state': [], 'action_prob': [], 'terminal': [], 'count': 0, 'advantage': [], 'td_target': torch.FloatTensor([])}

    def new_random_game(self):
        self.env.reset()
        action = self.env.action_space.sample()
        screen, reward, terminal, info = self.env.step(action)
        return screen, reward, action, terminal

    
    def train(self):
        step = 0
        episode = 0
        avg_reward = []
        reward_history = []
        solved = False

        # A new episode
        while not solved:
            start_step = step
            episode += 1
            episode_length = 0

            # Get initial state
            state, reward, action, terminal = self.new_random_game()
            current_state = state
            total_episode_reward = 1

            # A step in an episode
            while not solved:
                step += 1
                episode_length += 1
                # Choose action
                prob_a = self.policy_network.pi(torch.FloatTensor(current_state).to(device))
                # print(prob_a)
                action = torch.distributions.Categorical(prob_a).sample().item()

                # Act
                state, reward, terminal, _ = self.env.step(action)
                new_state = state

                reward = -1 if terminal else reward

                self.add_memory(current_state, action, reward/10.0, new_state, terminal, prob_a[action].item())

                current_state = new_state
                total_episode_reward += reward

                if terminal:
                    episode_length = step - start_step
                    reward_history.append(total_episode_reward)
                    avg_reward.append(sum(reward_history[-10:])/10.0)

                    self.finish_path(episode_length)

                    if (len(reward_history) > 100 and sum(reward_history[-100:-1]) >= 19500):
                        solved = True

                    print('episode: %.2f, total step: %.2f, last_episode length: %.2f, last_episode_reward: %.2f, ' 'loss: %.4f, lr: %.4f' % (episode, step, episode_length, total_episode_reward, self.loss, self.scheduler.get_lr()[0]))

                    self.env.reset()

                    break

            if episode % self.update_freq == 0:
                for _ in range(self.k_epoch):
                    self.update_network()

            if episode % self.plot_every == 0:
                plot_graph(reward_history, avg_reward)

    def update_network(self):
        # get ratio
        pi = self.policy_network.pi(torch.FloatTensor(self.memory['state']).to(device))
        new_probs_a = torch.gather(pi, 1, torch.tensor(self.memory['action']))
        old_probs_a = torch.FloatTensor(self.memory['action_prob'])
        ratio = torch.exp(torch.log(new_probs_a) - torch.log(old_probs_a))

        # surrogate loss
        surr1 = ratio * torch.FloatTensor(self.memory['advantage'])
        surr2 = torch.clamp(ratio, 1 - self.eps_clip, 1 + self.eps_clip) * torch.FloatTensor(self.memory['advantage'])
        pred_v = self.policy_network.v(torch.FloatTensor(self.memory['state']).to(device))
        v_loss = 0.5 * (pred_v - self.memory['td_target']).pow(2)  # Huber loss
        entropy = torch.distributions.Categorical(pi).entropy()
        entropy = torch.tensor([[e] for e in entropy])
        self.loss = (-torch.min(surr1, surr2) + self.v_coef * v_loss - self.entropy_coef * entropy).mean()

        self.optimizer.zero_grad()
        self.loss.backward()
        self.optimizer.step()
        self.scheduler.step()

    def add_memory(self, s, a, r, next_s, t, prob):
        # sourcery skip: extract-method
        if self.memory['count'] < self.memory_size:
            self.memory['count'] += 1
        else:
            self.memory['state'] = self.memory['state'][1:]
            self.memory['action'] = self.memory['action'][1:]
            self.memory['reward'] = self.memory['reward'][1:]
            self.memory['next_state'] = self.memory['next_state'][1:]
            self.memory['terminal'] = self.memory['terminal'][1:]
            self.memory['action_prob'] = self.memory['action_prob'][1:]
            self.memory['advantage'] = self.memory['advantage'][1:]
            self.memory['td_target'] = self.memory['td_target'][1:]
        self.memory['state'].append(s)
        self.memory['action'].append([a])
        self.memory['reward'].append([r])
        self.memory['next_state'].append(next_s)
        self.memory['terminal'].append([1 - t])
        self.memory['action_prob'].append(prob)

    def finish_path(self, length):
        state = self.memory['state'][-length:]
        reward = self.memory['reward'][-length:]
        next_state = self.memory['next_state'][-length:]
        terminal = self.memory['terminal'][-length:]

        td_target = torch.FloatTensor(reward) + \
                    self.gamma * self.policy_network.v(torch.FloatTensor(next_state)) * torch.FloatTensor(terminal)
        delta = td_target - self.policy_network.v(torch.FloatTensor(state))
        delta = delta.detach().numpy()

        # get advantage
        advantages = []
        adv = 0.0
        for d in delta[::-1]:
            adv = self.gamma * self.lmbda * adv + d[0]
            advantages.append([adv])
        advantages.reverse()

        if self.memory['td_target'].shape == torch.Size([1, 0]):
            self.memory['td_target'] = td_target.data
        else:
            self.memory['td_target'] = torch.cat((self.memory['td_target'], td_target.data), dim=0)
        self.memory['advantage'] += advantages


def plot_graph(reward_history, avg_reward):
    df = pd.DataFrame({'x': range(len(reward_history)), 'Reward': reward_history, 'Average': avg_reward})
    plt.style.use('seaborn-darkgrid')
    plt.plot(df['x'], df['Average'], marker='', color='tomato', linewidth=1, alpha=0.9, label='Average')
    plt.title("CartPole", fontsize=14)
    plt.xlabel("episode", fontsize=12)
    plt.ylabel("reward", fontsize=12)
    plt.savefig('Rewards/PPO_reward.png')



def main():
    agent = Agent()
    agent.train()

    # Visualize test episodes
    agent.policy_network.eval()  # Set the policy network to evaluation mode

    for _ in range(10):
        state = agent.env.reset()
        done = False
        total_reward = 0

        while not done:
            action_probs = agent.policy_network.pi(torch.FloatTensor(state).to(device))
            action = torch.argmax(action_probs).item()

            next_state, reward, done, _ = agent.env.step(action)
            total_reward += reward

            agent.env.render()  # Render the environment

            state = next_state

        print("Total reward:", total_reward)

    agent.env.close()  # Close the environment after visualization
    


if __name__ == '__main__':
    main()