from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

connection = psycopg.connect(
    host = os.getenv("DB_HOST"),
    dbname = os.getenv("DB_NAME"), 
    user = os.getenv("DB_USER"),
    password = os.getenv("DB_PASSWORD"),
    port = os.getenv("DB_PORT")
)

cursor = connection.cursor()

## test code


app = FastAPI()

# This describes the required format of a submitted score.
class Score(BaseModel):
    username: str
    score: int

# This checks whether the API is running.
@app.get("/")
def home():
    return {"message": "LeafMan API is running"}


# This receives and saves a new score.
@app.post("/scores")
def add_score(new_score: Score):
    cursor.execute("SELECT * FROM players WHERE username = (%s)", 
        (new_score.username,)
    )

    player = cursor.fetchone()

    if player is None:
        raise HTTPException(
            status_code = 404,
            detail = "NOT FOUND"
        )

    player_id = player[0]

    cursor.execute("INSERT INTO scores(user_id, score) VALUES (%s,%s)",
        (player_id, new_score.score)
    )

    connection.commit()

    return {
        "message": "Score saved",
        "username": new_score.username,
        "score": new_score.score
    }

# This showcases everything in the players table.
@app.get("/playersinfo")
def get_players():
    cursor.execute(
        "SELECT * FROM players"
    )

    players = []

    playersInfo = cursor.fetchall()

    for row in playersInfo:
        player = {
            "user_id": row[0],
            "username": row[1]
        }

        players.append(player)

    return players


# This showcases everything in the scores table.
@app.get("/scoresinfo")
def get_scores():
    cursor.execute(
        "SELECT * FROM scores"
    )

    scores = []

    scoresInfo = cursor.fetchall()

    for row in scoresInfo:
        score = {
            "score_id": row[0],
            "user_id": row[1],
            "score": row[2],
            "created_at": row[3]
        }

        scores.append(score)

    return scores


# This showcases everything in the leaderboard.
@app.get("/leaderboard")
def get_leaderboard():
    cursor.execute("""
        SELECT players.username, scores.score 
        FROM players
        JOIN scores
        ON players.user_id = scores.user_id
        ORDER BY scores.score DESC
        LIMIT 10
    """)

    leaderBoards = []
    
    Scores = cursor.fetchall()
    
    for row in Scores:
        player = {
            "username": row[0],
            "score": row[1]
        }
    
        leaderBoards.append(player)
    
    return leaderBoards



