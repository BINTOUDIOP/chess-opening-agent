# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API externes
    youtube_api_key: str = ""
    mistral_api_key: str = ""

    # MongoDB
    mongodb_uri: str = "mongodb://mongo:27017"
    mongodb_db: str = "ffe_chess"

    # Milvus
    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_collection: str = "chess_openings"

    # Stockfish
    stockfish_path: str = "/usr/games/stockfish"
    stockfish_depth: int = 15

    # Lichess
    lichess_api_url: str = "https://explorer.lichess.ovh/masters"
    lichess_token: str = ""

    # CORS
    cors_origins: str = "http://localhost:4200"

    class Config:
        env_file = ".env"

settings = Settings()
