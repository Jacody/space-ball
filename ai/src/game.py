import pygame
import math
import sys
import time
import random
import os
import csv
from datetime import datetime

# Pfad zum Hauptverzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, root_dir)

import bot_left
import bot_right as bot_right
import visuals

# reset 
# reward
# play(action) -> direction
# game_iteration
# is_collision

# --- Konstanten ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
DEFAULT_P1_COLOR = (0, 255, 255)  # Türkis
DEFAULT_P2_COLOR = (255, 192, 203)  # Rosa

# --- Einstellbare Parameter (jetzt feste Standardwerte) ---
PLAYER_RADIUS = 15
BALL_RADIUS = 10
# ----------------------------

PLAYER_ROTATION_SPEED = 180
PLAYER_SPRINT_SPEED = 250
BALL_FRICTION = 0.5
BALL_KICK_MULTIPLIER = 1.1

GOAL_HEIGHT = SCREEN_HEIGHT / 3
GOAL_WIDTH = 10

TRIBUNE_HEIGHT = 50
NUM_SPECTATORS = 200

FPS = 60
GAME_DURATION = 60
RESET_DELAY = 1.5

# --- SPIELZUSTÄNDE ---
STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_GOAL_PAUSE = "GOAL_PAUSE"
STATE_GAME_OVER = "GAME_OVER"

# --- Bot Konfiguration ---
PLAYER1_IS_BOT = True
PLAYER2_IS_BOT = True
PLAYER2_IS_AI_AGENT = False  # Neue Option für RL-Agent

# --- Reward-System ---
current_reward = 0
total_reward = 0
previous_ball_x = SCREEN_WIDTH / 2
player2_touched_ball = False
last_direction_reward_time = 0

# --- Dauerschleife-System ---
round_number = 1
auto_restart_delay = 3.0  # Sekunden bis zum automatischen Neustart
game_over_start_time = 0

# --- Klassen (Player, Ball) ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, start_color, control_key, start_angle):
        super().__init__()
        self.radius = PLAYER_RADIUS
        self.control_key = control_key
        self.original_image = None; self.image = None; self.rect = None
        self.set_avatar(start_color)
        self.pos = pygame.Vector2(x, y)
        if self.rect: self.rect.center = self.pos
        else: self.rect = pygame.Rect(0,0, self.radius*2, self.radius*2); self.rect.center = self.pos
        self.velocity = pygame.Vector2(0, 0); self.angle = start_angle
        self.is_sprinting = False
        self.rotation_speed = PLAYER_ROTATION_SPEED
        self.sprint_speed = PLAYER_SPRINT_SPEED
        self.sprint_particle_timer = 0

    def update_radius(self):
        self.radius = PLAYER_RADIUS
        if hasattr(self, 'color'):
            self.set_avatar(self.color)

    def set_avatar(self, color):
        self.color = color
        self.original_image = visuals.create_player_avatar(color, self.radius)
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        if hasattr(self, 'pos') and self.pos: self.rect.center = self.pos

    def rotate(self, dt):
        if not self.original_image: return
        self.angle = (self.angle + self.rotation_speed * dt) % 360
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        # Nach der Rotation muss der rect.center neu gesetzt werden, da sich die Größe des rect ändern kann.
        self.rect = self.image.get_rect(center=self.pos)

    def start_sprint(self): self.is_sprinting = True
    def stop_sprint(self): self.is_sprinting = False; self.velocity = pygame.Vector2(0, 0)

    def update(self, dt, keys):
        self.sprint_particle_timer -= dt
        if self.is_sprinting:
            rad_angle = math.radians(self.angle)
            direction = pygame.Vector2(math.cos(rad_angle), math.sin(rad_angle))
            self.velocity = direction * self.sprint_speed
            self.pos += self.velocity * dt
            if self.sprint_particle_timer <= 0:
                particle_pos = self.pos - direction * self.radius # Partikel von hinten
                visuals.emit_particles(2, particle_pos, (220, 220, 220), vel_range=(-40, 40), life_range=(0.2, 0.5), radius_range=(2, 4))
                self.sprint_particle_timer = 0.02
        else:
            self.rotate(dt)
            self.velocity = pygame.Vector2(0, 0)

        # Kollisionsabfrage mit Spielfeldgrenzen (basierend auf self.pos und self.radius)
        field_top = TRIBUNE_HEIGHT; field_bottom = SCREEN_HEIGHT - TRIBUNE_HEIGHT
        field_left = 0; field_right = SCREEN_WIDTH
        
        # Korrektur der Position, damit der Kreis-Teil des Spielers im Feld bleibt
        if self.pos.x - self.radius < field_left: self.pos.x = field_left + self.radius
        if self.pos.x + self.radius > field_right: self.pos.x = field_right - self.radius
        if self.pos.y - self.radius < field_top: self.pos.y = field_top + self.radius
        if self.pos.y + self.radius > field_bottom: self.pos.y = field_bottom - self.radius
        
        self.rect.center = self.pos # Stelle sicher, dass rect.center immer aktuell ist

    def reset(self, x, y, angle, start_color):
         self.set_avatar(start_color)
         field_center_y = TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2
         self.pos = pygame.Vector2(x, field_center_y)
         if self.rect: self.rect.center = self.pos
         self.angle = angle
         self.is_sprinting = False
         self.velocity = pygame.Vector2(0, 0)

class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.radius = BALL_RADIUS
        self.update_appearance()
        self.pos = pygame.Vector2(x, y)
        if self.rect: self.rect.center = self.pos
        self.velocity = pygame.Vector2(0, 0)
        self.friction_factor = BALL_FRICTION
        self.trail_positions = []

    def update_radius(self):
        self.radius = BALL_RADIUS
        self.update_appearance()

    def update_appearance(self):
        self.image = visuals.create_ball_image(self.radius)
        self.rect = self.image.get_rect()
        if hasattr(self, 'pos') and self.pos: self.rect.center = self.pos

    def apply_friction(self, dt):
        self.velocity *= (self.friction_factor ** dt)
        if self.velocity.length() < 0.5: self.velocity = pygame.Vector2(0, 0)

    def update(self, dt, *args, **kwargs):
        if self.velocity.length() > visuals.BALL_TRAIL_MIN_SPEED: # Nur Spur zeichnen wenn schnell
             self.trail_positions.append(self.pos.copy())
             if len(self.trail_positions) > visuals.BALL_TRAIL_LENGTH:
                 self.trail_positions.pop(0)
        elif self.trail_positions: # Langsam geworden, Spur leeren
            self.trail_positions.clear()

        self.apply_friction(dt)
        self.pos += self.velocity * dt

        field_top = TRIBUNE_HEIGHT; field_bottom = SCREEN_HEIGHT - TRIBUNE_HEIGHT
        field_left = 0; field_right = SCREEN_WIDTH
        field_height = field_bottom - field_top
        goal_y_abs_start = field_top + (field_height / 2 - GOAL_HEIGHT / 2)
        goal_y_abs_end = field_top + (field_height / 2 + GOAL_HEIGHT / 2)
        
        if self.pos.x - self.radius < field_left:
            if not (goal_y_abs_start < self.pos.y < goal_y_abs_end):
                self.pos.x = field_left + self.radius; self.velocity.x *= -1
        if self.pos.x + self.radius > field_right:
             if not (goal_y_abs_start < self.pos.y < goal_y_abs_end):
                self.pos.x = field_right - self.radius; self.velocity.x *= -1
        if self.pos.y - self.radius < field_top:
            self.pos.y = field_top + self.radius; self.velocity.y *= -1
        if self.pos.y + self.radius > field_bottom:
            self.pos.y = field_bottom - self.radius; self.velocity.y *= -1
        self.rect.center = self.pos

    def reset(self):
         field_center_y = TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2
         self.pos = pygame.Vector2(SCREEN_WIDTH / 2, field_center_y)
         if self.rect: self.rect.center = self.pos # Sicherstellen, dass rect aktualisiert wird
         self.velocity = pygame.Vector2(0, 0)
         self.trail_positions.clear()

# --- Spiel Initialisierung ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Simple Soccer Game - Select Mode")
clock = pygame.time.Clock()
main_font = pygame.font.Font(None, 50)
menu_font = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 35)

# Spectators generieren
visuals.generate_spectators(SCREEN_WIDTH, SCREEN_HEIGHT, TRIBUNE_HEIGHT, NUM_SPECTATORS)

field_center_y = TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2
player1 = Player(SCREEN_WIDTH * 0.25, field_center_y, DEFAULT_P1_COLOR, pygame.K_a, 0)
player2 = Player(SCREEN_WIDTH * 0.75, field_center_y, DEFAULT_P2_COLOR, pygame.K_l, 180)
ball = Ball(SCREEN_WIDTH / 2, field_center_y)
all_sprites = pygame.sprite.Group(player1, player2, ball)
players = pygame.sprite.Group(player1, player2)

score1 = 0; score2 = 0
game_state = STATE_PLAYING  # Direkt im Spielmodus starten
start_time = time.time()  # Timer direkt starten
remaining_time = GAME_DURATION
last_goal_time = 0

# Initialisiere Reward-System
current_reward = 0
total_reward = 0
previous_ball_x = SCREEN_WIDTH / 2
player2_touched_ball = False
last_direction_reward_time = 0

# Bot-States initialisieren
bot_left.reset_bot_state()
bot_right.reset_bot_state()

pygame.display.set_caption("Soccer - Bot vs Bot")

def reset_positions():
    player1.update_radius()
    player2.update_radius()
    ball.update_radius()
    
    p1_color = DEFAULT_P1_COLOR
    p2_color = DEFAULT_P2_COLOR
    
    player1_start_x = SCREEN_WIDTH * 0.25; player2_start_x = SCREEN_WIDTH * 0.75
    field_center_y = TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2
        
    player1.reset(player1_start_x, field_center_y, 0, p1_color)
    player2.reset(player2_start_x, field_center_y, 180, p2_color)
    ball.reset()
    visuals.clear_particles()

def calculate_ball_direction_reward():
    """Berechnet Reward basierend auf Ball-Richtung zum gegnerischen Tor (links für player right)"""
    global previous_ball_x, player2_touched_ball, last_direction_reward_time
    
    current_time = time.time()
    
    # Ball bewegt sich nach links (Richtung gegnerisches Tor für player right)
    ball_moving_left = ball.pos.x < previous_ball_x
    previous_ball_x = ball.pos.x
    
    # Nur Reward geben wenn player2 den Ball berührt hat, Ball sich nach links bewegt 
    # UND mindestens 3 Sekunden seit dem letzten Reward vergangen sind
    if (player2_touched_ball and ball_moving_left and ball.velocity.length() > 0 
        and current_time - last_direction_reward_time >= 3.0):
        player2_touched_ball = False  # Reset nach Reward
        last_direction_reward_time = current_time  # Timer zurücksetzen
        return 1
    
    # Reset wenn Ball sich nicht nach links bewegt
    if not ball_moving_left:
        player2_touched_ball = False
        
    return 0

def handle_ball_collision():
    """Behandelt Ball-Spieler-Kollisionen und setzt player2_touched_ball Flag"""
    global player2_touched_ball
    
    collided_players = pygame.sprite.spritecollide(ball, players, False, pygame.sprite.collide_circle)
    for player in collided_players:
        # Verfolge wenn player2 den Ball berührt
        if player == player2:
            player2_touched_ball = True
            
        distance_vec = ball.pos - player.pos; distance = distance_vec.length()
        if distance == 0: collision_normal = pygame.Vector2(1, 0)
        else: collision_normal = distance_vec.normalize()

        if player.is_sprinting:
            kick_speed = player.sprint_speed * BALL_KICK_MULTIPLIER
            ball.velocity = collision_normal * kick_speed
            visuals.emit_particles(8, ball.pos, (255, 255, 100), vel_range=(-80, 80), life_range=(0.1, 0.4), radius_range=(1, 3))
        else: # Sanfter Stoß, wenn nicht gesprintet wird
            # Spieler wird leicht zurückgestoßen, Ball bekommt einen kleinen Impuls
            player_repel_strength = 20 
            ball_push_strength = 50
            
            # Spieler zurückstoßen
            # player.pos -= collision_normal * player_repel_strength * dt # Zu stark, wenn dt groß
            
            # Ball stoßen
            ball.velocity += collision_normal * ball_push_strength
        
        # Kollisionsauflösung (Overlap entfernen)
        overlap = (player.radius + ball.radius) - distance
        if overlap > 0.1: # Kleiner Puffer, um Jitter zu vermeiden
             correction_vec = collision_normal * overlap
             ball.pos += correction_vec * 0.51 # Ball etwas mehr bewegen
             player.pos -= correction_vec * 0.5 # Spieler etwas weniger
             ball.rect.center = ball.pos
             player.rect.center = player.pos

def save_score_to_csv(round_num, score_p1, score_p2, total_reward_value):
    """Speichert das Spielergebnis in eine CSV-Datei"""
    csv_filename = "game_results.csv"
    
    # Prüfen ob Datei existiert, um Header hinzuzufügen
    file_exists = os.path.exists(csv_filename)
    
    with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Runde', 'Datum_Zeit', 'Score_Bot_Left', 'Score_Bot_Right', 'Gewinner', 'Total_Reward']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Header nur schreiben wenn Datei neu ist
        if not file_exists:
            writer.writeheader()
        
        # Gewinner bestimmen
        if score_p1 > score_p2:
            winner = "Bot_Left"
        elif score_p2 > score_p1:
            winner = "Bot_Right"
        else:
            winner = "Unentschieden"
        
        # Zeile hinzufügen
        writer.writerow({
            'Runde': round_num,
            'Datum_Zeit': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Score_Bot_Left': score_p1,
            'Score_Bot_Right': score_p2,
            'Gewinner': winner,
            'Total_Reward': total_reward_value
        })
    
    print(f"Score wurde in {csv_filename} gespeichert: Runde {round_num}, {score_p1}:{score_p2}, Reward: {total_reward_value}")

def start_new_game():
    global score1, score2, start_time, remaining_time, last_goal_time, game_state, current_reward, total_reward, previous_ball_x, player2_touched_ball, last_direction_reward_time, round_number
    
    print(f"\n{'='*60}")
    print(f"RUNDE {round_number} STARTET!")
    print(f"{'='*60}\n")
    
    score1 = 0; score2 = 0; start_time = time.time(); remaining_time = GAME_DURATION; last_goal_time = 0
    current_reward = 0; total_reward = 0; previous_ball_x = SCREEN_WIDTH / 2; player2_touched_ball = False; last_direction_reward_time = 0
    reset_positions()
    if PLAYER1_IS_BOT:
        bot_left.reset_bot_state()
    if PLAYER2_IS_BOT:
        bot_right.reset_bot_state()
    # Sicherstellen, dass nach Spielstart der Zustand auf PLAYING ist
    game_state = STATE_PLAYING

# Jetzt das Spielfeld initialisieren
reset_positions()

running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            if game_state == STATE_PLAYING:
                if event.key == player1.control_key and not PLAYER1_IS_BOT: player1.start_sprint()
                if not PLAYER2_IS_BOT and event.key == player2.control_key: player2.start_sprint()

        if event.type == pygame.KEYUP:
            if game_state == STATE_PLAYING:
                if event.key == player1.control_key and not PLAYER1_IS_BOT: player1.stop_sprint()
                if not PLAYER2_IS_BOT and event.key == player2.control_key: player2.stop_sprint()

    if game_state == STATE_PLAYING:        
        # Reward für Ball-Richtung berechnen
        direction_reward = calculate_ball_direction_reward()
        current_reward = direction_reward
        total_reward += current_reward
        
        # Terminal-Ausgabe der Spielwerte
        ball_speed = ball.velocity.length()
        ball_direction = 0
        if ball_speed > 0:
            ball_direction = math.degrees(math.atan2(ball.velocity.y, ball.velocity.x))
        
        print(f"RUNDE {round_number} | Zeit: {int(remaining_time//60):02}:{int(remaining_time%60):02} | Score: {score1}:{score2}")
        print(f"Position Player Right: ({player2.pos.x:.1f}, {player2.pos.y:.1f})")
        print(f"Direction Player Right: {player2.angle:.1f}°")
        print(f"Position Ball: ({ball.pos.x:.1f}, {ball.pos.y:.1f})")
        print(f"Speed Ball: {ball_speed:.1f}")
        print(f"Direction Ball: {ball_direction:.1f}°")
        print(f"Position Player Left: ({player1.pos.x:.1f}, {player1.pos.y:.1f})")
        print(f"Current Reward: {current_reward}")
        print(f"Total Reward: {total_reward}")
        
        # Cooldown-Information für Richtungs-Reward
        current_time = time.time()
        cooldown_remaining = max(0, 3.0 - (current_time - last_direction_reward_time))
        print(f"Direction Reward Cooldown: {cooldown_remaining:.1f}s")
        print("-" * 50)
        
        # Bot-Logik für Player1 (bot_left)
        if PLAYER1_IS_BOT:
             target_goal_x = SCREEN_WIDTH - GOAL_WIDTH  # Rechtes Tor für Player1 (bot_left)
             should_sprint = bot_left.get_bot_decision(
                 player1, ball, target_goal_x,
                 SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS, BALL_RADIUS,
                 TRIBUNE_HEIGHT,
                 dt
             )
             if should_sprint and not player1.is_sprinting: player1.start_sprint()
             elif not should_sprint and player1.is_sprinting: player1.stop_sprint()

        # Bot-Logik für Player2 (bot_right)
        if PLAYER2_IS_BOT:
             target_goal_x = 0  # Linkes Tor für Player2 (bot_right)
             should_sprint = bot_right.get_bot_decision(
                 player2, ball, target_goal_x,
                 SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS, BALL_RADIUS,
                 TRIBUNE_HEIGHT,
                 dt
             )
             if should_sprint and not player2.is_sprinting: player2.start_sprint()
             elif not should_sprint and player2.is_sprinting: player2.stop_sprint()

        all_sprites.update(dt, keys)

        handle_ball_collision()

        # Spieler-Spieler-Kollision
        if pygame.sprite.collide_circle(player1, player2): # Nutze die eingebaute circle collision
             dist_vec_p1_p2 = player2.pos - player1.pos
             dist_p1_p2 = dist_vec_p1_p2.length()
             # Überprüfe, ob sie wirklich überlappen, da collide_circle nur prüft, ob rects kollidieren
             # und DANN die Kreiskollision macht. Wenn sie durch andere Logik schon getrennt wurden, ist dist > summe_radien
             if dist_p1_p2 < (player1.radius + player2.radius) and dist_p1_p2 > 0: # dist > 0 um Division durch Null zu vermeiden
                 correction_normal = dist_vec_p1_p2.normalize()
                 overlap = (player1.radius + player2.radius) - dist_p1_p2
                 
                 player1.pos -= correction_normal * overlap / 2
                 player2.pos += correction_normal * overlap / 2
                 player1.rect.center = player1.pos
                 player2.rect.center = player2.pos


        goal_scored = False
        field_top = TRIBUNE_HEIGHT; field_bottom = SCREEN_HEIGHT - TRIBUNE_HEIGHT
        field_height = field_bottom - field_top; goal_y_abs_start = field_top + (field_height / 2 - GOAL_HEIGHT / 2)
        goal_y_abs_end = field_top + (field_height / 2 + GOAL_HEIGHT / 2)
        goal_scorer_color = None

        if ball.rect.right < GOAL_WIDTH and goal_y_abs_start < ball.pos.y < goal_y_abs_end:
            score2 += 1; goal_scored = True; print("Goal for Blue!")
            goal_scorer_color = player2.color
            # Tor für player right (linkes Tor) = +100 Reward
            current_reward = 100
            total_reward += current_reward
            print(f"TOR! Reward: {current_reward}, Total Reward: {total_reward}")
        elif ball.rect.left > SCREEN_WIDTH - GOAL_WIDTH and goal_y_abs_start < ball.pos.y < goal_y_abs_end:
            score1 += 1; goal_scored = True; print("Goal for Red!")
            goal_scorer_color = player1.color
            # Gegentor für player right (rechtes Tor) = -100 Reward
            current_reward = -100
            total_reward += current_reward
            print(f"GEGENTOR! Reward: {current_reward}, Total Reward: {total_reward}")

        if goal_scored:
            game_state = STATE_GOAL_PAUSE; last_goal_time = time.time()
            player1.stop_sprint(); player2.stop_sprint()
            # Konfetti-Effekt
            confetti_source_y = SCREEN_HEIGHT / 2 # Etwas über der Mitte
            for _ in range(60): # Mehr Partikel für Torjubel
                pos_x = random.uniform(SCREEN_WIDTH * 0.3, SCREEN_WIDTH * 0.7) # Breiter gestreut
                pos_y = random.uniform(confetti_source_y - 50, confetti_source_y + 50) # Vertikal gestreut
                
                # Wähle eine Farbe, die die Tor-Farbe oder eine zufällige Tribünenfarbe sein kann
                if random.random() < 0.6 and goal_scorer_color: # 60% Chance für Tor-Farbe
                    base_conf_color = goal_scorer_color
                else:
                    base_conf_color = random.choice(visuals.SPECTATOR_COLORS)

                visuals.emit_particles(1, (pos_x, pos_y), base_conf_color,
                               vel_range=(-60, 60), life_range=(1.5, 3.0), # Längere Lebensdauer, mehr Streuung
                               radius_range=(4, 8), gravity=70) # Größere Partikel, stärkere Gravitation

        if start_time > 0 and game_state == STATE_PLAYING: # Timer nur im PLAYING-Zustand aktualisieren
            elapsed_time = time.time() - start_time
            remaining_time = max(0, GAME_DURATION - elapsed_time)
            if remaining_time == 0:
                game_state = STATE_GAME_OVER
                game_over_start_time = time.time()
                player1.stop_sprint(); player2.stop_sprint()
                
                # Score in CSV speichern
                save_score_to_csv(round_number, score1, score2, total_reward)
                
                # Ergebnis der Runde ausgeben
                print(f"\n{'='*60}")
                print(f"RUNDE {round_number} BEENDET!")
                if score1 > score2:
                    print(f"GEWINNER: Bot Left (Rot) - {score1}:{score2}")
                elif score2 > score1:
                    print(f"GEWINNER: Bot Right (Rosa) - {score2}:{score1}")
                else:
                    print(f"UNENTSCHIEDEN - {score1}:{score2}")
                print(f"Nächste Runde startet in {auto_restart_delay} Sekunden...")
                print(f"{'='*60}\n")

    elif game_state == STATE_GOAL_PAUSE:
        if time.time() - last_goal_time > RESET_DELAY:
            reset_positions()
            game_state = STATE_PLAYING
            start_time = time.time() - (GAME_DURATION - remaining_time) # Timer korrekt fortsetzen
    
    elif game_state == STATE_GAME_OVER:
        # Automatischer Neustart nach Verzögerung
        if time.time() - game_over_start_time > auto_restart_delay:
            round_number += 1
            start_new_game()

    screen.fill((0,0,0))
    visuals.draw_tribunes_and_spectators(screen, SCREEN_WIDTH, SCREEN_HEIGHT, TRIBUNE_HEIGHT)

    # Menu entfernt - automatischer Dauerlauf
    if game_state in [STATE_PLAYING, STATE_GOAL_PAUSE, STATE_GAME_OVER]:
        visuals.draw_field(screen, SCREEN_WIDTH, SCREEN_HEIGHT, TRIBUNE_HEIGHT, GOAL_WIDTH, GOAL_HEIGHT)
        if ball.velocity.length() > visuals.BALL_TRAIL_MIN_SPEED or len(ball.trail_positions) > 0 : # Trail nur wenn nötig
            visuals.draw_ball_trail(screen, ball.trail_positions, BALL_RADIUS)
        
        all_sprites.draw(screen) # Zeichnet Spieler und Ball

        score_text = f"P1: {score1} - P2: {score2}"
        visuals.draw_text(screen, score_text, main_font, SCREEN_WIDTH / 2, TRIBUNE_HEIGHT / 2)
        minutes = int(remaining_time // 60); seconds = int(remaining_time % 60)
        timer_text = f"{minutes:02}:{seconds:02}"
        visuals.draw_text(screen, timer_text, main_font, SCREEN_WIDTH - 100, TRIBUNE_HEIGHT / 2)

        if game_state == STATE_GOAL_PAUSE:
             visuals.draw_text(screen, "GOAL!", menu_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        elif game_state == STATE_GAME_OVER:
             winner_text = ""
             if score1 > score2: 
                 winner_text = f"Bot Left gewinnt!"
             elif score2 > score1: 
                 winner_text = f"Bot Right gewinnt!"
             else: 
                 winner_text = "Unentschieden!"
             
             countdown = max(0, auto_restart_delay - (time.time() - game_over_start_time))
             visuals.draw_text(screen, f"Runde {round_number} beendet", menu_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 60)
             visuals.draw_text(screen, winner_text, main_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 10)
             visuals.draw_text(screen, f"Nächste Runde in {countdown:.1f}s", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40)
             visuals.draw_text(screen, "ESC: Quit", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 70)
    
    # Partikel immer zuletzt zeichnen, damit sie über allem liegen
    visuals.update_and_draw_particles(dt, screen)

    pygame.display.flip()

pygame.quit()
sys.exit()