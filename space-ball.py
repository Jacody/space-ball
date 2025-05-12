import pygame
import math
import sys
import time
import random
import bot_logic

# --- Konstanten ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FIELD_COLOR = (34, 139, 34)
LINE_COLOR = (255, 255, 255)
TEXT_COLOR = (255, 255, 255)
# HIGHLIGHT_COLOR = (255, 255, 0) # Nicht mehr benötigt für Avatar-Auswahl
# DISABLED_COLOR = (100, 100, 100) # Nicht mehr benötigt für Avatar-Auswahl
DEFAULT_P1_COLOR = (255, 0, 0) # Rot
DEFAULT_P2_COLOR = (0, 0, 255) # Blau
BALL_COLOR = (255, 255, 255)
TRIBUNE_COLOR = (60, 60, 60)

# --- Einstellbare Parameter (jetzt feste Standardwerte) ---
PLAYER_RADIUS = 15  # Früher DEFAULT_PLAYER_RADIUS
BALL_RADIUS = 10    # Früher DEFAULT_BALL_RADIUS
# MIN_RADIUS = 5 # Nicht mehr für Einstellungen benötigt
# MAX_PLAYER_RADIUS = 25 # Nicht mehr für Einstellungen benötigt
# MAX_BALL_RADIUS = 20 # Nicht mehr für Einstellungen benötigt
# ----------------------------

PLAYER_ROTATION_SPEED = 180
PLAYER_SPRINT_SPEED = 250
BALL_FRICTION = 0.5
BALL_KICK_MULTIPLIER = 1.1

GOAL_HEIGHT = SCREEN_HEIGHT / 3
GOAL_WIDTH = 10

TRIBUNE_HEIGHT = 50
NUM_SPECTATORS = 200
SPECTATOR_RADIUS = 3
SPECTATOR_COLORS = [
    (200, 0, 0), (0, 0, 200), (200, 200, 0), (0, 200, 0),
    (200, 100, 0), (150, 0, 150), (100, 100, 100), (255, 150, 150),
    (150, 150, 255), (255, 255, 150)
]

FPS = 60
GAME_DURATION = 120
RESET_DELAY = 1.5

# --- Effekt Konstanten ---
MAX_PARTICLES = 300 # Begrenzung der Partikelanzahl
BALL_TRAIL_LENGTH = 12
BALL_TRAIL_MIN_SPEED = 150 # Nur Spur zeichnen, wenn Ball schnell genug ist

# --- SPIELZUSTÄNDE ---
# STATE_SETTINGS = "SETTINGS" # Entfernt
# STATE_AVATAR_SELECT = "AVATAR_SELECT" # Entfernt
STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_GOAL_PAUSE = "GOAL_PAUSE"
STATE_GAME_OVER = "GAME_OVER"

# --- AVATAR KONSTANTEN & DATEN (nicht mehr für Auswahl benötigt) ---
# AVATAR_COLORS = [ ... ] # Entfernt
# AVATAR_DISPLAY_SIZE = PLAYER_RADIUS * 3 # Entfernt
# AVATAR_SPACING = AVATAR_DISPLAY_SIZE + 20 # Entfernt

# --- Bot Konfiguration ---
PLAYER2_IS_BOT = False

# --- Partikel Klasse ---
class Particle:
    def __init__(self, pos, vel, color, lifetime, radius_range=(1, 3), gravity=0):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.color = color
        self.lifetime = lifetime
        self.start_lifetime = lifetime # Für Fading
        self.radius = random.uniform(radius_range[0], radius_range[1])
        self.gravity = gravity

    def update(self, dt):
        self.vel.y += self.gravity * dt # Schwerkraft anwenden
        self.pos += self.vel * dt
        self.lifetime -= dt
        # Radius schrumpfen lassen
        if self.start_lifetime > 0:
            self.radius = max(0, self.radius * (self.lifetime / self.start_lifetime))

    def draw(self, surface):
        if self.lifetime > 0 and self.radius >= 1:
            # Alpha basierend auf Lebenszeit für Fade-Out
            alpha = max(0, min(255, int(255 * (self.lifetime / self.start_lifetime))))
            try:
                # Zeichne auf temporärer Surface für Alpha-Blending
                temp_surf = pygame.Surface((int(self.radius*2), int(self.radius*2)), pygame.SRCALPHA)
                draw_color = (*self.color[:3], alpha) # Stelle sicher, dass Alpha gesetzt wird
                pygame.draw.circle(temp_surf, draw_color, (int(self.radius), int(self.radius)), int(self.radius))
                surface.blit(temp_surf, self.pos - pygame.Vector2(self.radius, self.radius))
            except ValueError: # Kann bei ungültigen Farben/Alpha passieren
                pass # Einfach nicht zeichnen
            except TypeError: # Falls Farbe kein Tupel ist
                 pygame.draw.circle(surface, self.color, self.pos, int(self.radius)) # Fallback ohne Alpha

# Liste für alle Partikel im Spiel
particles = []

# --- Partikel Hilfsfunktionen ---
def emit_particles(count, pos, base_color, vel_range=(-50, 50), life_range=(0.2, 0.6), radius_range=(1, 3), gravity=0):
    if len(particles) > MAX_PARTICLES - count:
        return
    for _ in range(count):
        vel = pygame.Vector2(random.uniform(vel_range[0], vel_range[1]),
                             random.uniform(vel_range[0], vel_range[1]))
        r_offset = random.randint(-30, 30); g_offset = random.randint(-30, 30); b_offset = random.randint(-30, 30)
        p_color = (max(0, min(255, base_color[0] + r_offset)),
                   max(0, min(255, base_color[1] + g_offset)),
                   max(0, min(255, base_color[2] + b_offset)))
        lifetime = random.uniform(life_range[0], life_range[1])
        particles.append(Particle(pos, vel, p_color, lifetime, radius_range, gravity))

def update_and_draw_particles(dt, surface):
    for i in range(len(particles) - 1, -1, -1):
        p = particles[i]
        p.update(dt)
        if p.lifetime <= 0:
            particles.pop(i)
        else:
            p.draw(surface)

# --- Klassen (Player, Ball) ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, start_color, control_key, start_angle):
        super().__init__()
        self.radius = PLAYER_RADIUS # Verwendet globale Konstante
        self.control_key = control_key
        self.original_image = None; self.image = None; self.rect = None
        self.set_avatar(start_color) # Farbe wird hier gesetzt
        self.pos = pygame.Vector2(x, y)
        if self.rect: self.rect.center = self.pos
        else: self.rect = pygame.Rect(0,0, self.radius*2, self.radius*2); self.rect.center = self.pos
        self.velocity = pygame.Vector2(0, 0); self.angle = start_angle
        self.is_sprinting = False
        self.rotation_speed = PLAYER_ROTATION_SPEED
        self.sprint_speed = PLAYER_SPRINT_SPEED
        self.sprint_particle_timer = 0

    def update_radius(self): # Nimmt keine neue Radius mehr entgegen, verwendet globale Konstante
        self.radius = PLAYER_RADIUS
        if hasattr(self, 'color'):
            self.set_avatar(self.color)

    def set_avatar(self, color):
        self.color = color
        self.original_image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.original_image, self.color, (self.radius, self.radius), self.radius)
        pygame.draw.line(self.original_image, (0,0,0), (self.radius, self.radius), (self.radius * 2, self.radius), 3)
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        if hasattr(self, 'pos') and self.pos: self.rect.center = self.pos

    def rotate(self, dt):
        if not self.original_image: return
        self.angle = (self.angle + self.rotation_speed * dt) % 360
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
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
                particle_pos = self.pos - direction * self.radius
                emit_particles(2, particle_pos, (220, 220, 220), vel_range=(-40, 40), life_range=(0.2, 0.5), radius_range=(2, 4))
                self.sprint_particle_timer = 0.02
        else:
            self.rotate(dt)
            self.velocity = pygame.Vector2(0, 0)

        field_top = TRIBUNE_HEIGHT; field_bottom = SCREEN_HEIGHT - TRIBUNE_HEIGHT
        field_left = 0; field_right = SCREEN_WIDTH
        if self.pos.x - self.radius < field_left: self.pos.x = field_left + self.radius
        if self.pos.x + self.radius > field_right: self.pos.x = field_right - self.radius
        if self.pos.y - self.radius < field_top: self.pos.y = field_top + self.radius
        if self.pos.y + self.radius > field_bottom: self.pos.y = field_bottom - self.radius
        self.rect.center = self.pos

    def reset(self, x, y, angle, start_color):
         self.set_avatar(start_color) # Avatar wird mit der übergebenen Farbe neu gesetzt
         field_center_y = TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2
         self.pos = pygame.Vector2(x, field_center_y)
         if self.rect: self.rect.center = self.pos
         self.angle = angle
         self.is_sprinting = False
         self.velocity = pygame.Vector2(0, 0)

class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.radius = BALL_RADIUS # Verwendet globale Konstante
        self.update_appearance()
        self.pos = pygame.Vector2(x, y)
        if self.rect: self.rect.center = self.pos
        self.velocity = pygame.Vector2(0, 0)
        self.friction_factor = BALL_FRICTION
        self.trail_positions = []

    def update_radius(self): # Nimmt keine neue Radius mehr entgegen, verwendet globale Konstante
        self.radius = BALL_RADIUS
        self.update_appearance()

    def update_appearance(self):
        self.original_image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.original_image, BALL_COLOR, (self.radius, self.radius), self.radius)
        self.image = self.original_image
        self.rect = self.image.get_rect()
        if hasattr(self, 'pos') and self.pos: self.rect.center = self.pos

    def apply_friction(self, dt):
        self.velocity *= (self.friction_factor ** dt)
        if self.velocity.length() < 0.5: self.velocity = pygame.Vector2(0, 0)

    def update(self, dt, *args, **kwargs):
        if self.velocity.length() > 0:
             self.trail_positions.append(self.pos.copy())
             if len(self.trail_positions) > BALL_TRAIL_LENGTH:
                 self.trail_positions.pop(0)
        elif self.trail_positions:
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
         self.rect.center = self.pos
         self.velocity = pygame.Vector2(0, 0)
         self.trail_positions.clear()

# --- Spiel Initialisierung ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Simple Soccer Game - Select Mode") # Geänderter Start-Titel
clock = pygame.time.Clock()
main_font = pygame.font.Font(None, 50)
menu_font = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 35)

# --- Zuschauer generieren ---
spectator_positions_colors = []
def generate_spectators():
    spectator_positions_colors.clear()
    top_tribune_rect = pygame.Rect(0, 0, SCREEN_WIDTH, TRIBUNE_HEIGHT)
    for _ in range(NUM_SPECTATORS // 2):
        pos = (random.randint(top_tribune_rect.left, top_tribune_rect.right),
               random.randint(top_tribune_rect.top, top_tribune_rect.bottom))
        color = random.choice(SPECTATOR_COLORS); spectator_positions_colors.append((pos, color))
    bottom_tribune_rect = pygame.Rect(0, SCREEN_HEIGHT - TRIBUNE_HEIGHT, SCREEN_WIDTH, TRIBUNE_HEIGHT)
    for _ in range(NUM_SPECTATORS // 2):
        pos = (random.randint(bottom_tribune_rect.left, bottom_tribune_rect.right),
               random.randint(bottom_tribune_rect.top, bottom_tribune_rect.bottom))
        color = random.choice(SPECTATOR_COLORS); spectator_positions_colors.append((pos, color))
generate_spectators()

# --- Spielobjekte erstellen ---
field_center_y = TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2
player1 = Player(SCREEN_WIDTH * 0.25, field_center_y, DEFAULT_P1_COLOR, pygame.K_a, 0)
player2 = Player(SCREEN_WIDTH * 0.75, field_center_y, DEFAULT_P2_COLOR, pygame.K_l, 180)
ball = Ball(SCREEN_WIDTH / 2, field_center_y)
all_sprites = pygame.sprite.Group(player1, player2, ball)
players = pygame.sprite.Group(player1, player2)

# --- Spielzustand Variablen ---
score1 = 0; score2 = 0
game_state = STATE_MENU # Startet direkt im Menü
start_time = 0; remaining_time = GAME_DURATION; last_goal_time = 0

# --- Avatar Auswahl Variablen (nicht mehr benötigt) ---
# selecting_player = 1; p1_avatar_index = -1; p2_avatar_index = -1; current_highlighted_index = 0

# --- Einstellungen Variablen (nicht mehr benötigt) ---
# settings_option = 0
# current_player_radius = DEFAULT_PLAYER_RADIUS
# current_ball_radius = DEFAULT_BALL_RADIUS

# --- Hilfsfunktionen ---
def draw_tribunes_and_spectators():
    pygame.draw.rect(screen, TRIBUNE_COLOR, (0, 0, SCREEN_WIDTH, TRIBUNE_HEIGHT))
    pygame.draw.rect(screen, TRIBUNE_COLOR, (0, SCREEN_HEIGHT - TRIBUNE_HEIGHT, SCREEN_WIDTH, TRIBUNE_HEIGHT))
    for pos, color in spectator_positions_colors: pygame.draw.circle(screen, color, pos, SPECTATOR_RADIUS)

def draw_field():
    field_rect = pygame.Rect(0, TRIBUNE_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT)
    pygame.draw.rect(screen, FIELD_COLOR, field_rect)
    field_top = TRIBUNE_HEIGHT; field_bottom = SCREEN_HEIGHT - TRIBUNE_HEIGHT; field_height = field_bottom - field_top
    field_center_x = SCREEN_WIDTH / 2; field_center_y = field_top + field_height / 2
    pygame.draw.line(screen, LINE_COLOR, (field_center_x, field_top), (field_center_x, field_bottom), 2)
    pygame.draw.circle(screen, LINE_COLOR, (field_center_x, field_center_y), 70, 2)
    goal_y_abs_start = field_top + (field_height / 2 - GOAL_HEIGHT / 2)
    goal_y_abs_end = field_top + (field_height / 2 + GOAL_HEIGHT / 2)
    pygame.draw.line(screen, LINE_COLOR, (GOAL_WIDTH, goal_y_abs_start), (GOAL_WIDTH, goal_y_abs_end), 5)
    pygame.draw.line(screen, LINE_COLOR, (SCREEN_WIDTH - GOAL_WIDTH, goal_y_abs_start), (SCREEN_WIDTH - GOAL_WIDTH, goal_y_abs_end), 5)

def draw_text(text, font, x, y, color=TEXT_COLOR):
    text_surface = font.render(text, True, color); text_rect = text_surface.get_rect(center=(x, y)); screen.blit(text_surface, text_rect)

# def draw_avatar_selection_screen(): # Entfernt
    # ...

def reset_positions():
    # Spieler- und Ballgrößen mit globalen Konstanten aktualisieren (stellt sicher, dass sie korrekt sind)
    player1.update_radius()
    player2.update_radius()
    ball.update_radius()
    
    # Standardfarben direkt verwenden
    p1_color = DEFAULT_P1_COLOR
    p2_color = DEFAULT_P2_COLOR
    
    player1_start_x = SCREEN_WIDTH * 0.25; player2_start_x = SCREEN_WIDTH * 0.75
    field_center_y = TRIBUNE_HEIGHT + (SCREEN_HEIGHT - 2 * TRIBUNE_HEIGHT) / 2
        
    player1.reset(player1_start_x, field_center_y, 0, p1_color)
    player2.reset(player2_start_x, field_center_y, 180, p2_color)
    ball.reset()
    particles.clear()

def start_new_game():
    global score1, score2, start_time, remaining_time, last_goal_time
    score1 = 0; score2 = 0; start_time = time.time(); remaining_time = GAME_DURATION; last_goal_time = 0
    reset_positions()
    if PLAYER2_IS_BOT:
        bot_logic.reset_bot_state()

# def reset_avatar_selection(): # Entfernt
    # ...

def draw_ball_trail(surface, trail, current_ball_radius): # Parameter current_ball_radius beibehalten für Klarheit
    num_points = len(trail)
    if num_points < 2: return
    for i in range(num_points):
        pos = trail[i]
        alpha = max(0, int(150 * (i / num_points)))
        radius = max(1, int(current_ball_radius * 0.8 * (i / num_points)))
        if radius >= 1:
            try:
                temp_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                draw_color = (*BALL_COLOR[:3], alpha)
                pygame.draw.circle(temp_surf, draw_color, (radius, radius), radius)
                surface.blit(temp_surf, pos - pygame.Vector2(radius, radius))
            except (ValueError, TypeError): pass

# def draw_settings_screen(): # Entfernt
    # ...

# def apply_settings(): # Entfernt, da feste Werte verwendet werden
    # ...

# --- Haupt Game Loop ---
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    keys = pygame.key.get_pressed()

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            if event.key == pygame.K_r: # "R" führt jetzt zum Hauptmenü
                game_state = STATE_MENU
                pygame.display.set_caption("Simple Soccer Game - Select Mode")

            # if game_state == STATE_SETTINGS: # Entfernt
                # ...
            # elif game_state == STATE_AVATAR_SELECT: # Entfernt
                # ...
            if game_state == STATE_MENU:
                if event.key == pygame.K_1: PLAYER2_IS_BOT = False; start_new_game(); game_state = STATE_PLAYING; pygame.display.set_caption("Soccer - PvP")
                elif event.key == pygame.K_2: PLAYER2_IS_BOT = True; start_new_game(); game_state = STATE_PLAYING; pygame.display.set_caption("Soccer - PvE")

            elif game_state == STATE_PLAYING:
                if event.key == player1.control_key: player1.start_sprint()
                if not PLAYER2_IS_BOT and event.key == player2.control_key: player2.start_sprint()

        if event.type == pygame.KEYUP:
            if game_state == STATE_PLAYING:
                if event.key == player1.control_key: player1.stop_sprint()
                if not PLAYER2_IS_BOT and event.key == player2.control_key: player2.stop_sprint()

    # --- Partikel Update ---
    update_and_draw_particles(dt, screen)

    # --- Spiel Logik & Updates ---
    if game_state == STATE_PLAYING:
        if PLAYER2_IS_BOT:
             target_goal_x = SCREEN_WIDTH - GOAL_WIDTH
             should_sprint = bot_logic.get_bot_decision(
                 player2, ball, target_goal_x,
                 SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS, BALL_RADIUS, # Globale Konstanten verwenden
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
                emit_particles(8, ball.pos, (255, 255, 100), vel_range=(-80, 80), life_range=(0.1, 0.4), radius_range=(1, 3))
            else:
                repel_speed = 50; ball.velocity += collision_normal * repel_speed
                player.pos -= collision_normal * repel_speed * 0.1 * dt

            overlap = (player.radius + ball.radius) - distance
            if overlap > 0.1:
                 correction_vec = collision_normal * overlap; ball.pos += correction_vec * 0.51
                 player.pos -= correction_vec * 0.5; ball.rect.center = ball.pos; player.rect.center = player.pos

        if pygame.sprite.collide_circle(player1, player2):
             dist_vec_p1_p2 = player2.pos - player1.pos; dist_p1_p2 = dist_vec_p1_p2.length()
             if dist_p1_p2 < (player1.radius + player2.radius):
                 if dist_p1_p2 == 0: correction_vec = pygame.Vector2(1, 0)
                 else: correction_vec = dist_vec_p1_p2.normalize()
                 overlap = (player1.radius + player2.radius) - dist_p1_p2
                 if overlap > 0:
                     player1.pos -= correction_vec * overlap / 2; player2.pos += correction_vec * overlap / 2
                     player1.rect.center = player1.pos; player2.rect.center = player2.pos

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
            for _ in range(50):
                pos_x = random.uniform(SCREEN_WIDTH * 0.2, SCREEN_WIDTH * 0.8)
                pos_y = random.uniform(TRIBUNE_HEIGHT, TRIBUNE_HEIGHT + 30)
                confetti_color = random.choice(SPECTATOR_COLORS + [goal_scorer_color] * 3)
                emit_particles(1, (pos_x, pos_y), confetti_color,
                               vel_range=(-40, 40), life_range=(1.0, 2.5),
                               radius_range=(3, 6), gravity=60)

        if start_time > 0:
            elapsed_time = time.time() - start_time
            remaining_time = max(0, GAME_DURATION - elapsed_time)
            if remaining_time == 0:
                game_state = STATE_GAME_OVER
                player1.stop_sprint(); player2.stop_sprint()

    elif game_state == STATE_GOAL_PAUSE:
        if time.time() - last_goal_time > RESET_DELAY:
            reset_positions(); game_state = STATE_PLAYING

    # --- Zeichnen ---
    screen.fill((0,0,0))

    # if game_state == STATE_SETTINGS: # Entfernt
        # draw_settings_screen()
    # elif game_state == STATE_AVATAR_SELECT: # Entfernt
        # draw_avatar_selection_screen()
    # else: # Bezieht sich jetzt auf MENU, PLAYING, GOAL_PAUSE, GAME_OVER

    draw_tribunes_and_spectators() # Immer zeichnen, außer vielleicht in einem Splash-Screen (den es nicht gibt)

    if game_state == STATE_MENU:
        draw_text("Wähle den Modus:", menu_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 100)
        draw_text("1 : Spieler vs Spieler", main_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        draw_text("(Uses default avatars)", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40) # Angepasster Text
        draw_text("2 : Spieler vs Bot", main_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100)
        draw_text("(P1 uses default avatar)", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 140) # Angepasster Text
        draw_text("ESC: Quit", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT - 50) # "R" Option entfernt

    elif game_state == STATE_PLAYING or game_state == STATE_GOAL_PAUSE or game_state == STATE_GAME_OVER:
        draw_field()
        draw_ball_trail(screen, ball.trail_positions, BALL_RADIUS) # Globale Konstante verwenden
        all_sprites.draw(screen)
        update_and_draw_particles(dt, screen) # Partikel werden bereits global gezeichnet, hier ggf. redundant, aber schadet nicht

        score_text = f"P1: {score1} - P2: {score2}"
        draw_text(score_text, main_font, SCREEN_WIDTH / 2, TRIBUNE_HEIGHT / 2, TEXT_COLOR)
        minutes = int(remaining_time // 60); seconds = int(remaining_time % 60)
        timer_text = f"{minutes:02}:{seconds:02}"
        draw_text(timer_text, main_font, SCREEN_WIDTH - 100, TRIBUNE_HEIGHT / 2, TEXT_COLOR)

        if game_state == STATE_GOAL_PAUSE:
             draw_text("GOAL!", menu_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, TEXT_COLOR)
        elif game_state == STATE_GAME_OVER:
             winner_text = ""
             if score1 > score2: winner_text = f"Player 1 wins!"
             elif score2 > score1: winner_text = f"Player 2 wins!"
             else: winner_text = "Draw!"
             draw_text("Game Over", menu_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 60, TEXT_COLOR)
             draw_text(winner_text, main_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 10, TEXT_COLOR)
             draw_text("Press R for Main Menu", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40, TEXT_COLOR) # Angepasster Text
             draw_text("Press ESC to Quit", small_font, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 70, TEXT_COLOR)

    ball_speed = ball.velocity.length()
    print(f"P1: ({int(player1.pos.x)}, {int(player1.pos.y)}) Angle: {int(player1.angle)} | P2: ({int(player2.pos.x)}, {int(player2.pos.y)}) Angle: {int(player2.angle)} || Ball: ({int(ball.pos.x)}, {int(ball.pos.y)}) Speed: {ball_speed:.1f}")

    pygame.display.flip()

# --- Spiel beenden ---
pygame.quit()
sys.exit()