from fastapi import FastAPI
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from database import init_models
from database import get_session

import schemas
import database
import asyncio
import datetime

#Запуск веб приложения
app = FastAPI()

class UserSchema(BaseModel):
    name: str
    lang: str
    
class AchieveSchema(BaseModel):
    name: str
    count: int
    text: str

class BelongAchieveSchema(BaseModel):
    user_id: int
    achieve_id: int

#При переходе по адресу /users/get получаем пользователей. Запрос GET
@app.get("/users/get")
async def get_users(id : int = None, name : str = None, lang : str = None, session: AsyncSession = Depends(get_session)):
    user = await schemas.get_users(session, id=id, name=name, lang=lang)

    return user
    
#При переходе по адресу /users/add добавляем пользователя. Запрос POST    
@app.post("/users/add")
async def add_user(user: UserSchema, session: AsyncSession = Depends(get_session)):
    new_user = schemas.add_user(session, user.name, user.lang)
    await session.commit()
    return new_user
    
#При переходе по адресу /achieve/add получаем достижения. Запрос GET  
@app.get("/achieve/get")
async def get_achieves(id : int = None, name : str = None, count : str = None, session: AsyncSession = Depends(get_session)):
    achive = await schemas.get_achieves(session, id=id, name=name, count=count)
    return achive
    
#При переходе по адресу /achieve/add добавляем достижение. Запрос POST  
@app.post("/achieve/add")
async def create_achieve(achive: AchieveSchema, session: AsyncSession = Depends(get_session)):
    if achive.count <= 0:
        return {"status" : "error", "message" : "'count' - the number must be completed"}
    achive = schemas.create_achieve(session, name=achive.name, count=achive.count, text=achive.text)
    await session.commit()
    return achive
    
#Выдаем достижения. Запрос POST. Адрес: /achieve/give
@app.post("/achieve/give")
async def give_achive(achive: BelongAchieveSchema, session: AsyncSession = Depends(get_session)):

    if achive.user_id <= 0:
        return {"status" : "error", "message" : "'user_id' - the number must be completed"}
    elif achive.achieve_id <= 0:
        return {"status" : "error", "message" : "'achieve_id' - the number must be completed"}
    achive = schemas.give_achieve(session, user_id=achive.user_id, achieve_id=achive.achieve_id)
    await session.commit()
    return achive

#Получаем выданные достижения. Запрос GET. Адрес: /achieve/get_belong
@app.get("/achieve/get_belong")
async def get_belong_achieve(id : int = None, user_id : int = None, achieve_id : int = None, session: AsyncSession = Depends(get_session)):
    achive = await schemas.get_belong_achieves(session, id=id, user_id=user_id, achieve_id=achieve_id)
    return achive
    
#Получаем достижения пользователя на выбранном им языке. Запрос GET.
#Адрес: /achieve/get_by_user_id    
@app.get("/achieve/get_by_user_id")
async def get_user_achieve(id : int, session: AsyncSession = Depends(get_session)):
    achive = await schemas.get_user_achieve(session, id=id)
    return achive
    
#Получаем статические данные. Запрос GET.
#Адрес: /get_static_data      
@app.get("/get_static_data")
async def get_static_data(session: AsyncSession = Depends(get_session)):
    achive = await schemas.get_static_data(session)
    return achive
