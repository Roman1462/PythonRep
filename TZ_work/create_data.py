import requests
from random import randint
users = [
    {
        "name" : "Иван",
        "lang" : "ru"
    },
    {
        "name" : "Вася",
        "lang" : "ru"
    },
    {
        "name" : "Олег",
        "lang" : "ru"
    },
    {
        "name" : "Игорь",
        "lang" : "ru"
    },
    {
        "name" : "Дмитрий",
        "lang" : "ru"
    },
    {
        "name" : "John",
        "lang" : "en"
    },
    {
        "name" : "Elvis",
        "lang" : "en"
    },
    {
        "name" : "Eric",
        "lang" : "en"
    },
    {
        "name" : "Bob",
        "lang" : "en"
    },
    {
        "name" : "Lui",
        "lang" : "en"
    }
]


achieve = [
    {
        "name" : "Начинающий пользователь",
        "count" : 10,
        "text" : "Выдается начинающему пользователю, который только начинает знакомиться с компьютерной системой."
    },
    {
        "name" : "Пользователь",
        "count" : 25,
        "text" : "Выдается пользователю, имеющему некоторый пользовательский опыт."
    },
    {
        "name" : "Уверенный пользователь",
        "count" : 40,
        "text" : "Выдается уверенному пользователю, имеющий хороший опыт и знания, для работы в компьютерных системах."
    },
    {
        "name" : "Хацкерок",
        "count" : 65,
        "text" : "Начинающий хакер, владеющий теоритической базой и небольшим опытом о обходе компьютерных систем."
    },
    {
        "name" : "Хакер",
        "count" : 80,
        "text" : "Хакер, владеющий достаточным опытом и знаниями, что бы обойти систему средней сложности."
    },
    {
        "name" : "Кибер-Бог",
        "count" : 100,
        "text" : "Хакер, владющий достаточный опыто и знаниями, что бы обойти компьютерную систему любой сложности."
    }
]


#Создание пользователей
for i in range(len(users)):
    res = requests.post("http://127.0.0.1:8000/users/add", json={"name" : users[i]["name"], "lang" : users[i]["lang"]})
    print(res.text)

#Создание достижений
for i in range(len(achieve)):
    res = requests.post("http://127.0.0.1:8000/achieve/add", json={"name" : achieve[i]["name"], "count" : achieve[i]["count"], "text" : achieve[i]["text"]})
    print(res.text)
  
countAchieve = {}
for i in range(len(users)):   
    countAchieve[i] = 0
    
#Выдача достижений пользователю
for i in range(10):
    user_id = randint(0, len(users) - 1)
    achieve_id = randint(0, len(achieve) - 1)
    res = requests.post("http://127.0.0.1:8000/achieve/give", json={"user_id" : user_id + 1, "achieve_id" : achieve_id + 1})
    print(res.text)
    countAchieve[user_id] += achieve[achieve_id]["count"]


#Вывод максимального количества очков для проверки работы запросов
print("max_sum_count_achieve:", max(countAchieve.values()))
