from fastapi import FastAPI, HTTPException
import psycopg2
from pydantic import BaseModel



app = FastAPI()

def db_connect():
    conn = psycopg2.connect(
        host = "localhost",
        dbname = "postgres",
        user = "postgres",
        password = "ganesh",
        port = 5432,
    )
    return conn

class Post(BaseModel):
    title : str
    content : str
    author : str


@app.get("/")
def test():
    return {"message" : "Test"}


@app.get("/all-posts")
def all_posts():
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id,title,content,author FROM posts
                """
            )
            rows = cur.fetchall()
            if not  rows:
                raise HTTPException(status_code=404,detail="Posts not found")
            posts = [
                {
                    "id" :  row[0],
                    "title" : row[1],
                    "content" : row[2],
                    "author" : row[3]
                }
                for row in rows
            ]
            return posts
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()

@app.post("/new-post")
def new_post(post : Post):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS posts(
                id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                content TEXT,
                author VARCHAR(255)
                )
                """
            )
            cur.execute(
                """
                INSERT INTO posts(title,content,author)
                VALUES (%s,%s,%s)
                RETURNING id
                """,
                (post.title,post.content,post.author)
            )
            conn.commit()
            return {
                "message" : "Post created"
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()

@app.post("/update-post/{id}")
def update_post(updated_post : Post,id:int):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE posts 
                SET title = %s,content = %s,author=%s
                WHERE id = %s
                RETURNING id, title,content,author
                """,
                (updated_post.title,updated_post.content,updated_post.author,id)
            )
            updated_row = cur.fetchone()
            if not updated_row:
                raise HTTPException(status_code=404,detail="Post not found")
            conn.commit()
            return {
                "id": updated_row[0],
                "title": updated_row[1],
                "author": updated_row[2],
                "content": updated_row[3]
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()

@app.delete("/delete-post")
def delete_post():
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                
                """
            )

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()