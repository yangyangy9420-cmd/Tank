import pygame
import random
import math

# 初始化Pygame
pygame.init()

# ========== 常量定义 ==========
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 40
MAP_WIDTH = SCREEN_WIDTH // GRID_SIZE  # 20
MAP_HEIGHT = SCREEN_HEIGHT // GRID_SIZE  # 15

# 颜色定义
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_BROWN = (139, 69, 19)
COLOR_BLUE = (0, 0, 255)

# 方向常量
DIR_UP = 0
DIR_RIGHT = 1
DIR_DOWN = 2
DIR_LEFT = 3

# 游戏设置
PLAYER_SPEED = 4
ENEMY_SPEED = 3
BULLET_SPEED = 8
PLAYER_SHOOT_DELAY = 15  # 帧数冷却
ENEMY_SHOOT_DELAY = 60
PLAYER_LIVES = 3
INVINCIBLE_FRAMES = 90  # 无敌帧数

# 地图砖块类型
TILE_EMPTY = 0
TILE_BRICK = 1

# ========== 辅助函数 ==========
def direction_to_vector(direction):
    """将方向转换为移动向量"""
    if direction == DIR_UP:
        return (0, -1)
    elif direction == DIR_RIGHT:
        return (1, 0)
    elif direction == DIR_DOWN:
        return (0, 1)
    elif direction == DIR_LEFT:
        return (-1, 0)

# ========== 子弹类 ==========
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner):
        super().__init__()
        self.image = pygame.Surface((6, 6))
        self.image.fill(COLOR_YELLOW)
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = direction
        self.speed = BULLET_SPEED
        self.owner = owner  # 发射者，用于避免误伤
        self.damage = 1

    def update(self):
        # 移动
        dx, dy = direction_to_vector(self.direction)
        self.rect.x += dx * self.speed
        self.rect.y += dy * self.speed

        # 超出屏幕则销毁
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill()

# ========== 坦克基类 ==========
class Tank(pygame.sprite.Sprite):
    def __init__(self, x, y, color, speed, shoot_delay):
        super().__init__()
        self.image = pygame.Surface((GRID_SIZE - 4, GRID_SIZE - 4))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.direction = DIR_UP
        self.speed = speed
        self.shoot_cooldown = 0
        self.shoot_delay = shoot_delay
        self.alive = True
        self.color = color

    def shoot(self, bullet_group):
        """发射子弹"""
        if self.shoot_cooldown <= 0:
            center_x = self.rect.centerx
            center_y = self.rect.centery
            # 根据方向调整子弹生成位置，使其从炮口发出
            offset = 20
            if self.direction == DIR_UP:
                bullet = Bullet(center_x, self.rect.top, self.direction, self)
            elif self.direction == DIR_DOWN:
                bullet = Bullet(center_x, self.rect.bottom, self.direction, self)
            elif self.direction == DIR_LEFT:
                bullet = Bullet(self.rect.left, center_y, self.direction, self)
            elif self.direction == DIR_RIGHT:
                bullet = Bullet(self.rect.right, center_y, self.direction, self)
            bullet_group.add(bullet)
            self.shoot_cooldown = self.shoot_delay

    def update_cooldown(self):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def move(self, walls, all_tanks):
        """移动坦克，考虑墙壁和其他坦克碰撞"""
        dx, dy = direction_to_vector(self.direction)
        new_x = self.rect.x + dx * self.speed
        new_y = self.rect.y + dy * self.speed
        original_pos = self.rect.topleft
        self.rect.topleft = (new_x, new_y)

        # 边界碰撞
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

        # 墙壁碰撞
        if self.collide_with_walls(walls):
            self.rect.topleft = original_pos

        # 坦克之间碰撞
        for other in all_tanks:
            if other != self and self.rect.colliderect(other.rect):
                self.rect.topleft = original_pos
                break

    def collide_with_walls(self, walls):
        """检测是否与墙壁碰撞"""
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                return True
        return False

    def draw(self, screen):
        """绘制坦克及炮管"""
        screen.blit(self.image, self.rect)
        # 绘制炮管
        center = self.rect.center
        length = 15
        if self.direction == DIR_UP:
            end = (center[0], self.rect.top - 5)
        elif self.direction == DIR_DOWN:
            end = (center[0], self.rect.bottom + 5)
        elif self.direction == DIR_LEFT:
            end = (self.rect.left - 5, center[1])
        else:  # RIGHT
            end = (self.rect.right + 5, center[1])
        pygame.draw.line(screen, COLOR_RED, center, end, 3)

# ========== 玩家坦克 ==========
class PlayerTank(Tank):
    def __init__(self, x, y):
        super().__init__(x, y, COLOR_GREEN, PLAYER_SPEED, PLAYER_SHOOT_DELAY)
        self.lives = PLAYER_LIVES
        self.invincible = 0  # 无敌倒计时
        self.respawn_pos = (x, y)

    def update(self, keys, bullet_group, walls, enemies):
        """更新玩家状态"""
        self.update_cooldown()
        if self.invincible > 0:
            self.invincible -= 1
            # 无敌闪烁效果
            if self.invincible // 5 % 2 == 0:
                self.image.fill(COLOR_WHITE)
            else:
                self.image.fill(self.color)
        else:
            self.image.fill(self.color)

        # 控制移动
        if keys[pygame.K_UP]:
            self.direction = DIR_UP
            self.move(walls, list(enemies) + [self])
        elif keys[pygame.K_DOWN]:
            self.direction = DIR_DOWN
            self.move(walls, list(enemies) + [self])
        elif keys[pygame.K_LEFT]:
            self.direction = DIR_LEFT
            self.move(walls, list(enemies) + [self])
        elif keys[pygame.K_RIGHT]:
            self.direction = DIR_RIGHT
            self.move(walls, list(enemies) + [self])

        # 射击
        if keys[pygame.K_SPACE]:
            self.shoot(bullet_group)

    def hit(self):
        """玩家被击中"""
        if self.invincible <= 0 and self.alive:
            self.lives -= 1
            if self.lives <= 0:
                self.alive = False
                self.kill()
            else:
                # 重置位置并进入无敌状态
                self.rect.topleft = self.respawn_pos
                self.invincible = INVINCIBLE_FRAMES

# ========== 敌方坦克 ==========
class EnemyTank(Tank):
    def __init__(self, x, y):
        super().__init__(x, y, COLOR_GRAY, ENEMY_SPEED, ENEMY_SHOOT_DELAY)
        self.direction = random.choice([DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT])
        self.change_dir_timer = random.randint(30, 90)
        self.ai_timer = 0

    def update(self, bullet_group, walls, all_tanks):
        """更新敌方坦克AI"""
        self.update_cooldown()
        self.ai_timer += 1

        # 定时改变方向
        if self.ai_timer >= self.change_dir_timer:
            self.direction = random.choice([DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT])
            self.ai_timer = 0
            self.change_dir_timer = random.randint(30, 90)

        # 移动
        self.move(walls, all_tanks)

        # 随机射击
        if random.randint(1, 60) == 1:
            self.shoot(bullet_group)

# ========== 墙壁砖块 ==========
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, tile_type):
        super().__init__()
        self.tile_type = tile_type
        if tile_type == TILE_BRICK:
            self.image = pygame.Surface((GRID_SIZE, GRID_SIZE))
            self.image.fill(COLOR_BROWN)
            # 绘制砖纹
            pygame.draw.rect(self.image, COLOR_GRAY, (0, 0, GRID_SIZE, GRID_SIZE), 2)
            pygame.draw.line(self.image, COLOR_GRAY, (GRID_SIZE//2, 0), (GRID_SIZE//2, GRID_SIZE), 2)
            pygame.draw.line(self.image, COLOR_GRAY, (0, GRID_SIZE//2), (GRID_SIZE, GRID_SIZE//2), 2)
        else:
            # 预留其他类型
            self.image = pygame.Surface((GRID_SIZE, GRID_SIZE))
            self.image.fill(COLOR_BLACK)
        self.rect = self.image.get_rect(topleft=(x, y))

# ========== 地图类 ==========
class GameMap:
    def __init__(self):
        self.walls = pygame.sprite.Group()
        self.map_data = [[TILE_EMPTY for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
        self.create_map()

    def create_map(self):
        """创建初始地图（砖墙边界和障碍物）"""
        # 边界墙体
        for x in range(MAP_WIDTH):
            self.add_wall(x, 0, TILE_BRICK)  # 上边界
            self.add_wall(x, MAP_HEIGHT - 1, TILE_BRICK)  # 下边界
        for y in range(1, MAP_HEIGHT - 1):
            self.add_wall(0, y, TILE_BRICK)  # 左边界
            self.add_wall(MAP_WIDTH - 1, y, TILE_BRICK)  # 右边界

        # 内部障碍物（几个砖墙块）
        obstacles = [
            (5, 5), (5, 6), (6, 5), (6, 6),
            (12, 8), (13, 8), (14, 8), (12, 9), (13, 9),
            (8, 10), (9, 10), (10, 10), (11, 10),
            (3, 12), (4, 12), (5, 12),
            (15, 3), (15, 4), (16, 3), (16, 4)
        ]
        for x, y in obstacles:
            if 0 < x < MAP_WIDTH-1 and 0 < y < MAP_HEIGHT-1:
                self.add_wall(x, y, TILE_BRICK)

    def add_wall(self, grid_x, grid_y, tile_type):
        """添加墙体"""
        if 0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT:
            self.map_data[grid_y][grid_x] = tile_type
            wall = Wall(grid_x * GRID_SIZE, grid_y * GRID_SIZE, tile_type)
            self.walls.add(wall)

    def remove_wall(self, grid_x, grid_y):
        """移除墙体"""
        if 0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT:
            if self.map_data[grid_y][grid_x] != TILE_EMPTY:
                self.map_data[grid_y][grid_x] = TILE_EMPTY
                # 从精灵组中移除对应墙体
                for wall in self.walls:
                    if wall.rect.x == grid_x * GRID_SIZE and wall.rect.y == grid_y * GRID_SIZE:
                        wall.kill()
                        break

    def draw(self, screen):
        self.walls.draw(screen)

    def check_bullet_collision(self, bullet):
        """子弹与墙体碰撞检测并处理"""
        # 计算子弹影响的网格区域
        grid_x = bullet.rect.centerx // GRID_SIZE
        grid_y = bullet.rect.centery // GRID_SIZE
        # 检查周围几个网格
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = grid_x + dx, grid_y + dy
                if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                    if self.map_data[ny][nx] == TILE_BRICK:
                        # 破坏砖墙
                        self.remove_wall(nx, ny)
                        bullet.kill()
                        return True
        return False

# ========== 游戏主类 ==========
class TankGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("坦克大战")
        self.clock = pygame.time.Clock()
        self.running = True
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.reset_game()

    def reset_game(self):
        """重置游戏状态"""
        # 创建地图
        self.game_map = GameMap()
        
        # 玩家坦克
        self.player = PlayerTank(GRID_SIZE * 2, GRID_SIZE * 2)
        self.player_group = pygame.sprite.Group(self.player)
        
        # 敌方坦克
        self.enemies = pygame.sprite.Group()
        enemy_positions = [(GRID_SIZE * 15, GRID_SIZE * 2),
                           (GRID_SIZE * 10, GRID_SIZE * 5),
                           (GRID_SIZE * 12, GRID_SIZE * 10),
                           (GRID_SIZE * 5, GRID_SIZE * 8),
                           (GRID_SIZE * 18, GRID_SIZE * 12)]
        for pos in enemy_positions:
            enemy = EnemyTank(pos[0], pos[1])
            self.enemies.add(enemy)
        
        # 子弹组
        self.bullets = pygame.sprite.Group()
        
        # 游戏状态
        self.score = 0
        self.game_over = False
        self.victory = False
        
        # 无敌重生闪烁初始化
        if self.player:
            self.player.invincible = INVINCIBLE_FRAMES

    def handle_events(self):
        """处理输入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.game_over and event.key == pygame.K_r:
                    self.reset_game()
                elif self.victory and event.key == pygame.K_r:
                    self.reset_game()

    def update(self):
        """更新游戏逻辑"""
        if self.game_over or self.victory:
            return
        
        keys = pygame.key.get_pressed()
        
        # 更新玩家
        self.player.update(keys, self.bullets, self.game_map.walls, self.enemies)
        
        # 更新敌方坦克
        all_tanks = list(self.enemies.sprites()) + [self.player] if self.player.alive else list(self.enemies.sprites())
        for enemy in self.enemies:
            enemy.update(self.bullets, self.game_map.walls, all_tanks)
        
        # 更新子弹
        self.bullets.update()
        
        # 子弹与墙壁碰撞
        for bullet in self.bullets:
            self.game_map.check_bullet_collision(bullet)
        
        # 子弹与坦克碰撞
        # 玩家子弹击中敌方
        player_bullets = [b for b in self.bullets if b.owner == self.player]
        for bullet in player_bullets:
            hit_enemies = pygame.sprite.spritecollide(bullet, self.enemies, False)
            for enemy in hit_enemies:
                enemy.kill()
                bullet.kill()
                self.score += 100
                break
        
        # 敌方子弹击中玩家
        enemy_bullets = [b for b in self.bullets if b.owner != self.player]
        for bullet in enemy_bullets:
            if self.player.alive and bullet.rect.colliderect(self.player.rect):
                self.player.hit()
                bullet.kill()
                if not self.player.alive:
                    self.game_over = True
                break
        
        # 玩家与敌方坦克碰撞伤害（碰撞即损失生命，避免重叠）
        if self.player.alive:
            collided_enemies = pygame.sprite.spritecollide(self.player, self.enemies, False)
            if collided_enemies:
                self.player.hit()
                # 把敌方坦克弹开
                for enemy in collided_enemies:
                    # 反向推开
                    if self.player.rect.centerx < enemy.rect.centerx:
                        enemy.rect.x += 20
                    else:
                        enemy.rect.x -= 20
                    if self.player.rect.centery < enemy.rect.centery:
                        enemy.rect.y += 20
                    else:
                        enemy.rect.y -= 20
                if not self.player.alive:
                    self.game_over = True
        
        # 检查胜利条件
        if len(self.enemies) == 0:
            self.victory = True

    def draw(self):
        """渲染画面"""
        self.screen.fill(COLOR_BLACK)
        
        # 绘制地图
        self.game_map.draw(self.screen)
        
        # 绘制坦克
        if self.player.alive:
            self.player.draw(self.screen)
        self.enemies.draw(self.screen)
        for enemy in self.enemies:
            enemy.draw(self.screen)
        
        # 绘制子弹
        for bullet in self.bullets:
            self.screen.blit(bullet.image, bullet.rect)
        
        # 绘制UI信息
        score_text = self.font.render(f"Score: {self.score}", True, COLOR_WHITE)
        self.screen.blit(score_text, (10, 10))
        
        lives_text = self.font.render(f"Lives: {self.player.lives}", True, COLOR_WHITE)
        self.screen.blit(lives_text, (10, 50))
        
        enemies_text = self.font.render(f"Enemies: {len(self.enemies)}", True, COLOR_WHITE)
        self.screen.blit(enemies_text, (10, 90))
        
        # 游戏结束或胜利画面
        if self.game_over:
            over_text = self.font.render("GAME OVER! Press R to restart", True, COLOR_RED)
            text_rect = over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(over_text, text_rect)
        elif self.victory:
            win_text = self.font.render("VICTORY! Press R to restart", True, COLOR_GREEN)
            text_rect = win_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(win_text, text_rect)
        
        pygame.display.flip()

    def run(self):
        """主循环"""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()

# ========== 程序入口 ==========
if __name__ == "__main__":
    game = TankGame()
    game.run()