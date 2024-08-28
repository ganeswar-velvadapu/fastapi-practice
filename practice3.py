from fastapi import FastAPI,HTTPException
import psycopg2
from pydantic import BaseModel
app = FastAPI()

class Blog(BaseModel):
    title : str
    content : str
    author : str


def db_connect():
    conn = psycopg2.connect(
        host = "localhost",
        dbname = "postgres",
        user = "postgres",
        password = "ganesh",
        port = 5432
    )
    return conn


@app.post("/create-blog")
def create_blog(blog:Blog):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS blogs(
                id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                author VARCHAR(255),
                content TEXT
                )
                """
            )
            cur.execute(
                """
                INSERT INTO blogs(title,content,author)
                VALUES (%s,%s,%s)
                RETURNING id
                """,
                (blog.title,blog.author,blog.content)
            )
            blog_id = cur.fetchone()[0]
            conn.commit()
            return {
                "id" : blog_id,
                "title" : blog.title,
                "author" : blog.author,
                "content" : blog.content
            }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server error")
    finally:
        conn.close()

@app.get("/allblogs")
def allblogs():
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id,title,author,content FROM blogs
                """
            )
            rows = cur.fetchall()
            if not rows:
                raise HTTPException(status_code=404,detail="No Blogs")
            blogs = [
                {"id": row[0], "title": row[1], "author": row[2], "content": row[3]}
                for row in rows
            ]
            return blogs
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal server error")
    finally:
        conn.close()


@app.put("/update-blog/{id}")
def update_blog(updated_blog :Blog,id:int):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            print("Updating blog 1")
            cur.execute(
                """
                UPDATE blogs
                SET title = %s,author = %s,content = %s
                WHERE id = %s
                RETURNING id,title,author,content
                """,
                (updated_blog.title,updated_blog.author,updated_blog.content,id)
            )
            print("Updating blog 2")
            updated_row = cur.fetchone()
            if updated_row is None:
                raise HTTPException(status_code=404, detail="Blog not found")

            conn.commit()
            print("Blog Updated")
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


@app.delete("/delete-blog/{id}")
def delete_blog(id : int):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE from blogs
                WHERE id = %s
                RETURNING id
                """,
                (id,)
            )
            conn.commit()
            return {
                f"Blog with id {id} deleted"
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal server error")
    finally:
        conn.close()

