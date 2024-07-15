from settings import logger

import json
import peewee as pw
from typing import Dict, List, TypeVar, Any, Tuple

import database.common.models as models
from database.common.models import db, UserList, History, ActorFilms

T = TypeVar("T")

class CRUDInterface:
    """
    Интерфейс для создания и чтения данных в БД
    """
    @classmethod
    def create(cls, model: T, *data: List[Dict]) -> None:
        """
        Записать данные в БД

        :param model: Таблица
        :param data: Набор данных для записи

        :return: None
        """
        # Исключил параметр "param_db: db"
        with db.atomic():
            model.insert_many(*data).execute()

        log.debug('Добавление в таблицу {} записей в количестве {} шт.'.
                  format(model.__name__, len(*data)))
        return

    @classmethod
    def retrieve(cls, model: T, *columns, **param_where) -> pw.ModelSelect:
        """
        Чтение из БД

        :param model: Таблица
        :param columns: Набор полей
        :param param_where: Условие выборки данных

        :return: None
        """
        # Исключил параметр "param_db: db"
        with db.atomic():
            if len(param_where):
                response = model.select(*columns).where(param_where)
            else:
                response = model.select(*columns)

        log.debug('Чтение из БД вернуло данные с типом {} длиной {}'.
                  format(type(response), len(response)))
        return response

    @classmethod
    def execute_sql(cls, sql_text: str = 'SELECT 1', is_one: bool = False) \
            -> List | Tuple | str:
        """
        Выполнение произвольных запросов SQL созданных пользователем

        :param sql_text: Скрипт запроса (SQL)
        :param is_one: Истина, если нужна только одно значение
        (одно поле, одна запись)

        :return: Результат работы запроса (список, кортеж или строка)
        """
        with db.atomic():
            if is_one:
                result = db.execute_sql(sql=sql_text).fetchone()
                log.debug('SQL запрос вернул тип {} длиной {}'.
                          format(type(result), len(result)))
                if isinstance(result, tuple) and len(result) == 1:
                    result = str(result[0])
                else:
                    result = str(result)
            else:
                result = db.execute_sql(sql=sql_text).fetchall()
                log.debug('SQL запрос вернул {} записей'.format(len(result)))
        return result


class TGUsersInterface:
    """
    Класс, обеспечивающий интерфейс с базой данных на более специфических
    задачах. Каждый метод имеет определённый функционал и нарушает
    универсальность пакета.
    """

    @classmethod
    def get_user_info(cls, data_set: Dict, get_id: int) -> Dict[str, Any]:
        """
        Вернуть информацию о пользователе из базы данных.
        Если нет пользователя с нужным ID, то добавить запись
        в БД. После сделать попытку чтения и вернуть результат.

        :param get_id: Уникальный код пользователя в телеграм.
        :type get_id: int

        :param data_set: Структура для записи данных.
        :type data_set: Dict

        :return: Полученные данные из базы данных (только первая запись)
        :rtype: Dict[str:Any]
        """

        result: Dict = dict()
        no_data: bool = False  # Результат первого запроса пуст
        with db.atomic():
            while True:
                # Получить данные из БД
                response = UserList.select().where((
                        UserList.id_user == get_id
                )).limit(1).get_or_none()
                if response or (no_data and data_set):
                    # Если есть данные или уже одна итерация прошла,
                    # то копируем в result
                    result['id'] = response.id
                    result['created_at'] = response.created_at
                    result['id_user'] = response.id_user
                    result['is_bot'] = response.is_bot
                    result['first_name'] = response.first_name
                    result['last_name'] = response.last_name
                    result['username'] = response.username
                    result['is_admin'] = response.is_admin
                    result['is_agree'] = response.is_agree
                    break
                no_data = True

                # Добавить запись в базу данных (если есть данные)
                if data_set:
                    UserList.insert(data_set).execute()

        # Закончили. Вернуть одну запись из БД, если есть такая
        return result

    @classmethod
    def get_last_record_from_history(cls, user_id: int) -> Dict:
        """
        Получить ID записи для абонента "user_id" из таблицы истории запросов.

        :param user_id: ID абонента в телеграм (не код строки записи о пользователе!).
        :type user_id: int

        :return: Последняя запись из таблицы History (для связи вопрос-ответ)
        :rtype: Dict
        """

        result = {}
        with db.atomic():
            try:
                record: History = History.select()\
                    .where(History.id_users == user_id)\
                    .order_by(History.id.desc()).limit(1).get()
                result = {
                    'id': record.get_id(),
                    'created_at': record.created_at,
                    'users_id': record.id_users,
                    'query_type': record.query_type,
                    'query_string': record.query_string
                }
            except pw.DoesNotExist as err:
                log.exception('Ошибка получении последней записи из '
                              f'истории абонента {user_id}: {str(err)}')

        return result

    @classmethod
    def get_actor_by_id(cls, actor_id: str) -> Dict:
        """
        Вернуть информацию об актёре по ID актёра.

        :param actor_id: Уникальный код актёра в БД
        :type actor_id: str

        :return: Сведения в виде словаря. Если нет такой записи,
            то словарь пустой
        :rtype: Dict
        """

        with db.atomic():
            query: ActorFilms = ActorFilms.select()\
                .where(ActorFilms.data_key == actor_id).get_or_none()
        result = dict()

        if query:
            result['id'] = query.get_id()
            result['actor_id'] = query.data_key
            result['actor_info'] = query.data_json

        return result

    @classmethod
    def save_actor_if_absent(cls, actor_info: Dict,
                             history_id: int | str = '') -> None:
        """
        Записать в базу данных актёра, если информации с указанным кодом
        нет в базе данных (таблица ActorFilms).

        :param actor_info: Полная информация об актёре для записи.
        :type actor_info: Dict
        :param history_id: ID записи из таблицы истории запросов.
        :type history_id: int | str
        :return:
        """

        # Преобразовать ID истории запроса в строку
        if isinstance(history_id, int):
            history_id = str(history_id)

        actor_id = actor_info.get('id', actor_info.get('actor_id', ''))
        check_item = cls.get_actor_by_id(actor_id)
        if check_item:
            return

        # Мы тут, значит надо записать данные
        actor_json = json.dumps(actor_info, ensure_ascii=False, indent=4)
        with db.atomic():
            # Получить имя актёра (если нет русского варианта, взять альтернативный)
            actor_name = actor_info.get('name', '')
            if not actor_name:
                actor_name = actor_info.get('enName', 'None!')

            # Добавить актёра в БД
            ActorFilms.insert({'id_history': history_id,
                               'data_key': actor_id,
                               'data_json': actor_json,
                               'actor_name': actor_name
                               }).execute()
        return

    @classmethod
    def update(cls, model: T, *new_data, **param_what) -> None:
        # Исключил параметр "param_db: db"
        with db.atomic():
            model.update(new_data).where(param_what).execute()

        return


def get_file_id(file_url: str) -> str:
    """
    Получить ID файла из базы данных.

    :param file_url: Ссылка на файл
    :type file_url: str

    :return: ID файла
    :rtype: str
    """
    result = ''
    if file_url:
        data = models.FilesForBot.get_or_none(
            models.FilesForBot.file_name == file_url
        )
        if data:
            result = data.file_code

    return result


def save_file_id(file_url: str, file_id: str) -> None:
    """
    Сохранить ID файла в базу данных.

    :param file_url: Ссылка на файл
    :type file_url: str
    :param file_id: ID файла
    :type file_id: str

    :return: None
    """
    if (not file_url) or (not file_id):
        return

    # Определим тип файла по URL
    if file_url.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.tif')):
        file_type = 'image'
    elif file_url.lower().endswith(('.avi', '.mpg', '.mpeg', '.mp4', '.mkv')):
        file_type = 'video'
    elif file_url.lower().endswith(('.doc', '.docx', '.xls', '.xlsx',
                                    '.rar', '.zip', '.7z', '.ppt')):
        file_type = 'document'
    else:
        file_type = 'unknown'

    # Готовим структуру для записи в БД и создаём запись
    file_info = {
        'file_type': file_type,
        'file_name': file_url,
        'file_code': file_id
    }
    with db.atomic():
        models.FilesForBot.insert(file_info).execute()

    return

# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)

if __name__ == "__main__":
    CRUDInterface()
    TGUsersInterface()
    get_file_id()
    save_file_id()
