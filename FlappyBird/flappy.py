import random
import pygame
import os
import math

# --- Global Constants ---
BASE_WIDTH = 400
BASE_HEIGHT = 600
SCREEN_WIDTH = BASE_WIDTH
SCREEN_HEIGHT = BASE_HEIGHT
GROUND_HEIGHT = 50
PIPE_WIDTH = 70
PIPE_CAP_HEIGHT = 30
BIRD_START_X = 50
FPS = 60

# --- Colors ---
COLOR_SKY = (20, 20, 40)
COLOR_MOON = (200, 200, 220)
COLOR_BUILDING = (10, 10, 25)
COLOR_PIPE_DARK = (0, 168, 0)
COLOR_PIPE_LIGHT = (80, 208, 0)
COLOR_PIPE_SHADOW = (0, 80, 0)
COLOR_OUTLINE = (0, 0, 0)
COLOR_GROUND = (50, 50, 50)
COLOR_GROUND_TOP = (0, 255, 150)

# --- UI Colors (Apple Style) ---
COLOR_BUTTON_BG = (255, 255, 255, 220) 
COLOR_BUTTON_HOVER = (255, 255, 255, 255)
COLOR_TEXT_DARK = (40, 40, 40)

# --- Difficulty Defaults ---
DIFFICULTY = {
    "EASY": {"gap": 200, "speed": 3, "gravity": 0.4, "flap": -7},
    "MEDIUM": {"gap": 170, "speed": 4, "gravity": 0.45, "flap": -7.5},
    "HARD": {"gap": 140, "speed": 5, "gravity": 0.55, "flap": -8.5},
    "CUSTOM": {"gap": 170, "speed": 4, "gravity": 0.45, "flap": -7.5} # Default custom
}

HITBOX_SHRINK_X = 32
HITBOX_SHRINK_Y = 20

pygame.init()
pygame.mixer.init()

# --- Fullscreen Support ---
is_fullscreen = False
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
game_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))  # Render game at base resolution
pygame.display.set_caption("Flappy Bird: Custom Edition")
clock = pygame.time.Clock()

def toggle_fullscreen():
    global screen, is_fullscreen, SCREEN_WIDTH, SCREEN_HEIGHT
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        info = pygame.display.Info()
        SCREEN_WIDTH = info.current_w
        SCREEN_HEIGHT = info.current_h
    else:
        SCREEN_WIDTH = BASE_WIDTH
        SCREEN_HEIGHT = BASE_HEIGHT
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

def get_scale_and_offset():
    """Calculate scale factor and offset to center the game on screen"""
    scale_x = SCREEN_WIDTH / BASE_WIDTH
    scale_y = SCREEN_HEIGHT / BASE_HEIGHT
    scale = min(scale_x, scale_y)  # Maintain aspect ratio
    offset_x = (SCREEN_WIDTH - BASE_WIDTH * scale) // 2
    offset_y = (SCREEN_HEIGHT - BASE_HEIGHT * scale) // 2
    return scale, offset_x, offset_y

def scale_mouse_pos(pos):
    """Convert screen mouse position to game coordinates"""
    scale, offset_x, offset_y = get_scale_and_offset()
    return ((pos[0] - offset_x) / scale, (pos[1] - offset_y) / scale)

# Fonts
try:
    ui_font = pygame.font.SysFont("arial", 25, bold=True)
    title_font = pygame.font.SysFont("arial", 50, bold=True)
    score_font = pygame.font.SysFont("arial", 40, bold=True)
    small_label_font = pygame.font.SysFont("arial", 20, bold=True)
except:
    ui_font = pygame.font.Font(None, 30)
    title_font = pygame.font.Font(None, 60)
    score_font = pygame.font.Font(None, 50)
    small_label_font = pygame.font.Font(None, 25)

# --- ASSETS ---
def load_assets():
    assets = {}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    def get_path(filename): return os.path.join(script_dir, filename)

    try:
        bird_img = pygame.image.load(get_path("flappy.png")).convert_alpha()
        img_w = bird_img.get_width()
        img_h = bird_img.get_height()
        aspect_ratio = img_w / img_h
        target_width = 50 
        target_height = int(target_width / aspect_ratio)
        assets['bird'] = pygame.transform.scale(bird_img, (target_width, target_height))
        
        assets['flap'] = pygame.mixer.Sound(get_path("flapping.wav"))
        assets['point'] = pygame.mixer.Sound(get_path("point.wav"))
        assets['hit'] = pygame.mixer.Sound(get_path("hit.wav"))
        assets['die'] = pygame.mixer.Sound(get_path("hit.wav")) 
    except Exception as e:
        print(f"Asset Warning: {e}")
        bg = pygame.Surface((50, 36))
        bg.fill((255, 255, 0))
        assets['bird'] = bg
        assets['flap'] = None; assets['point'] = None; assets['hit'] = None; assets['die'] = None
    return assets

assets = load_assets()

# --- DRAWING HELPERS ---
def draw_mario_pipe(surface, x, y, width, height, is_top_pipe):
    body_rect = pygame.Rect(x + 4, y, width - 8, height)
    if is_top_pipe:
        body_rect = pygame.Rect(x + 4, 0, width - 8, height - PIPE_CAP_HEIGHT)
    else:
        body_rect = pygame.Rect(x + 4, y + PIPE_CAP_HEIGHT, width - 8, height - PIPE_CAP_HEIGHT)
        
    pygame.draw.rect(surface, COLOR_PIPE_DARK, body_rect)
    pygame.draw.rect(surface, COLOR_PIPE_LIGHT, (body_rect.x + 4, body_rect.y, 8, body_rect.height)) 
    pygame.draw.rect(surface, COLOR_PIPE_SHADOW, (body_rect.right - 10, body_rect.y, 6, body_rect.height))
    pygame.draw.rect(surface, COLOR_OUTLINE, body_rect, 2)

    cap_y = height - PIPE_CAP_HEIGHT if is_top_pipe else y
    cap_rect = pygame.Rect(x, cap_y, width, PIPE_CAP_HEIGHT)
    pygame.draw.rect(surface, COLOR_PIPE_DARK, cap_rect)
    pygame.draw.rect(surface, COLOR_PIPE_LIGHT, (cap_rect.x + 4, cap_rect.y, 8, cap_rect.height))
    pygame.draw.rect(surface, COLOR_PIPE_LIGHT, (cap_rect.x + 16, cap_rect.y, 4, cap_rect.height))
    pygame.draw.rect(surface, COLOR_PIPE_SHADOW, (cap_rect.right - 10, cap_rect.y, 6, cap_rect.height))
    pygame.draw.rect(surface, COLOR_OUTLINE, cap_rect, 2)

# --- CLASSES ---

class SmoothButton:
    def __init__(self, text, center_x, center_y, width, height, action_key):
        self.text = text
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (center_x, center_y)
        self.original_center = (center_x, center_y)
        self.action_key = action_key
        self.scale = 1.0
        self.target_scale = 1.0
        self.hovered = False
        self.visible = True 
        
    def update(self, mouse_pos):
        if not self.visible: return
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered: self.target_scale = 1.15
        else: self.target_scale = 1.0
        self.scale += (self.target_scale - self.scale) * 0.2

    def draw(self, surface):
        if not self.visible: return
        w = int(self.rect.width * self.scale)
        h = int(self.rect.height * self.scale)
        scaled_rect = pygame.Rect(0, 0, w, h)
        scaled_rect.center = self.original_center
        
        shadow_rect = scaled_rect.copy()
        shadow_rect.y += 4
        pygame.draw.rect(surface, (0, 0, 0, 100), shadow_rect, border_radius=15)
        
        color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON_BG
        shape_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(shape_surf, color, (0, 0, w, h), border_radius=15)
        surface.blit(shape_surf, scaled_rect.topleft)
        
        pygame.draw.rect(surface, (255, 255, 255), scaled_rect, 2, border_radius=15)
        text_surf = ui_font.render(self.text, True, COLOR_TEXT_DARK)
        text_rect = text_surf.get_rect(center=scaled_rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if not self.visible: return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered: return True
        return False

class Bird:
    def __init__(self, settings):
        self.x = BIRD_START_X
        self.y = SCREEN_HEIGHT // 2
        self.velocity = 0
        self.image = assets['bird']
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.angle = 0
        self.gravity = settings["gravity"]
        self.flap_strength = settings["flap"]
        self.hover_timer = 0
    
    def flap(self):
        self.velocity = self.flap_strength
        if assets['flap']: assets['flap'].play()
        
    def update(self):
        self.velocity += self.gravity
        if self.velocity > 15: self.velocity = 15 
        self.y += self.velocity
        
        if self.velocity < 0: self.angle = 20
        else:
            if self.angle > -90: self.angle -= 3 
        self.rect.centery = int(self.y)

    def update_falling(self):
        self.velocity += self.gravity
        if self.velocity > 15: self.velocity = 15
        self.y += self.velocity
        self.angle -= 5 
        if self.angle < -90: self.angle = -90
        self.rect.centery = int(self.y)

    def update_menu(self):
        self.hover_timer += 0.05
        self.y = (BASE_HEIGHT // 2 - 80) + math.sin(self.hover_timer) * 10
        self.rect.centery = int(self.y)
        self.angle = 0

    def draw(self):
        rotated_image = pygame.transform.rotate(self.image, self.angle)
        new_rect = rotated_image.get_rect(center=self.rect.center)
        game_surface.blit(rotated_image, new_rect.topleft)

class Pipe:
    def __init__(self, x, settings):
        self.x = x
        self.width = PIPE_WIDTH
        self.gap = settings["gap"]
        self.speed = settings["speed"]
        max_height = BASE_HEIGHT - GROUND_HEIGHT - self.gap - 50
        min_height = 80
        self.height = random.randint(min_height, max_height)
        self.passed = False

    def update(self):
        self.x -= self.speed

    def draw(self):
        draw_mario_pipe(game_surface, self.x, 0, self.width, self.height, is_top_pipe=True)
        bottom_y = self.height + self.gap
        bottom_h = BASE_HEIGHT - GROUND_HEIGHT - bottom_y
        draw_mario_pipe(game_surface, self.x, bottom_y, self.width, bottom_h, is_top_pipe=False)

class BackgroundManager:
    def __init__(self):
        self.bg_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
        self.x = 0
        self.speed = 0.5
        self.generate_city() 

    def generate_city(self):
        self.bg_surface.fill(COLOR_SKY)
        pygame.draw.circle(self.bg_surface, COLOR_MOON, (300, 100), 40)
        for _ in range(30):
            pygame.draw.circle(self.bg_surface, (255, 255, 255), 
                             (random.randint(0, BASE_WIDTH), random.randint(0, BASE_HEIGHT // 2)), 1)
        current_x = 0
        while current_x < BASE_WIDTH:
            w = random.randint(30, 80)
            h = random.randint(100, 300)
            rect = (current_x, BASE_HEIGHT - GROUND_HEIGHT - h, w, h + GROUND_HEIGHT)
            pygame.draw.rect(self.bg_surface, COLOR_BUILDING, rect)
            for win_y in range(rect[1] + 10, rect[1] + h, 20):
                if random.random() > 0.5:
                    win_x = current_x + random.randint(5, w - 10)
                    pygame.draw.rect(self.bg_surface, (255, 255, 100), (win_x, win_y, 5, 10))
            current_x += w

    def update(self):
        self.x -= self.speed
        if self.x <= -BASE_WIDTH:
            self.x = 0

    def draw(self):
        game_surface.blit(self.bg_surface, (self.x, 0))
        game_surface.blit(self.bg_surface, (self.x + BASE_WIDTH, 0))

class Ground:
    def __init__(self):
        self.y = BASE_HEIGHT - GROUND_HEIGHT
        self.x = 0
        self.speed = 3

    def update(self, speed_override=None):
        s = speed_override if speed_override else self.speed
        self.x -= s
        if self.x <= -20: self.x = 0

    def draw(self):
        pygame.draw.rect(game_surface, COLOR_GROUND, (0, self.y, BASE_WIDTH, GROUND_HEIGHT))
        pygame.draw.rect(game_surface, COLOR_GROUND_TOP, (0, self.y, BASE_WIDTH, 5))
        for i in range(0, BASE_WIDTH + 20, 20):
            pygame.draw.line(game_surface, (30, 30, 30), (self.x + i, self.y), (self.x + i - 10, BASE_HEIGHT), 2)

# --- HELPER: Draw settings row ---
def draw_setting_row(surface, label, value, y_pos):
    # Label
    lbl_surf = small_label_font.render(label, True, (255, 255, 255))
    surface.blit(lbl_surf, (50, y_pos - 10))
    # Value
    val_surf = ui_font.render(str(round(value, 2)), True, (255, 255, 0))
    surface.blit(val_surf, (BASE_WIDTH//2 - 10, y_pos - 10))

# --- MAIN LOOP ---
def main():
    global game_surface
    state = "MENU" # MENU, CUSTOM_MENU, PLAYING, FALLING, GAMEOVER
    current_difficulty = "MEDIUM"
    
    bg_manager = BackgroundManager()
    ground = Ground()
    bird = Bird(DIFFICULTY["MEDIUM"]) 
    pipes = []
    score = 0
    dead_sound_played = False
    
    # --- MENUS ---
    # Main Menu (use BASE dimensions for positioning)
    btn_easy = SmoothButton("Easy", BASE_WIDTH//2, 280, 160, 45, "EASY")
    btn_med = SmoothButton("Medium", BASE_WIDTH//2, 340, 160, 45, "MEDIUM")
    btn_hard = SmoothButton("Hard", BASE_WIDTH//2, 400, 160, 45, "HARD")
    btn_custom = SmoothButton("Custom", BASE_WIDTH//2, 460, 160, 45, "CUSTOM_MENU")
    main_menu_btns = [btn_easy, btn_med, btn_hard, btn_custom]
    
    # Custom Menu
    btn_spd_dec = SmoothButton("-", 140, 150, 40, 40, "SPD_DEC")
    btn_spd_inc = SmoothButton("+", 260, 150, 40, 40, "SPD_INC")
    
    btn_gap_dec = SmoothButton("-", 140, 250, 40, 40, "GAP_DEC")
    btn_gap_inc = SmoothButton("+", 260, 250, 40, 40, "GAP_INC")
    
    btn_grv_dec = SmoothButton("-", 140, 350, 40, 40, "GRV_DEC")
    btn_grv_inc = SmoothButton("+", 260, 350, 40, 40, "GRV_INC")
    
    btn_play_custom = SmoothButton("Play Custom", BASE_WIDTH//2, 480, 200, 50, "PLAY_CUSTOM")
    btn_back = SmoothButton("Back", 50, 50, 80, 40, "BACK")
    
    custom_menu_btns = [btn_spd_dec, btn_spd_inc, btn_gap_dec, btn_gap_inc, 
                        btn_grv_dec, btn_grv_inc, btn_play_custom, btn_back]

    # Game Over
    btn_restart = SmoothButton("Restart", BASE_WIDTH//2, 330, 160, 50, "RESTART")
    btn_menu = SmoothButton("Menu", BASE_WIDTH//2, 400, 160, 50, "MENU")
    game_over_btns = [btn_restart, btn_menu]

    running = True 
    while running:
        clock.tick(FPS)
        # Scale mouse position for fullscreen
        raw_mouse_pos = pygame.mouse.get_pos()
        mouse_pos = scale_mouse_pos(raw_mouse_pos)
        
        # --- EVENT HANDLING ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False 
            
            # F11 to toggle fullscreen, ESC to exit fullscreen
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE and is_fullscreen:
                    toggle_fullscreen()
            
            if state == "MENU":
                for btn in main_menu_btns:
                    if btn.is_clicked(event):
                        if btn.action_key == "CUSTOM_MENU":
                            state = "CUSTOM_MENU"
                        else:
                            current_difficulty = btn.action_key
                            state = "PLAYING"
                            settings = DIFFICULTY[current_difficulty]
                            bird = Bird(settings)
                            pipes = [Pipe(BASE_WIDTH + 100, settings)]
                            ground.speed = settings["speed"]
                            score = 0
            
            elif state == "CUSTOM_MENU":
                for btn in custom_menu_btns:
                    if btn.is_clicked(event):
                        cust = DIFFICULTY["CUSTOM"]
                        k = btn.action_key
                        
                        if k == "SPD_INC": cust["speed"] = min(15, cust["speed"] + 1)
                        elif k == "SPD_DEC": cust["speed"] = max(1, cust["speed"] - 1)
                        elif k == "GAP_INC": cust["gap"] = min(300, cust["gap"] + 10)
                        elif k == "GAP_DEC": cust["gap"] = max(80, cust["gap"] - 10)
                        elif k == "GRV_INC": cust["gravity"] = min(1.5, round(cust["gravity"] + 0.05, 2))
                        elif k == "GRV_DEC": cust["gravity"] = max(0.1, round(cust["gravity"] - 0.05, 2))
                        elif k == "PLAY_CUSTOM":
                            current_difficulty = "CUSTOM"
                            state = "PLAYING"
                            settings = DIFFICULTY["CUSTOM"]
                            bird = Bird(settings)
                            pipes = [Pipe(BASE_WIDTH + 100, settings)]
                            ground.speed = settings["speed"]
                            score = 0
                        elif k == "BACK":
                            state = "MENU"

            elif state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        bird.flap()
            
            elif state == "GAMEOVER":
                for btn in game_over_btns:
                    if btn.is_clicked(event):
                        if btn.action_key == "RESTART":
                            state = "PLAYING"
                            settings = DIFFICULTY[current_difficulty]
                            bird = Bird(settings)
                            pipes = [Pipe(BASE_WIDTH + 100, settings)]
                            score = 0
                            dead_sound_played = False
                        elif btn.action_key == "MENU":
                            state = "MENU"
                            dead_sound_played = False
                
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    state = "PLAYING"
                    settings = DIFFICULTY[current_difficulty]
                    bird = Bird(settings)
                    pipes = [Pipe(BASE_WIDTH + 100, settings)]
                    score = 0
                    dead_sound_played = False

        if not running: break

        # --- DRAWING (render to game_surface first) ---
        bg_manager.draw()
        
        if state == "MENU":
            bg_manager.update()
            ground.update(speed_override=2)
            bird.update_menu()
            ground.draw()
            bird.draw()
            
            t_surf = title_font.render("FLAPPY BIRD", True, (255, 255, 255))
            t_rect = t_surf.get_rect(center=(BASE_WIDTH//2, 100))
            game_surface.blit(t_surf, t_rect)
            
            for btn in main_menu_btns:
                btn.update(mouse_pos)
                btn.draw(game_surface)

        elif state == "CUSTOM_MENU":
            # Static background for custom menu
            ground.draw()
            
            t_surf = ui_font.render("CUSTOM SETTINGS", True, (255, 255, 255))
            game_surface.blit(t_surf, (BASE_WIDTH//2 - 100, 30))
            
            # Draw Values and Labels
            cust = DIFFICULTY["CUSTOM"]
            draw_setting_row(game_surface, "Speed", cust["speed"], 150)
            draw_setting_row(game_surface, "Pipe Gap", cust["gap"], 250)
            draw_setting_row(game_surface, "Gravity", cust["gravity"], 350)

            for btn in custom_menu_btns:
                btn.update(mouse_pos)
                btn.draw(game_surface)

        elif state == "PLAYING":
            bg_manager.update()
            bird.update()
            ground.update()
            
            if pipes[-1].x < BASE_WIDTH - 200:
                pipes.append(Pipe(BASE_WIDTH, DIFFICULTY[current_difficulty]))

            for pipe in pipes:
                pipe.update()
                pipe.draw()
                
                hitbox = bird.rect.inflate(-HITBOX_SHRINK_X, -HITBOX_SHRINK_Y)
                if hitbox.colliderect(pygame.Rect(pipe.x + 4, 0, pipe.width - 8, pipe.height)) or \
                   hitbox.colliderect(pygame.Rect(pipe.x + 4, pipe.height + pipe.gap, pipe.width - 8, BASE_HEIGHT)):
                    state = "FALLING"
                    if assets['hit']: assets['hit'].play()

                if not pipe.passed and pipe.x < bird.x:
                    score += 1
                    pipe.passed = True
                    if assets['point']: assets['point'].play()

            if bird.y >= BASE_HEIGHT - GROUND_HEIGHT - 10:
                state = "GAMEOVER"
                if assets['hit']: assets['hit'].play()

            if bird.y < 0: bird.y = 0
            if pipes[0].x < -100: pipes.pop(0)
                
            bird.draw()
            ground.draw()
            
            s_surf = score_font.render(str(score), True, (255, 255, 255))
            game_surface.blit(s_surf, (BASE_WIDTH//2 - 10, 50))
            
        elif state == "FALLING":
            bird.update_falling()
            for pipe in pipes: pipe.draw()
            ground.draw()
            bird.draw()
            if bird.y >= BASE_HEIGHT - GROUND_HEIGHT - 10:
                state = "GAMEOVER"
            
        elif state == "GAMEOVER":
            for pipe in pipes: pipe.draw()
            ground.draw()
            bird.draw()
            
            overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            game_surface.blit(overlay, (0,0))
            
            over_surf = title_font.render("GAME OVER", True, (255, 80, 80))
            over_rect = over_surf.get_rect(center=(BASE_WIDTH//2, 150))
            game_surface.blit(over_surf, over_rect)
            
            score_surf = score_font.render(f"Score: {score}", True, (255, 255, 255))
            score_rect = score_surf.get_rect(center=(BASE_WIDTH//2, 220))
            game_surface.blit(score_surf, score_rect)
            
            for btn in game_over_btns:
                btn.visible = True
                btn.update(mouse_pos)
                btn.draw(game_surface)

        # Scale game_surface to screen (with letterboxing for fullscreen)
        scale, offset_x, offset_y = get_scale_and_offset()
        screen.fill((0, 0, 0))  # Black letterbox bars
        scaled_surface = pygame.transform.scale(game_surface, (int(BASE_WIDTH * scale), int(BASE_HEIGHT * scale)))
        screen.blit(scaled_surface, (offset_x, offset_y))
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()