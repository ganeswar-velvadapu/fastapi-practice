from fastapi import FastAPI,HTTPException
import psycopg2
from pydantic import BaseModel
from typing import Optional
app = FastAPI()


#Data base connection
def connect_db():
    conn = psycopg2.connect(
        host = "localhost",
        dbname = 'postgres',
        user = "postgres",
        password = "ganesh",
        port = 5432
    )
    return conn

class PostUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    content: Optional[str] = None


class Post(BaseModel):
    title : str
    author : str
    content : str

@app.post("/create-post")
def create_post(post : Post):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            print("Data base connected")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS post(
                id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                author VARCHAR(255),
                content TEXT
                )
                """
            )
            cur.execute(
                """
                INSERT INTO post(title,author,content)
                VALUES (%s,%s,%s)
                RETURNING ID
                """,
                (post.title,post.author,post.content)
            )
            post_id = cur.fetchone()[0]
            conn.commit()
            return {**post.dict(),"id":post_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=404,detail="Error in create post route")
    finally:
        conn.close()


@app.get("/allposts")
def allposts():
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id,title,author,content from post
                """
            )
            rows = cur.fetchall()
            if not rows:
                raise HTTPException(status_code=404,detail="no posts")
            posts = [
                {"id": row[0], "title": row[1], "author": row[2], "content": row[3]}
                for row in rows
            ]
            return posts
    except Exception as e:
        raise HTTPException(status_code=404,detail="Error in all posts route")
    finally:
        conn.close()



@app.put("/update/{id}")
def update(updated_post :Post,id:int):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE post
                SET title = %s,author = %s,content = %s
                WHERE id = %s
                RETURNING id,title,author,content
                """,
                (updated_post.title,updated_post.author,updated_post.content,id)
            )
            updated_row = cur.fetchone()
            if updated_row is None:
                raise HTTPException(status_code=404, detail="Post not found")
            conn.commit()
            return {
                "id": updated_row[0],
                "title": updated_row[1],
                "author": updated_row[2],
                "content": updated_row[3]
            }
    except Exception as e:
        raise HTTPException(status_code=404,detail="Error in update route")
    finally:
        conn.close()


@app.delete("/delete/{id}")
def delete(id :int):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE from post
                WHERE id = %s
                RETURNING id
                """,
                (id,)
            )
            deleted_row = cur.fetchone()
            if deleted_row is None:
                raise HTTPException(status_code=404,detail="Not found")
            conn.commit()
            return {"message" : f"Test with {id} deleted"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=404,detail="Error in delete route")
    finally:
        conn.close()    