from fastapi import FastAPI,HTTPException,Response
import psycopg2
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime,timedelta
import jwt
app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data : dict):
    exp = datetime.utcnow() + timedelta(minutes=30)
    data.update({"exp" :exp})
    token = jwt.encode(data,"secret","HS256")
    return token

def db_connect():
    conn = psycopg2.connect(
        host = "localhost",
        dbname = "postgres",
        user = "postgres",
        password = "ganesh",
        port = 5432
    )
    return conn




class User(BaseModel):
    username:str
    email : str
    password : str



@app.post("/signup")
def signup(user : User,response:Response):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
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
            hashed_password = hash_password(user.password)
            cur.execute(
                """
                INSERT INTO users(username,email,password)
                VALUES (%s,%s,%s)
                RETURNING id
                """,
                (user.username,user.email,hashed_password)
            )
            conn.commit()
            token = create_token({"sub" : user.username})
            response.set_cookie(key="access_token",value=f"{token}",httponly=True)
            return {"message": "Signup successful"}
            
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    finally:
        conn.close()


@app.post("/login")
def login(email:str,password:str,response: Response):
    conn = db_connect()
    try:
        print("Login 1")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id,username,email,password FROM users WHERE email = %s
                """,
                (email,)
            )
            user = cur.fetchone()
            print("Login 2")
            if not user:
                raise HTTPException(status_code=500,detail="User not found")
            
            user_id,db_username,db_email,db_password = user
            print(db_username)
            verify = verify_password(password,db_password)
            
            if not verify:
                raise HTTPException(status_code=500,detail="Invalid password")
            token = create_token({"sub" : db_username})
            response.set_cookie(key="access_token", value = f"{token}" ,httponly=True)
            return {"Login successful"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500,detail="Internal server error")
    finally:
        conn.close()