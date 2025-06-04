import pygame
import math
import sys
import time
import random
import os

# Pfad zum Hauptverzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, root_dir)

import bot_logic as bot_logic
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
PLAYER2_IS_BOT = False
PLAYER2_IS_AI_AGENT = False  # Neue Option für RL-Agent

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
game_state = STATE_MENU
start_time = 0; remaining_time = GAME_DURATION; last_goal_time = 0

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

def start_new_game():
    global score1, score2, start_time, remaining_time, last_goal_time, game_state
    score1 = 0; score2 = 0; start_time = time.time(); remaining_time = GAME_DURATION; last_goal_time = 0
    reset_positions()
    if PLAYER2_IS_BOT:
        bot_logic.reset_bot_state()
    # Sicherstellen, dass nach Spielstart der Zustand auf PLAYING ist
    game_state = STATE_PLAYING

running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            if event.key == pygame.K_r:
                game_state = STATE_MENU
                pygame.display.set_caption("Simple Soccer Game - Select Mode")

            if game_state == STATE_MENU:
                if event.key == pygame.K_1: 
                    PLAYER2_IS_BOT = False; 
                    start_new_game(); 
                    # game_state = STATE_PLAYING # Wird in start_new_game gesetzt
                    pygame.display.set_caption("Soccer - PvP")
                elif event.key == pygame.K_2: 
                    PLAYER2_IS_BOT = True; 
                    start_new_game(); 
                    # game_state = STATE_PLAYING # Wird in start_new_game gesetzt
                    pygame.display.set_caption("Soccer - PvE")

            elif game_state == STATE_PLAYING:
                if event.key == player1.control_key: player1.start_sprint()
                if not PLAYER2_IS_BOT and event.key == player2.control_key: player2.start_sprint()

        if event.type == pygame.KEYUP:
            if game_state == STATE_PLAYING:
                if event.key == player1.control_key: player1.stop_sprint()
                if not PLAYER2_IS_BOT and event.key == player2.control_key: player2.stop_sprint()

    if game_state == STATE_PLAYING:
        if PLAYER2_IS_BOT:
             target_goal_x = SCREEN_WIDTH - GOAL_WIDTH
             should_sprint = bot_logic.get_bot_decision(
                 player2, ball, target_goal_x,
                 SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS, BALL_RADIUS,
                 TRIBUNE_HEIGHT,
                 dt
             )
             if should_sprint and not player2.is_sprinting: player2.start_sprint()
             elif not should_sprint and player2.is_sprinting: player2.stop_sprint()

        all_sprites.update(dt, keys)

        collided_players = pygame.sprite.spritecollide(ball, players, False, pygame.sprite.collide_circle)
        for player in collided_players:
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
        elif ball.rect.left > SCREEN_WIDTH - GOAL_WIDTH and goal_y_abs_start < ball.pos.y < goal_y_abs_end:
            score1 += 1; goal_scored = True; print("Goal for Red!")
            goal_scorer_color = player1.color

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
                player1.stop_sprint(); player2.stop_sprint()

    elif game_state == STATE_GOAL_PAUSE:
        if time.time() - last_goal_time > RESET_DELAY:
            reset_positions()
            game_state = STATE_PLAYING
            start_time = time.time() - (GAME_DURATION - remaining_time) # Timer korrekt fortsetzen


    screen.fill((0,0,0))
    visuals.draw_tribunes_and_spectators(screen, SCREEN_WIDTH, SCREEN_HEIGHT, TRIBUNE_HEIGHT)

    if game_state == STATE_MENU:
        visuals.draw_text(screen, "Wähle den Modus:", menu_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 100)
        visuals.draw_text(screen, "1 : Spieler vs Spieler", main_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        visuals.draw_text(screen, "2 : Spieler vs Bot", main_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100)
        visuals.draw_text(screen, "ESC: Quit | R: Menu", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT - 50)

    elif game_state in [STATE_PLAYING, STATE_GOAL_PAUSE, STATE_GAME_OVER]:
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
             if score1 > score2: winner_text = f"Player 1 wins!"
             elif score2 > score1: winner_text = f"Player 2 wins!"
             else: winner_text = "Draw!"
             visuals.draw_text(screen, "Game Over", menu_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 60)
             visuals.draw_text(screen, winner_text, main_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 10)
             visuals.draw_text(screen, "Press R for Main Menu", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40)
             visuals.draw_text(screen, "Press ESC to Quit", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 70)
    
    # Partikel immer zuletzt zeichnen, damit sie über allem liegen
    visuals.update_and_draw_particles(dt, screen)

    pygame.display.flip()

pygame.quit()
sys.exit()