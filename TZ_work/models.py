from database import Base, init_models
from sqlalchemy import  Column, Integer, String, DateTime, ForeignKey
import datetime
import asyncio

class Users(Base):
    #Название таблицы
    __tablename__ = "users"
    #Ид пользователя
    id = Column(Integer, primary_key=True, index=True)
    #Имя пользователя (ограничено 30 символами)
    name = Column(String(30))
    #Текст
    lang = Column(String(4))
    
class Achievements(Base):
    #Название таблицы
    __tablename__ = "achievements"
    #Ид достижения
    id = Column(Integer, primary_key=True, index=True)
    #Название достижения (ограничен 30 символами)
    name = Column(String(30))
    #Количество очков
    count = Column(Integer)
    #Описания достижения
    text = Column(String)
    
class BelongAchievements(Base):
    #Название таблицы
    __tablename__ = "belong_achievements"
    #Ид
    id = Column(Integer, primary_key=True, index=True)
    #Ид пользователя
    user_id = Column(Integer, ForeignKey('users.id'))
    #Ид достижения
    achieve_id = Column(Integer, ForeignKey('achievements.id'))
    #Время выдачи достижения
    issue_date = Column(DateTime, default=datetime.datetime.utcnow)


if __name__ == "__main__":
    #При запуске из терминала, создаются таблицы
    asyncio.run(init_models())
    print("Done")
