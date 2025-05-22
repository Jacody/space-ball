import os
from stable_baselines3 import PPO, A2C, DQN # Wähle einen Algorithmus
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv # Für paralleles Training (optional)
# from stable_baselines3.common.env_checker import check_env # Zum Testen der Umgebung

from rl_env import SoccerEnv # Deine Umgebung

# --- Konfiguration ---
LOG_DIR = "logs/"
MODEL_DIR = "models/"
MODEL_NAME = "ppo_soccer_agent" # Oder a2c_soccer_agent etc.
TOTAL_TIMESTEPS = 1_000_000 # Anzahl der Trainingsschritte
SAVE_FREQ = 50_000 # Wie oft das Modell gespeichert wird

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

if __name__ == '__main__':
    # Umgebung erstellen
    # Für schnelleres Training kann man mehrere Umgebungen parallel laufen lassen:
    # env = make_vec_env(SoccerEnv, n_envs=4, vec_env_cls=SubprocVecEnv)
    env = SoccerEnv(render_mode=None) # Einzelne Umgebung, kein Rendering während Training für Speed

    # Umgebung überprüfen (optional, aber gut für Debugging)
    # from stable_baselines3.common.env_checker import check_env
    # check_env(env) # Gibt Fehler aus, wenn etwas nicht stimmt

    # Callback zum Speichern des Modells
    checkpoint_callback = CheckpointCallback(
        save_freq=SAVE_FREQ,
        save_path=os.path.join(MODEL_DIR, "checkpoints/"),
        name_prefix=MODEL_NAME
    )

    # Modell initialisieren oder laden
    # model_path = os.path.join(MODEL_DIR, f"{MODEL_NAME}.zip")
    # if os.path.exists(model_path):
    #     print(f"Lade existierendes Modell von {model_path}")
    #     model = PPO.load(model_path, env=env, tensorboard_log=LOG_DIR)
    # else:
    #     print("Erstelle neues Modell")
    #     model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=LOG_DIR, learning_rate=0.0003, n_steps=2048, batch_size=64, gamma=0.99)
    #     # PPO Hyperparameter sind wichtig: learning_rate, n_steps, batch_size, gamma, ent_coef, etc.
    #     # Siehe SB3 Dokumentation für Details zu PPO und anderen Algorithmen.

    model = PPO(
        "MlpPolicy",            # Standard Feedforward Neural Network
        env,
        verbose=1,              # Zeigt Trainingsfortschritt
        tensorboard_log=LOG_DIR,
        learning_rate=3e-4,     # Lernrate
        n_steps=2048,           # Anzahl Schritte pro PPO Update
        batch_size=64,          # Mini-Batch Größe
        gamma=0.99,             # Discount Faktor für zukünftige Rewards
        gae_lambda=0.95,        # Faktor für Generalized Advantage Estimation
        ent_coef=0.0,           # Entropie Koeffizient für Exploration
        vf_coef=0.5,            # Value Function Koeffizient
        # Weitere Hyperparameter können hier gesetzt werden
    )


    print("Starte Training...")
    try:
        model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=checkpoint_callback, progress_bar=True)
    except KeyboardInterrupt:
        print("Training unterbrochen.")
    finally:
        print("Speichere finales Modell...")
        model.save(os.path.join(MODEL_DIR, f"{MODEL_NAME}_final.zip"))
        print(f"Modell gespeichert in {os.path.join(MODEL_DIR, f'{MODEL_NAME}_final.zip')}")

    # Um TensorBoard zu nutzen: `tensorboard --logdir=logs/` im Terminal ausführen