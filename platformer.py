import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
WIDTH = 800
HEIGHT = 600
WORLD_WIDTH = 5600
HOLE_LEFT = 800
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 60
PLAYER_SPEED = 5
PLAYER_JUMP = -17
GRAVITY = 0.8
ENEMY_WIDTH = 30
ENEMY_HEIGHT = 30
ENEMY_SPEED = 3
PLATFORM_BREAK_DELAY = 1000  # ms
PICKUP_MESSAGE_DURATION = 2000  # ms
BUTTON_LARGE = (200, 60)
BUTTON_SMALL = (150, 50)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

#  Display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AMONG THE ASTEROIDS")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 74)
speech_font = pygame.font.Font(None, 30)
button_font = pygame.font.Font(None, 40)

# Classes
class Enemy:
    def __init__(self, x, y, width, height, speed):
        self.rect = pygame.Rect(x, y, width, height)
        self.base_speed = speed
        self.current_speed = speed
        self.origin_x = x
        self.is_chasing = False
        self.chase_start_time = 0
        self.speed_increase_timer = 0

    def update(self, player_x, player_width, platforms, camera_x):
        if camera_x <= self.rect.x <= camera_x + WIDTH:
            player_center = player_x + player_width / 2
            enemy_center = self.rect.x + self.rect.width / 2
            current_time = pygame.time.get_ticks()
            is_trying_to_move = False
            next_x = self.rect.x

            if player_center < enemy_center:
                next_x = self.rect.x - self.current_speed
                can_move = any(p.rect.y == HEIGHT - 40 and p.rect.left <= next_x <= p.rect.right for p in platforms)
                if can_move and next_x >= 0:
                    self.rect.x = next_x
                    is_trying_to_move = True
            elif player_center > enemy_center:
                next_x = self.rect.x + self.current_speed
                next_right = next_x + self.rect.width
                can_move = any(p.rect.y == HEIGHT - 40 and p.rect.left <= next_right <= p.rect.right for p in platforms)
                if can_move and next_right <= WORLD_WIDTH:
                    self.rect.x = next_x
                    is_trying_to_move = True

            if is_trying_to_move:
                if not self.is_chasing:
                    self.is_chasing = True
                    self.chase_start_time = current_time
                    self.speed_increase_timer = current_time
                if current_time - self.speed_increase_timer >= 2000:
                    self.current_speed += 1
                    self.speed_increase_timer = current_time
            else:
                if self.is_chasing:
                    self.is_chasing = False
                    self.current_speed = self.base_speed

        self.rect.x = max(0, min(self.rect.x, WORLD_WIDTH - self.rect.width))

class Platform:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

class Interactable:
    def __init__(self, x, y, width, height, name):
        self.rect = pygame.Rect(x, y, width, height)
        self.name = name

# Initial platforms
initial_platforms = [
    Platform(0, HEIGHT - 40, 800, 40),
    Platform(296, 400, 200, 20),
    Platform(850, 400, 200, 20),
    Platform(1200, HEIGHT - 40, 1200, 40),
    Platform(1400, 400, 200, 20),
    Platform(2000, 450, 200, 20),
    Platform(2300, 350, 200, 20),
    Platform(2600, 250, 200, 20),
    Platform(2900, 400, 200, 20),
    Platform(3200, 300, 200, 20),
    Platform(3500, HEIGHT - 40, 1800, 40),
    Platform(3600, 400, 200, 20),
    Platform(3900, 350, 200, 20),
    Platform(5400, 400, 200, 20)  # breaks after blaster pickup
]
BREAKABLE_PLATFORM_INDEX = len(initial_platforms) - 1  # Index of platform at x=5400, y=400

# Game state
platforms = initial_platforms.copy()
enemies = [
    Enemy(1600, HEIGHT - 40 - 30, ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_SPEED),
    Enemy(4000, HEIGHT - 40 - 30, ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_SPEED)
]
blaster = Interactable(5450, 400 - 20, 20, 20, "Blaster")
player_x = 100
player_y = HEIGHT - PLAYER_HEIGHT - 10
player_velocity_y = 0
is_jumping = False
camera_x = 0
is_game_over = False
is_game_won = False
is_title_screen = True
show_speech_bubble = False
pickup_message = None
pickup_message_timer = 0
is_blaster_acquired = False
is_platform_breaking = False
platform_break_timer = 0
running = True

# functions
def reset_game(full_reset=True):
    global player_x, player_y, player_velocity_y, is_jumping, camera_x, is_game_over, is_game_won
    global is_title_screen, show_speech_bubble, pickup_message, is_blaster_acquired
    global is_platform_breaking, platform_break_timer, blaster, platforms
    player_x = 100
    player_y = HEIGHT - PLAYER_HEIGHT - 10
    player_velocity_y = 0
    is_jumping = False
    camera_x = 0
    is_game_over = False
    is_game_won = False
    show_speech_bubble = False
    pickup_message = None
    for enemy in enemies:
        enemy.rect.x = enemy.origin_x
        enemy.rect.y = HEIGHT - 40 - 30
        enemy.current_speed = enemy.base_speed
        enemy.is_chasing = False
    if full_reset:
        is_blaster_acquired = False
        blaster = Interactable(5450, 400 - 20, 20, 20, "Blaster")
        platforms = initial_platforms.copy()
    is_platform_breaking = False
    platform_break_timer = 0

def render_button(text, rect, text_color=BLACK, bg_color=WHITE):
    pygame.draw.rect(screen, bg_color, rect)
    text_surface = button_font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    return rect

def render_title():
    screen.fill(BLACK)
    title_text = font.render("AMONG THE ASTEROIDS", True, WHITE)
    screen.blit(title_text, title_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))
    start_rect = render_button("Start", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 + 50, *BUTTON_LARGE))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 + 120, *BUTTON_LARGE))
    return start_rect, quit_rect

def render_game_over():
    screen.fill(BLACK)
    lose_text = font.render("YOU DIED!", True, WHITE)
    screen.blit(lose_text, lose_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))
    restart_rect = render_button("Restart", pygame.Rect(WIDTH / 2 - 200, HEIGHT / 2 + 50, *BUTTON_SMALL))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 + 50, HEIGHT / 2 + 50, *BUTTON_SMALL))
    return restart_rect, quit_rect

def render_win():
    screen.fill(BLACK)
    win_text = font.render("YOU WIN!", True, WHITE)
    screen.blit(win_text, win_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))
    restart_rect = render_button("Restart", pygame.Rect(WIDTH / 2 - 200, HEIGHT / 2 + 50, *BUTTON_SMALL))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 + 50, HEIGHT / 2 + 50, *BUTTON_SMALL))
    return restart_rect, quit_rect

def render_game():
    global pickup_message, pickup_message_timer 
    screen.fill(BLACK)
    pygame.draw.rect(screen, WHITE, (player_x - camera_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT))
    for enemy in enemies:
        pygame.draw.rect(screen, RED, (enemy.rect.x - camera_x, enemy.rect.y, enemy.rect.width, enemy.rect.height))
    if blaster and not is_blaster_acquired:
        pygame.draw.rect(screen, BLUE, (blaster.rect.x - camera_x, blaster.rect.y, blaster.rect.width, blaster.rect.height))
    for platform in platforms:
        pygame.draw.rect(screen, GRAY, (platform.rect.x - camera_x, platform.rect.y, platform.rect.width, platform.rect.height))
    if show_speech_bubble and blaster:
        text = speech_font.render("Pick up the blaster?", True, WHITE)
        screen.blit(text, text.get_rect(topleft=(blaster.rect.x - camera_x - 50, blaster.rect.y - 50)))
    if pickup_message:
        current_time = pygame.time.get_ticks()
        if current_time - pickup_message_timer > PICKUP_MESSAGE_DURATION:
            pickup_message = None
        else:
            message_text = speech_font.render(pickup_message, True, WHITE)
            screen.blit(message_text, message_text.get_rect(center=(WIDTH / 2, HEIGHT / 2)))

# Game loop
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if is_title_screen:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    reset_game(full_reset=True)
                    is_title_screen = False
                elif event.key == pygame.K_q:
                    running = False
            elif is_game_over:
                if event.key == pygame.K_r:
                    reset_game(full_reset=False) 
                elif event.key == pygame.K_q:
                    reset_game(full_reset=True)
                    is_title_screen = True
            elif is_game_won:
                if event.key == pygame.K_r:
                    reset_game(full_reset=True) 
                elif event.key == pygame.K_q:
                    reset_game(full_reset=True)
                    is_title_screen = True
            elif event.key == pygame.K_e:
                player_rect = pygame.Rect(player_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT)
                if blaster and player_rect.colliderect(blaster.rect) and not is_blaster_acquired:
                    show_speech_bubble = not show_speech_bubble
                    if not show_speech_bubble:
                        pickup_message = "Blaster Acquired!"
                        pickup_message_timer = pygame.time.get_ticks()
                        is_blaster_acquired = True
                        is_platform_breaking = True
                        platform_break_timer = pygame.time.get_ticks()
                        blaster = None
            elif event.key == pygame.K_SPACE and not is_jumping:
                player_velocity_y = PLAYER_JUMP
                is_jumping = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            if is_title_screen:
                start_rect, quit_rect = render_title()
                if start_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                    is_title_screen = False
                elif quit_rect.collidepoint(mouse_pos):
                    running = False
            elif is_game_over:
                restart_rect, quit_rect = render_game_over()
                if restart_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=False)
                elif quit_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                    is_title_screen = True
            elif is_game_won:
                restart_rect, quit_rect = render_win()
                if restart_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                elif quit_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                    is_title_screen = True

    if not (is_game_over or is_game_won or is_title_screen):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] and player_x > 0:
            player_x -= PLAYER_SPEED
        if keys[pygame.K_d] and player_x < WORLD_WIDTH - PLAYER_WIDTH:
            player_x += PLAYER_SPEED

        player_velocity_y += GRAVITY
        player_y += player_velocity_y

        camera_x = max(0, min(player_x - WIDTH / 2 + PLAYER_WIDTH / 2, WORLD_WIDTH - WIDTH))

        player_rect = pygame.Rect(player_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT)
        for enemy in enemies:
            enemy.update(player_x, PLAYER_WIDTH, platforms, camera_x)
            if player_rect.colliderect(enemy.rect):
                is_game_over = True

        if player_y > HEIGHT and player_x >= HOLE_LEFT:
            if is_blaster_acquired:
                is_game_won = True
            else:
                is_game_over = True

        for platform in platforms:
            if player_rect.colliderect(platform.rect):
                if player_velocity_y > 0:
                    player_y = platform.rect.top - PLAYER_HEIGHT
                    player_velocity_y = 0
                    is_jumping = False
                elif player_velocity_y < 0:
                    player_y = platform.rect.bottom
                    player_velocity_y = 0

        if player_y > HEIGHT - PLAYER_HEIGHT - 40 and player_x < HOLE_LEFT:
            player_y = HEIGHT - PLAYER_HEIGHT - 40
            player_velocity_y = 0
            is_jumping = False

        if is_platform_breaking and pygame.time.get_ticks() - platform_break_timer >= PLATFORM_BREAK_DELAY:
            if BREAKABLE_PLATFORM_INDEX < len(platforms):
                platforms.pop(BREAKABLE_PLATFORM_INDEX)
            is_platform_breaking = False

    # Render
    if is_title_screen:
        render_title()
    elif is_game_over:
        render_game_over()
    elif is_game_won:
        render_win()
    else:
        render_game()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()