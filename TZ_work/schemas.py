from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from models import *
from translate import Translator
import datetime
from random import randint

#Получает пользоваля
async def get_users(session: AsyncSession, id, name, lang) -> list[Users]:
    if id is not None:
        id = Users.id == id
    else:
        id = True
        
    if name is not None:
        name = Users.name == name
    else:
        name = True
        
    if lang is not None:
        lang = Users.lang == lang
    else:
        lang = True

    result = await session.execute(select(Users).where(id, name, lang))
    return result.scalars().all()

#Создает нового пользователя
def add_user(session: AsyncSession, name: str, lang: str):
    new_user = Users(name=name, lang=lang)
    session.add(new_user)
    return new_user
    
#Получает достижения
async def get_achieves(session: AsyncSession, id, name, count) -> list[Achievements]:
    if id is not None:
        id = Achievements.id == id
    else:
        id = True
        
    if name is not None:
        name = Achievements.name == name
    else:
        name = True
        
    if count is not None:
        count = Achievements.count == count
    else:
        count = True
        

    result = await session.execute(select(Achievements).where(id, name, count))
    return result.scalars().all()

#Создает новое достижение    
def create_achieve(session: AsyncSession, name: str, count: int, text: str):
    new_achive = Achievements(name=name, count=count, text=text)
    session.add(new_achive)
    return new_achive
    

#Получение информации о выдаче достижения (ИД пользователя, ИД достижения, время выдачи)
async def get_belong_achieves(session: AsyncSession, id, user_id, achieve_id) -> list[BelongAchievements]:
    if id is not None:
        id = BelongAchievements.id == id
    else:
        id = True
        
    if user_id is not None:
        user_id = BelongAchievements.user_id == user_id
    else:
        user_id = True
        
    if achieve_id is not None:
        achieve_id = BelongAchievements.achieve_id == achieve_id
    else:
        achieve_id = True

    result = await session.execute(select(BelongAchievements).where(id, user_id, achieve_id))       
    
    return result.scalars().all()

#Выдача достижений пользователю
def give_achieve(session: AsyncSession, user_id: str, achieve_id: str):
    #Рандомная дата от сегодняшней на 10 дней
    """issue_date = datetime.datetime.utcnow() + datetime.timedelta(days=randint(1,10))
    new_achive = BelongAchievements(user_id=user_id, achieve_id=achieve_id, issue_date=issue_date)"""
    
    #Текущая дата
    new_achive = BelongAchievements(user_id=user_id, achieve_id=achieve_id)
    
    session.add(new_achive)
    return new_achive
    
#получение достижений пользователя
async def get_user_achieve(session, id):
    user = await session.execute(select(Users).where(Users.id == id))
    user = user.scalars().all()
    if len(user) < 0:
        return {"status" : "error", "message" : "user not found"}

    lang = user[0].lang
    achieves = await session.execute(select(Achievements, BelongAchievements).join(BelongAchievements).where(BelongAchievements.user_id == id))
    a = achieves.all()
    
    achieves = []
    
    for i in a:
        name = i[0].name
        text = i[0].text
        if lang != "ru":
            translator = Translator(from_lang="ru", to_lang=lang)
            text = translator.translate(text)
            name = translator.translate(name)
        achieves.append({"id": i[1].id, "name" : name, "count" : i[0].count, "text" : text, "issue_date" : i[1].issue_date})
 
        
    return achieves
    
async def get_static_data(session):
    
    #пользователь с максимальным количеством достижений (штук); ◦
    achieve = await session.execute(select(BelongAchievements, func.count(BelongAchievements.id)).group_by(BelongAchievements.user_id).order_by(BelongAchievements.id))
    achieve = achieve.first()
    
    #пользователь с максимальным количеством очков достижений (баллов суммарно);
    
    sum_scope_user_id = await session.execute(select(BelongAchievements, Achievements, func.sum(Achievements.count).label("cc")).join(BelongAchievements, BelongAchievements.achieve_id == Achievements.id).group_by(BelongAchievements.user_id).order_by(text('cc desc')))
    sum_scope_user_id = sum_scope_user_id.all()
    deff_scope_user_id = sum_scope_user_id
    sum_scope_user_id = sum_scope_user_id[0]
    
    #пользователи с минимальной и максимальной разностью очков достижений(разность баллов между пользователями); ◦
    
    max_deff = -1000000000 
    max_users_id = []
    min_deff = 1000000000
    min_users_id = []

    for i in deff_scope_user_id:
        for j in deff_scope_user_id:
            if i[0].user_id != j[0].user_id:
                deff = i[1].count - j[1].count
                if abs(deff) > max_deff:
                    max_deff = abs(deff)
                    max_users_id = [i[0].user_id, j[0].user_id]
                    
                if abs(deff) < min_deff:
                    min_deff = abs(deff)
                    min_users_id = [i[0].user_id, j[0].user_id]
    # пользователи, которые получали достижения 7 дней подряд (по дате выдачи, хотя бы одно в каждый из 7 дней).
    days = await session.execute(text("SELECT a.user_id, COUNT(a.user_id) FROM belong_achievements a, belong_achievements b WHERE ROUND(julianday(a.issue_date) - julianday(b.issue_date)) = 0 AND a.id != b.id AND a.user_id = b.user_id GROUP BY a.user_id"))
    days = days.all()
    print(days)
    users_7_days = []
    for i in days:
        if i[1] >= 7:
            users_7_days.append(i[0])
        
    
    

    return {"max_achievements" : {"user_id" : achieve[0].user_id, "count" : achieve[1]}, "max_sum_count_scope" : {"user_id" : sum_scope_user_id[0].user_id, "count" : sum_scope_user_id[2]}, "max_deff_count_scope" : {"users_id" : max_users_id, "count" : max_deff}, "min_deff_count_scope" : {"users_id" : min_users_id, "count" : min_deff}, "users_7_days" : users_7_days}
    
