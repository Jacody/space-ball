import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pygame # Für Konstanten und ggf. interne Spielinstanz

# Importiere dein Spiel oder die relevanten Teile
# Du musst main_game.py so anpassen, dass es als Modul importiert werden kann
# und eine Klasse oder Funktionen bereitstellt, um das Spiel zu steuern/abzufragen.
# Beispiel: from main_game import SoccerGameInstance, PLAYER_RADIUS, BALL_RADIUS etc.
# Für dieses Beispiel tue ich so, als gäbe es eine solche Klasse:
from main_game import (
    Player, Ball, SCREEN_WIDTH, SCREEN_HEIGHT, TRIBUNE_HEIGHT,
    PLAYER_RADIUS, BALL_RADIUS, GOAL_WIDTH, GOAL_HEIGHT,
    DEFAULT_P1_COLOR, DEFAULT_P2_COLOR,
    Particle, emit_particles, update_and_draw_particles, particles, # Wenn Partikel Teil des States/Rewards sind
    # ... und andere relevante Konstanten/Funktionen
)

# --- Konstanten für RL ---
# Definiere die Aktionen, die der Agent ausführen kann
# Beispiel: 0: Nichtstun/Rotation stoppen, 1: Sprinten, 2: Links drehen (wenn nicht sprintend), 3: Rechts drehen (wenn nicht sprintend)
ACTION_DO_NOTHING = 0
ACTION_SPRINT = 1
ACTION_ROTATE_LEFT = 2
ACTION_ROTATE_RIGHT = 3
# Alternativ könnte man auch Sprint und Rotation getrennt steuern (MultiDiscrete Action Space)

MAX_STEPS_PER_EPISODE = 2500 # Verhindert Endlos-Episoden

class SoccerEnv(gym.Env):
    metadata = {'render_modes': ['human', 'rgb_array'], 'render_fps': 60}

    def __init__(self, render_mode=None):
        super().__init__()

        self.render_mode = render_mode
        self.screen = None
        self.clock = None

        # Definiere den Aktionsraum (Beispiel mit 4 diskreten Aktionen)
        self.action_space = spaces.Discrete(4) # 0: Idle, 1: Sprint, 2: Rotate Left, 3: Rotate Right

        # Definiere den Beobachtungsraum (State)
        # Beispiel:
        # P2_x, P2_y, P2_angle_cos, P2_angle_sin, P2_is_sprinting
        # Ball_x, Ball_y, Ball_vx, Ball_vy
        # P1_x, P1_y, P1_angle_cos, P1_angle_sin, P1_is_sprinting (Gegner)
        # Dist_P2_to_Ball, Angle_P2_to_Ball_cos, Angle_P2_to_Ball_sin
        # Dist_Ball_to_Opp_Goal, Angle_Ball_to_Opp_Goal_cos, Angle_Ball_to_Opp_Goal_sin
        # Dist_P2_to_Opp_Goal, Angle_P2_to_Opp_Goal_cos, Angle_P2_to_Opp_Goal_sin

        # Normalisiere die Werte!
        # Positionen: 0 bis 1 (geteilt durch SCREEN_WIDTH/HEIGHT)
        # Winkel: cos/sin sind bereits [-1, 1]
        # Geschwindigkeiten: geteilt durch eine Maximalgeschwindigkeit
        # ist_sprinting: 0 oder 1

        # Anzahl der Features im State
        # P2(pos_x, pos_y, cos_angle, sin_angle, is_sprinting) = 5
        # Ball(pos_x, pos_y, vel_x, vel_y) = 4
        # P1(pos_x, pos_y, cos_angle, sin_angle, is_sprinting) = 5
        # Relative_P2_Ball(dist, cos_angle, sin_angle) = 3
        # Relative_Ball_OppGoal(dist, cos_angle, sin_angle) = 3
        # Relative_P2_OppGoal(dist, cos_angle, sin_angle) = 3
        # Total = 5 + 4 + 5 + 3 + 3 + 3 = 23
        # Die genaue Anzahl hängt von deinem State Design ab.
        # Es ist oft besser, relative Positionen/Winkel zu verwenden.

        # Beispiel für einen einfachen State:
        # P2_x_norm, P2_y_norm, P2_angle_rad_norm,
        # Ball_x_norm, Ball_y_norm,
        # Ball_vx_norm, Ball_vy_norm,
        # Dist_P2_Ball_norm, Angle_P2_Ball_rad_norm (relativer Winkel)
        # (9 Features)
        # Wichtig: Winkel als cos/sin für Kontinuität
        num_obs_features = 10 # (P2_x, P2_y, P2_cos, P2_sin, Ball_x, Ball_y, Ball_vx, Ball_vy, P1_x, P1_y)
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(num_obs_features,), dtype=np.float32)


        # Spielinstanz initialisieren
        self._init_game_state()
        self.current_step = 0


    def _init_game_state(self):
        # Hier wird dein Pygame-Spiel initialisiert oder zurückgesetzt
        # Erstelle Spieler, Ball etc.
        # Verwende die Logik aus deinem `reset_positions` und `start_new_game` (ohne Zeit)
        self.player1 = Player(SCREEN_WIDTH * 0.25, self._field_center_y(), DEFAULT_P1_COLOR, pygame.K_a, 0)
        self.agent_player = Player(SCREEN_WIDTH * 0.75, self._field_center_y(), DEFAULT_P2_COLOR, -1, 180) # -1 da keine Taste
        self.ball = Ball(SCREEN_WIDTH / 2, self._field_center_y())
        
        self.score_agent = 0
        self.score_opponent = 0
        particles.clear() # Partikel zurücksetzen

        # Wichtig: Spieler 1 (Gegner) braucht eine Logik.
        # Fürs Erste: Steht still oder einfache Heuristik
        # from bot_logic import get_bot_decision # Falls du den Bot als Gegner willst

    def _field_center_y(self):
        return TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2

    def _get_obs(self):
        # Sammle den aktuellen Zustand und normalisiere ihn
        p2 = self.agent_player
        b = self.ball
        p1 = self.player1 # Gegner

        obs = np.array([
            p2.pos.x / SCREEN_WIDTH,
            (p2.pos.y - TRIBUNE_HEIGHT) / (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT), # Normalisiere y relativ zum Spielfeld
            np.cos(np.radians(p2.angle)),
            np.sin(np.radians(p2.angle)),
            b.pos.x / SCREEN_WIDTH,
            (b.pos.y - TRIBUNE_HEIGHT) / (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT),
            b.velocity.x / (self.agent_player.sprint_speed * 1.5), # Annahme max Ball Speed
            b.velocity.y / (self.agent_player.sprint_speed * 1.5),
            p1.pos.x / SCREEN_WIDTH, # Gegnerinfo
            (p1.pos.y - TRIBUNE_HEIGHT) / (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT)
            # Füge ggf. mehr hinzu: p1 Winkel, relative Distanzen/Winkel etc.
        ], dtype=np.float32)
        return np.clip(obs, -1.0, 1.0) # Sicherstellen, dass Werte im Bereich bleiben

    def _get_info(self):
        # Optionale Debug-Infos
        return {"agent_score": self.score_agent, "opponent_score": self.score_opponent}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed) # Wichtig für Reproduzierbarkeit
        self._init_game_state()
        self.current_step = 0
        
        observation = self._get_obs()
        info = self._get_info()
        
        if self.render_mode == "human":
            self._render_frame()
            
        return observation, info

    def step(self, action):
        self.current_step += 1
        reward = 0
        terminated = False # Episode endet (z.B. Tor, Zeitlimit im Spiel)
        truncated = False  # Episode wird vorzeitig abgebrochen (z.B. MAX_STEPS_PER_EPISODE erreicht)

        # 1. Aktion des Agenten (player2) ausführen
        p2 = self.agent_player
        prev_p2_dist_to_ball = p2.pos.distance_to(self.ball.pos)
        prev_ball_dist_to_opp_goal = self.ball.pos.distance_to(pygame.Vector2(0, self._field_center_y())) # Gegnerisches Tor ist links für P2

        if action == ACTION_SPRINT:
            if not p2.is_sprinting: p2.start_sprint()
        elif action == ACTION_DO_NOTHING:
            if p2.is_sprinting: p2.stop_sprint()
            # Keine Rotation
        elif action == ACTION_ROTATE_LEFT:
            if p2.is_sprinting: p2.stop_sprint()
            p2.angle = (p2.angle - p2.rotation_speed * (1/self.metadata['render_fps'])) % 360 # Annahme dt = 1/fps
        elif action == ACTION_ROTATE_RIGHT:
            if p2.is_sprinting: p2.stop_sprint()
            p2.angle = (p2.angle + p2.rotation_speed * (1/self.metadata['render_fps'])) % 360

        # 2. Gegner-Logik (player1) - sehr einfach hier
        # player1.update(dt, keys) # Hier müsste eine KI oder Heuristik für P1 rein
        # Fürs Erste: P1 macht nichts oder einfache Verfolgung
        if self.ball.pos.x < SCREEN_WIDTH / 2: # Wenn Ball in P1s Hälfte
            if not self.player1.is_sprinting: self.player1.start_sprint()
            # Einfache Ausrichtung auf Ball
            target_angle = (self.ball.pos - self.player1.pos).angle_to(pygame.Vector2(1,0))
            self.player1.angle = target_angle
        else:
            if self.player1.is_sprinting: self.player1.stop_sprint()


        # 3. Spielphysik aktualisieren (dt simulieren)
        # Normalerweise würde man hier die update-Methoden der Spielobjekte aufrufen
        # mit einem festen dt, z.B. 1.0 / self.metadata['render_fps']
        dt = 1.0 / self.metadata['render_fps'] # Wichtig für konsistente Physik
        
        self.agent_player.update(dt, None) # None für keys, da wir direkt steuern
        self.player1.update(dt, None)     # P1 wird hier rudimentär gesteuert
        self.ball.update(dt)
        
        # Partikel (optional, wenn sie den State oder Reward beeinflussen sollen)
        # update_and_draw_particles(dt, None) # 'None' für surface, da wir hier nicht rendern müssen
        
        # 4. Kollisionen und Spielregeln
        # Ball-Spieler Kollision
        players = pygame.sprite.Group(self.player1, self.agent_player)
        collided_players = pygame.sprite.spritecollide(self.ball, players, False, pygame.sprite.collide_circle)
        agent_kicked_ball = False
        for player in collided_players:
            distance_vec = self.ball.pos - player.pos; distance = distance_vec.length()
            if distance == 0: collision_normal = pygame.Vector2(1, 0)
            else: collision_normal = distance_vec.normalize()

            if player.is_sprinting:
                kick_speed = player.sprint_speed * 1.1 # BALL_KICK_MULTIPLIER
                self.ball.velocity = collision_normal * kick_speed
                if player == self.agent_player: # Agent hat gekickt
                    agent_kicked_ball = True
                    # emit_particles(8, self.ball.pos, (255,255,100)) # Optional
            else:
                self.ball.velocity += collision_normal * 50 # Sanfter Stoß

            overlap = (player.radius + self.ball.radius) - distance
            if overlap > 0.1:
                 correction_vec = collision_normal * overlap
                 self.ball.pos += correction_vec * 0.51
                 player.pos -= correction_vec * 0.5
                 self.ball.rect.center = self.ball.pos
                 player.rect.center = player.pos
        
        # Spieler-Spieler Kollision (vereinfacht)
        if pygame.sprite.collide_circle(self.player1, self.agent_player):
             dist_vec = self.agent_player.pos - self.player1.pos
             dist = dist_vec.length()
             if dist < (self.player1.radius + self.agent_player.radius) and dist > 0:
                 correction_normal = dist_vec.normalize()
                 overlap = (self.player1.radius + self.agent_player.radius) - dist
                 self.player1.pos -= correction_normal * overlap / 2
                 self.agent_player.pos += correction_normal * overlap / 2
                 # rects updaten nicht nötig für reine Logik, nur für Pygame draw


        # Torerfassung
        field_top = TRIBUNE_HEIGHT; field_bottom = SCREEN_HEIGHT - TRIBUNE_HEIGHT
        field_height = field_bottom - field_top;
        goal_y_start = field_top + (field_height / 2 - GOAL_HEIGHT / 2)
        goal_y_end = field_top + (field_height / 2 + GOAL_HEIGHT / 2)

        goal_for_agent = False
        goal_for_opponent = False

        if self.ball.rect.right < GOAL_WIDTH and goal_y_start < self.ball.pos.y < goal_y_end: # Agent (P2) schießt ins linke Tor
            self.score_agent += 1
            goal_for_agent = True
            terminated = True
            print(f"RL Agent scored! Current step: {self.current_step}")
        elif self.ball.rect.left > SCREEN_WIDTH - GOAL_WIDTH and goal_y_start < self.ball.pos.y < goal_y_end: # Gegner (P1) schießt ins rechte Tor
            self.score_opponent += 1
            goal_for_opponent = True
            terminated = True
            print(f"Opponent scored! Current step: {self.current_step}")

        # 5. Reward berechnen (Zielfunktion)
        # Grundbelohnungen
        if goal_for_agent: reward += 100.0
        if goal_for_opponent: reward -= 100.0

        # Shaping Rewards (um das Lernen zu lenken)
        # - Annäherung an den Ball
        current_p2_dist_to_ball = self.agent_player.pos.distance_to(self.ball.pos)
        reward += (prev_p2_dist_to_ball - current_p2_dist_to_ball) * 0.1 # Belohnung für Annäherung

        # - Ball in Richtung gegnerisches Tor bewegen (wenn Agent gekickt hat)
        if agent_kicked_ball:
            current_ball_dist_to_opp_goal = self.ball.pos.distance_to(pygame.Vector2(0, self._field_center_y()))
            reward += (prev_ball_dist_to_opp_goal - current_ball_dist_to_opp_goal) * 0.5
            # Belohnung für das Schießen des Balls
            reward += 5.0

        # - Strafe für jeden Zeitschritt (um schnelles Handeln zu fördern)
        reward -= 0.01

        # - Strafe, wenn Ball ins eigene Tor geschossen wird (oder in die Nähe)
        # TODO: Verfeinern

        # 6. Prüfen, ob Episode beendet ist
        if self.current_step >= MAX_STEPS_PER_EPISODE:
            truncated = True # Zeitlimit der Episode erreicht

        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self._render_frame()

        return observation, reward, terminated, truncated, info

    def render(self):
        if self.render_mode == "rgb_array":
            return self._render_frame()
        # human mode wird in step und reset gehandhabt

    def _render_frame(self):
        if self.screen is None and self.render_mode == "human":
            pygame.init()
            pygame.display.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("RL Soccer Training")
        if self.clock is None and self.render_mode == "human":
            self.clock = pygame.time.Clock()

        if self.screen is None: # Für rgb_array, erstelle eine Surface, falls nicht vorhanden
             self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))


        # Hier die Zeichenlogik aus deinem Hauptspiel einfügen
        # (draw_tribunes, draw_field, draw_sprites, draw_text etc.)
        # --- Temporäre einfache Zeichenlogik ---
        self.screen.fill((0,0,0)) # Black background
        # Field
        field_rect = pygame.Rect(0, TRIBUNE_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT)
        pygame.draw.rect(self.screen, (34,139,34), field_rect) # FIELD_COLOR
        # Goals (vereinfacht)
        goal_y_start = TRIBUNE_HEIGHT + (field_rect.height / 2 - GOAL_HEIGHT / 2)
        goal_y_end = TRIBUNE_HEIGHT + (field_rect.height / 2 + GOAL_HEIGHT / 2)
        pygame.draw.line(self.screen, (255,255,255), (GOAL_WIDTH, goal_y_start), (GOAL_WIDTH, goal_y_end), 5)
        pygame.draw.line(self.screen, (255,255,255), (SCREEN_WIDTH - GOAL_WIDTH, goal_y_start), (SCREEN_WIDTH - GOAL_WIDTH, goal_y_end), 5)

        # Spieler und Ball (manuell zeichnen, da all_sprites nicht direkt hier ist)
        # Wichtig: Die `image` und `rect` Attribute der Spieler/Ball müssen aktuell sein
        # Dies geschieht in deren `update` Methoden, wenn sie mit Pygame Sprites arbeiten.
        # Wenn nicht, musst du sie hier manuell transformieren/zeichnen.
        # Für dieses Beispiel nehmen wir an, die Player/Ball Klassen haben eine draw(surface) Methode.
        # Oder wir erstellen temporäre Sprites für die Darstellung
        temp_sprites = pygame.sprite.Group(self.player1, self.agent_player, self.ball)
        
        # Sicherstellen, dass die Sprites Bilder haben, falls sie im RL-Loop nicht immer welche generieren
        if not self.player1.image: self.player1.set_avatar(self.player1.color)
        if not self.agent_player.image: self.agent_player.set_avatar(self.agent_player.color)
        if not self.ball.image: self.ball.update_appearance()

        # Wichtig: rects müssen aktuell sein für pygame.sprite.Group().draw()
        self.player1.rect.center = self.player1.pos
        self.agent_player.rect.center = self.agent_player.pos
        self.ball.rect.center = self.ball.pos

        # Drehung anwenden, falls die Spieler nicht von sich aus ihr rotiertes Bild aktualisieren
        # In deinem Code rotiert Player.image im Player.rotate()
        # Wenn Spieler nicht sprinten, wird rotate() in Player.update() aufgerufen.
        # Wenn sie sprinten, nicht. Fürs Rendering hier könnte man es erzwingen,
        # aber besser ist es, wenn die Player-Klasse das self.image immer aktuell hält.
        # Die Original-Player-Klasse sollte das tun.

        temp_sprites.draw(self.screen)

        if self.render_mode == "human":
            pygame.event.pump() # Wichtig für Pygame Fenster-Events
            pygame.display.flip()
            self.clock.tick(self.metadata['render_fps'])
        elif self.render_mode == "rgb_array":
            return np.transpose(
                pygame.surfarray.array3d(self.screen), axes=(1, 0, 2)
            )

    def close(self):
        if self.screen is not None:
            pygame.display.quit()
            pygame.quit()
            self.screen = None
            self.clock = None