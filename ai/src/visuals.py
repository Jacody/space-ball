import pygame
import math
import random

# --- Visuelle Konstanten ---
FIELD_COLOR = (0, 0, 0)  # Schwarz statt Grün
LINE_COLOR = (255, 255, 255)
TEXT_COLOR = (255, 255, 255)
BALL_COLOR = (255, 255, 255)
TRIBUNE_COLOR = (60, 60, 60)

# --- Effekt Konstanten ---
MAX_PARTICLES = 300
BALL_TRAIL_LENGTH = 15
BALL_TRAIL_MIN_SPEED = 10

# --- Spectator Konstanten ---
SPECTATOR_RADIUS = 3
SPECTATOR_COLORS = [
    (200, 0, 0), (0, 0, 200), (200, 200, 0), (0, 200, 0),
    (200, 100, 0), (150, 0, 150), (100, 100, 100), (255, 150, 150),
    (150, 150, 255), (255, 255, 150)
]

# --- Partikel Klasse ---
class Particle:
    def __init__(self, pos, vel, color, lifetime, radius_range=(1, 3), gravity=0):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.color = color
        self.lifetime = lifetime
        self.start_lifetime = lifetime
        self.radius = random.uniform(radius_range[0], radius_range[1])
        self.gravity = gravity

    def update(self, dt):
        self.vel.y += self.gravity * dt
        self.pos += self.vel * dt
        self.lifetime -= dt
        if self.start_lifetime > 0:
            self.radius = max(0, self.radius * (self.lifetime / self.start_lifetime))

    def draw(self, surface):
        if self.lifetime > 0 and self.radius >= 1:
            alpha = max(0, min(255, int(255 * (self.lifetime / self.start_lifetime))))
            try:
                temp_surf = pygame.Surface((int(self.radius*2), int(self.radius*2)), pygame.SRCALPHA)
                draw_color = (*self.color[:3], alpha)
                pygame.draw.circle(temp_surf, draw_color, (int(self.radius), int(self.radius)), int(self.radius))
                surface.blit(temp_surf, self.pos - pygame.Vector2(self.radius, self.radius))
            except (ValueError, TypeError):
                 pygame.draw.circle(surface, self.color, self.pos, int(self.radius))

# Globale Partikel-Liste
particles = []

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

def clear_particles():
    particles.clear()

# --- Spectator Verwaltung ---
spectator_positions_colors = []

def generate_spectators(screen_width, screen_height, tribune_height, num_spectators):
    spectator_positions_colors.clear()
    top_tribune_rect = pygame.Rect(0, 0, screen_width, tribune_height)
    for _ in range(num_spectators // 2):
        pos = (random.randint(top_tribune_rect.left, top_tribune_rect.right),
               random.randint(top_tribune_rect.top, top_tribune_rect.bottom))
        color = random.choice(SPECTATOR_COLORS)
        spectator_positions_colors.append((pos, color))
    bottom_tribune_rect = pygame.Rect(0, screen_height - tribune_height, screen_width, tribune_height)
    for _ in range(num_spectators // 2):
        pos = (random.randint(bottom_tribune_rect.left, bottom_tribune_rect.right),
               random.randint(bottom_tribune_rect.top, bottom_tribune_rect.bottom))
        color = random.choice(SPECTATOR_COLORS)
        spectator_positions_colors.append((pos, color))

# --- Drawing-Funktionen ---
def draw_tribunes_and_spectators(surface, screen_width, screen_height, tribune_height):
    pygame.draw.rect(surface, TRIBUNE_COLOR, (0, 0, screen_width, tribune_height))
    pygame.draw.rect(surface, TRIBUNE_COLOR, (0, screen_height - tribune_height, screen_width, tribune_height))
    for pos, color in spectator_positions_colors:
        pygame.draw.circle(surface, color, pos, SPECTATOR_RADIUS)

def draw_field(surface, screen_width, screen_height, tribune_height, goal_width, goal_height):
    field_rect = pygame.Rect(0, tribune_height, screen_width, screen_height - 2 * tribune_height)
    pygame.draw.rect(surface, FIELD_COLOR, field_rect)
    field_top = tribune_height
    field_bottom = screen_height - tribune_height
    field_height = field_bottom - field_top
    field_center_x = screen_width / 2
    field_center_y = field_top + field_height / 2
    pygame.draw.line(surface, LINE_COLOR, (field_center_x, field_top), (field_center_x, field_bottom), 2)
    pygame.draw.circle(surface, LINE_COLOR, (field_center_x, field_center_y), 70, 2)
    goal_y_abs_start = field_top + (field_height / 2 - goal_height / 2)
    goal_y_abs_end = field_top + (field_height / 2 + goal_height / 2)
    pygame.draw.line(surface, LINE_COLOR, (goal_width, goal_y_abs_start), (goal_width, goal_y_abs_end), 5)
    pygame.draw.line(surface, LINE_COLOR, (screen_width - goal_width, goal_y_abs_start), (screen_width - goal_width, goal_y_abs_end), 5)

def draw_text(surface, text, font, x, y, color=TEXT_COLOR):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    surface.blit(text_surface, text_rect)

def draw_ball_trail(surface, trail, current_ball_radius):
    num_points = len(trail)
    if num_points < 2:
        return
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
            except (ValueError, TypeError):
                pass

# --- Player Avatar Creation ---
def create_player_avatar(color, radius):
    """Erstellt das visuelle Avatar-Bild für einen Spieler"""
    surface_size = radius * 3.5 
    avatar_image = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
    
    center_x, center_y = surface_size / 2, surface_size / 2
    wing_color = tuple(max(0, c - 40) for c in color[:3])

    # --- Parameter für Flügelform ---
    wing_base_width = radius * 3 
    wing_length = radius * 1.3    
    wing_tip_spread = radius * 1.0 

    # --- Flügel zeichnen ---
    p1_top = (center_x - radius * 0.4, center_y - wing_base_width / 2)
    p2_top = (center_x - radius * 0.3 - wing_length, center_y - wing_tip_spread)
    p3_top = (center_x + radius * 0.1, center_y - wing_base_width * 0.4)
    pygame.draw.polygon(avatar_image, wing_color, [p1_top, p2_top, p3_top])

    p1_bottom = (center_x - radius * 0.4, center_y + wing_base_width / 2)
    p2_bottom = (center_x - radius * 0.3 - wing_length, center_y + wing_tip_spread)
    p3_bottom = (center_x + radius * 0.1, center_y + wing_base_width * 0.4)
    pygame.draw.polygon(avatar_image, wing_color, [p1_bottom, p2_bottom, p3_bottom])

    # Körper zeichnen
    pygame.draw.circle(avatar_image, color, (center_x, center_y), radius)
    
    # --- V-förmige Nase zeichnen (Pfeilspitze nach außen) ---
    nose_color = (0, 0, 0) 
    nose_thickness = 2     
    
    # Die Spitze des V (Pfeilspitze) ragt etwas über den Kreis hinaus
    v_tip_extension = radius * 0.7 # Wie weit die Spitze des V vor dem Zentrum ist
    
    # Länge der "Arme" des V, die von der Spitze nach hinten gehen
    v_arm_length = radius * 0.8 
    # Spreizung der Arme am hinteren Ende (halber Abstand)
    v_arm_spread_at_base = radius * 0.5

    # Punkt der V-Spitze (auf der unrotierten Surface rechts vom Zentrum)
    v_tip_point = (center_x + v_tip_extension, center_y)

    # Endpunkt des oberen Arms des V (von der Spitze nach hinten-oben)
    base_x_offset = radius * 0.2 # Wie weit die Basis der Arme vom Zentrum nach vorne versetzt ist

    end_point_top_arm = (center_x + base_x_offset, center_y - v_arm_spread_at_base)
    end_point_bottom_arm = (center_x + base_x_offset, center_y + v_arm_spread_at_base)

    pygame.draw.line(avatar_image, nose_color, v_tip_point, end_point_top_arm, nose_thickness)
    pygame.draw.line(avatar_image, nose_color, v_tip_point, end_point_bottom_arm, nose_thickness)
    
    return avatar_image

def create_ball_image(radius):
    """Erstellt das visuelle Bild für den Ball"""
    ball_image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(ball_image, BALL_COLOR, (radius, radius), radius)
    return ball_image 