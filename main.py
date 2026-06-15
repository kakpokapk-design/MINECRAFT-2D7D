import pygame
import random
import math
import sys
import os
import array
import pickle

os.environ['SDL_VIDEO_EXTERNAL_CONTEXT'] = '1'

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
pygame.mixer.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 960
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.NOFRAME | pygame.SCALED)
clock = pygame.time.Clock()

TILE_SIZE = 32
GRAVITY = 0.65
JUMP_FORCE = -12.5

SKY_BLUE = (50, 160, 240)
CAVE_BLACK = (20, 16, 24)
WHITE = (255, 255, 255)
UI_BG = (35, 35, 40, 220)

sound_enabled = True
WORLDS_LIST_FILE = "worlds_manifest.dat"

# --- ПРОЦЕДУРНАЯ МУЗЫКА ---
def generate_sine_wave(frequency, duration=1.5, volume=0.15):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * num_samples)
    for i in range(num_samples):
        envelope = (num_samples - i) / num_samples
        t = float(i) / sample_rate
        value = int(math.sin(t * frequency * 2 * math.pi) * 32767 * volume * envelope)
        buf[i] = value
    return pygame.mixer.Sound(buffer=buf)

SURFACE_NOTES = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
CAVE_NOTES = [130.81, 146.83, 155.56, 196.00, 220.00, 261.63]

class MinecraftMusicPlayer:
    def __init__(self): self.next_note_tick = 0
    def update(self, location):
        global sound_enabled
        if not sound_enabled: return
        now = pygame.time.get_ticks()
        if now > self.next_note_tick:
            freq = random.choice(SURFACE_NOTES if location == "surface" else CAVE_NOTES)
            sound = generate_sine_wave(freq, duration=2.0, volume=0.10)
            self.next_note_tick = now + random.randint(4000, 8000)
            sound.play()

music_player = MinecraftMusicPlayer()

# Текстуры мира и инструментов
def create_sharp_32_texture(color, details_color=None, style="block"):
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(color)
    if details_color:
        if style == "grass":
            pygame.draw.rect(surf, details_color, (0, 0, TILE_SIZE, 6))
            for i in range(0, TILE_SIZE, 4): pygame.draw.rect(surf, details_color, (i, 6, 2, random.randint(2, 4)))
        elif style == "dirt":
            for _ in range(6): pygame.draw.rect(surf, details_color, (random.randint(2, 28), random.randint(2, 28), 3, 3))
        elif style == "stone":
            for _ in range(5): pygame.draw.rect(surf, details_color, (random.randint(2, 26), random.randint(2, 26), random.randint(4, 8), 2))
        elif style == "wood":
            pygame.draw.rect(surf, details_color, (0, 0, TILE_SIZE, TILE_SIZE), 3)
            pygame.draw.line(surf, details_color, (8, 0), (8, TILE_SIZE), 2)
            pygame.draw.line(surf, details_color, (20, 0), (20, TILE_SIZE), 2)
    return surf

TEXTURES = {
    1: create_sharp_32_texture((40, 190, 60), (125, 80, 50), "grass"),
    2: create_sharp_32_texture((125, 80, 50), (90, 60, 40), "dirt"),
    3: create_sharp_32_texture((110, 110, 115), (80, 80, 85), "stone"),
    4: create_sharp_32_texture((255, 150, 20), style="stone"),  # Руда
    5: create_sharp_32_texture((150, 105, 65), (100, 70, 40), "wood"),  # Доски деревни
}

# Генерация иконок инструментов
def create_tool_icon(color_part, t_type):
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.line(surf, (110, 70, 30), (4, 28), (24, 8), 3) # Рукоятка
    if t_type == "pickaxe":
        pygame.draw.arc(surf, color_part, (12, 0, 20, 20), 0, 3.14, 5)
    elif t_type == "axe":
        pygame.draw.rect(surf, color_part, (18, 2, 10, 10), border_radius=2)
    elif t_type == "sword":
        surf.fill((0,0,0,0))
        pygame.draw.line(surf, (110, 70, 30), (6, 26), (12, 20), 4) # Ручка меча
        pygame.draw.line(surf, (180, 180, 185), (10, 22), (28, 4), 5) # Лезвие
    return surf

TOOL_TEXTURES = {
    "pickaxe": create_tool_icon((200, 200, 205), "pickaxe"),
    "axe": create_tool_icon((200, 200, 205), "axe"),
    "sword": create_tool_icon((200, 200, 205), "sword"),
}

# Персонаж в стиле Terraria
class TerrariaPlayer:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 24, 40)
        self.vx = 0; self.vy = 0
        self.on_ground = False; self.facing_right = True
        self.walk_cycle = 0.0; self.mine_angle = 0.0
        self.c_skin = (235, 180, 145); self.c_hair = (45, 32, 25)
        self.c_shirt = (210, 40, 40); self.c_pants = (40, 60, 150); self.c_shoe = (25, 25, 30)

    def draw(self, surf, camera_x, camera_y, is_mining, active_item):
        px = self.rect.x - camera_x; py = self.rect.y - camera_y
        left_leg_offset = right_leg_offset = 0
        if abs(self.vx) > 0.1 and self.on_ground:
            self.walk_cycle += 0.25
            left_leg_offset = math.sin(self.walk_cycle) * 5
            right_leg_offset = -math.sin(self.walk_cycle) * 5

        pygame.draw.rect(surf, self.c_pants, (px + 4, py + 26, 6, 10))
        pygame.draw.rect(surf, self.c_shoe, (px + 3 + (left_leg_offset if self.facing_right else -left_leg_offset), py + 34, 7, 3))
        pygame.draw.rect(surf, self.c_shirt, (px + 4, py + 14, 14, 13))
        pygame.draw.rect(surf, self.c_pants, (px + 12, py + 26, 6, 10))
        pygame.draw.rect(surf, self.c_shoe, (px + 11 + (right_leg_offset if self.facing_right else -right_leg_offset), py + 34, 7, 3))
        pygame.draw.rect(surf, self.c_hair, (px + 4, py, 14, 5))
        pygame.draw.rect(surf, self.c_skin, (px + 4, py + 4, 14, 10))
        
        if self.facing_right:
            pygame.draw.rect(surf, (255, 255, 255), (px + 12, py + 6, 4, 4))
            pygame.draw.rect(surf, (30, 110, 220), (px + 14, py + 6, 2, 4))
        else:
            pygame.draw.rect(surf, (255, 255, 255), (px + 6, py + 6, 4, 4))
            pygame.draw.rect(surf, (30, 110, 220), (px + 6, py + 6, 2, 4))

        if is_mining:
            self.mine_angle += 0.38
            hand_x = px + 10 + math.cos(self.mine_angle) * 14
            hand_y = py + 20 + math.sin(self.mine_angle) * 14
            pygame.draw.line(surf, self.c_skin, (px + 10, py + 18), (hand_x, hand_y), 5)
            
            if active_item in TOOL_TEXTURES:
                t_surf = pygame.transform.rotate(TOOL_TEXTURES[active_item], -math.degrees(self.mine_angle))
                surf.blit(t_surf, (hand_x - 16, hand_y - 16))
            elif isinstance(active_item, int) and active_item in TEXTURES:
                surf.blit(pygame.transform.scale(TEXTURES[active_item], (16,16)), (hand_x - 8, hand_y - 8))
        else:
            pygame.draw.rect(surf, self.c_skin, (px + (8 if self.facing_right else 10), py + 16, 4, 10))
            if active_item in TOOL_TEXTURES:
                surf.blit(TOOL_TEXTURES[active_item], (px + (16 if self.facing_right else -16), py + 12))

class World:
    def __init__(self, name="MyWorld", w_type="Normal", mode="Survival", location="surface"):
        self.name = name
        self.w_type = w_type
        self.mode = mode 
        self.location = location
        self.width = 150; self.height = 45
        self.data = {}
        self.generate()

    def generate(self):
        self.data.clear()
        if self.location == "surface":
            for x in range(self.width):
                y_ground = 24 if self.w_type == "Flat" else 18 + int(math.sin(x * 0.14) * 5 + math.cos(x * 0.06) * 2)
                self.data[(x, y_ground)] = 1 
                for dy in range(y_ground + 1, y_ground + 6): self.data[(x, dy)] = 2 
                for dy in range(y_ground + 6, self.height): self.data[(x, dy)] = 3 
                if x % 12 == 0 and random.random() > 0.4 and self.w_type != "Flat":
                    self.data[(x, y_ground + 7)] = 4 
            
            if self.w_type != "Flat":
                self.spawn_village(25)
                self.spawn_village(80)
        else:
            for x in range(self.width):
                for y in range(self.height):
                    if y < 3 or y > self.height - 3: self.data[(x, y)] = 3
                    elif (math.sin(x * 0.22) * math.cos(y * 0.28) + math.sin(y * 0.12)) < 0.20: self.data[(x, y)] = 3

    def spawn_village(self, start_x):
        base_y = self.get_spawn_y_tile(start_x)
        if base_y > 5:
            for x in range(start_x, start_x + 8):
                for y in range(base_y - 5, base_y):
                    if x == start_x or x == start_x + 7 or y == base_y - 1:
                        self.data[(x, y)] = 3 
                    else:
                        self.data[(x, y)] = 0 
            for x in range(start_x - 1, start_x + 9):
                self.data[(x, base_y - 6)] = 5
            self.data[(start_x + 3, base_y - 1)] = 0
            self.data[(start_x + 3, base_y - 2)] = 0

    def get_block(self, x, y): return self.data.get((x, y), 0)
    def set_block(self, x, y, b_type):
        if 0 <= x < self.width and 0 <= y < self.height:
            if b_type == 0: self.data.pop((x, y), None)
            else: self.data[(x, y)] = b_type

    def get_spawn_y_tile(self, x_tile):
        for y in range(self.height):
            if self.get_block(x_tile, y) != 0: return y
        return 20

class NormalPig:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 44, 30)
        self.vx = random.choice([-1.2, 1.2])
        self.vy = 0; self.hp = 6
        self.walk_anim = 0.0

    def update(self, world):
        self.vy += GRAVITY
        if self.vy > 12: self.vy = 12
        self.rect.x += self.vx
        if self.collide_with_blocks(world, self.vx, 0): self.vx *= -1
        self.rect.y += self.vy
        self.collide_with_blocks(world, 0, self.vy)
        self.walk_anim += 0.2

    def collide_with_blocks(self, world, vx, vy):
        x1, x2 = int(self.rect.left // TILE_SIZE), int(self.rect.right // TILE_SIZE)
        y1, y2 = int(self.rect.top // TILE_SIZE), int(self.rect.bottom // TILE_SIZE)
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                if world.get_block(x, y) != 0:
                    br = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(br):
                        if vx > 0: self.rect.right = br.left
                        if vx < 0: self.rect.left = br.right
                        if vy > 0: self.rect.bottom = br.top; self.vy = 0
                        return True
        return False

    def draw(self, surf, cx, cy):
        px = self.rect.x - cx; py = self.rect.y - cy
        pig_color = (245, 145, 165)
        dark_pink = (220, 115, 140)
        
        leg_offset = math.sin(self.walk_anim) * 4
        pygame.draw.rect(surf, dark_pink, (px + 6, py + 20, 6, 10)) 
        pygame.draw.rect(surf, dark_pink, (px + 30 + leg_offset, py + 20, 6, 10)) 
        pygame.draw.rect(surf, pig_color, (px + 4, py + 4, 36, 18), border_radius=3)
        
        if self.vx > 0:
            pygame.draw.rect(surf, pig_color, (px + 30, py - 4, 14, 14), border_radius=2)
            pygame.draw.rect(surf, dark_pink, (px + 42, py + 2, 4, 6)) 
            pygame.draw.rect(surf, (30, 30, 30), (px + 38, py, 2, 3)) 
        else:
            pygame.draw.rect(surf, pig_color, (px, py - 4, 14, 14), border_radius=2)
            pygame.draw.rect(surf, dark_pink, (px - 2, py + 2, 4, 6)) 
            pygame.draw.rect(surf, (30, 30, 30), (px + 4, py, 2, 3)) 

class DropItem:
    def __init__(self, x, y, b_type):
        self.rect = pygame.Rect(x, y, 14, 14)
        self.b_type = b_type
        self.vy = -4; self.vx = random.uniform(-2, 2)
    def update(self, world):
        self.vy += GRAVITY
        self.rect.x += self.vx
        self.rect.y += self.vy
        cx = int(self.rect.centerx // TILE_SIZE)
        cy = int(self.rect.bottom // TILE_SIZE)
        if world.get_block(cx, cy) != 0:
            self.rect.bottom = cy * TILE_SIZE
            self.vy = 0; self.vx = 0

class TouchController:
    def __init__(self):
        self.btn_left = pygame.Rect(60, SCREEN_HEIGHT - 180, 150, 150)
        self.btn_right = pygame.Rect(260, SCREEN_HEIGHT - 180, 150, 150)
        self.btn_jump = pygame.Rect(SCREEN_WIDTH - 210, SCREEN_HEIGHT - 180, 160, 160)
        self.btn_mine = pygame.Rect(SCREEN_WIDTH - 210, SCREEN_HEIGHT - 370, 160, 150)
        self.btn_loc = pygame.Rect(SCREEN_WIDTH - 260, 30, 230, 85)
        self.btn_inv_toggle = pygame.Rect(40, 30, 140, 85)
        self.hotbar_rects = [pygame.Rect(SCREEN_WIDTH//2 - 240 + i * 95, SCREEN_HEIGHT - 110, 80, 80) for i in range(5)]

    def is_ui_click(self, x, y):
        if (self.btn_left.collidepoint(x, y) or self.btn_right.collidepoint(x, y) or 
            self.btn_jump.collidepoint(x, y) or self.btn_mine.collidepoint(x, y) or 
            self.btn_loc.collidepoint(x, y) or self.btn_inv_toggle.collidepoint(x, y)):
            return True
        for r in self.hotbar_rects:
            if r.collidepoint(x, y): return True
        return False

    def draw(self, surf, hotbar, active_idx, loc):
        pygame.draw.rect(surf, UI_BG, self.btn_left, border_radius=30)
        pygame.draw.rect(surf, UI_BG, self.btn_right, border_radius=30)
        pygame.draw.rect(surf, UI_BG, self.btn_jump, border_radius=80)
        pygame.draw.rect(surf, (160, 60, 60, 220), self.btn_mine, border_radius=30)
        pygame.draw.rect(surf, (80, 50, 120, 230), self.btn_loc, border_radius=20)
        pygame.draw.rect(surf, (50, 50, 55, 230), self.btn_inv_toggle, border_radius=20)

        f = pygame.font.SysFont(None, 40)
        surf.blit(f.render("INV", True, WHITE), (85, 58))
        surf.blit(f.render("JUMP", True, WHITE), (SCREEN_WIDTH - 170, SCREEN_HEIGHT - 125))
        surf.blit(f.render("MINE", True, WHITE), (SCREEN_WIDTH - 170, SCREEN_HEIGHT - 315))
        
        txt = "В ПЕЩЕРУ" if loc == "surface" else "НА ВЕРХ"
        surf.blit(pygame.font.SysFont(None, 34, bold=True).render(txt, True, WHITE), (SCREEN_WIDTH - 225, 58))

        for i, rect in enumerate(self.hotbar_rects):
            bg = (180, 180, 100) if active_idx == i else (40, 40, 45, 200)
            pygame.draw.rect(surf, bg, rect, border_radius=15)
            pygame.draw.rect(surf, WHITE, rect, 3, border_radius=15)
            if i < len(hotbar):
                item = hotbar[i]
                if item in TEXTURES:
                    surf.blit(pygame.transform.scale(TEXTURES[item], (52, 52)), (rect.x + 14, rect.y + 14))
                elif item in TOOL_TEXTURES:
                    surf.blit(pygame.transform.scale(TOOL_TEXTURES[item], (52, 52)), (rect.x + 14, rect.y + 14))

def show_full_inventory(inventory, hotbar, is_creative):
    in_inv = True
    selected_inv_slot = None
    grid_rects = []
    
    for row in range(4):
        for col in range(6):
            grid_rects.append((row * 6 + col, pygame.Rect(350 + col * 100, 250 + row * 100, 85, 85)))
    ctrl_hb_rects = [pygame.Rect(400 + i * 100, 720, 90, 90) for i in range(5)]

    if is_creative:
        inventory[0] = 1; inventory[1] = 2; inventory[2] = 3; inventory[3] = 4; inventory[4] = 5
        inventory[5] = "pickaxe"; inventory[6] = "axe"; inventory[7] = "sword"

    while in_inv:
        screen.fill((25, 25, 30))
        f = pygame.font.SysFont(None, 45)
        screen.blit(f.render("МЕНЮ ИНВЕНТАРЯ", True, WHITE), (500, 100))

        b_close = pygame.Rect(540, 850, 200, 65)
        pygame.draw.rect(screen, (180, 50, 50), b_close, border_radius=15)
        screen.blit(f.render("ЗАКРЫТЬ", True, WHITE), (565, 865))

        for idx, rect in grid_rects:
            bg_col = (100, 100, 140) if selected_inv_slot == idx else (50, 50, 55)
            pygame.draw.rect(screen, bg_col, rect, border_radius=10)
            pygame.draw.rect(screen, WHITE, rect, 2, border_radius=10)
            if idx < len(inventory):
                item = inventory[idx]
                if item in TEXTURES:
                    screen.blit(pygame.transform.scale(TEXTURES[item], (60, 60)), (rect.x+12, rect.y+12))
                elif item in TOOL_TEXTURES:
                    screen.blit(pygame.transform.scale(TOOL_TEXTURES[item], (60, 60)), (rect.x+12, rect.y+12))

        for i, rect in enumerate(ctrl_hb_rects):
            pygame.draw.rect(screen, (30, 35, 40), rect, border_radius=10)
            pygame.draw.rect(screen, WHITE, rect, 3, border_radius=10)
            if i < len(hotbar):
                hb_item = hotbar[i]
                if hb_item in TEXTURES: screen.blit(pygame.transform.scale(TEXTURES[hb_item], (64, 64)), (rect.x+13, rect.y+13))
                elif hb_item in TOOL_TEXTURES: screen.blit(pygame.transform.scale(TOOL_TEXTURES[hb_item], (64, 64)), (rect.x+13, rect.y+13))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.FINGERDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT)) if event.type == pygame.FINGERDOWN else event.pos
                if b_close.collidepoint(mx, my): in_inv = False
                for idx, rect in grid_rects:
                    if rect.collidepoint(mx, my) and idx < len(inventory) and inventory[idx] != 0: selected_inv_slot = idx
                for i, rect in enumerate(ctrl_hb_rects):
                    if rect.collidepoint(mx, my) and selected_inv_slot is not None and i < len(hotbar):
                        hotbar[i] = inventory[selected_inv_slot]
                        selected_inv_slot = None

        pygame.display.flip()
        clock.tick(30)

def get_worlds_manifest():
    if os.path.exists(WORLDS_LIST_FILE):
        try:
            with open(WORLDS_LIST_FILE, "rb") as f: return pickle.load(f)
        except: return []
    return []

def save_worlds_manifest(manifest):
    with open(WORLDS_LIST_FILE, "wb") as f: pickle.dump(manifest, f)

def save_world_to_disk(world, player, inventory, hotbar):
    data = {"name": world.name, "type": world.w_type, "mode": world.mode, "loc": world.location, "blocks": world.data, "px": player.rect.x, "py": player.rect.y, "inv": inventory, "hb": hotbar}
    with open(f"world_{world.name}.dat", "wb") as f: pickle.dump(data, f)

def load_world_from_disk(name):
    filename = f"world_{name}.dat"
    if os.path.exists(filename):
        try:
            with open(filename, "rb") as f: return pickle.load(f)
        except: return None
    return None

def worlds_menu():
    loop = True; f = pygame.font.SysFont(None, 40)
    current_mode_selection = "Survival"
    
    while loop:
        screen.fill((40, 45, 50))
        manifest = get_worlds_manifest()
        
        b_create = pygame.Rect(440, 40, 420, 75)
        pygame.draw.rect(screen, (30, 120, 60), b_create, border_radius=15)
        screen.blit(f.render(f"+ МИР ({'ВЫЖИВАНИЕ' if current_mode_selection=='Survival' else 'ТВОРЧЕСТВО'})", True, WHITE), (460, 62))
        
        b_toggle_mode = pygame.Rect(880, 40, 300, 75)
        pygame.draw.rect(screen, (70, 70, 150), b_toggle_mode, border_radius=15)
        screen.blit(f.render("ИЗМЕНИТЬ РЕЖИМ", True, WHITE), (905, 62))

        b_back = pygame.Rect(50, 40, 160, 65)
        pygame.draw.rect(screen, (100, 100, 105), b_back, border_radius=10)
        screen.blit(f.render("Назад", True, WHITE), (85, 58))

        world_buttons = []; del_buttons = []
        for i, w_meta in enumerate(manifest):
            w_rect = pygame.Rect(100, 180 + i * 90, 820, 70)
            d_rect = pygame.Rect(950, 180 + i * 90, 130, 70)
            pygame.draw.rect(screen, (60, 65, 75), w_rect, border_radius=10)
            pygame.draw.rect(screen, (160, 40, 40), d_rect, border_radius=10)
            
            w_mode_str = "Творческий" if w_meta.get('mode', 'Survival') == 'Creative' else 'Выживание'
            txt = f"Мир: {w_meta['name']} | Режим: {w_mode_str} | Тип: {w_meta['type']}"
            screen.blit(f.render(txt, True, WHITE), (120, 200))
            screen.blit(f.render("УДАЛИТЬ", True, WHITE), (960, 202))
            world_buttons.append((w_meta['name'], w_rect))
            del_buttons.append((w_meta['name'], d_rect))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.FINGERDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT)) if event.type == pygame.FINGERDOWN else event.pos
                if b_back.collidepoint(mx, my): return None
                
                if b_toggle_mode.collidepoint(mx, my):
                    current_mode_selection = "Creative" if current_mode_selection == "Survival" else "Survival"

                if b_create.collidepoint(mx, my):
                    new_name = f"World_{random.randint(100,999)}"
                    manifest.append({"name": new_name, "type": "Normal", "mode": current_mode_selection})
                    save_worlds_manifest(manifest)
                    
                    dummy_w = World(new_name, "Normal", current_mode_selection)
                    dummy_p = TerrariaPlayer(400, dummy_w.get_spawn_y_tile(15)*TILE_SIZE - 40)
                    
                    start_hb = ["pickaxe", "axe", "sword", 1, 2] if current_mode_selection == "Survival" else [1, 2, 3, 4, 5]
                    start_inv = [0] * 24
                    if current_mode_selection == "Creative":
                        start_inv[0] = 1; start_inv[1] = 2; start_inv[2] = 3; start_inv[3] = 4; start_inv[4] = 5
                        start_inv[5] = "pickaxe"; start_inv[6] = "axe"; start_inv[7] = "sword"
                    
                    save_world_to_disk(dummy_w, dummy_p, start_inv, start_hb)
                
                for name, r in world_buttons:
                    if r.collidepoint(mx, my): return name
                for name, r in del_buttons:
                    if r.collidepoint(mx, my):
                        manifest = [m for m in manifest if m['name'] != name]
                        save_worlds_manifest(manifest)
                        if os.path.exists(f"world_{name}.dat"): os.remove(f"world_{name}.dat")

        pygame.display.flip()
        clock.tick(30)

def main_menu():
    global sound_enabled
    while True:
        screen.fill((90, 175, 245))
        f_title = pygame.font.SysFont(None, 110); f_btn = pygame.font.SysFont(None, 45)
        b_play = pygame.Rect(SCREEN_WIDTH//2 - 250, 360, 500, 80)
        
        screen.blit(f_title.render("2D MINECRAFT", True, WHITE), (SCREEN_WIDTH//2 - 250, 160))
        pygame.draw.rect(screen, (35, 35, 40, 240), b_play, border_radius=20)
        screen.blit(f_btn.render("УПРАВЛЕНИЕ МИРАМИ", True, WHITE), (SCREEN_WIDTH//2 - 180, 385))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.FINGERDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT)) if event.type == pygame.FINGERDOWN else event.pos
                if b_play.collidepoint(mx, my):
                    chosen = worlds_menu()
                    if chosen: return chosen
        pygame.display.flip()
        clock.tick(30)

# --- ИНИЦИАЛИЗАЦИЯ ИГРОВОЙ СЕССИИ ---
active_world_name = main_menu()
save_data = load_world_from_disk(active_world_name)

# Предотвращение вылета, если структуры данных повреждены
if not save_data:
    save_data = {
        "name": active_world_name, "type": "Normal", "mode": "Survival", "loc": "surface",
        "blocks": {}, "px": 400, "py": 200, "inv": [0]*24, "hb": ["pickaxe", "axe", "sword", 1, 2]
    }

world = World(save_data["name"], save_data["type"], save_data.get("mode", "Survival"), save_data["loc"])
if save_data["blocks"]:
    world.data = save_data["blocks"]
else:
    world.generate()

player = TerrariaPlayer(save_data["px"], save_data["py"])
inventory = save_data["inv"] if "inv" in save_data and save_data["inv"] else [0] * 24
hotbar = save_data["hb"] if "hb" in save_data and save_data["hb"] else ["pickaxe", "axe", "sword", 1, 2]

ctrl = TouchController()
active_hotbar_idx = 0
drops = []
active_fingers = {}
break_tile_x = break_tile_y = -1
break_progress = 0
last_save_time = pygame.time.get_ticks()

pigs = []
for _ in range(3):
    rx = random.randint(10, 100) * TILE_SIZE
    pigs.append(NormalPig(rx, world.get_spawn_y_tile(int(rx//TILE_SIZE))*TILE_SIZE - 40))

# Главный игровой цикл
while True:
    is_creative = (world.mode == "Creative")
    screen.fill(SKY_BLUE if world.location == "surface" else CAVE_BLACK)
    player.vx = 0
    music_player.update(world.location)

    if pygame.time.get_ticks() - last_save_time > 5000:
        save_world_to_disk(world, player, inventory, hotbar)
        last_save_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_world_to_disk(world, player, inventory, hotbar)
            pygame.quit(); sys.exit()
            
        if event.type == pygame.FINGERDOWN:
            fx, fy = int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT)
            active_fingers[event.finger_id] = (fx, fy)
            
            if ctrl.btn_inv_toggle.collidepoint(fx, fy):
                show_full_inventory(inventory, hotbar, is_creative)
                active_fingers.clear()
            
            if ctrl.btn_loc.collidepoint(fx, fy):
                save_world_to_disk(world, player, inventory, hotbar)
                world = World(world.name, world.w_type, world.mode, "caves" if world.location == "surface" else "surface")
                player.rect.y = world.get_spawn_y_tile(15)*TILE_SIZE - 40
                drops.clear(); pigs.clear()

            for i, r in enumerate(ctrl.hotbar_rects):
                if r.collidepoint(fx, fy): active_hotbar_idx = i

            if not ctrl.is_ui_click(fx, fy) and fy > 130:
                cx = int((fx + camera_x) // TILE_SIZE)
                cy = int((fy + camera_y) // TILE_SIZE)
                if active_hotbar_idx < len(hotbar):
                    current_place_item = hotbar[active_hotbar_idx]
                    if world.get_block(cx, cy) == 0 and isinstance(current_place_item, int) and current_place_item != 0:
                        world.set_block(cx, cy, current_place_item)

        if event.type == pygame.FINGERMOTION:
            active_fingers[event.finger_id] = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
        if event.type == pygame.FINGERUP:
            active_fingers.pop(event.finger_id, None)

    move_left = move_right = jump = mine = False
    for fid, (fx, fy) in active_fingers.items():
        if ctrl.btn_left.collidepoint(fx, fy): move_left = True
        elif ctrl.btn_right.collidepoint(fx, fy): move_right = True
        elif ctrl.btn_jump.collidepoint(fx, fy): jump = True
        elif ctrl.btn_mine.collidepoint(fx, fy): mine = True

    if move_left: player.vx = -5.0; player.facing_right = False
    if move_right: player.vx = 5.0; player.facing_right = True
    if jump and player.on_ground: player.vy = JUMP_FORCE

    if mine:
        look = 24 if player.facing_right else -16
        cx = int((player.rect.centerx + look) // TILE_SIZE)
        cy = int(player.rect.centery // TILE_SIZE)
        if world.get_block(cx, cy) == 0: 
            cx = int(player.rect.centerx // TILE_SIZE)
            cy = int((player.rect.bottom + 5) // TILE_SIZE)

        if world.get_block(cx, cy) != 0:
            if is_creative:
                world.set_block(cx, cy, 0)
            else:
                current_tool = hotbar[active_hotbar_idx] if active_hotbar_idx < len(hotbar) else 0
                target_block = world.get_block(cx, cy)
                
                speed_modifier = 3.5 
                if current_tool == "pickaxe" and target_block == 3: speed_modifier = 12.0 
                if current_tool == "axe" and target_block in [1, 2, 5]: speed_modifier = 14.0 

                if break_tile_x == cx and break_tile_y == cy:
                    break_progress += speed_modifier
                    if break_progress >= 100:
                        old_type = world.get_block(cx, cy)
                        world.set_block(cx, cy, 0)
                        drops.append(DropItem(cx * TILE_SIZE + 8, cy * TILE_SIZE + 8, old_type))
                        break_progress = 0
                else: break_tile_x, break_tile_y = cx, cy; break_progress = 0
        else: break_progress = 0; break_tile_x = break_tile_y = -1
    else: break_progress = 0; break_tile_x = break_tile_y = -1

    player.vy += GRAVITY
    if player.vy > 14: player.vy = 14
    player.rect.x += player.vx
    
    x1, x2 = int(player.rect.left // TILE_SIZE), int(player.rect.right // TILE_SIZE)
    y1, y2 = int(player.rect.top // TILE_SIZE), int(player.rect.bottom // TILE_SIZE)
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            if world.get_block(x, y) != 0:
                br = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if player.rect.colliderect(br):
                    if player.vx > 0: player.rect.right = br.left
                    elif player.vx < 0: player.rect.left = br.right

    player.on_ground = False
    player.rect.y += player.vy
    x1, x2 = int(player.rect.left // TILE_SIZE), int(player.rect.right // TILE_SIZE)
    y1, y2 = int(player.rect.top // TILE_SIZE), int(player.rect.bottom // TILE_SIZE)
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            if world.get_block(x, y) != 0:
                br = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if player.rect.colliderect(br):
                    if player.vy > 0: player.rect.bottom = br.top; player.vy = 0; player.on_ground = True
                    elif player.vy < 0: player.rect.top = br.bottom; player.vy = 0

    for pig in pigs: pig.update(world)

    for d in drops[:]:
        d.update(world)
        if player.rect.colliderect(d.rect):
            for idx in range(len(inventory)):
                if inventory[idx] == 0 or inventory[idx] == d.b_type:
                    inventory[idx] = d.b_type
                    if d in drops: drops.remove(d)
                    break

    camera_x = max(0, min(player.rect.x - SCREEN_WIDTH // 2, world.width * TILE_SIZE - SCREEN_WIDTH))
    camera_y = max(0, min(player.rect.y - SCREEN_HEIGHT // 2, world.height * TILE_SIZE - SCREEN_HEIGHT))

    for tile, b_id in world.data.items():
        bx, by = tile[0]*TILE_SIZE - camera_x, tile[1]*TILE_SIZE - camera_y
        if 0 <= bx <= SCREEN_WIDTH and 0 <= by <= SCREEN_HEIGHT:
            if b_id in TEXTURES:
                screen.blit(TEXTURES[b_id], (bx, by))
            if tile[0] == break_tile_x and tile[1] == break_tile_y and break_progress > 0:
                pygame.draw.rect(screen, (255, 0, 0), (bx + 2, by + 12, (TILE_SIZE-4)*(break_progress/100), 6))

    for d in drops:
        if d.b_type in TEXTURES:
            screen.blit(pygame.transform.scale(TEXTURES[d.b_type], (16,16)), (d.rect.x - camera_x, d.rect.y - camera_y))

    for pig in pigs: pig.draw(screen, camera_x, camera_y)
    
    current_active_item = hotbar[active_hotbar_idx] if active_hotbar_idx < len(hotbar) else 0
    player.draw(screen, camera_x, camera_y, mine, current_active_item)
    ctrl.draw(screen, hotbar, active_hotbar_idx, world.location)

    pygame.display.flip()
    clock.tick(60)
