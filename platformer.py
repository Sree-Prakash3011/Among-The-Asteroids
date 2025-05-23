import pygame  # type: ignore
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
ALIEN_HINT_DURATION = 1000  # 1 second
BUTTON_LARGE = (200, 60)
BUTTON_SMALL = (150, 50)
FADE_IN_DURATION = 1000  # 1 second for fade-in
FADE_OUT_DURATION = 500  # 0.5 seconds for fade-out on skip

# Colors(Placeholder)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AMONG THE ASTEROIDS")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 74)
speech_font = pygame.font.Font(None, 30)
button_font = pygame.font.Font(None, 40)
message_font = pygame.font.Font(None, 36)  

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
is_message_screen = False
is_message_fade_out = False
is_second_message = False
is_second_message_fade_out = False
is_third_message = False
is_third_message_fade_out = False
is_fourth_message = False  # New state for fourth message
is_fourth_message_fade_out = False  # New state for fourth message fade-out
message_timer = 0
show_speech_bubble = False
pickup_message = None
pickup_message_timer = 0
is_blaster_acquired = False
is_platform_breaking = False
platform_break_timer = 0
show_movement_hint = False
show_jump_hint = False
show_gap_hint = False
show_alien_hint = False
show_interact_hint = False
jump_hint_shown = False
gap_hint_shown = False
alien_hint_shown = False
interact_hint_shown = False
alien_hint_timer = 0
running = True

# Mission control messages
FIRST_MESSAGE = (
    "Mission Control…Do you read me, Mission Control? We had lost control of the ship and crashed into the asteroid belt. "
    "The ship was broken apart and I was ejected. I am currently by myself and lost contact with my crew. "
    "Mission Control, do you read me?"
)
SECOND_MESSAGE = (
    "Dang it, I’m not getting any response. The Communication Sytem must have been busted when we crash."
)
THIRD_MESSAGE = (
    "My oxygen is at 95%. That’s good for now, but I can’t stand idly forever."
)
FOURTH_MESSAGE = (
    "I need to move, find my crewmates and hopefully, get back home."
)

# Functions
def reset_game(full_reset=True):
    global player_x, player_y, player_velocity_y, is_jumping, camera_x, is_game_over, is_game_won
    global is_title_screen, is_message_screen, is_message_fade_out, is_second_message, is_second_message_fade_out
    global is_third_message, is_third_message_fade_out, is_fourth_message, is_fourth_message_fade_out
    global show_speech_bubble, pickup_message, is_blaster_acquired
    global is_platform_breaking, platform_break_timer, blaster, platforms
    global show_movement_hint, show_jump_hint, show_gap_hint, show_alien_hint, show_interact_hint
    global jump_hint_shown, gap_hint_shown, alien_hint_shown, interact_hint_shown, alien_hint_timer
    player_x = 100
    player_y = HEIGHT - PLAYER_HEIGHT - 10
    player_velocity_y = 0
    is_jumping = False
    camera_x = 0
    is_game_over = False
    is_game_won = False
    is_title_screen = False
    is_message_screen = False
    is_message_fade_out = False
    is_second_message = False
    is_second_message_fade_out = False
    is_third_message = False
    is_third_message_fade_out = False
    is_fourth_message = False
    is_fourth_message_fade_out = False
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
        jump_hint_shown = False
        gap_hint_shown = False
        alien_hint_shown = False
        interact_hint_shown = False
    is_platform_breaking = False
    platform_break_timer = 0
    show_movement_hint = True
    show_jump_hint = False
    show_gap_hint = False
    show_alien_hint = False
    show_interact_hint = False
    alien_hint_timer = 0

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

def render_message():
    screen.fill(BLACK)
    # Create a surface for the text
    text_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    # Select message based on state
    if is_fourth_message or is_fourth_message_fade_out:
        message = FOURTH_MESSAGE
    elif is_third_message or is_third_message_fade_out:
        message = THIRD_MESSAGE
    elif is_second_message or is_second_message_fade_out:
        message = SECOND_MESSAGE
    else:
        message = FIRST_MESSAGE
    # Split the message into lines
    words = message.split(' ')
    lines = []
    current_line = ""
    max_width = WIDTH - 40
    for word in words:
        test_line = current_line + word + " "
        test_surface = message_font.render(test_line, True, WHITE)
        if test_surface.get_width() < max_width:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())

    # Render lines onto the text surface
    y_offset = HEIGHT / 2 - len(lines) * 20
    for line in lines:
        line_surface = message_font.render(line, True, WHITE)
        line_rect = line_surface.get_rect(center=(WIDTH / 2, y_offset))
        text_surface.blit(line_surface, line_rect)
        y_offset += 40

    # Calculate alpha based on state
    current_time = pygame.time.get_ticks()
    elapsed = current_time - message_timer
    if is_message_fade_out or is_second_message_fade_out or is_third_message_fade_out or is_fourth_message_fade_out:
        # Fade out: 255 to 0
        alpha = int(255 * (1 - elapsed / FADE_OUT_DURATION))
    else:
        # Fade in or full opacity
        alpha = int(255 * min(elapsed / FADE_IN_DURATION, 1.0))
    alpha = max(0, min(255, alpha))  # Clamp alpha

    # Set surface alpha and blit to screen
    text_surface.set_alpha(alpha)
    screen.blit(text_surface, (0, 0))

def render_game():
    global pickup_message, pickup_message_timer, show_movement_hint, show_jump_hint, show_gap_hint, show_alien_hint, show_interact_hint
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
    if show_movement_hint:
        hint_text = speech_font.render("Press A and D to move", True, WHITE)
        hint_rect = hint_text.get_rect(center=(player_x - camera_x + PLAYER_WIDTH / 2, player_y - 50))
        screen.blit(hint_text, hint_rect)
    if show_jump_hint:
        jump_text = speech_font.render("Press SPACE to jump", True, WHITE)
        jump_rect = jump_text.get_rect(center=(400 - camera_x, 510))
        screen.blit(jump_text, jump_rect)
    if show_gap_hint:
        gap_text = speech_font.render("Avoid the gaps by jumping", True, WHITE)
        gap_rect = gap_text.get_rect(center=(950 - camera_x, 370))
        screen.blit(gap_text, gap_rect)
    if show_alien_hint:
        alien_text = speech_font.render("Avoid the alien from getting close", True, WHITE)
        alien_rect = alien_text.get_rect(center=(1500 - camera_x, 370))
        screen.blit(alien_text, alien_rect)
    if show_interact_hint:
        interact_text = speech_font.render("Press E to interact", True, WHITE)
        interact_rect = interact_text.get_rect(center=(5500 - camera_x, 370))
        screen.blit(interact_text, interact_rect)

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
                    is_message_screen = True
                    message_timer = pygame.time.get_ticks()
                elif event.key == pygame.K_q:
                    running = False
            elif is_message_screen and not is_message_fade_out:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    is_message_fade_out = True
                    message_timer = pygame.time.get_ticks()
            elif is_second_message and not is_second_message_fade_out:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    is_second_message_fade_out = True
                    message_timer = pygame.time.get_ticks()
            elif is_third_message and not is_third_message_fade_out:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    is_third_message_fade_out = True
                    message_timer = pygame.time.get_ticks()
            elif is_fourth_message and not is_fourth_message_fade_out:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    is_fourth_message_fade_out = True
                    message_timer = pygame.time.get_ticks()
            elif is_game_over:
                if event.key == pygame.K_r:
                    reset_game(full_reset=True)
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
                        if show_interact_hint and platforms[BREAKABLE_PLATFORM_INDEX].rect.collidepoint(player_x + PLAYER_WIDTH / 2, player_y + PLAYER_HEIGHT):
                            show_interact_hint = False
                            interact_hint_shown = True
            elif event.key == pygame.K_SPACE and not is_jumping:
                player_velocity_y = PLAYER_JUMP
                is_jumping = True
                show_jump_hint = False
                jump_hint_shown = True
                if not gap_hint_shown:
                    show_gap_hint = True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            if is_title_screen:
                start_rect, quit_rect = render_title()
                if start_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                    is_title_screen = False
                    is_message_screen = True
                    message_timer = pygame.time.get_ticks()
                elif quit_rect.collidepoint(mouse_pos):
                    running = False
            elif is_game_over:
                restart_rect, quit_rect = render_game_over()
                if restart_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
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

    if not (is_game_over or is_game_won or is_title_screen or is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] and player_x > 0:
            player_x -= PLAYER_SPEED
            show_movement_hint = False
            if not jump_hint_shown:
                show_jump_hint = True
        if keys[pygame.K_d] and player_x < WORLD_WIDTH - PLAYER_WIDTH:
            player_x += PLAYER_SPEED
            show_movement_hint = False
            if not jump_hint_shown:
                show_jump_hint = True

        # Apply gravity
        player_velocity_y += GRAVITY

        # Store the intended next position
        next_player_y = player_y + player_velocity_y
        next_player_rect = pygame.Rect(player_x, next_player_y, PLAYER_WIDTH, PLAYER_HEIGHT)

        # Check platform collisions
        on_platform = False
        for i, platform in enumerate(platforms):
            if next_player_rect.colliderect(platform.rect):
                if player_velocity_y > 0:  # Falling
                    next_player_y = platform.rect.top - PLAYER_HEIGHT
                    player_velocity_y = 0
                    is_jumping = False
                    on_platform = True
                    if i == 2 and show_gap_hint:
                        show_gap_hint = False
                        gap_hint_shown = True
                        if not alien_hint_shown:
                            show_alien_hint = True
                    elif i == 4 and show_alien_hint and not alien_hint_shown:
                        alien_hint_timer = pygame.time.get_ticks()
                        alien_hint_shown = True
                elif player_velocity_y < 0:  # Jumping upward
                    next_player_y = platform.rect.bottom
                    player_velocity_y = 0

        # Update player position
        player_y = next_player_y

        # Handle ground collision if not on a platform
        if not on_platform and player_y > HEIGHT - PLAYER_HEIGHT - 40 and player_x < HOLE_LEFT:
            player_y = HEIGHT - PLAYER_HEIGHT - 40
            player_velocity_y = 0
            is_jumping = False

        # Update camera
        camera_x = max(0, min(player_x - WIDTH / 2 + PLAYER_WIDTH / 2, WORLD_WIDTH - WIDTH))

        # Check enemy collisions
        player_rect = pygame.Rect(player_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT)
        for enemy in enemies:
            enemy.update(player_x, PLAYER_WIDTH, platforms, camera_x)
            if player_rect.colliderect(enemy.rect):
                is_game_over = True

        # Chheck win/lose conditions
        if player_y > HEIGHT and player_x >= HOLE_LEFT:
            if is_blaster_acquired:
                is_game_won = True
            else:
                is_game_over = True

        # alien hint timer
        if show_alien_hint and alien_hint_timer > 0:
            current_time = pygame.time.get_ticks()
            if current_time - alien_hint_timer >= ALIEN_HINT_DURATION:
                show_alien_hint = False
                if not interact_hint_shown:
                    show_interact_hint = True

        # platform break
        if is_platform_breaking and pygame.time.get_ticks() - platform_break_timer >= PLATFORM_BREAK_DELAY:
            if BREAKABLE_PLATFORM_INDEX < len(platforms):
                platforms.pop(BREAKABLE_PLATFORM_INDEX)
            is_platform_breaking = False

    # message fade-out
    if is_message_fade_out:
        current_time = pygame.time.get_ticks()
        if current_time - message_timer >= FADE_OUT_DURATION:
            is_message_screen = False
            is_message_fade_out = False
            is_second_message = True
            message_timer = pygame.time.get_ticks()
    elif is_second_message_fade_out:
        current_time = pygame.time.get_ticks()
        if current_time - message_timer >= FADE_OUT_DURATION:
            is_second_message = False
            is_second_message_fade_out = False
            is_third_message = True
            message_timer = pygame.time.get_ticks()
    elif is_third_message_fade_out:
        current_time = pygame.time.get_ticks()
        if current_time - message_timer >= FADE_OUT_DURATION:
            is_third_message = False
            is_third_message_fade_out = False
            is_fourth_message = True
            message_timer = pygame.time.get_ticks()
    elif is_fourth_message_fade_out:
        current_time = pygame.time.get_ticks()
        if current_time - message_timer >= FADE_OUT_DURATION:
            is_fourth_message = False
            is_fourth_message_fade_out = False

    # Render
    if is_title_screen:
        render_title()
    elif is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out:
        render_message()
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
