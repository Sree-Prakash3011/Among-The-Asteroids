# Loads modules for game functionality
import pygame  # type: ignore
import sys
import sqlite3
import os

# Constants: Game Settings
WIDTH = 800
HEIGHT = 600
WORLD_WIDTH = 5600
HOLE_LEFT = 800

# Constants: Player Build
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 60
PLAYER_SPEED = 5
PLAYER_JUMP = -17
GRAVITY = 0.8

# Constants: Enemy Build
ENEMY_WIDTH = 30
ENEMY_HEIGHT = 30
ENEMY_SPEED = 3

# Constants: Interaction Timers
PLATFORM_BREAK_DELAY = 1000
PICKUP_MESSAGE_DURATION = 2000
CHECKPOINT_MESSAGE_DURATION = 1000
ALIEN_HINT_DURATION = 1000
FADE_IN_DURATION = 1000
FADE_OUT_DURATION = 500

# Constants: Colours
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Constants: UI Elements
BUTTON_LARGE = (200, 60)
PAUSE_BUTTON_SIZE = (40, 40)
PAUSE_BUTTON_POS = (WIDTH - PAUSE_BUTTON_SIZE[0] - 10, 10)
PAUSE_OVERLAY_COLOR = (0, 0, 0, 128)
MENU_BUTTON_SIZE = (300, 50)
BACK_BUTTON_SIZE = (150, 50)
MENU_BUTTON_SPACING = 20
CONFIRM_BUTTON_SIZE = (150, 50)
NEW_GAME_BUTTON_SIZE = (300, 50)
SAVE_FILE = "game_save.db"

# Constants: Level 1 Story Text
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

# Pygame Setup: Initializes game window and clock
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AMONG THE ASTEROIDS")
clock = pygame.time.Clock()

# Font Setup: Defines fonts for text rendering
font = pygame.font.Font(None, 74)
speech_font = pygame.font.Font(None, 30)
button_font = pygame.font.Font(None, 40)
message_font = pygame.font.Font(None, 36)
timer_font = pygame.font.Font(None, 30)

# Enemy Class: Defines enemy properties and behavior
class Enemy:
    def __init__(self, x, y, width, height, speed):
        self.rect = pygame.Rect(x, y, width, height)
        self.base_speed = speed
        self.current_speed = speed
        self.origin_x = x
        self.is_chasing = False
        self.chase_start_time = 0
        self.speed_increase_timer = 0

    # Enemy Movement: Makes enemies chase player
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

# Platform Class: Defines platform properties
class Platform:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

# Interactable Class: Defines interactable objects
class Interactable:
    def __init__(self, x, y, width, height, name):
        self.rect = pygame.Rect(x, y, width, height)
        self.name = name

# Checkpoint Manager Class
class CheckpointManager:
    def __init__(self, db_file=SAVE_FILE):
        self.db_file = db_file
        self.conn = None
        self.checkpoints = [
            {"x": 100, "y": HEIGHT - 40 - PLAYER_HEIGHT, "width": 20, "height": 30, "reached": True, "id": "1.0", "player_x": 100, "player_y": HEIGHT - 40 - PLAYER_HEIGHT},
            {"x": 2990, "y": 370, "width": 20, "height": 30, "reached": False, "id": "1.1", "player_x": 2990, "player_y": 370},
            {"x": 150, "y": HEIGHT - 40 - PLAYER_HEIGHT, "width": 20, "height": 30, "reached": False, "id": "2.0", "player_x": 150, "player_y": HEIGHT - 40 - PLAYER_HEIGHT}
        ]
        self.current_checkpoint_id = "1.0"
        print(f"Initialized CheckpointManager with default checkpoint_id: {self.current_checkpoint_id}")
        self._init_db()
        self._validate_checkpoints()

    # Database Setup: Creates SQLite tables
    def _init_db(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    x INTEGER,
                    y INTEGER,
                    width INTEGER,
                    height INTEGER,
                    reached BOOLEAN,
                    player_x INTEGER,
                    player_y INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
            for checkpoint in self.checkpoints:
                cursor.execute("""
                    INSERT OR IGNORE INTO checkpoints (id, x, y, width, height, reached, player_x, player_y)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (checkpoint["id"], checkpoint["x"], checkpoint["y"], checkpoint["width"],
                      checkpoint["height"], checkpoint["reached"], checkpoint["player_x"], checkpoint["player_y"]))
            conn.commit()
            print(f"Database initialized: {self.db_file}")
        except sqlite3.Error as e:
            print(f"Database initialization failed: {e}")

    # Database Connection: Connects to SQLite database
    def _get_connection(self):
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.db_file)
                print(f"Opened SQLite connection to {self.db_file}")
            except sqlite3.Error as e:
                print(f"Failed to open SQLite connection: {e}")
                raise
        return self.conn

    # Checkpoint: Removes duplicate IDs
    def _validate_checkpoints(self):
        seen_ids = set()
        unique_checkpoints = []
        for checkpoint in self.checkpoints:
            if checkpoint["id"] not in seen_ids:
                seen_ids.add(checkpoint["id"])
                unique_checkpoints.append(checkpoint)
            else:
                print(f"Warning: Duplicate checkpoint ID {checkpoint['id']} found and removed")
        self.checkpoints = unique_checkpoints

    # Checkpoint: Retrieves checkpoint by ID
    def read_checkpoint(self, id):
        id = str(id)
        for checkpoint in self.checkpoints:
            if checkpoint["id"] == id:
                return checkpoint
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM checkpoints WHERE id = ?", (id,))
            row = cursor.fetchone()
            if row:
                checkpoint = {
                    "id": row[0], "x": row[1], "y": row[2], "width": row[3],
                    "height": row[4], "reached": bool(row[5]), "player_x": row[6], "player_y": row[7]
                }
                self.checkpoints.append(checkpoint)
                return checkpoint
        except sqlite3.Error as e:
            print(f"Failed to read checkpoint {id}: {e}")
        return None

    # Checkpoint: Adds new checkpoint
    def create_checkpoint(self, x, y, width, height, id, player_x, player_y):
        id = str(id)
        checkpoint = {"x": x, "y": y, "width": width, "height": height, "reached": False, "id": id, "player_x": player_x, "player_y": player_y}
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO checkpoints (id, x, y, width, height, reached, player_x, player_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (id, x, y, width, height, False, player_x, player_y))
            conn.commit()
            self.checkpoints.append(checkpoint)
            print(f"Created checkpoint {id} at ({x}, {y})")
            return True
        except sqlite3.Error as e:
            print(f"Failed to create checkpoint {id}: {e}")
            return False

    # Checkpoint: Updates checkpoint status
    def update_checkpoint(self, id, reached=True, player_x=None, player_y=None):
        id = str(id)
        checkpoint = self.read_checkpoint(id)
        if checkpoint:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                if reached:
                    if player_x is not None and player_y is not None:
                        cursor.execute("""
                            UPDATE checkpoints
                            SET reached = ?, player_x = ?, player_y = ?
                            WHERE id = ?
                        """, (reached, player_x, player_y, id))
                        print(f"Updated checkpoint {id} with player position ({player_x}, {player_y})")
                    else:
                        cursor.execute("UPDATE checkpoints SET reached = ? WHERE id = ?", (reached, id))
                        print(f"Updated checkpoint {id} reached status to {reached}")
                conn.commit()
                for cp in self.checkpoints:
                    if cp["id"] == id:
                        cp["reached"] = reached
                        if reached and player_x is not None and player_y is not None:
                            cp["player_x"] = player_x
                            cp["player_y"] = player_y
                        break
                if reached:
                    self.current_checkpoint_id = id
                    self.save_game()
                    print(f"Set current_checkpoint_id to {id}")
                return True
            except sqlite3.Error as e:
                print(f"Failed to update checkpoint {id}: {e}")
                return False
        print(f"Checkpoint {id} not found")
        return False

    # Checkpoint: Removes checkpoint
    def delete_checkpoint(self, id):
        id = str(id)
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checkpoints WHERE id = ?", (id,))
            conn.commit()
            for i, checkpoint in enumerate(self.checkpoints):
                if checkpoint["id"] == id:
                    self.checkpoints.pop(i)
                    if self.current_checkpoint_id == id:
                        self.current_checkpoint_id = self.get_latest_checkpoint()
                    print(f"Deleted checkpoint {id}, current_checkpoint_id set to {self.current_checkpoint_id}")
                    return True
            print(f"Checkpoint {id} not found for deletion")
            return False
        except sqlite3.Error as e:
            print(f"Failed to delete checkpoint {id}: {e}")
            return False

    # Checkpoint: Finds most recent checkpoint
    def get_latest_checkpoint(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM checkpoints WHERE reached = 1 ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            latest_id = result[0] if result else "1.0"
            print(f"Latest checkpoint: {latest_id}")
            return latest_id
        except sqlite3.Error as e:
            print(f"Failed to get latest checkpoint: {e}")
            return "1.0"

    # Saves game state
    def save_game(self):
        global is_blaster_acquired
        for attempt in range(3):
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                              ("current_checkpoint_id", self.current_checkpoint_id))
                cursor.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                              ("is_blaster_acquired", str(is_blaster_acquired)))
                conn.commit()
                print(f"Game saved: current_checkpoint_id={self.current_checkpoint_id}, is_blaster_acquired={is_blaster_acquired}")
                return True
            except sqlite3.Error as e:
                print(f"Failed to save game (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    print("Retrying save...")
                    continue
                return False

    # Loads saved game state
    def load_game(self):
        global is_blaster_acquired
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM checkpoints")
            self.checkpoints = [
                {
                    "id": row[0], "x": row[1], "y": row[2], "width": row[3],
                    "height": row[4], "reached": bool(row[5]), "player_x": row[6], "player_y": row[7]
                } for row in cursor.fetchall()
            ]
            print(f"Loaded checkpoints: {[cp['id'] for cp in self.checkpoints]}")
            cursor.execute("SELECT value FROM game_state WHERE key = 'current_checkpoint_id'")
            result = cursor.fetchone()
            if result and self.read_checkpoint(result[0]):
                self.current_checkpoint_id = result[0]
            else:
                self.current_checkpoint_id = self.get_latest_checkpoint()
                print(f"No valid current_checkpoint_id found, using latest: {self.current_checkpoint_id}")
            cursor.execute("SELECT value FROM game_state WHERE key = 'is_blaster_acquired'")
            result = cursor.fetchone()
            is_blaster_acquired = result[0].lower() == 'true' if result else False
            print(f"Loaded game: current_checkpoint_id={self.current_checkpoint_id}, is_blaster_acquired={is_blaster_acquired}")
            self._ensure_default_checkpoints()
            return True
        except sqlite3.Error as e:
            print(f"Failed to load save file: {e}")
            self.current_checkpoint_id = self.get_latest_checkpoint()
            is_blaster_acquired = False
            self._ensure_default_checkpoints()
            print(f"Load failed, using latest checkpoint: {self.current_checkpoint_id}")
            return False

    #Checkpoints: Adds default checkpoints
    def _ensure_default_checkpoints(self):
        default_checkpoints = [
            {"x": 100, "y": HEIGHT - 40 - PLAYER_HEIGHT, "width": 20, "height": 30, "reached": True, "id": "1.0", "player_x": 100, "player_y": HEIGHT - 40 - PLAYER_HEIGHT},
            {"x": 2990, "y": 370, "width": 20, "height": 30, "reached": False, "id": "1.1", "player_x": 2990, "player_y": 370},
            {"x": 150, "y": HEIGHT - 40 - PLAYER_HEIGHT, "width": 20, "height": 30, "reached": False, "id": "2.0", "player_x": 150, "player_y": HEIGHT - 40 - PLAYER_HEIGHT}
        ]
        for default in default_checkpoints:
            if not self.read_checkpoint(default["id"]):
                self.create_checkpoint(
                    default["x"], default["y"], default["width"], default["height"],
                    default["id"], default["player_x"], default["player_y"]
                )
                if default["reached"]:
                    self.update_checkpoint(default["id"], reached=True)
        print(f"Ensured default checkpoints: {', '.join(cp['id'] for cp in self.checkpoints)}")

    # Close Database: Closes SQLite connection
    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            print(f"Closed SQLite connection to {self.db_file}")

# Platforms: Level 1
initial_platforms_level1 = [
    Platform(0, HEIGHT - 40, 800, 40),        # Index 0: Ground 
    Platform(1200, HEIGHT - 40, 1200, 40),    # Index 1: Ground  
    Platform(3500, HEIGHT - 40, 1800, 40),    # Index 2: Ground  
    Platform(296, 400, 200, 20),              # Index 3: Floating  
    Platform(850, 400, 200, 20),              # Index 4: Floating  
    Platform(1400, 400, 200, 20),             # Index 5: Floating 
    Platform(2000, 450, 200, 20),             # Index 6: Floating 
    Platform(2300, 350, 200, 20),             # Index 7: Floating 
    Platform(2600, 250, 200, 20),             # Index 8: Floating   
    Platform(2900, 400, 200, 20),             # Index 9: Floating  
    Platform(3200, 300, 200, 20),             # Index 10: Floating   
    Platform(3600, 400, 200, 20),             # Index 11: Floating   
    Platform(3900, 350, 200, 20),             # Index 12: Floating  
    Platform(5400, 400, 200, 20),             # Index 13: Floating 
    Platform(4650, 400, 200, 20)              # Index 14: Floating   
]

# Platforms: Level 2
initial_platforms_level2 = [
    Platform(100, HEIGHT - PLAYER_HEIGHT - 10, 50, 40),
    Platform(300, 380, 50, 40),
    Platform(500, 530, 50, 40),
    Platform(700, 380, 50, 40),
    Platform(900, 530, 50, 40),
    Platform(1000, 380, 50, 40),
    Platform(1100, 230, 50, 40),
    Platform(1300, 380, 50, 40),
    Platform(1500, 230, 50, 40),
    Platform(1700, 180, 50, 40),
    Platform(1900, 330, 50, 40),
    Platform(2100, 400, 50, 40),
    Platform(2300, 350, 50, 40),
    Platform(2500, 450, 50, 40),
    Platform(2700, 300, 50, 40),
    Platform(2900, 400, 50, 40),
]

# Configiring level 1
level_data = {
    1: {
        "platforms": initial_platforms_level1,
        "breakable_index": 13,
        "enemies": [
            Enemy(1600, HEIGHT - 40 - 30, ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_SPEED),
            Enemy(4000, HEIGHT - 40 - 30, ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_SPEED),
            Enemy(4700, HEIGHT - 40 - 30, ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_SPEED)
        ],
        "blaster": Interactable(5450, 400 - 20, 20, 20, "Blaster"),
        "hints": {
            "jump": {"platform_index": 4, "message": "Press SPACE to jump", "y_offset": -30},
            "gap": None,
            "alien": {"platform_index": 6, "message": "Beware of the alien", "y_offset": 480},
            "interact": {"position_x": 5500, "position_y": 370, "message": "Press E to interact"}
        }
    },

    # Configiring level 2
    2: {
        "platforms": initial_platforms_level2,
        "breakable_index": 0,
        "enemies": [],
        "blaster": None,
        "hints": {
            "jump": None,
            "gap": None,
            "alien": None,
            "interact": None
        }
    }
}

# Initialize checkpoints and level objects
checkpoint_manager = CheckpointManager(SAVE_FILE)
platforms = level_data[1]["platforms"].copy()
enemies = level_data[1]["enemies"].copy()
blaster = level_data[1]["blaster"]

# Initialize starting position and movement
player_x = 100
player_y = HEIGHT - PLAYER_HEIGHT - 10
player_velocity_y = 0
is_jumping = False
camera_x = 0
current_level = 1

# Initialize flags for game flow
is_game_over = False
is_game_won = False
is_title_screen = True
is_game_select_screen = False
is_new_game_options = False
is_message_screen = False
is_message_fade_out = False
is_second_message = False
is_second_message_fade_out = False
is_third_message = False
is_third_message_fade_out = False
is_fourth_message = False
is_fourth_message_fade_out = False
is_resume_confirm = False
is_new_game_confirm = False
message_timer = 0
show_speech_bubble = False
pickup_message = None
pickup_message_timer = 0
checkpoint_message = None
checkpoint_message_timer = 0
is_blaster_acquired = False
is_platform_breaking = False
platform_break_timer = 0
show_movement_hint = True
show_jump_hint = False
show_alien_hint = False
show_interact_hint = False
jump_hint_shown = False
alien_hint_shown = False
interact_hint_shown = False
alien_hint_timer = 0
is_paused = False
is_confirm_save = False
is_confirm_save_game_over = False
running = True
start_timer = None
end_timer = None
paused_time = 0
last_pause_start = None

# Delete Save File
def delete_save_file():
    global checkpoint_manager
    try:
        checkpoint_manager.close()
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
            print(f"Deleted {SAVE_FILE}")
        else:
            print(f"No save file found at {SAVE_FILE}")
        checkpoint_manager = CheckpointManager(SAVE_FILE)
        checkpoint_manager.current_checkpoint_id = "1.0"
        checkpoint_manager.save_game()
        print(f"Reset CheckpointManager to default checkpoint 1.0")
        return True
    except OSError as e:
        print(f"Failed to delete {SAVE_FILE}: {e}")
        checkpoint_manager._get_connection()
        return False

# Restarts game state
def reset_game(full_reset=True, level=1):
    global player_x, player_y, player_velocity_y, is_jumping, camera_x, is_game_over, is_game_won
    global is_title_screen, is_message_screen, is_message_fade_out, is_second_message, is_second_message_fade_out
    global is_third_message, is_third_message_fade_out, is_fourth_message, is_fourth_message_fade_out
    global show_speech_bubble, pickup_message, is_blaster_acquired
    global is_platform_breaking, platform_break_timer, blaster, platforms, enemies
    global show_movement_hint, show_jump_hint, show_alien_hint, show_interact_hint
    global jump_hint_shown, alien_hint_shown, interact_hint_shown, alien_hint_timer
    global is_paused, is_confirm_save, is_confirm_save_game_over, is_game_select_screen
    global checkpoint_message, checkpoint_message_timer, start_timer, end_timer, paused_time, last_pause_start
    global is_resume_confirm, is_new_game_confirm, current_level

    print(f"reset_game called with full_reset={full_reset}, level={level}")
    
    # Checkpoint: Loads or creates checkpoint
    checkpoint = None
    if full_reset:
        current_level = level
        checkpoint_id = f"{level}.0"
        checkpoint = checkpoint_manager.read_checkpoint(checkpoint_id)
        if not checkpoint:
            print(f"Creating default checkpoint {checkpoint_id}")
            checkpoint_manager.create_checkpoint(
                x=100, y=HEIGHT - 40 - PLAYER_HEIGHT, width=20, height=30,
                id=checkpoint_id, player_x=100, player_y=HEIGHT - 40 - PLAYER_HEIGHT
            )
            checkpoint = checkpoint_manager.read_checkpoint(checkpoint_id)
        checkpoint_manager.update_checkpoint(checkpoint_id, True, player_x=100, player_y=HEIGHT - 40 - PLAYER_HEIGHT)
        for cp in checkpoint_manager.checkpoints:
            if cp["id"] != checkpoint_id:
                cp["reached"] = False
                checkpoint_manager.update_checkpoint(cp["id"], reached=False)
        checkpoint_manager.current_checkpoint_id = checkpoint_id
        checkpoint_manager.save_game()
        print(f"Full reset to checkpoint {checkpoint_id} at ({checkpoint['player_x']}, {checkpoint['player_y']})")
    else:
        if not checkpoint_manager.load_game():
            print("Load game failed, using latest checkpoint")
            checkpoint_id = checkpoint_manager.get_latest_checkpoint()
            checkpoint = checkpoint_manager.read_checkpoint(checkpoint_id)
            if not checkpoint:
                print(f"Latest checkpoint {checkpoint_id} not found, creating default {level}.0")
                checkpoint_id = f"{level}.0"
                checkpoint_manager.create_checkpoint(
                    x=100, y=HEIGHT - 40 - PLAYER_HEIGHT, width=20, height=30,
                    id=checkpoint_id, player_x=100, player_y=HEIGHT - 40 - PLAYER_HEIGHT
                )
                checkpoint = checkpoint_manager.read_checkpoint(checkpoint_id)
            checkpoint_manager.update_checkpoint(checkpoint_id, True, player_x=checkpoint["player_x"], player_y=checkpoint["player_y"])
            checkpoint_manager.current_checkpoint_id = checkpoint_id
            checkpoint_manager.save_game()
        else:
            latest_checkpoint_id = checkpoint_manager.current_checkpoint_id
            checkpoint = checkpoint_manager.read_checkpoint(latest_checkpoint_id)
            if checkpoint is None:
                print(f"Checkpoint {latest_checkpoint_id} not found, using latest checkpoint")
                checkpoint_id = checkpoint_manager.get_latest_checkpoint()
                checkpoint = checkpoint_manager.read_checkpoint(checkpoint_id)
                if not checkpoint:
                    print(f"Latest checkpoint {id} not found, creating default {level}.0")
                    checkpoint_id = f"{level}.0"
                    checkpoint_manager.create_checkpoint(
                        x=100, y=HEIGHT - 40 - PLAYER_HEIGHT, width=20, height=30,
                        id=checkpoint_id, player_x=100, player_y=HEIGHT - 40 - PLAYER_HEIGHT
                    )
                    checkpoint = checkpoint_manager.read_checkpoint(checkpoint_id)
                checkpoint_manager.update_checkpoint(checkpoint_id, True, player_x=checkpoint["player_x"], player_y=checkpoint["player_y"])
                checkpoint_manager.current_checkpoint_id = checkpoint_id
                checkpoint_manager.save_game()
            else:
                try:
                    current_level = int(latest_checkpoint_id.split('.')[0])
                except (ValueError, IndexError):
                    print(f"Invalid checkpoint ID {latest_checkpoint_id}, defaulting to level {level}")
                    current_level = level
                print(f"Loaded checkpoint {latest_checkpoint_id} at ({checkpoint['player_x']}, {checkpoint['player_y']}), level={current_level}")
        checkpoint_manager.save_game()

    # Reset player position and state
    player_x = checkpoint["player_x"]
    player_y = checkpoint["player_y"]
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
    is_resume_confirm = False
    is_new_game_confirm = False
    show_speech_bubble = False
    pickup_message = None
    checkpoint_message = None
    checkpoint_message_timer = 0

    # Reset and reinitializes objects
    if current_level in level_data:
        platforms = [Platform(p.rect.x, p.rect.y, p.rect.width, p.rect.height) for p in level_data[current_level]["platforms"]]
        enemies = [Enemy(e.rect.x, e.rect.y, e.rect.width, e.rect.height, e.base_speed) for e in level_data[current_level]["enemies"]]
        blaster_data = level_data[current_level]["blaster"]
        blaster = Interactable(blaster_data.rect.x, blaster_data.rect.y, blaster_data.rect.width, blaster_data.rect.height, blaster_data.name) if blaster_data and not is_blaster_acquired else None
    else:
        print(f"Level {current_level} not found, defaulting to level 1")
        current_level = 1
        platforms = [Platform(p.rect.x, p.rect.y, p.rect.width, p.rect.height) for p in level_data[1]["platforms"]]
        enemies = [Enemy(e.rect.x, e.rect.y, e.rect.width, e.rect.height, e.base_speed) for e in level_data[1]["enemies"]]
        blaster_data = level_data[1]["blaster"]
        blaster = Interactable(blaster_data.rect.x, blaster_data.rect.y, blaster_data.rect.width, blaster_data.rect.height, blaster_data.name) if blaster_data and not is_blaster_acquired else None

    # Reset enemy positions
    for enemy in enemies:
        enemy.rect.x = enemy.origin_x
        enemy.rect.y = HEIGHT - 40 - 30
        enemy.current_speed = enemy.base_speed
        enemy.is_chasing = False

    # Reset Game Flags for new game
    if full_reset:
        is_blaster_acquired = False
        jump_hint_shown = False
        alien_hint_shown = False
        interact_hint_shown = False
        start_timer = None
        end_timer = None
        paused_time = 0
        last_pause_start = None
    else:
        if last_pause_start is not None:
            paused_time += pygame.time.get_ticks() - last_pause_start
            last_pause_start = None

    is_platform_breaking = False
    platform_break_timer = 0
    show_movement_hint = True
    show_jump_hint = False
    show_alien_hint = False
    show_interact_hint = False
    alien_hint_timer = 0
    is_paused = False
    is_confirm_save = False
    is_confirm_save_game_over = False
    is_game_select_screen = False

# Render Button
def render_button(text, rect, text_color=BLACK, bg_color=WHITE):
    mouse_pos = pygame.mouse.get_pos()
    bg_color = (200, 200, 200) if rect.collidepoint(mouse_pos) else bg_color
    pygame.draw.rect(screen, bg_color, rect)
    text_surface = button_font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    return rect

# Render Title Screen
def render_title():
    screen.fill(BLACK)
    title_text = font.render("AMONG THE ASTEROIDS", True, WHITE)
    screen.blit(title_text, title_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))
    start_rect = render_button("Start", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 + 50, *BUTTON_LARGE))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 + 120, *BUTTON_LARGE))
    return start_rect, quit_rect

# Render Game Select
def render_game_select():
    screen.fill(BLACK)
    new_game_rect = render_button("New Game", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 - 70, *BUTTON_LARGE))
    resume_game_rect = render_button("Resume Game", pygame.Rect(WIDTH / 2 - BUTTON_LARGE[0] / 2, HEIGHT / 2 + 10, *BUTTON_LARGE))
    back_rect = render_button("Back", pygame.Rect(WIDTH / 2 - BACK_BUTTON_SIZE[0] / 2, HEIGHT / 2 + 90, *BACK_BUTTON_SIZE))
    if os.path.exists(SAVE_FILE):
        screen.blit(speech_font.render("There is a saved progress", True, WHITE), (WIDTH / 2 - 120, HEIGHT / 2 - 150))
    return new_game_rect, resume_game_rect, back_rect

# Render New Game Options
def render_new_game_options():
    screen.fill(BLACK)
    title_text = button_font.render("Select Level", True, WHITE)
    screen.blit(title_text, title_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 200)))
    button_height = HEIGHT / 2 - 150
    buttons = []
    for i in range(5):
        y = button_height + i * (NEW_GAME_BUTTON_SIZE[1] + MENU_BUTTON_SPACING)
        rect = pygame.Rect(WIDTH / 2 - NEW_GAME_BUTTON_SIZE[0] / 2, y, *NEW_GAME_BUTTON_SIZE)
        text = f"Level {i + 1}"
        buttons.append(render_button(text, rect))
    back_rect = render_button("Back", pygame.Rect(WIDTH / 2 - BACK_BUTTON_SIZE[0] / 2, HEIGHT - 100, *BACK_BUTTON_SIZE))
    return buttons, back_rect

# Render Pause Button
def render_pause_button():
    pygame.draw.rect(screen, BLACK, (*PAUSE_BUTTON_POS, *PAUSE_BUTTON_SIZE))
    pygame.draw.rect(screen, WHITE, (*PAUSE_BUTTON_POS, *PAUSE_BUTTON_SIZE), 2)
    text = button_font.render("||", True, WHITE)
    screen.blit(text, text.get_rect(center=(PAUSE_BUTTON_POS[0] + PAUSE_BUTTON_SIZE[0] / 2, PAUSE_BUTTON_POS[1] + PAUSE_BUTTON_SIZE[1] / 2)))

# Render Skip Button
def render_skip_button():
    skip_rect = pygame.Rect(WIDTH - 110, 10, 100, 40)
    pygame.draw.rect(screen, BLACK, skip_rect)
    pygame.draw.rect(screen, WHITE, skip_rect, 2)
    text = button_font.render("Skip", True, WHITE)
    screen.blit(text, text.get_rect(center=skip_rect.center))
    return skip_rect

# Render Pause Menu
def render_pause_menu():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(PAUSE_OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))
    resume_rect = render_button("Resume", pygame.Rect(WIDTH / 2 - MENU_BUTTON_SIZE[0] / 2, HEIGHT / 2 - MENU_BUTTON_SIZE[1] - 10, *MENU_BUTTON_SIZE))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 - MENU_BUTTON_SIZE[0] / 2, HEIGHT / 2 + 10, *MENU_BUTTON_SIZE))
    return resume_rect, quit_rect

# Render Confirm Save
def render_confirm_save(message="Do you wanna save?", show_cancel=False):
    screen.fill(BLACK)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(PAUSE_OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))
    confirm_text = button_font.render(message, True, WHITE)
    screen.blit(confirm_text, confirm_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 100)))
    spacing = 20
    yes_no_width = CONFIRM_BUTTON_SIZE[0] * 2 + spacing
    start_x = WIDTH / 2 - yes_no_width / 2
    yes_rect = render_button("Yes", pygame.Rect(start_x, HEIGHT / 2 + 20, *CONFIRM_BUTTON_SIZE))
    no_rect = render_button("No", pygame.Rect(start_x + CONFIRM_BUTTON_SIZE[0] + spacing, HEIGHT / 2 + 20, *CONFIRM_BUTTON_SIZE))
    cancel_rect = None
    if show_cancel:
        cancel_rect = render_button("Cancel", pygame.Rect(WIDTH / 2 - CONFIRM_BUTTON_SIZE[0] / 2, HEIGHT / 2 + 20 + CONFIRM_BUTTON_SIZE[1] + spacing, *CONFIRM_BUTTON_SIZE))
    return yes_rect, no_rect, cancel_rect

# Render Game Over
def render_game_over():
    global last_pause_start
    screen.fill(BLACK)
    lose_text = font.render("YOU DIED!", True, WHITE)
    screen.blit(lose_text, lose_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))
    if start_timer is not None and not is_confirm_save_game_over:
        if last_pause_start is None:
            last_pause_start = pygame.time.get_ticks()
        elapsed_time = (last_pause_start - start_timer) - paused_time
        minutes = int(elapsed_time // 60000)
        seconds = int((elapsed_time % 60000) // 1000)
        milliseconds = int(elapsed_time % 1000)
        time_text = timer_font.render(f"Time: {minutes:02d}:{seconds:02d}.{milliseconds:03d}", True, WHITE)
        screen.blit(time_text, time_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 10)))
    restart_rect = render_button("Restart", pygame.Rect(WIDTH / 2 - 200, HEIGHT / 2 + 50, 200, 50))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 + 50, HEIGHT / 2 + 50, 200, 50))
    return restart_rect, quit_rect

# Render Win Screen
def render_win():
    screen.fill(BLACK)
    win_text = font.render("YOU WIN!", True, WHITE)
    screen.blit(win_text, win_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))
    if end_timer and start_timer is not None:
        elapsed_time = (end_timer - start_timer) - paused_time
        minutes = int(elapsed_time // 60000)
        seconds = int((elapsed_time % 60000) // 1000)
        milliseconds = int(elapsed_time % 1000)
        time_text = timer_font.render(f"Time: {minutes:02d}:{seconds:02d}.{milliseconds:03d}", True, WHITE)
        screen.blit(time_text, time_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 10)))
    restart_rect = render_button("Restart", pygame.Rect(WIDTH / 2 - 200, HEIGHT / 2 + 50, 200, 50))
    quit_rect = render_button("Quit", pygame.Rect(WIDTH / 2 + 50, HEIGHT / 2 + 50, 200, 50))
    return restart_rect, quit_rect

# Render Messages
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
        if test_surface.get_size()[0] < max_width:
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
    elapsed_time = current_time - message_timer
    if is_message_fade_out or is_second_message_fade_out or is_third_message_fade_out or is_fourth_message_fade_out:
        alpha = int(255 * (1 - elapsed_time / FADE_OUT_DURATION))
    else:
        alpha = int(255 * min(elapsed_time / FADE_IN_DURATION, 1.0))
    alpha = max(0, min(255, alpha))
    text_surface.set_alpha(alpha)
    screen.blit(text_surface, (0, 0))

# Render Game
def render_game():
    global pickup_message, pickup_message_timer, show_speech_bubble, show_movement_hint, show_jump_hint, show_alien_hint, show_interact_hint
    global checkpoint_message, checkpoint_message_timer
    screen.fill(BLACK)

    # Renders player rectangle
    pygame.draw.rect(screen, WHITE, (player_x - camera_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT))

    # Renders enemy rectangles
    for enemy in enemies:
        pygame.draw.rect(screen, RED, (enemy.rect.x - camera_x, enemy.rect.y, enemy.rect.width, enemy.rect.height))

    # Renders blaster rectangle
    if blaster and not is_blaster_acquired:
        pygame.draw.rect(screen, BLUE, (blaster.rect.x - camera_x, blaster.rect.y, blaster.rect.width, blaster.rect.height))

    # Renders checkpoint rectangles
    for checkpoint in checkpoint_manager.checkpoints:
        checkpoint_level = int(checkpoint["id"].split('.')[0])
        if checkpoint_level == current_level:
            if not ((checkpoint["id"] == "1.0" and checkpoint["x"] == 100 and checkpoint["y"] == HEIGHT - 40 - PLAYER_HEIGHT) or \
                   (checkpoint["id"] == "2.0" and checkpoint["x"] == 150 and checkpoint["y"] == HEIGHT - 40 - PLAYER_HEIGHT)):
                if not checkpoint["reached"]:
                    pygame.draw.rect(screen, (0, 255, 0), (checkpoint["x"] - camera_x, checkpoint["y"], checkpoint["width"], checkpoint["height"]))

    # Renders platform rectangles
    for platform in platforms:
        pygame.draw.rect(screen, GRAY, (platform.rect.x - camera_x, platform.rect.y, platform.rect.width, platform.rect.height))

    # Shows blaster pickup prompt
    if show_speech_bubble and blaster:
        text = speech_font.render("Pick up the blaster?", True, WHITE)
        screen.blit(text, text.get_rect(topleft=(blaster.rect.x - camera_x - 50, 20)))

    # Shows blaster acquisition message
    if pickup_message:
        current_time = pygame.time.get_ticks()
        if current_time - pickup_message_timer > PICKUP_MESSAGE_DURATION:
            pickup_message = None
        else:
            message_text = speech_font.render(pickup_message, True, WHITE)
            screen.blit(message_text, message_text.get_rect(center=(WIDTH / 2, HEIGHT / 2)))

    # Shows checkpoint reached message
    if checkpoint_message:
        current_time = pygame.time.get_ticks()
        if current_time - checkpoint_message_timer > CHECKPOINT_MESSAGE_DURATION:
            checkpoint_message = None
        else:
            message_text = speech_font.render(checkpoint_message, True, WHITE)
            screen.blit(message_text, message_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 60)))

    # Shows movement instructions
    if show_movement_hint:
        hint_text = speech_font.render("Press A and D to move", True, WHITE)
        hint_rect = hint_text.get_rect(center=(player_x - camera_x + PLAYER_WIDTH / 2, player_y - 20))
        screen.blit(hint_text, hint_rect)
    
    # Shows level-specific hints
    hints = level_data[current_level]["hints"]
    if current_level == 1:
        if show_jump_hint and hints["jump"] and isinstance(hints["jump"], dict):
            jump_hint = hints["jump"]
            platform_index = jump_hint["platform_index"]
            if platform_index < len(platforms):
                jump_text = speech_font.render(jump_hint["message"], True, WHITE)
                jump_rect = jump_text.get_rect(center=(platforms[platform_index].rect.x + platforms[platform_index].rect.width / 2 - camera_x, platforms[platform_index].rect.y + jump_hint["y_offset"]))
                screen.blit(jump_text, jump_rect)
        if show_alien_hint and hints["alien"] and isinstance(hints["alien"], dict):
            alien_hint = hints["alien"]
            platform_index = alien_hint["platform_index"]
            if platform_index < len(platforms):
                alien_text = speech_font.render(alien_hint["message"], True, WHITE)
                alien_rect = alien_text.get_rect(center=(platforms[platform_index].rect.x + platforms[platform_index].rect.width / 2 - camera_x, alien_hint["y_offset"]))
                screen.blit(alien_text, alien_rect)
        if show_interact_hint and hints["interact"] and isinstance(hints["interact"], dict):
            interact_hint = hints["interact"]
            if blaster:
                interact_text = speech_font.render(interact_hint["message"], True, WHITE)
                interact_rect = interact_text.get_rect(center=(blaster.rect.x - camera_x, 370))
                screen.blit(interact_text, interact_rect)
    
    # Shows timer
    if start_timer is not None:
        if end_timer is not None and start_timer is not None:
            elapsed_time = (end_timer - start_timer) - paused_time
        elif is_paused and last_pause_start is not None:
            elapsed_time = (last_pause_start - start_timer) - paused_time
        else:
            elapsed_time = (pygame.time.get_ticks() - start_timer) - paused_time
        minutes = int(elapsed_time // 60000)
        seconds = int((elapsed_time % 60000) // 1000)
        milliseconds = elapsed_time % 1000
        time_text = timer_font.render(f"Time: {minutes:02d}:{seconds:02d}.{milliseconds:03d}", True, WHITE)
        screen.blit(time_text, (10, 10))

# Main Game Loop
while running:

    # Handle Events: Processes user inputs
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Title Screen Input: Selects game start
            if is_title_screen:
                start_rect, quit_rect = render_title()
                if start_rect.collidepoint(mouse_pos):
                    is_title_screen = False
                    is_game_select_screen = True
                elif quit_rect.collidepoint(mouse_pos):
                    running = False

            # Game Select Input: Chooses New game or resume game
            elif is_game_select_screen:
                new_game_rect, resume_game_rect, back_rect = render_game_select()
                if new_game_rect.collidepoint(mouse_pos):
                    if os.path.exists(SAVE_FILE):
                        is_game_select_screen = False
                        is_new_game_confirm = True
                    else:
                        is_game_select_screen = False
                        is_new_game_options = True
                elif resume_game_rect.collidepoint(mouse_pos):
                    if os.path.exists(SAVE_FILE):
                        is_game_select_screen = False
                        is_resume_confirm = True
                    else:
                        reset_game(full_reset=True)
                        is_game_select_screen = False
                        is_message_screen = True
                        message_timer = pygame.time.get_ticks()
                elif back_rect.collidepoint(mouse_pos):
                    is_game_select_screen = False
                    is_title_screen = True
            elif is_resume_confirm:
                yes_rect, no_rect, _ = render_confirm_save("Continue game?")
                if yes_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=False)
                    is_resume_confirm = False
                    is_message_screen = True
                    message_timer = pygame.time.get_ticks()
                elif no_rect.collidepoint(mouse_pos):
                    is_resume_confirm = False
                    is_game_select_screen = True

            # New Game: Confirms save deletion
            elif is_new_game_confirm:
                yes_rect, no_rect, _ = render_confirm_save("Erase existing save?")
                if yes_rect.collidepoint(mouse_pos):
                    if delete_save_file():
                        is_new_game_confirm = False
                        is_new_game_options = True
                    else:
                        print("Failed to erase save file")
                elif no_rect.collidepoint(mouse_pos):
                    is_new_game_confirm = False
                    is_game_select_screen = True

            # New Game: Selects level
            elif is_new_game_options:
                buttons, back_rect = render_new_game_options()
                if back_rect.collidepoint(mouse_pos):
                    is_new_game_options = False
                    is_game_select_screen = True
                for i, button in enumerate(buttons):
                    if button.collidepoint(mouse_pos):
                        reset_game(full_reset=True, level=i + 1)
                        is_new_game_options = False
                        is_message_screen = True
                        message_timer = pygame.time.get_ticks()
                        break

            # Game Over: Handles restart or quit
            elif is_game_over:
                if is_confirm_save_game_over:
                    yes_rect, no_rect, cancel_rect = render_confirm_save("Do you wish to save?", show_cancel=True)
                    if yes_rect and yes_rect.collidepoint(mouse_pos):
                        checkpoint_manager.save_game()
                        reset_game(full_reset=False)
                        is_title_screen = True
                        is_game_over = False
                        is_confirm_save_game_over = False
                    elif no_rect and no_rect.collidepoint(mouse_pos):
                        reset_game(full_reset=True)
                        is_title_screen = True
                        is_game_over = False
                        is_confirm_save_game_over = False
                    elif cancel_rect and cancel_rect.collidepoint(mouse_pos):
                        is_confirm_save_game_over = False
                else:
                    restart_rect, quit_rect = render_game_over()
                    if restart_rect.collidepoint(mouse_pos):
                        reset_game(full_reset=False)
                        is_game_over = False
                    elif quit_rect.collidepoint(mouse_pos):
                        is_confirm_save_game_over = True

            # Win Game: Handles restart or quit
            elif is_game_won:
                restart_rect, quit_rect = render_win()
                if restart_rect.collidepoint(mouse_pos):
                    reset_game(full_reset=True)
                elif quit_rect.collidepoint(mouse_pos):
                    checkpoint_manager.save_game()
                    reset_game(full_reset=False)
                    is_title_screen = True

            # Skip Story
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

            # Gameplay: Toggles pause
            elif not (is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out):
                pause_rect = pygame.Rect(*PAUSE_BUTTON_POS, *PAUSE_BUTTON_SIZE)
                if pause_rect.collidepoint(mouse_pos) and not is_paused:
                    is_paused = True
                    if start_timer is not None and last_pause_start is None:
                        last_pause_start = pygame.time.get_ticks()

                # Pause Menu: Handles pause options
                elif is_paused:
                    if is_confirm_save:
                        yes_rect, no_rect, cancel_rect = render_confirm_save("Do you want to save?", show_cancel=True)
                        if yes_rect and yes_rect.collidepoint(mouse_pos):
                            checkpoint_manager.save_game()
                            reset_game(full_reset=False)
                            is_title_screen = True
                            is_paused = False
                            is_confirm_save = False
                        elif no_rect and no_rect.collidepoint(mouse_pos):
                            reset_game(full_reset=True)
                            is_title_screen = True
                            is_paused = False
                            is_confirm_save = False
                        elif cancel_rect and cancel_rect.collidepoint(mouse_pos):
                            is_confirm_save = False
                    else:
                        resume_rect, quit_rect = render_pause_menu()
                        if resume_rect.collidepoint(mouse_pos):
                            if last_pause_start is not None:
                                paused_time += pygame.time.get_ticks() - last_pause_start
                            last_pause_start = None
                            is_paused = False
                        elif quit_rect.collidepoint(mouse_pos):
                            is_confirm_save = True

        # Keyboard Input: Processes key presses
        elif event.type == pygame.KEYDOWN:

            # Title Screen Keys: Navigates title
            if is_title_screen:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    is_title_screen = False
                    is_game_select_screen = True
                elif event.key == pygame.K_q:
                    running = False

            # Select Keys: Chooses mode
            elif is_game_select_screen:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if os.path.exists(SAVE_FILE):
                        is_game_select_screen = False
                        is_new_game_confirm = True
                    else:
                        is_game_select_screen = False
                        is_new_game_options = True
                elif event.key == pygame.K_r:
                    if os.path.exists(SAVE_FILE):
                        is_game_select_screen = False
                        is_resume_confirm = True
                    else:
                        reset_game(full_reset=True)
                        is_game_select_screen = False
                        is_message_screen = True
                        message_timer = pygame.time.get_ticks()
                elif event.key == pygame.K_BACKSPACE:
                    is_game_select_screen = False
                    is_title_screen = True

            # Confirm Keys: Confirms resume
            elif is_resume_confirm:
                yes_rect, no_rect, _ = render_confirm_save("Continue game?")
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    reset_game(full_reset=False)
                    is_resume_confirm = False
                    is_message_screen = True
                    message_timer = pygame.time.get_ticks()
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    is_resume_confirm = False
                    is_game_select_screen = True

            # Confirm Keys: Confirms save deletion
            elif is_new_game_confirm:
                yes_rect, no_rect, _ = render_confirm_save("Erase existing save?")
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    if delete_save_file():
                        is_new_game_confirm = False
                        is_new_game_options = True
                    else:
                        print("Failed to erase save file")
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    is_new_game_confirm = False
                    is_game_select_screen = True

            # Options Keys: Selects level
            elif is_new_game_options:
                buttons, back_rect = render_new_game_options()
                if event.key == pygame.K_BACKSPACE:
                    is_new_game_options = False
                    is_game_select_screen = True
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    for i, button in enumerate(buttons):
                        if button.collidepoint(pygame.mouse.get_pos()):
                            reset_game(full_reset=True, level=i + 1)
                            is_new_game_options = False
                            is_message_screen = True
                            message_timer = pygame.time.get_ticks()
                            break

            # Message Keys: Advance Story
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

            # Game Over Keys: Restarts or quits
            elif is_game_over:
                if event.key == pygame.K_r:
                    reset_game(full_reset=False)
                    is_game_over = False
                elif event.key == pygame.K_q:
                    is_confirm_save_game_over = True

            # Win Game Keys: Restarts or quits
            elif is_game_won:
                if event.key == pygame.K_r:
                    reset_game(full_reset=True)
                elif event.key == pygame.K_q:
                    checkpoint_manager.save_game()
                    reset_game(full_reset=False)
                    is_title_screen = True

            # Gameplay Keys: Controls player
            elif not is_paused:

                # Interactable Objects: Blaster
                if event.key == pygame.K_e:
                    player_rect = pygame.Rect(player_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT)
                    if blaster and player_rect.colliderect(blaster.rect):
                        show_speech_bubble = not show_speech_bubble
                        if not show_speech_bubble:
                            pickup_message = "Blaster Acquired!"
                            pickup_message_timer = pygame.time.get_ticks()
                            is_blaster_acquired = True
                            if current_level in level_data and level_data[current_level]["breakable_index"] < len(platforms):
                                is_platform_breaking = True
                                platform_break_timer = pygame.time.get_ticks()
                            blaster = None
                            if show_interact_hint and level_data[current_level]["hints"]["interact"]:
                                show_interact_hint = False
                                interact_hint_shown = True

                # Player Jump
                elif event.key == pygame.K_SPACE and not is_jumping:
                    player_velocity_y = PLAYER_JUMP
                    is_jumping = True
                    show_jump_hint = False
                    jump_hint_shown = True
                    if current_level == 1 and not alien_hint_shown and level_data[current_level]["hints"]["alien"]:
                        show_alien_hint = True

                # Pause Game: Toggles pause
                elif event.key == pygame.K_p and not (is_game_over or is_game_won):
                    is_paused = True
                    if start_timer is not None and last_pause_start is None:
                        last_pause_start = pygame.time.get_ticks()

            # Pause Menu Keys: Resumes or quits
            elif is_paused:
                if event.key == pygame.K_p:
                    if last_pause_start is not None:
                        paused_time += pygame.time.get_ticks() - last_pause_start
                    last_pause_start = None
                    is_paused = False
                elif event.key == pygame.K_q:
                    is_confirm_save = True

    # Processes game mechanics
    if not (is_game_over or is_game_won or is_title_screen or is_game_select_screen or is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out or is_paused or is_new_game_options or is_resume_confirm or is_new_game_confirm):
        
        # Player Moving left and right
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] and player_x > 0:
            player_x -= PLAYER_SPEED
            show_movement_hint = False
            if current_level == 1 and not show_movement_hint and not jump_hint_shown and level_data[current_level]["hints"]["jump"]:
                show_jump_hint = True
            if start_timer is None:
                start_timer = pygame.time.get_ticks()
        if keys[pygame.K_d] and player_x < WORLD_WIDTH - PLAYER_WIDTH:
            player_x += PLAYER_SPEED
            show_movement_hint = False
            if current_level == 1 and not show_movement_hint and not jump_hint_shown and level_data[current_level]["hints"]["jump"]:
                show_jump_hint = True
            if start_timer is None:
                start_timer = pygame.time.get_ticks()

        # Player Physics: gravity and collisions
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
                    hints = level_data[current_level]["hints"]
                    if current_level == 1:
                        if hints["jump"] and i == hints["jump"].get("platform_index") and not alien_hint_shown and hints["alien"]:
                            show_alien_hint = True
                            alien_hint_timer = pygame.time.get_ticks()
                        elif hints["alien"] and i == hints["alien"].get("platform_index") and show_alien_hint and not alien_hint_shown:
                            alien_hint_timer = pygame.time.get_ticks()
                            alien_hint_shown = True
                elif player_velocity_y < 0:
                    next_player_y = platform.rect.bottom
                    player_velocity_y = 0

        player_y = next_player_y

        # Collision: Places player on ground
        if current_level == 1 and not on_platform and player_y > HEIGHT - PLAYER_HEIGHT - 40 and player_x < HOLE_LEFT:
            player_y = HEIGHT - PLAYER_HEIGHT - 40
            player_velocity_y = 0
            is_jumping = False

        # Collision: Updates checkpoint status
        player_rect = pygame.Rect(player_x, player_y, PLAYER_WIDTH, PLAYER_HEIGHT)
        for checkpoint in checkpoint_manager.checkpoints:
            if checkpoint["id"].startswith(str(current_level)):
                checkpoint_rect = pygame.Rect(checkpoint["x"], checkpoint["y"], checkpoint["width"], checkpoint["height"])
                if not checkpoint["reached"] and player_rect.colliderect(checkpoint_rect):
                    print(f"Player collided with checkpoint {checkpoint['id']} at ({checkpoint['x']}, {checkpoint['y']}) with player at ({player_x}, {player_y})")
                    checkpoint_manager.update_checkpoint(checkpoint["id"], True, player_x=player_x, player_y=player_y)
                    checkpoint_message = f"Checkpoint {checkpoint['id']} Reached!"
                    checkpoint_message_timer = pygame.time.get_ticks()
                    break

        # Camera Movement: Tracks player position
        camera_x = max(0, min(player_x - WIDTH // 2 + PLAYER_WIDTH // 2, WORLD_WIDTH - WIDTH))

        # Update Enemies: Moves enemies and checks collisions
        for enemy in enemies:
            enemy.update(player_x, PLAYER_WIDTH, platforms, camera_x)
            if player_rect.colliderect(enemy.rect):
                is_game_over = True

        # Check Win/Lose conditions
        if player_y > HEIGHT:
            if player_x >= HOLE_LEFT and is_blaster_acquired:
                is_game_won = True
                if end_timer is None:
                    end_timer = pygame.time.get_ticks()
            else:
                is_game_over = True

        # Controls hints visibility
        if show_alien_hint and alien_hint_timer > 0:
            current_time = pygame.time.get_ticks()
            if current_time - alien_hint_timer >= ALIEN_HINT_DURATION:
                show_alien_hint = False
                if current_level == 1 and not interact_hint_shown and level_data[current_level]["hints"]["interact"]:
                    show_interact_hint = True

        # Removes breakable platform
        if is_platform_breaking and pygame.time.get_ticks() - platform_break_timer > PLATFORM_BREAK_DELAY:
            if current_level in level_data and level_data[current_level]["breakable_index"] < len(platforms):
                platforms.pop(level_data[current_level]["breakable_index"])
            is_platform_breaking = False

    # Manages story sequence
    if is_message_fade_out:
        current_time = pygame.time.get_ticks()
        if current_time - message_timer >= FADE_OUT_DURATION:
            is_message_fade_out = False
            is_message_screen = False
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

    # Render Scene: Draws current screen
    if is_title_screen:
        render_title()
    elif is_game_select_screen:
        render_game_select()
    elif is_resume_confirm:
        render_confirm_save("Continue game?")
    elif is_new_game_confirm:
        render_confirm_save("Erase existing save?")
    elif is_new_game_options:
        render_new_game_options()
    elif is_message_screen or is_message_fade_out or is_second_message or is_second_message_fade_out or is_third_message or is_third_message_fade_out or is_fourth_message or is_fourth_message_fade_out:
        render_message()
        render_skip_button()
    elif is_game_over:
        if is_confirm_save_game_over:
            render_confirm_save("Do you want to save?", show_cancel=True)
        else:
            render_game_over()
    elif is_game_won:
        render_win()
    else:
        render_game()
        render_pause_button()
        if is_paused:
            if is_confirm_save:
                render_confirm_save("Do you want to save?", show_cancel=True)
            else:
                render_pause_menu()

    # Update Display: Refreshes screen
    pygame.display.flip()
    clock.tick(60)

# Closes game
checkpoint_manager.close()
pygame.quit()
sys.exit()
