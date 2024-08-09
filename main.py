import pygame
import random
import math
import colorsys
import logging
from typing import List, Tuple, Dict
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json
import os

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
def load_config() -> Dict:
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Config file not found. Using default settings.")
        return {}

CONFIG = load_config()

# Constants
WIDTH = CONFIG.get('WIDTH', 800)
HEIGHT = CONFIG.get('HEIGHT', 600)
FPS = CONFIG.get('FPS', 60)
PADDLE_WIDTH = CONFIG.get('PADDLE_WIDTH', 15)
PADDLE_HEIGHT = CONFIG.get('PADDLE_HEIGHT', 90)
BALL_SIZE = CONFIG.get('BALL_SIZE', 15)
AI_SPEED = CONFIG.get('AI_SPEED', 7)
ELEMENTS = CONFIG.get('ELEMENTS', ["Fire", "Water", "Earth", "Air", "Void", "Time"])

@dataclass
class Color:
    r: int
    g: int
    b: int

    @classmethod
    def random(cls) -> 'Color':
        return cls(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))

    def to_tuple(self) -> Tuple[int, int, int]:
        return self.r, self.g, self.b

class DynamicColorManager:
    def __init__(self):
        self.shift: float = 0
        self.colors: Dict[str, Color] = {element: Color.random() for element in ELEMENTS}

    def update(self) -> None:
        self.shift += 0.01
        for element in ELEMENTS:
            h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in self.colors[element].to_tuple()])
            h = (h + self.shift) % 1.0
            r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v)]
            self.colors[element] = Color(r, g, b)

    def get(self, element: str) -> Tuple[int, int, int]:
        return self.colors[element].to_tuple()

class VisualEffects:
    def __init__(self):
        self.wave_distortion: float = 0
        self.kaleidoscope: bool = False
        self.kaleidoscope_intensity: int = 0

    def update(self) -> None:
        self.wave_distortion = math.sin(pygame.time.get_ticks() * 0.001) * 2  # Reduced distortion factor
        if random.random() < 0.0005:
            self.kaleidoscope = not self.kaleidoscope
            self.kaleidoscope_intensity = random.choice([0, 45, 90]) if self.kaleidoscope else 0

    def apply(self, surface: pygame.Surface) -> None:
        if self.wave_distortion != 0:
            self.apply_wave_distortion(surface)
        if self.kaleidoscope:
            self.apply_kaleidoscope(surface)

    def apply_wave_distortion(self, surface: pygame.Surface) -> None:
        for y in range(HEIGHT):
            offset = int(math.sin(y * 0.1 + self.wave_distortion) * 5)
            if offset != 0:
                surface.scroll(dx=offset, dy=0)

    def apply_kaleidoscope(self, surface: pygame.Surface) -> None:
        if self.kaleidoscope_intensity > 0:
            center = (WIDTH // 2, HEIGHT // 2)
            for angle in range(0, 360, self.kaleidoscope_intensity):
                rotated = pygame.transform.rotate(surface, angle)
                surface.blit(rotated, rotated.get_rect(center=center), special_flags=pygame.BLEND_ADD)

class GameObject(ABC):
    @abstractmethod
    def update(self) -> None:
        pass

    @abstractmethod
    def draw(self, screen: pygame.Surface) -> None:
        pass

class Particle(GameObject):
    def __init__(self, x: float, y: float, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(2, 5)
        self.speed = random.uniform(1, 3)
        self.angle = random.uniform(0, 2 * math.pi)

    def update(self) -> bool:
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.size -= 0.1
        return self.size <= 0

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

class Paddle(GameObject):
    def __init__(self, x: int, y: int, is_ai: bool = False):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.element = random.choice(ELEMENTS)
        self.is_ai = is_ai
        self.charge = 0
        self.max_charge = 100
        self.combo_meter = 0
        self.combo_multiplier = 1
        self.particles: List[Particle] = []

    def update(self, ball: 'Ball') -> None:
        if not self.is_ai:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w] and self.rect.top > 0:
                self.rect.y -= 5
            if keys[pygame.K_s] and self.rect.bottom < HEIGHT:
                self.rect.y += 5
            if keys[pygame.K_LSHIFT]:
                self.charge = min(self.charge + 1, self.max_charge)
            else:
                self.charge = max(self.charge - 0.5, 0)
        else:
            self._ai_move(ball)

        self._update_particles()

    def _ai_move(self, ball: 'Ball') -> None:
        if self.rect.centery < ball.rect.centery and self.rect.bottom < HEIGHT:
            self.rect.y += AI_SPEED
        elif self.rect.centery > ball.rect.centery and self.rect.top > 0:
            self.rect.y -= AI_SPEED

    def _update_particles(self) -> None:
        self.particles = [p for p in self.particles if not p.update()]
        if random.random() < 0.2:
            self.particles.append(Particle(self.rect.centerx, random.randint(self.rect.top, self.rect.bottom), COLOR_MANAGER.get(self.element)))

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, COLOR_MANAGER.get(self.element), self.rect)
        for particle in self.particles:
            particle.draw(screen)
        # Add glow effect
        for i in range(5):
            glow_rect = self.rect.inflate(i * 2, i * 2)
            pygame.draw.rect(screen, (*COLOR_MANAGER.get(self.element), 50 - i * 10), glow_rect, 1)

class Ball(GameObject):
    def __init__(self):
        self.rect = pygame.Rect(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)
        self.reset()
        self.trail: List[Tuple[int, int]] = []
        self.particles: List[Particle] = []

    def reset(self) -> None:
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        speed = 5
        angle = random.uniform(-math.pi / 4, math.pi / 4)
        self.dx = speed * math.cos(angle) * random.choice([-1, 1])
        self.dy = speed * math.sin(angle)
        self.element = random.choice(ELEMENTS)
        self.dimension = 0

    def update(self, time_factor: float) -> None:
        self.rect.x += self.dx * time_factor
        self.rect.y += self.dy * time_factor
        self.trail.insert(0, self.rect.center)
        if len(self.trail) > 20:
            self.trail.pop()
        if random.random() < 0.2:
            self.particles.append(Particle(self.rect.centerx, self.rect.centery, COLOR_MANAGER.get(self.element)))
        self.particles = [p for p in self.particles if not p.update()]

    def draw(self, screen: pygame.Surface) -> None:
        for i, pos in enumerate(self.trail):
            size = self.rect.width - i * 0.5
            alpha = 255 - i * 12
            color = (*COLOR_MANAGER.get(self.element)[:3], alpha)
            pygame.draw.circle(screen, color, pos, int(size))
        pygame.draw.ellipse(screen, COLOR_MANAGER.get(self.element), self.rect)
        for particle in self.particles:
            particle.draw(screen)
        # Add glow effect
        for i in range(5):
            glow_rect = self.rect.inflate(i * 2, i * 2)
            pygame.draw.ellipse(screen, (*COLOR_MANAGER.get(self.element), 50 - i * 10), glow_rect, 1)

class PowerUp(GameObject):
    def __init__(self):
        self.rect = pygame.Rect(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100), 20, 20)
        self.type = random.choice(["Multi-ball", "Elemental Lock", "Paddle Growth", "Gravity Shift",
                                   "Dimension Hop", "Time Warp", "Reality Bend", "Quantum Tunneling"])
        self.color = Color.random()
        self.pulse = 0

    def update(self) -> None:
        self.pulse += 0.1

    def draw(self, screen: pygame.Surface) -> None:
        size = int(self.rect.width + math.sin(self.pulse) * 5)
        pygame.draw.rect(screen, self.color.to_tuple(),
                         (self.rect.centerx - size // 2, self.rect.centery - size // 2, size, size))

class InterdimensionalRift(GameObject):
    def __init__(self):
        self.x = random.randint(100, WIDTH - 100)
        self.y = random.randint(100, HEIGHT - 100)
        self.radius = random.randint(30, 50)
        self.destination = random.randint(1, 3)
        self.color = Color.random()
        self.particles: List[Particle] = []

    def update(self) -> None:
        if random.random() < 0.2:
            angle = random.uniform(0, 2 * math.pi)
            x = self.x + math.cos(angle) * self.radius
            y = self.y + math.sin(angle) * self.radius
            self.particles.append(Particle(x, y, self.color.to_tuple()))
        self.particles = [p for p in self.particles if not p.update()]

    def draw(self, screen: pygame.Surface) -> None:
        for i in range(5):
            alpha = 100 - i * 20
            color = (*self.color.to_tuple(), alpha)
            pygame.draw.circle(screen, color, (self.x, self.y), self.radius - i * 2, 2)
        for particle in self.particles:
            particle.draw(screen)
        font = pygame.font.Font(None, 24)
        text = font.render(f"D{self.destination}", True, self.color.to_tuple())
        screen.blit(text, (self.x - text.get_width() // 2, self.y - text.get_height() // 2))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Psychedelic Interdimensional Pong Overload")
        self.clock = pygame.time.Clock()
        self.player_paddle = Paddle(50, HEIGHT // 2 - PADDLE_HEIGHT // 2)
        self.ai_paddle = Paddle(WIDTH - 50 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2, is_ai=True)
        self.ball = Ball()
        self.powerups: List[PowerUp] = []
        self.rifts: List[InterdimensionalRift] = []
        self.score = [0, 0]
        self.time_factor = 1.0
        self.reality_shift = 0
        self.particles: List[Particle] = []
        self.visual_effects = VisualEffects()

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

    def update(self) -> None:
        COLOR_MANAGER.update()
        self.visual_effects.update()

        self.player_paddle.update(self.ball)
        self.ai_paddle.update(self.ball)
        self.ball.update(self.time_factor)

        self._handle_collisions()
        self._update_game_state()
        self._handle_powerups()
        self._handle_rifts()

        self.particles = [p for p in self.particles if not p.update()]

    def _handle_collisions(self) -> None:
        if self.ball.rect.top <= 0 or self.ball.rect.bottom >= HEIGHT:
            self.ball.dy *= -1

        for paddle in [self.player_paddle, self.ai_paddle]:
            if self.ball.rect.colliderect(paddle.rect):
                self.ball.dx *= -1.1
                paddle.combo_meter += 1
                paddle.combo_multiplier = 1 + (paddle.combo_meter // 3) * 0.2
                self._create_collision_particles(20)

    def _update_game_state(self) -> None:
        if self.ball.rect.left <= 0 or self.ball.rect.right >= WIDTH:
            if self.ball.rect.left <= 0:
                self.score[1] += 1
            else:
                self.score[0] += 1
            self.ball.reset()
            self.player_paddle.combo_meter = 0
            self.ai_paddle.combo_meter = 0

    def _handle_powerups(self) -> None:
        if random.random() < 0.01:
            self.powerups.append(PowerUp())

        for powerup in self.powerups[:]:
            powerup.update()
            if self.ball.rect.colliderect(powerup.rect):
                self._apply_powerup(powerup)
                self.powerups.remove(powerup)
                self._create_collision_particles(30, powerup.color.to_tuple())

    def _apply_powerup(self, powerup: PowerUp) -> None:
        if powerup.type == "Time Warp":
            self.time_factor = random.uniform(0.5, 1.5)
        elif powerup.type == "Reality Bend":
            self.reality_shift = random.uniform(-0.2, 0.2)
        # Add more powerup effects here

    def _handle_rifts(self) -> None:
        if random.random() < 0.005:
            self.rifts.append(InterdimensionalRift())

        for rift in self.rifts[:]:
            rift.update()
            if math.hypot(self.ball.rect.centerx - rift.x, self.ball.rect.centery - rift.y) < rift.radius:
                self.ball.dimension = rift.destination
                self._create_collision_particles(50, rift.color.to_tuple())

    def _create_collision_particles(self, num_particles: int, color: Tuple[int, int, int] = None) -> None:
        color = color or COLOR_MANAGER.get(self.ball.element)
        for _ in range(num_particles):
            self.particles.append(Particle(self.ball.rect.centerx, self.ball.rect.centery, color))

    def draw(self) -> None:
        game_surface = pygame.Surface((WIDTH, HEIGHT))
        game_surface.fill((0, 0, 0))

        for rift in self.rifts:
            rift.draw(game_surface)

        for powerup in self.powerups:
            powerup.draw(game_surface)

        self.player_paddle.draw(game_surface)
        self.ai_paddle.draw(game_surface)
        self.ball.draw(game_surface)

        for particle in self.particles:
            particle.draw(game_surface)

        self.visual_effects.apply(game_surface)

        self.screen.blit(game_surface, (0, 0))

        self._draw_ui()

    def _draw_ui(self) -> None:
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"{self.score[0]} - {self.score[1]}", True, (255, 255, 255))
        self.screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 10))

        dimension_text = font.render(f"Dimension: {self.ball.dimension}", True, (255, 255, 255))
        self.screen.blit(dimension_text, (10, 10))

        time_text = font.render(f"Time: {self.time_factor:.2f}x", True, (255, 255, 255))
        self.screen.blit(time_text, (WIDTH - time_text.get_width() - 10, 10))

        reality_text = font.render(f"Reality Shift: {self.reality_shift:.2f}", True, (255, 255, 255))
        self.screen.blit(reality_text, (WIDTH - reality_text.get_width() - 10, 50))

# Global instances
COLOR_MANAGER = DynamicColorManager()

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)