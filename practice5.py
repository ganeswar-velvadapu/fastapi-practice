from fastapi import FastAPI, HTTPException,Response,Request,Depends
import psycopg2
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt
from datetime import datetime,timedelta
from fastapi.security import OAuth2PasswordBearer


app = FastAPI()

oauth_scheme = OAuth2PasswordBearer(tokenUrl="login")

def check_token(token:str = Depends(oauth_scheme)):
    if not token:
        raise HTTPException(status_code=404,detail="Unauthorized")
    try:
        decode = jwt.decode(token,"secret","HS256")
        username = decode.get("sub")
    except Exception as e:
        raise HTTPException(status_code=500,detail="Invalid token")
    return username





def create_token(username)-> str:
    payload = {
        "sub" : username,
        "exp" : datetime.utcnow() + timedelta(minutes = 1)
    }
    token = jwt.encode(payload,"secret","HS256")
    return token

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")

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


class User(BaseModel):
    username : str
    email : str
    password : str

@app.get("/")
def test():
    return {"message" : "Test"}

#Post routes
@app.get("/all-posts", tags=["posts"])
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

@app.post("/new-post",tags=["posts"])
def new_post(post : Post,current_user = Depends(check_token)):
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
            new_id = cur.fetchone()[0]
            conn.commit()
            return {
                "message" : "Post created",
                "id" : new_id
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()

@app.post("/update-post/{id}",tags=["posts"])
def update_post(updated_post : Post,id:int,current_user = Depends(check_token)):
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

@app.delete("/delete-post/{id}",tags=["posts"])
def delete_post(id : int,current_user = Depends(check_token)):

    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM posts
                WHERE id = %s
                RETURNING ID
                """,
                (id,)
            )
            deleted_id = cur.fetchone()[0]
            if not deleted_id:
                raise HTTPException(status_code=404,detail="Post not found")
            cur.execute("SELECT COUNT(*) FROM posts")
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("ALTER SEQUENCE posts_id_seq RESTART WITH 1")
                conn.commit()
            conn.commit()
            return {
                "message" : f"Post with id {id} removed"
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()

#User routes
@app.post("/signup",tags=["users"])
def signup(user : User,response:Response):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE,
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255)
                )
                """
            )
            hash_password = pwd_context.hash(user.password)
            cur.execute(
                """
                INSERT INTO users(username,email,password)
                VALUES (%s,%s,%s)
                RETURNING id
                """,
                (user.username,user.email,hash_password)
            )
            conn.commit()
            token = create_token(user.username)
            response.set_cookie(key="token",value=f"{token}",httponly=True)
            return {
                "message" : "Signup successful"
            }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()

@app.post("/login",tags=['users'])
def login(email:str,password:str,response:Response):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT username,email,password FROM users WHERE email = %s
                """,
                (email,)
            )
            user = cur.fetchone()
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            
            db_username,db_email,db_password = user
            password_check = pwd_context.verify(password,db_password)
            if not password_check:
                raise HTTPException(status_code=404,detail="Wrong Password")
            token = create_token(db_username)
            print(token)
            response.set_cookie(key="token",value=f"{token}",httponly=True)
            return {
                "message" : "login successful"
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server error")
    finally:
        conn.close()

