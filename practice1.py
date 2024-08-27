from fastapi import FastAPI, HTTPException
import psycopg2
from pydantic import BaseModel

def db_connect():
    conn = psycopg2.connect(
        host="localhost",
        dbname="postgres",
        user="postgres",
        password="ganesh",
        port=5432
    )
    return conn

class Test(BaseModel):
    test: str

app = FastAPI()

@app.get("/test")
def test():
    return {"message": "Test"}

@app.post("/create")
def create(test: Test):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            print("Database connected")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS test (
                    id SERIAL PRIMARY KEY,
                    test VARCHAR(255)
                )
                """
            )
            cur.execute(
                """
                INSERT INTO test (test)
                VALUES (%s)
                RETURNING id
                """,
                (test.test,)
            )
            test_id = cur.fetchone()[0]
            conn.commit()
            return {**test.dict(), "id": test_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.put("/update/{id}")
def update(updated_test: Test, id: int):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE test
                SET test = %s
                WHERE id = %s
                RETURNING id, test
                """,
                (updated_test.test, id)  # Pass parameters as a tuple
            )
            updated_row = cur.fetchone()
            if updated_row is None:
                raise HTTPException(status_code=404, detail="Test not found")
            conn.commit()
            return {"id": updated_row[0], "test": updated_row[1]}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.delete("/delete/{id}")
def delete(id:int):
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM test
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
        raise HTTPException(status_code=500,detail=f"Error {e}")    
    finally:
        conn.close()