import time
import sys
import os

# Pfad zur src/ai hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
ai_dir = os.path.join(project_root, 'src', 'ai')
sys.path.insert(0, ai_dir)

from stable_baselines3 import PPO # oder den Algorithmus, den du trainiert hast
from rl_env import SoccerEnv
import os

MODEL_DIR = "models/"
# Wähle das Modell, das du laden möchtest (z.B. das letzte oder ein bestimmtes Checkpoint)
MODEL_NAME = "ppo_soccer_agent_final.zip" # oder "checkpoints/ppo_soccer_agent_XXXXX_steps.zip"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)

if __name__ == '__main__':
    if not os.path.exists(MODEL_PATH):
        print(f"Modell {MODEL_PATH} nicht gefunden. Bitte zuerst trainieren.")
        exit()

    env = SoccerEnv(render_mode='human') # 'human' für sichtbares Spielen

    # Lade das trainierte Modell
    model = PPO.load(MODEL_PATH, env=env)
    print(f"Modell {MODEL_PATH} geladen.")

    obs, info = env.reset()
    terminated = False
    truncated = False
    total_reward = 0
    num_episodes = 5 # Wie viele Spiele sollen gespielt werden

    for episode in range(num_episodes):
        print(f"\nStarte Episode {episode + 1}/{num_episodes}")
        obs, info = env.reset()
        terminated = False
        truncated = False
        episode_reward = 0
        step = 0
        while not terminated and not truncated:
            action, _states = model.predict(obs, deterministic=True) # deterministic=True für beste Aktion
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            env.render() # Wird intern in step gehandhabt, wenn render_mode='human'
            step +=1
            # time.sleep(0.01) # Um das Spiel zu verlangsamen, falls nötig

            if terminated or truncated:
                print(f"Episode beendet nach {step} Schritten.")
                print(f"Agent Score: {info.get('agent_score', 0)}, Opponent Score: {info.get('opponent_score', 0)}")
                print(f"Episode Reward: {episode_reward}")
                total_reward += episode_reward
        
    print(f"\nDurchschnittlicher Reward über {num_episodes} Episoden: {total_reward / num_episodes}")
    env.close()