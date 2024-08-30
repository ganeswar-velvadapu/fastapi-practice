from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from passlib.context import CryptContext
import psycopg2
from datetime import datetime,timedelta
import jwt


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_token(username:str):
    payload = {
        "sub" : username,
        "exp" : datetime.utcnow() + timedelta(minutes=1)
    }
    token = jwt.encode(payload,"secret","HS256")
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
    username : str
    email : str
    password : str


app = FastAPI()


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
def login(email : str,password:str,response:Response):
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