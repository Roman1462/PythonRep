from datetime import datetime
import peewee as pw
from typing import List, Type

db = pw.SqliteDatabase('diploma.db')

class _BaseModel(pw.Model):
    """Класс доступа к базе данных дипломной работы.
        Attributes: created_at (DateTimeField): Дата/время создания записи
    """
    created_at = pw.DateTimeField(default=datetime.now())

    class Meta():
        """ Связь с базой данных через database."""
        database = db

class _Tables(_BaseModel):
    """
    Общая часть у всех таблиц.
    Attributes:
        id_history (int): Код из таблицы History
        data_key (VarChar): Ключ из API сайта
        data_json (TEXT): Данные ответа на запрос
    """

    # Связь с таблицей истории запросов, на случай если потребуется
    # отследить по какой причине появилась та или иная запись в таблице
    id_history = pw.IntegerField(null=True)

    # Код (ключ) записи из API сайта (на всякий случай разрешить пустые)
    data_key = pw.CharField(null=True)

    # Структурированная запись сведений (JSON)
    data_json = pw.TextField(null=True)

class History(_BaseModel):
    """
    Класс таблица - история запросов к ресурсам сайта (site API)

    Attributes:
        id_users (int): Код пользователя, который делал этот запрос.
        query_type (varchar): Что именно запрашивается (имя класса API), по
            которому уточняем что искали.
        query_string (TEXT): Строка запроса, по которой определяем
            что именно запрашивали.
    """

    # ID пользователя (по таблице UserList), который делал этот запрос
    id_users = pw.IntegerField(null=False)

    # Что именно запрашивается (callback, message, ...)
    query_type = pw.CharField(null=True)

    # Строка запроса (введено или название кнопки)
    query_string = pw.TextField(null=True)

    class Meta:
        db_table = 'History'


class _Actors(_Tables):
    """
    Общая часть по актёрам, которые снимались в фильмах.

    Attributes:
        actor_name (varchar): Имя актёра.
    """
    actor_name = pw.CharField(null=False)  # Имя актёра


class ActorFilms(_Actors):
    """
    Класс таблица - кэш ответов по актёрам, которые снимались в фильмах.
    """

    class Meta:
        db_table = 'ActorFilms'


class ActorNews(_Actors):
    """
    Класс таблица - кэш ответов новостей по актёрам.

    Attributes:
        actor_key (объявлен в _Actors): Кодовое значение актёра

        message (объявлен в _Tables): Все новости об актёре/актрисе.
    """

    class Meta:
        db_table = 'ActorNews'


class ActorBio(_Actors):
    """
    Класс таблица - кэш ответов по биографии актёров.

    Attributes:
        actor_key (объявлен в _Actors): Кодовое значение актёра

        message (объявлен в _Tables): Вся биография актёра/актрисы.
    """

    class Meta:
        db_table = 'ActorBio'


class FilmNews(_Tables):
    """
    Класс таблица - кэш ответов новостей по фильмам.

    Attributes:
        film_key (объявлен в _Films): Кодовое значение фильма

        message (объявлен в _Tables): Все новости о фильме
    """
    class Meta:
        db_table = 'FilmNews'

class FilmInfo(_Tables):
    """
    Класс таблица - кэш ответов информации по фильмам.
    """
    # Тип фильма (кино, сериал и т.п.)
    film_type = pw.CharField(null=False)

    # Название фильма
    film_name = pw.CharField(null=False)

    class Meta():
        db_table = 'FilmInfo'

class UserList(_BaseModel):
    """
    Класс таблица - список пользователей и уровень их прав.
    Права устанавливаются админом. Кто первый зашёл, тот админ.

    Attributes:
    """
    # Unique identifier for this user or bot. This number may have more
    # than 32 significant bits and some programming languages may have
    # difficulty/silent defects in interpreting it. But it has at most
    # 52 significant bits, so a 64-bit integer or double-precision float
    # type are safe for storing this identifier.
    id_user = pw.BigIntegerField(null=False, unique=True)

    # Value `True`, if this user is a bot
    is_bot = pw.BooleanField(null=False, default=False)

    # User's or bot's first name
    first_name = pw.CharField(null=True)

    # User's or bot's last name
    last_name = pw.CharField(null=True)

    # User's or bot's username
    username = pw.CharField(null=True)

    # Значение `True`, если этот пользователь является администратором
    is_admin = pw.BooleanField(null=False, default=False)

    # Значение `True`, если этот пользователь дал согласие на обработку ПД
    is_agree = pw.BooleanField(null=False, default=True)

    class Meta:
        db_table = 'user_list'

class FilesForBot(_BaseModel):
    """
    Список файлов, которые загрузили в телеграм и их коды.
    Attributes:
    """
    # Тип файла (image, video, document, ...)
    file_type = pw.CharField(null=False, max_length=10)

    # Имя файла (URL источника для точной идентификации)
    file_name = pw.TextField(null=False)

    # Код файла в телеграм-боте
    file_code = pw.TextField(null=False)

    class Meta:
        db_table = 'files_for_bot'

# Список таблиц для более удобного их создания (через цикл)
tables_list: List[Type] = [
    UserList,
    History,
    FilmInfo,
    ActorFilms,
    FilesForBot
]

if __name__ == "__main__":
    ActorNews()
    ActorFilms()
    ActorBio()
    FilmNews()
    FilmInfo()
    History()
    UserList()
