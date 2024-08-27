from fastapi import FastAPI, HTTPException
import psycopg2
from pydantic import BaseModel

# Database configuration
DATABASE = {
    "host": "localhost",
    "dbname": "postgres",
    "username": "postgres",
    "password": "ganesh",
    "port": 5432
}

# Database connection
def connect_db():
    conn = psycopg2.connect(
        host=DATABASE["host"],
        dbname=DATABASE["dbname"],
        user=DATABASE["username"],
        password=DATABASE["password"],
        port=DATABASE["port"]
    )
    return conn

# Pydantic model
class Post(BaseModel):
    title: str
    content: str
    author: str

app = FastAPI()

@app.get("/")
def test():
    return {"Data": "Hello"}

@app.post("/posts", response_model=Post)
def create_post(post: Post):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS posts(
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    author VARCHAR(255),
                    content TEXT
                )
                """
            )
            cur.execute(
                """
                INSERT INTO posts (title, content, author) 
                VALUES (%s, %s, %s) 
                RETURNING id;
                """,
                (post.title, post.content, post.author)
            )
            post_id = cur.fetchone()[0]
            conn.commit()
            return {**post.dict(), "id": post_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()





