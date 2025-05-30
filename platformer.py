import pygame  # type: ignore
import sys
import os

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
PLATFORM_BREAK_DELAY = 1000  
PICKUP_MESSAGE_DURATION = 2000  
ALIEN_HINT_DURATION = 1000 
BUTTON_LARGE = (200, 60)
BUTTON_SMALL = (150, 50)
FADE_IN_DURATION = 1000 
FADE_OUT_DURATION = 500  
PAUSE_BUTTON_SIZE = (40, 40)
PAUSE_BUTTON_POS = (WIDTH - PAUSE_BUTTON_SIZE[0] - 10, 10)  
PAUSE_OVERLAY_COLOR = (0, 0, 0, 128) 
MENU_BUTTON_SIZE = (150, 50)
MENU_BUTTON_SPACING = 20

# Colors (Placeholder)
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

# Fixed Platform class to accept parameters
class Platform:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

class Interactable:
    def __init__(self, x, y, width, height, name):
        self.rect = pygame.Rect(x, y, width, height)
        self.name = name

class CheckpointManager:
    def __init__(self):
        self.checkpoints = [
            {"x": 2990, "y": 370, "width": 20, "height": 30, "reached": False, "id": 1}
        ]
        self.current_checkpoint_id = None
        self.save_file = "save_data.txt"

    def create_checkpoint(self, x, y, width, height, id):
        """Create a new checkpoint."""
        new_checkpoint = {"x": x, "y": y, "width": width, "height": height, "reached": False, "id": id}
        self.checkpoints.append(new_checkpoint)
        return new_checkpoint

    def read_checkpoint(self, id):
        """Read a checkpoint's state."""
        for checkpoint in self.checkpoints:
            if checkpoint["id"] == id:
                return checkpoint
        return None

    def update_checkpoint(self, id, reached=True):
        """Update a checkpoint's reached status."""
        for checkpoint in self.checkpoints:
            if checkpoint["id"] == id:
                checkpoint["reached"] = reached
                if reached:
                    self.current_checkpoint_id = id
                return True
        return False

    def delete_checkpoint(self, id):
        """Delete a checkpoint (mark as unreachable for now)."""
        for checkpoint in self.checkpoints:
            if checkpoint["id"] == id:
                checkpoint["reached"] = False
                if self.current_checkpoint_id == id:
                    self.current_checkpoint_id = None
                return True
        return False

    def save_game(self):
        """Save current checkpoint state to file."""
        data = {
            "current_checkpoint_id": str(self.current_checkpoint_id),
            "checkpoints": str(self.checkpoints)
        }
        with open(self.save_file, "w") as file:
            for key, value in data.items():
                file.write(f"{key}={value}\n")

    def load_game(self):
        """Load checkpoint state from file."""
        try:
            with open(self.save_file, "r") as file:
                data = {}
                for line in file:
                    key, value = line.strip().split("=", 1)
                    if key == "checkpoints":
                        value = eval(value)
                    elif key == "current_checkpoint_id":
                        value = int(value) if value.isdigit() else None
                    data[key] = value
            self.current_checkpoint_id = data.get("current_checkpoint_id")
            self.checkpoints = data.get("checkpoints", self.checkpoints)
            return True
        except FileNotFoundError:
            self.current_checkpoint_id = None
            self.checkpoints = [{"x": 2990, "y": 370, "width": 20, "height": 30, "reached": False, "id": 1}]
            return False

# Platforms
initial_platforms = [
    Platform(0, HEIGHT - 40, 800, 40),        # Index 0: Ground platform from x=0 to 800.
    Platform(1200, HEIGHT - 40, 1200, 40),    # Index 1: Ground platform from x=1200 to 2400.
    Platform(3500, HEIGHT - 40, 1800, 40),    # Index 2: Ground platform from x=3500 to 5300.
    Platform(296, 400, 200, 20),              # Index 3: Floating platform at y=400, x=296-496.
    Platform(850, 400, 200, 20),              # Index 4: Floating platform at y=400, x=850-1050.
    Platform(1400, 400, 200, 20),             # Index 5: Floating platform at y=400, x=1400-1600.
    Platform(2000, 450, 200, 20),             # Index 6: Floating platform at y=450, x=2000-2200.
    Platform(2300, 350, 200, 20),             # Index 7: Floating platform at y=350, x=2300-2500.
    Platform(2600, 250, 200, 20),             # Index 8: Floating platform at y=250, x=2600-2800.
    Platform(2900, 400, 200, 20),             # Index 9: Floating platform at y=400, x=2900-3100 (near checkpoint).
    Platform(3200, 300, 200, 20),             # Index 10: Floating platform at y=300, x=3200-3400.
    Platform(3600, 400, 200, 20),             # Index 11: Floating platform at y=400, x=3600-3800.
    Platform(3900, 350, 200, 20),             # Index 12: Floating platform at y=350, x=3900-4100.
    Platform(5400, 400, 200, 20)              # Index 13: Floating platform at y=400, x=5400-5600 (breakable).
]
BREAKABLE_PLATFORM_INDEX = len(initial_platforms) - 1

# Game state
platforms = initial_platforms.copy()
enemies = [
    Enemy(1600, HEIGHT - 40 - 30, ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_SPEED),
    Enemy(4000, HEIGHT - 40 - 30, ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_SPEED)
]
blaster = Interactable(5450, 400 - 20, 20, 20, "Blaster")
checkpoint_manager = CheckpointManager()
player_x = 100
player_y = HEIGHT - PLAYER_HEIGHT - 10
player_velocity_y = 0
is_jumping = False
camera_x = 0
is_game_over = False
is_game_won = False
is_title_screen = True
is_game_select_screen = False
is_message_screen = False
is_message_fade_out = False
is_second_message = False
is_second_message_fade_out = False
is_third_message = False
is_third_message_fade_out = False
is_fourth_message = False
is_fourth_message_fade_out = False
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
is_paused = False
is_confirm_save = False
is_confirm_save_game_over = False
running = True

# Mission control messages
FIRST_MESSAGE = (
    "Mission Control…Do you read me, Mission Control? We have lost control of Elixir II and crashed into the asteroid belt. "
    "The ship was broken apart and I was ejected. I am on an asteroid, currently by myself and lost contact with my crew... "
    "Mission Control, do you hear me?"
)
SECOND_MESSAGE = (
    "Dang it, I’m not getting any response. I must have lost communication when we crash."
)
THIRD_MESSAGE = (
    "My oxygen is at 95%. That’s good for now, but I can’t stay here forever."
)
FOURTH_MESSAGE = (
    "I need to move, find my crewmates and then we can all, hopefully, get back home."
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
    global is_paused, is_confirm_save, is_confirm_save_game_over, is_game_select_screen
    if checkpoint_manager.current_checkpoint_id and not full_reset:
        checkpoint = checkpoint_manager.read_checkpoint(checkpoint_manager.current_checkpoint_id)
        if checkpoint:
            player_x = checkpoint["x"]
            player_y = checkpoint["y"] - PLAYER_HEIGHT
    else:
        player_x = 100
        player_y = HEIGHT - PLAYER_HEIGHT - 10
        checkpoint_manager.current_checkpoint_id = None
        for checkpoint in checkpoint_manager.checkpoints:
            checkpoint_manager.update_checkpoint(checkpoint["id"], False)
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
    is_paused = False
    is_confirm_save = False
    is_confirm_save_game_over = False
    is_game_select_screen = False

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

def render_game_select():
    screen.fill(BLACK)
    save_exists = os.path.exists("save_data.txt")
    new_game_rect = render_button("New Game", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 - 70, *BUTTON_LARGE))
    if save_exists:
        resume_game_rect = render_button("Resume Game", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 + 10, *BUTTON_LARGE))
    else:
        resume_game_rect = render_button("Resume Game", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 + 10, *BUTTON_LARGE), text_color=WHITE, bg_color=GRAY)
    return new_game_rect, resume_game_rect

def render_pause_button():
    pygame.draw.rect(screen, BLACK, (*PAUSE_BUTTON_POS, *PAUSE_BUTTON_SIZE))
    pygame.draw.rect(screen, WHITE, (*PAUSE_BUTTON_POS, *PAUSE_BUTTON_SIZE), 2)
    text = button_font.render("||", True, WHITE)
    screen.blit(text, text.get_rect(center=(PAUSE_BUTTON_POS[0] + PAUSE_BUTTON_SIZE[0] / 2, PAUSE_BUTTON_POS[1] + PAUSE_BUTTON_SIZE[1] / 2)))

def render_skip_button():
    skip_rect = pygame.Rect(WIDTH - 110, 10, 100, 40)
    pygame.draw.rect(screen, BLACK, skip_rect)
    pygame.draw.rect(screen, WHITE, skip_rect, 2)
    text = button_font.render("Skip", True, WHITE)
    screen.blit(text, text.get_rect(center=skip_rect.center))
    return skip_rect

def render_pause_menu():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(PAUSE_OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))
    resume_rect = render_button("Resume", pygame.Rect(WIDTH / 2 - MENU_BUTTON_SIZE[0] / 2, HEIGHT / 2 - MENU_BUTTON_SIZE[1] / 2, *MENU_BUTTON_SIZE))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 - MENU_BUTTON_SIZE[0] / 2, HEIGHT / 2 + MENU_BUTTON_SIZE[1] / 2 + MENU_BUTTON_SPACING, *MENU_BUTTON_SIZE))
    return resume_rect, quit_rect

def render_confirm_save(message="Do you wanna save?"):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(PAUSE_OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))
    confirm_text = button_font.render(message, True, WHITE)
    screen.blit(confirm_text, confirm_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))
    yes_rect = render_button("Yes", pygame.Rect(WIDTH / 2 - MENU_BUTTON_SIZE[0] - 10, HEIGHT / 2 + 20, *MENU_BUTTON_SIZE))
    no_rect = render_button("No", pygame.Rect(WIDTH / 2 + 10, HEIGHT / 2 + 20, *MENU_BUTTON_SIZE))
    cancel_rect = render_button("Cancel", pygame.Rect(WIDTH / 2 - MENU_BUTTON_SIZE[0] / 2, HEIGHT / 2 + 20 + MENU_BUTTON_SIZE[1] + MENU_BUTTON_SPACING, *MENU_BUTTON_SIZE))
    return yes_rect, no_rect, cancel_rect

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
    text_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    if is_fourth_message or is_fourth_message_fade_out:
        message = FOURTH_MESSAGE
    elif is_third_message or is_third_message_fade_out:
        message = THIRD_MESSAGE
    elif is_second_message or is_second_message_fade_out:
        message = SECOND_MESSAGE
    else:
        message = FIRST_MESSAGE
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
    y_offset = HEIGHT / 2 - len(lines) * 20
    for line in lines:
        line_surface = message_font.render(line, True, WHITE)
        line_rect = line_surface.get_rect(center=(WIDTH / 2, y_offset))
        text_surface.blit(line_surface, line_rect)
        y_offset += 40
    current_time = pygame.time.get_ticks()
    elapsed = current_time - message_timer
    if is_message_fade_out or is_second_message_fade_out or is_third_message_fade_out or is_fourth_message_fade_out:
        alpha = int(255 * (1 - elapsed / FADE_OUT_DURATION))
    else:
        alpha = int(255 * min(elapsed / FADE_IN_DURATION, 1.0))
    alpha = max(0, min(255, alpha))
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
    for checkpoint in checkpoint_manager.checkpoints:
        if not checkpoint["reached"]:
            pygame.draw.rect(screen, (0, 255, 0), (checkpoint["x"] - camera_x, checkpoint["y"], checkpoint["width"], checkpoint["height"]))
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
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            if is_title_screen:
                start_rect, quit_rect = render_title()
                if start_rect.collidepoint(mouse_pos):
                    is_title_screen = False
                    is_game_select_screen = True
                elif quit_rect.collidepoint(mouse_pos):
                    running = False
            elif is_game_select_screen:
                new_game_rect, resume_game_rect = render_game_select()
                if new_game_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                    is_game_select_screen = False
                    is_message_screen = True
                    message_timer = pygame.time.get_ticks()
                elif resume_game_rect.collidepoint(mouse_pos):
                    if os.path.exists("save_data.txt"):
                        checkpoint_manager.load_game()
                        if checkpoint_manager.current_checkpoint_id:
                            checkpoint = checkpoint_manager.read_checkpoint(checkpoint_manager.current_checkpoint_id)
                            if checkpoint:
                                player_x = checkpoint["x"]
                                player_y = checkpoint["y"] - PLAYER_HEIGHT
                        else:
                            player_x = 100
                            player_y = HEIGHT - PLAYER_HEIGHT - 10
                        is_game_select_screen = False
                        is_message_screen = False
                        is_message_fade_out = False
                        is_second_message = False
                        is_second_message_fade_out = False
                        is_third_message = False
                        is_third_message_fade_out = False
                        is_fourth_message = False
                        is_fourth_message_fade_out = False
            elif is_game_over:
                if is_confirm_save_game_over:
                    yes_rect, no_rect, cancel_rect = render_confirm_save("Do you wish to save?")
                    if yes_rect.collidepoint(mouse_pos):
                        checkpoint_manager.save_game()
                        reset_game(full_reset=True)
                        is_title_screen = True
                        is_game_over = False
                        is_confirm_save_game_over = False
                    elif no_rect.collidepoint(mouse_pos):
                        reset_game(full_reset=True)
                        is_title_screen = True
                        is_game_over = False
                        is_confirm_save_game_over = False
                    elif cancel_rect.collidepoint(mouse_pos):
                        is_confirm_save_game_over = False
                else:
                    restart_rect, quit_rect = render_game_over()
                    if restart_rect.collidepoint(mouse_pos):
                        reset_game(full_reset=False)
                    elif quit_rect.collidepoint(mouse_pos):
                        is_confirm_save_game_over = True
            elif is_game_won:
                restart_rect, quit_rect = render_win()
                if restart_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                elif quit_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                    is_title_screen = True
            elif is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out:
                skip_rect = render_skip_button()
                if skip_rect.collidepoint(mouse_pos):
                    is_message_screen = False
                    is_message_fade_out = False
                    is_second_message = False
                    is_second_message_fade_out = False
                    is_third_message = False
                    is_third_message_fade_out = False
                    is_fourth_message = False
                    is_fourth_message_fade_out = False
            elif not (is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out):
                pause_rect = pygame.Rect(*PAUSE_BUTTON_POS, *PAUSE_BUTTON_SIZE)
                if pause_rect.collidepoint(mouse_pos) and not is_paused:
                    is_paused = True
                elif is_paused:
                    if is_confirm_save:
                        yes_rect, no_rect, cancel_rect = render_confirm_save()
                        if yes_rect.collidepoint(mouse_pos):
                            checkpoint_manager.save_game()
                            reset_game(full_reset=True)
                            is_title_screen = True
                            is_paused = False
                            is_confirm_save = False
                        elif no_rect.collidepoint(mouse_pos):
                            reset_game(full_reset=True)
                            is_title_screen = True
                            is_paused = False
                            is_confirm_save = False
                        elif cancel_rect.collidepoint(mouse_pos):
                            is_confirm_save = False
                    else:
                        resume_rect, quit_rect = render_pause_menu()
                        if resume_rect.collidepoint(mouse_pos):
                            is_paused = False
                        elif quit_rect.collidepoint(mouse_pos):
                            is_confirm_save = True

        elif event.type == pygame.KEYDOWN:
            if is_title_screen:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    is_title_screen = False
                    is_game_select_screen = True
                elif event.key == pygame.K_q:
                    running = False
            elif is_game_select_screen:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    reset_game(full_reset=True)
                    is_game_select_screen = False
                    is_message_screen = True
                    message_timer = pygame.time.get_ticks()
                elif event.key == pygame.K_r and os.path.exists("save_data.txt"):
                    checkpoint_manager.load_game()
                    if checkpoint_manager.current_checkpoint_id:
                        checkpoint = checkpoint_manager.read_checkpoint(checkpoint_manager.current_checkpoint_id)
                        if checkpoint:
                            player_x = checkpoint["x"]
                            player_y = checkpoint["y"] - PLAYER_HEIGHT
                    else:
                        player_x = 100
                        player_y = HEIGHT - PLAYER_HEIGHT - 10
                    is_game_select_screen = False
                    is_message_screen = False
                    is_message_fade_out = False
                    is_second_message = False
                    is_second_message_fade_out = False
                    is_third_message = False
                    is_third_message_fade_out = False
                    is_fourth_message = False
                    is_fourth_message_fade_out = False
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
                    reset_game(full_reset=False)
                elif event.key == pygame.K_q:
                    is_confirm_save_game_over = True
            elif is_game_won:
                if event.key == pygame.K_r:
                    reset_game(full_reset=True)
                elif event.key == pygame.K_q:
                    reset_game(full_reset=True)
                    is_title_screen = True
            elif not is_paused:
                if event.key == pygame.K_e:
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

    if not (is_game_over or is_game_won or is_title_screen or is_game_select_screen or is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out or is_paused):
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

        player_velocity_y += GRAVITY
        next_player_y = player_y + player_velocity_y
        next_player_rect = pygame.Rect(player_x, next_player_y, PLAYER_WIDTH, PLAYER_HEIGHT)

        on_platform = False
        for i, platform in enumerate(platforms):
            if next_player_rect.colliderect(platform.rect):
                if player_velocity_y > 0:
                    next_player_y = platform.rect.top - PLAYER_HEIGHT
                    player_velocity_y = 0
                    is_jumping = False
                    on_platform = True
                    if i == 4 and show_gap_hint:
                        show_gap_hint = False
                        gap_hint_shown = True
                        if not alien_hint_shown:
                            show_alien_hint = True
                    elif i == 5 and show_alien_hint and not alien_hint_shown:
                        alien_hint_timer = pygame.time.get_ticks()
                        alien_hint_shown = True
                elif player_velocity_y < 0:
                    next_player_y = platform.rect.bottom
                    player_velocity_y = 0

        player_y = next_player_y

        if not on_platform and player_y > HEIGHT - PLAYER_HEIGHT - 40 and player_x < HOLE_LEFT:
            player_y = HEIGHT - PLAYER_HEIGHT - 40
            player_velocity_y = 0
            is_jumping = False

        player_rect = pygame.Rect(player_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT)
        for checkpoint in checkpoint_manager.checkpoints:
            if not checkpoint["reached"] and player_rect.colliderect(
                pygame.Rect(checkpoint["x"], checkpoint["y"], checkpoint["width"], checkpoint["height"])
            ):
                checkpoint_manager.update_checkpoint(checkpoint["id"])
                if checkpoint["id"] == 1:
                    player_y = platforms[9].rect.top - PLAYER_HEIGHT
                break
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

        if show_alien_hint and alien_hint_timer > 0:
            current_time = pygame.time.get_ticks()
            if current_time - alien_hint_timer >= ALIEN_HINT_DURATION:
                show_alien_hint = False
                if not interact_hint_shown:
                    show_interact_hint = True

        if is_platform_breaking and pygame.time.get_ticks() - platform_break_timer >= PLATFORM_BREAK_DELAY:
            if BREAKABLE_PLATFORM_INDEX < len(platforms):
                platforms.pop(BREAKABLE_PLATFORM_INDEX)
            is_platform_breaking = False

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
    elif is_game_select_screen:
        render_game_select()
    elif is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out:
        render_message()
        render_skip_button()
    elif is_game_over:
        if is_confirm_save_game_over:
            render_confirm_save("Do you wish to save?")
        else:
            render_game_over()
    elif is_game_won:
        render_win()
    else:
        render_game()
        render_pause_button()
        if is_paused:
            if is_confirm_save:
                render_confirm_save()
            else:
                render_pause_menu()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
