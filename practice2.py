import stat
from fastapi import Depends, FastAPI,HTTPException,Response
import psycopg2
from pydantic import BaseModel
from typing import Optional 
import jwt
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from datetime import datetime,timedelta
app = FastAPI()

# def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
#     token = authorization.credentials
#     try:
#         payload = jwt.decode(token, "secret", "HS256")
#         username: str = payload.get("sub")
#         if username is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Could not validate credentials",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
#         return username
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code=stat.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     except jwt.PyJWTError:
#         raise HTTPException(
#             status_code=stat.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )




def generate_access_token(data :dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp" : expire})
    encode_jwt = jwt.encode(to_encode,"secret",algorithm="HS256")
    return encode_jwt

# Data base connection
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
def create_post(post: Post):
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
                RETURNING id
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
def update(updated_post: Post, id: int):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            # Print to debug
            print(f"Updating post with ID: {id}")
            print(f"New data: {updated_post.dict()}")
            
            # Update the post
            cur.execute(
                """
                UPDATE post
                SET title = %s, author = %s, content = %s
                WHERE id = %s
                RETURNING id, title, author, content
                """,
                (updated_post.title, updated_post.author, updated_post.content, id)
            )
            updated_row = cur.fetchone()
            
            # Check if the post was updated
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
        # Log the exception for debugging
        print(f"Error occurred: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error in update route")
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
class User(BaseModel):
    username:str
    email:str
    password:str


@app.post("/create-user")
def create_user(user:User,response:Response):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            print("Data base connected")
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

            cur.execute(
                """
                INSERT INTO users(username,email,password)
                VALUES (%s,%s,%s)
                RETURNING id
                """,
                (user.username,user.email,user.password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            #Generate token
            token = generate_access_token({"sub" : user.username})
            response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
            return {"id": user_id, "username": user.username, "email": user.email,}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail="Error in create user route")
    finally:
        conn.close()
    

@app.post("/login")
def login_user(email: str, password: str, response: Response):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password FROM users WHERE email = %s",
                (email,)  # Fixed the missing comma
            )
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="Invalid email or password")
            
            user_id, db_username, db_password = user
            
            # Verify the password using bcrypt
            if not (password, db_password):
                raise HTTPException(status_code=404, detail="Invalid password")
            
            # Generate JWT token
            token = generate_access_token({"sub": db_username})
            response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)

            return {"message": "Login successful"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=404,detail="Error in login route")
    finally:
        conn.close()
    


