from dataclasses import dataclass
from environs import Env

@dataclass
class DatabaseConfig:
    database: str

@dataclass
class TgBot:
    token: str
    admin_ids: list[int]

@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig

def load_config(path: str = None) -> Config:
    env = Env()
    env.read_env(path)
    
    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMIN_IDS")))
        ),
        db=DatabaseConfig(
            database=env.str("DATABASE")
        )
    )
