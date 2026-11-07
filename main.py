from contextlib import asynccontextmanager
import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")


def get_connection():
    return psycopg.connect(DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Create the tables when the API starts
    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGSERIAL PRIMARY KEY,
                    username VARCHAR(30) UNIQUE NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    score_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL
                        REFERENCES players(user_id)
                        ON DELETE CASCADE,
                    score INTEGER NOT NULL CHECK (score >= 0),
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
            """)

    yield


app = FastAPI(lifespan=lifespan)

# Allow the browser version of LeafMan to call this API from itch.io.
# The API does not use cookies or browser credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class Player(BaseModel):
    username: str


class Score(BaseModel):
    username: str
    score: int


@app.get("/")
def home():
    return {"message": "LeafMan API is running"}


@app.post("/players")
def add_player(new_player: Player):

    username = new_player.username.strip()

    if username == "":
        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty"
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO players (username)
                VALUES (%s)
                ON CONFLICT (username) DO NOTHING
                RETURNING user_id
                """,
                (username,)
            )

            created_player = cursor.fetchone()

    if created_player is None:
        return {
            "message": "Player already exists",
            "username": username
        }

    return {
        "message": "Player created",
        "username": username
    }


@app.post("/scores")
def add_score(new_score: Score):

    username = new_score.username.strip()

    if new_score.score < 0:
        raise HTTPException(
            status_code=400,
            detail="Score cannot be negative"
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT user_id FROM players WHERE username = %s",
                (username,)
            )

            player = cursor.fetchone()

            if player is None:
                raise HTTPException(
                    status_code=404,
                    detail="Player not found"
                )

            player_id = player[0]

            cursor.execute(
                """
                INSERT INTO scores (user_id, score)
                VALUES (%s, %s)
                """,
                (player_id, new_score.score)
            )

    return {
        "message": "Score saved",
        "username": username,
        "score": new_score.score
    }


@app.get("/playersinfo")
def get_players():

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT user_id, username
                FROM players
                ORDER BY user_id
            """)

            rows = cursor.fetchall()

    return [
        {
            "user_id": row[0],
            "username": row[1]
        }
        for row in rows
    ]


@app.get("/scoresinfo")
def get_scores():

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT score_id, user_id, score, created_at
                FROM scores
                ORDER BY score_id
            """)

            rows = cursor.fetchall()

    return [
        {
            "score_id": row[0],
            "user_id": row[1],
            "score": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]


@app.get("/leaderboard")
def get_leaderboard():

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT players.username, MAX(scores.score) AS best_score
                FROM players
                JOIN scores
                    ON players.user_id = scores.user_id
                GROUP BY players.user_id, players.username
                ORDER BY best_score DESC
                LIMIT 10
            """)

            rows = cursor.fetchall()

    return [
        {
            "username": row[0],
            "score": row[1]
        }
        for row in rows
    ]
