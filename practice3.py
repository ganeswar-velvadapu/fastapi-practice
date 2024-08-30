from fastapi import FastAPI, HTTPException, Response,Depends
from pydantic import BaseModel
from passlib.context import CryptContext
import psycopg2
from datetime import datetime,timedelta
import jwt
from fastapi.security import OAuth2PasswordBearer


app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def create_token(username:str):
    payload = {
        "sub" : username,
        "exp" : datetime.utcnow() + timedelta(minutes=1)
    }
    token = jwt.encode(payload,"secret","HS256")
    return token

def get_current_user(token:str = Depends(oauth2_scheme)):
    credentials_error = HTTPException(
        status_code=401,
        detail="Unauthorized",
    )
    try:
        payload = jwt.decode(token,"secret","HS256")
        username :str = payload.get("sub")
        if not username:
            raise credentials_error
    except Exception as e:
        raise credentials_error
    return username



class Blog(BaseModel):
    title : str
    content : str
    author : str
class User(BaseModel):
    username : str
    email : str
    password : str

class LoginRequest(BaseModel):
    email: str
    password: str


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
def create_blog(blog:Blog,current_user: str = Depends(get_current_user)):
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
def update_blog(updated_blog :Blog,id:int,current_user: str = Depends(get_current_user)):
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
def delete_blog(id : int,current_user: str = Depends(get_current_user)):
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

@app.post("/signup")
def signup(user : User,response:Response):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id FROM users WHERE email = %s""",(user.email,)
            )
            existing_user = cur.fetchone()
            if existing_user:
                return {"message" : "User Already exists"}
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                username VARCHAR(255),
                email VARCHAR(255),
                password VARCHAR(255)
                )
                """
            )
            #hash password
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
            response.set_cookie(key="token" ,value=f"{token}",httponly=True)
            return {
               "message" : "Signup successful"
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        conn.close()

@app.post("/login")
def login(loginrequest : LoginRequest,response:Response):
    email = loginrequest.email,
    password = loginrequest.password
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id,username,email,password FROM users WHERE email = %s""",(email,)
            )
            user = cur.fetchone()
            if not user:
                return {"message" :"user does not exist"}
            
            id,db_username,db_email,db_password = user
            verify = pwd_context.verify(password,db_password)
            if not verify:
                return {"message" : "Wrong Password"}
            token =  create_token(db_username)
            response.set_cookie(key="token",value=f"{token}",httponly=True)
            return {
                "message" : "Login Successful"
            }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal Server Error")
    finally:
        conn.close()


@app.post("/logout")
def logout(reponse : Response):
    reponse.delete_cookie(key="token")
    return {
        "message" : "Logout successful"
    }