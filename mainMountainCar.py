import gym
import numpy as np
import matplotlib.pyplot as plt


def plot_training_results(rewards, algorithm, color):
    plt.plot(rewards, color=color, label=algorithm)


def run_episode(env, policy):
    observation = env.reset()
    total_reward = 0
    done = False

    while not done:
        action = policy(observation)
        next_observation, reward, done, _ = env.step(action)
        total_reward += reward
        env.render()
        observation = next_observation

    return total_reward


def vpg(env, policy, learning_rate, num_episodes):
    rewards = []

    for episode in range(num_episodes):
        total_reward = run_episode(env, policy)

        rewards.append(total_reward)

        if episode % 10 == 0:
            print(f'VPG - Episode: {episode}, Total Reward: {total_reward}')

    return rewards


def ppo(env, policy, learning_rate, num_episodes):
    rewards = []

    for episode in range(num_episodes):
        total_reward = run_episode(env, policy)

        rewards.append(total_reward)

        if episode % 10 == 0:
            print(f'PPO - Episode: {episode}, Total Reward: {total_reward}')

    return rewards


def trpo(env, policy, learning_rate, num_episodes):
    rewards = []

    for episode in range(num_episodes):
        total_reward = run_episode(env, policy)

        rewards.append(total_reward)

        if episode % 10 == 0:
            print(f'TRPO - Episode: {episode}, Total Reward: {total_reward}')

    return rewards


# Policy function for random actions
def random_policy(observation):
    return env.action_space.sample()


# Set up the environment
env = gym.make('MountainCar-v0', render_mode="human") # render_mode="human" || render_mode="rgb_array"

# Training parameters
learning_rate = 0.01
num_episodes = 100

# Run VPG
vpg_rewards = vpg(env, random_policy, learning_rate, num_episodes)
plot_training_results(vpg_rewards, "VPG", color='blue')

# Run PPO
ppo_rewards = ppo(env, random_policy, learning_rate, num_episodes)
plot_training_results(ppo_rewards, "PPO", color='green')

# Run TRPO
trpo_rewards = trpo(env, random_policy, learning_rate, num_episodes)
plot_training_results(trpo_rewards, "TRPO", color='orange')

# Plot the combined training results
plt.xlabel('Episode')
plt.ylabel('Total Reward')
plt.title('Training Results - VPG, PPO, and TRPO')
plt.legend()
plt.show()

env.close()
