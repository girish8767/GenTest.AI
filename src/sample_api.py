from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI(title="Sample API", version="1.0.0")

class User(BaseModel):
    name: str
    email: str
    age: int

users_db: Dict[int, dict] = {}

@app.get("/")
async def root():
    return {
        "message": "Welcome to API Testing Service",
        "version": "1.0.0",
        "endpoints": {
            "/api/users": "POST - Create a new user",
            "/api/users/{user_id}": "GET - Retrieve a user"
        }
    }

@app.post("/api/users", status_code=201)
async def create_user(user: User):
    user_dict = user.dict()
    user_dict["id"] = len(users_db) + 1
    users_db[user_dict["id"]] = user_dict
    return user_dict

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]