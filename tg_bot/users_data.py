"""
Модуль для работы с таблицами и словарями пользователей. 
Использует объекты из пакетов (телеграм, сайт, база данных) для
формирования информации в телеграм.
"""

from settings import logger
from datetime import datetime
from time import strftime
from typing import Dict, List, Tuple
import re
import json

from aiogram.types import User, Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
import aiogram.exceptions

import peewee
from peewee import IntegrityError

from database.core import crud
from database.utils.crud import TGUsersInterface
import database.common.models as models

from tg_API.utils.commands import get_message, send_photo_by_url
from tg_API.utils.keys import builder_random_films, builder_start, \
    builder_custom_buttons, buttons_search_films, buttons_search_persons
from tg_API.utils.commands import safe_send_message

from templates import load_template

from site_API.core import site_api


def check_admin_rights_in_db(from_user: User) -> bool:
    """
    Проверка наличия уровня прав администратора.

    :param from_user: Объект, связанный с пользователем в телеграм.
    :type from_user: User

    :return: Истина, если пользователь является админом, иначе Ложь
    :rtype: bool
    """

    result: bool = False
    try:
        # Получить данные из базы данных (при отсутствии добавить)
        data: Dict = {
            "id_user": from_user.id,
            "is_bot": from_user.is_bot,
            "first_name": from_user.first_name,
            "last_name": from_user.last_name,
            "username": from_user.username,
        }
        response = TGUsersInterface().get_user_info(
            get_id=from_user.id,
            data_set=data
        )

        if response.get("id", 0) == 1:
            if not response.get("is_admin"):
                # Первая запись - назначить админом. По ИБ неразумно,
                # но в ТЗ такое ограничение не указано.
                response["is_admin"] = True
                models.UserList.set_by_id(1, {"is_admin": True})

        result = bool(response.get("is_admin"))
    except peewee.PeeweeException:
        log.exception(
            "Ошибка проверки административных прав пользователя",
            exc_info=True
        )
    return result


def register_user_action_query(action: CallbackQuery | Message) -> Dict:
    """
    Запись действия пользователя в таблицу истории и вернуть запись из
    словаря (кеша) по данному пользователю.

    :param action: Событие пользователя в телеграм-чате (кнопка или текст).
    :type action: CallbackQuery или Message

    :return: Словарь (кеш) пользователя, который указан в action.from_user
    В словаре ключи соответствуют именам полей в таблицах, куда что-либо
    записывается. А также ключ stage - в каком режиме находится
    взаимодействие с этим пользователем (запрос и ожидание).
    :rtype: Dict
    """

    # Получить сведения о пользователе
    if isinstance(action, CallbackQuery):
        user_id = action.from_user.id
    else:
        user_id = action.chat.id

    # Записываем событие в историю для пользователя
    data = {'id_users': user_id}
    if isinstance(action, CallbackQuery):
        data['query_type'] = 'callback'
        data['query_string'] = action.data
    else:
        data['query_type'] = 'message'
        data['query_string'] = action.text
    crud.create(models.History, data)

    # Получить ID записи в истории для последнего события
    result = TGUsersInterface.get_last_record_from_history(user_id)

    return result


async def search_film(action: CallbackQuery | Message,
                      state: FSMContext = None,
                      history: Dict = None
                      ) -> bool:
    """
    Поиск фильма по фильтру.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Пример: https://api.kinopoisk.dev/v1.3/movie
    # ?page=1&limit=10&type=movie&year=2020-2023
    # &genres.name=%D0%B1%D0%BE%D0%B5%D0%B2%D0%B8%D0%BA
    # &genres.name=%D1%84%D0%B0%D0%BD%D1%82%D0%B0%D1%81%D1%82%D0%B8%D0%BA%D0%B0

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = register_user_action_query(action)
    history_id = history.get('id')

    # Создаём кнопки для работы фильтра в зависимости от накопленных действий
    current_state = await state.get_state()
    log.debug('Поиск фильма по фильтру. ID истории {}. Статус "{}".'.
              format(history_id, current_state))
    if current_state and (current_state == 'FilterState:command_doit'):
        # Выполнить сформированный запрос
        log.debug("Перед запросом. Контроль")

        await safe_send_message(message, 'Первые 10 фильмов по запросу:')
        data = await state.get_data()
        our_filter = dict()
        if 'filter_name' in data:
            our_filter['name'] = data.get('filter_name')
        if 'filter_en_name' in data:
            our_filter['enName'] = data.get('filter_en_name')
        if 'filter_type' in data:
            our_filter['type'] = data.get('filter_type')
        if 'filter_year' in data:
            our_filter['year'] = data.get('filter_year')
        if 'filter_rating_kp' in data:
            our_filter['rating.kp'] = data.get('filter_rating_kp')
        if 'filter_rating_imdb' in data:
            our_filter['rating.imdb'] = data.get('filter_rating_imdb')
        if 'filter_age_rating' in data:
            our_filter['ageRating'] = data.get('filter_age_rating')
        if 'filter_genres' in data:
            our_filter['genres.name'] = data.get('filter_genres')
        log.debug('Фильтр для запроса: {}'.format(our_filter))

        response = 0
        try:
            response = site_api.get_film_by_filter(our_filter)
        except BaseException as err:
            log.exception(err, exc_info=True)
        log.debug('После запроса. Контроль. {0}'.format(type(response)))

        if isinstance(response, int):
            await safe_send_message(message,
                                    'Ошибка {} получения сведений о фильме'.
                                    format(response))
            return False
        data: Dict = json.loads(response.text)
        log.debug('Получено фильмов {} шт.'.format(len(data)))

        for i_item in data.get('docs', []):
            await send_film_info(message, i_item, history_id)

        await state.clear()
    else:
        # Подготовить параметры для запроса
        out_text = 'Формируем фильтр для поиска фильмов:'
        buttons = builder_custom_buttons(out_text,
                                         buttons=buttons_search_films)
        await safe_send_message(message, out_text, buttons)
        log.debug(out_text[:-1])

    return True


def calculation_of_statistical_data(query_string: str,
                                    user_id: str,
                                    use_today: bool = False) -> str:
    """
    Расчёт статистики запросов.

    :param query_string: Строка, по которой делаем подсчёт записей
    :type query_string: str

    :param user_id: ID пользователя в базе данных
    :type user_id: str

    :param use_today: Подсчёт за сегодня (истина) или в целом (ложь)
    :type use_today: bool

    :return: Числовое значение строкового типа (для удобства добавления
    к выводимому тексту)
    """
    # Общая часть всех запросов
    query_text = 'SELECT count(h.id) quantity FROM History h ' \
                 'WHERE h.query_string like "{string}" AND ' \
                 'h.id_users = {user}'.format(string=query_string,
                                              user=user_id)

    # Учитывать сегодняшний день в запросах
    if use_today:
        query_text += ' AND h.created_at like CAST(date("NOW") AS VARCHAR) ' \
                      '|| " %"'

    # Выполнить запрос и вернуть его результат
    total = crud.execute_sql(query_text, is_one=True)
    return total


async def get_history_info(callback: CallbackQuery | Message,
                           data_key: List = None,
                           state: FSMContext = None
                           ) -> bool:
    """
    Получить историю действий пользователя за дату, которую выбирает
    пользователь. По умолчанию сегодня. Возвращает текст и набор кнопок

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(callback)

    query_date = 'сегодня'
    if len(data_key):
        query_date = data_key[0]
    out_text_lines = [f'История Ваших запросов за <b>{query_date}</b>:', '']
    user_id = str(message.chat.id)

    # Есть ли дата в запросе. Если нет, то рекурсивный вызов с текущей датой
    if len(data_key):
        query_text = 'SELECT id, substr(created_at, 12, 8) only_time, ' \
                     'query_string FROM History WHERE id_users = ' \
                     f'"{user_id}" AND created_at like "{query_date}%"'
        records = crud.execute_sql(query_text)
        if records:
            # Данные получены из базы данных. Формируем отчёт
            log.debug('Получено {} записей из истории запросов пользователя'.
                      format(len(records)))
            # print(records)
            for i_record in records:
                # print(i_record)
                temp_text = '{time} {event}.'
                string_time = i_record[1]
                event_code = i_record[2]

                # Анализ событий из истории запросов
                event_list = event_code.split('.')
                if event_list[0] in ('st', 'ap', 'af', 'bp', 'bf'):
                    # Для совместимости со старой версией БД
                    event_list[0] += '_' + event_list.pop(1)

                if event_list[0].startswith('st'):
                    if event_list[0].endswith('want_film'):
                        event_code = 'Предложен случайный фильм'
                        try:
                            film_list = models.FilmInfo.select().where(
                                models.FilmInfo.id_history == i_record[0]
                            )
                            if film_list:
                                films_list = []
                                for i_film in film_list:
                                    films_list.append(i_film.film_name)
                                event_code += ' (' + ', '.join(films_list) + ')'
                        except peewee.PeeweeException as err:
                            log.exception('Ошибка в запросе {}: {}'.
                                          format(type(err), str(err)),
                                          exc_info=True)
                    elif event_list[1] == 'search_film':
                        event_code = 'Поиск фильмов по фильтру'
                    elif event_list[1] == 'search_person':
                        event_code = 'Поиск актёров по фильтру'
                elif event_list[0] == 'bf_doit':
                    event_code = 'Выполнен поиск фильмов по фильтру'
                elif event_list[0] == 'bp_doit':
                    event_code = 'Выполнен поиск персон по фильтру'
                elif event_list[0] == 'af_persons':
                    event_code = 'Просмотр списка актёров фильма'
                    try:
                        film_list = models.FilmInfo.select().where(
                            models.FilmInfo.data_key == event_list[1]
                        )
                        if film_list:
                            films_list = []
                            for i_film in film_list:
                                films_list.append(i_film.film_name)
                            event_code += ' (' + ', '.join(films_list) + ')'
                    except peewee.PeeweeException as err:
                        log.exception('Ошибка в запросе {}: {}'.
                                      format(type(err), str(err)),
                                      exc_info=True)
                elif event_list[0] in ('ap_persons', 'ap_one_person'):
                    event_code = 'Просмотр информации об актёре'
                    try:
                        item_list = models.ActorFilms.select().where(
                            models.ActorFilms.data_key == event_list[2]
                        )
                        if item_list:
                            items_list = []
                            for i_item in item_list:
                                items_list.append(i_item.actor_name)
                            event_code += ' (' + ', '.join(items_list) + ')'
                    except peewee.PeeweeException as err:
                        log.exception('Ошибка в запросе {}: {}'.
                                      format(type(err), str(err)),
                                      exc_info=True)

                temp_text = temp_text.format(time=string_time,
                                             event=event_code)
                out_text_lines.append(temp_text)
        else:
            # Данные не получены из базы данных
            out_text_lines.append('Нет данных за дату ' + data_key[0])
    else:
        # Рекурсивный вызов с текущей датой
        query_date = strftime('%Y-%m-%d')
        await get_history_info(callback, [query_date], state)
        return True

    query_text = 'SELECT DISTINCT substr(created_at, 1, 10) only_date ' \
                 f'FROM History WHERE id_users = "{user_id}" ORDER BY ' \
                 f'only_date DESC'
    query_data = crud.execute_sql(query_text)
    buttons_list = []
    for i_data in query_data:
        buttons_list.append((str(i_data[0]), f'mm_history.{i_data[0]}'))
        if len(buttons_list) > 15:
            break  # Ограничимся 16ю последними событиями

    # Вернуть результат для вывода пользователю
    out_text = '\n'.join(out_text_lines)
    out_text += '\n\nКонец списка истории запросов'

    buttons = builder_custom_buttons(text=out_text, buttons=buttons_list)

    await safe_send_message(message, out_text, buttons)
    return True


async def send_film_info(action: Message,
                         response_text: str | Dict,
                         history_id: str
                         ) -> None:
    """
    Вывести информацию о фильме с подробностями.

    :param action: Связующий объект с чат-ботом
    :type action: Message

    :param response_text: Ответ с сайта или из БД со сведениями
    :type response_text: str | Dict

    :param history_id: Данные из таблицы истории запросов (только id)
    :type history_id: str

    :return: None
    """
    if response_text is None:
        return  # Нет данных для парсинга или что-то пошло не так

    if isinstance(response_text, dict):
        data: Dict = response_text
    else:
        data: Dict = json.loads(response_text)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Записать полученный ответ для этого пользователя,
    # если такого фильма нет в БД
    if not models.FilmInfo.get_or_none(
            models.FilmInfo.data_key == str(data.get('id'))
    ):
        data_for_save: Dict = {
            'id_history': history_id,
            'data_key': data.get('id'),
            'data_json': json.dumps(data, ensure_ascii=False, indent=4),
            'film_type': data.get('type', ''),
            'film_name': data.get('name', data.get('alternativeName', ''))
        }
        crud.create(models.FilmInfo, data_for_save)

    # Грузим постеры в телеграм для доступа по ID
    try:
        posters = data.get('poster', None)
        if posters:
            poster = posters.get('url', '')
            if poster:
                await send_photo_by_url(url=poster, action=action)
    except BaseException as err:
        log.exception('Ошибка получения или отправки постера: ' + str(err),
                      exc_info=True)

    # Сохраняем актёров в базу данных
    try:
        for i_actor in data.get('persons', {}):
            TGUsersInterface().save_actor_if_absent(i_actor, history_id)
    except TypeError as err:
        log.exception('Ошибка получения актёров: ' + str(err), exc_info=True)
    except (peewee.PeeweeException, IntegrityError) as err:
        log.exception('{0}: Ошибка сохранения актёров: {1}'.
                      format(type(err), str(err)), exc_info=True)

    # Получаем имя фильма, если вдруг нет "основного", то берём из
    # списка альтернативных имён
    film_name = data.get(
        'name',
        data.get('names', [{'name': None}])[0].get("name")
    )

    # Длительность фильма в часах и минутах
    movie_length = data.get('movieLength', 0)
    if isinstance(movie_length, int):
        movie_length_time = '{0} ч {1:02} мин'.format(movie_length // 60,
                                                      movie_length % 60)
    else:
        try:
            movie_length_time = str(movie_length)
        except TypeError:
            movie_length_time = 'Ошибка! ' + type(movie_length)

    # Формируем список жанров
    film_genres = ', '.join([i_data.get('name')
                             for i_data in data.get('genres', {})
                             if 'name' in i_data])

    # Извлекаем список стран
    film_countries = ', '.join([i_data.get('name')
                                for i_data in data.get('countries', {})
                                if 'name' in i_data])

    # Сведения и бюджете фильма
    dict_budget: Dict = data.get('budget', {})
    film_budget = str(dict_budget.get('value', 'Неизвестно')) + \
                  str(dict_budget.get('currency', ''))

    # Формируем полный текст на основе шаблона
    out_text: str = load_template('templates/film_info.txt')
    try:
        out_text = out_text.format(
            name=film_name,
            length=movie_length_time,
            description=data.get('description', 'Нет описания'),
            year=data.get('year'),
            genres=film_genres,
            countries=film_countries,
            id=data.get('id', 0),
            type=data.get('type', 'Нет сведений'),
            budget=film_budget,
            age_rating=data.get('ageRating', 'Нет сведений')
        )
    except KeyError as err:
        log.exception('Ошибка в шаблоне: ' + str(err), exc_info=True)
    except aiogram.exceptions.TelegramBadRequest as err:
        log.exception('Ошибка с файлом: ' + str(err), exc_info=True)

    # Создаём кнопки, если был ответ
    buttons = None
    if out_text:
        buttons = builder_random_films('Что сделать с предложенным?',
                                       str(data.get('id', '')))
    else:
        out_text = 'Внимание! Что-то пошло не по плану. Повторите запрос'

    # Отправить сформированную информацию
    await safe_send_message(message, out_text, buttons)


async def get_random_films(action: CallbackQuery | Message,
                           history: Dict = None
                           ) -> None:
    """
    Получаем информацию о случайном фильме через API сайта-источника

    :param action: Связь с абонентом из обработчика обратного вызова.
    :type action: CallbackQuery | Message

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """

    # Записать сведения о пользователе
    if history is None:
        history = register_user_action_query(action)
    history_id = history.get('id')

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получаем информацию о фильме, а затем парсим результат
    response = site_api.get_random_films()
    if isinstance(response, int):
        await safe_send_message(
            message,
            'Ошибка {} получения сведений о фильме'.format(response)
        )
        return None

    await send_film_info(message, response.text, history_id)
    return None


async def get_rating_films(action: CallbackQuery | Message,
                           data_key: List = None,
                           history: Dict = None
                           ) -> None:
    """
    Вывести информацию о рейтинге фильма.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе
    if history is None:
        register_user_action_query(action)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения о фильме из БД
    buttons = None
    str_key = ''
    if data_key:
        str_key = data_key[0]
    info = models.FilmInfo.get_or_none(models.FilmInfo.data_key == str_key)
    if info:
        data = json.loads(info.data_json)
        # Формируем полный текст на основе шаблона
        out_text: str = load_template('templates/rating_info.txt')
        try:
            out_text = out_text.format(
                name=data.get(
                    'name',
                    data.get('names', [{'name': None}])[0].get("name", None)
                ),
                rating_kp=data.get('rating', {}).get('kp', 'N/A'),
                votes_kp=data.get('votes', {}).get('kp', 'N/A'),
                rating_imdb=data.get('rating', {}).get('imdb', 'N/A'),
                votes_imdb=data.get('votes', {}).get('imdb', 'N/A'),
                rating_tmdb=data.get('rating', {}).get('tmdb', 'N/A'),
                votes_tmdb=data.get('votes', {}).get('tmdb', 'N/A'),
                rating_filmCritics=data.get('rating', {}).get('filmCritics',
                                                              'N/A'),
                votes_filmCritics=data.get('votes', {}).get('filmCritics',
                                                            'N/A'),
                rating_russianFilmCritics=data.get(
                    'rating',
                    {}
                ).get('russianFilmCritics', 'N/A'),
                votes_russianFilmCritics=data.get(
                    'votes',
                    {}
                ).get('russianFilmCritics', 'N/A'),
                rating_await=data.get('rating', {}).get('await', 'N/A'),
                votes_await=data.get('votes', {}).get('await', 'N/A')
            )

            # Создаём кнопки
            buttons = builder_random_films('Что ещё интересно?', str_key)
        except KeyError as err:
            log.exception('Ошибка в шаблоне: ' + str(err), exc_info=True)
        except aiogram.exceptions.TelegramBadRequest as err:
            log.exception('Ошибка с файлом: ' + str(err), exc_info=True)
    else:
        out_text = f"Нет сведений о рейтинге для фильма с ID {str_key}!"
        buttons = builder_start("Начнём сначала...")

    await safe_send_message(message, out_text, buttons)
    # return out_text, buttons
    return None


async def get_companies_films(action: CallbackQuery | Message,
                              data_key: List = None,
                              history: Dict = None
                              ) -> None:
    """
    Вывести сведения о компаниях, принявших участие в съёмках.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе
    if history is None:
        register_user_action_query(action)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения о фильме из БД
    out_text = ''
    str_key = ''
    if data_key:
        str_key = data_key[0]

    info = models.FilmInfo.get_or_none(models.FilmInfo.data_key == str_key)
    if info:
        data = json.loads(info.data_json)
        name = data.get(
            'name',
            data.get('names', [{'name': None}])[0].get("name", None)
        )

        try:
            await safe_send_message(message,
                                    f'Фильм <b>{name}</b> снят:')

            # Извлекаем список компаний, участвующих в создании фильма
            companies: List[Dict] = data.get('productionCompanies', [])
            for i_company in companies:
                # Название компании
                name_item = i_company.get('name')
                if not name_item:
                    continue

                # Ссылка на логотип компании (может и не быть)
                url_item = i_company.get('url')
                if not url_item:
                    url_item = i_company.get('previewUrl')

                # Отправить абоненту информацию
                await send_photo_by_url(
                    url=url_item,
                    text=f'Компания: <b>{name_item}</b>.',
                    action=action
                )

            await safe_send_message(message,
                                    '\nВсего было указано компаний: '
                                    f'<b>{len(companies)}</b> шт.')

        except KeyError as err:
            log.exception('Ошибка в шаблоне: ' + str(err), exc_info=True)
        except (aiogram.exceptions.TelegramBadRequest,
                aiogram.exceptions.TelegramNetworkError) as err:
            log.exception('Ошибка с файлом: ' + str(err), exc_info=True)

        # Создаём кнопки
        buttons = builder_random_films('Что ещё интересно?', str_key)
    else:
        out_text = f"Нет сведений о рейтинге для фильма с ID {str_key}!"
        buttons = builder_start("Начнём сначала...")

    await safe_send_message(message, out_text, buttons)
    # return out_text, buttons
    return None


async def get_persons_films(action: CallbackQuery | Message,
                            data_key: List = None,
                            history: Dict = None
                            ) -> None:
    """
    Вывести сведения об актёрах фильма.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        register_user_action_query(action)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения о фильме из БД
    buttons = None
    buttons_persons = []
    out_text = ''
    str_key = ''
    if data_key:
        str_key = data_key[0]

    info = models.FilmInfo.get_or_none(models.FilmInfo.data_key == str_key)
    if info:
        data = json.loads(info.data_json)
        name = data.get(
            'name',
            data.get('names', [{'name': None}])[0].get("name", None)
        )

        try:
            await safe_send_message(message,
                                    f'В фильме <b>{name}</b> снимались:')

            # Извлекаем список актёров фильма
            persons: List[Dict] = data.get('persons', [])
            persons_count = 0
            for i_persons in persons:
                # Имя актёра
                name_item = i_persons.get('name', i_persons.get('enName'))
                if not name_item:
                    continue

                # Сохраняем актёров в базу данных (на случай отсутствия в БД)
                try:
                    TGUsersInterface().save_actor_if_absent(i_persons,
                                                            info.id_history)
                except TypeError as err:
                    log.exception('Ошибка получения актёров: ' +
                                      str(err), exc_info=True)
                except (peewee.PeeweeException, IntegrityError) as err:
                    log.exception('{0}: Ошибка сохранения актёров: {1}'.
                                      format(type(err), str(err)))

                # Формируем список актёров в виде набора кнопок
                id_person = str(i_persons.get('id', ''))
                if id_person:
                    # Только при наличии ID актёра (и только актёров)
                    if (i_persons.get('profession') != 'актеры') and \
                            (i_persons.get('enProfession') != 'actor'):
                        continue
                    persons_count += 1
                    buttons_persons.append(
                        (name_item, f'ap_one_person.{str_key}.{id_person}')
                    )

            # Подготовить набор кнопок
            out_text = 'Список персон фильма'
            buttons = builder_custom_buttons(out_text, str_key,
                                             buttons_persons)

            # Готовим текст результата (статистика)
            out_text = f'Всего было указано людей: <b>{len(persons)}</b>,' \
                       f' из них актёров: <b>{persons_count}</b>.\n\n{out_text}'

        except KeyError as err:
            log.exception('Ошибка в шаблоне: ' + str(err), exc_info=True)
        except (aiogram.exceptions.TelegramBadRequest,
                aiogram.exceptions.TelegramNetworkError) as err:
            log.exception('Ошибка с файлом: ' + str(err), exc_info=True)

        # Создаём кнопки, если не создано ранее (список актёров)
        if not buttons:
            buttons = builder_random_films('Что ещё интересно?', str_key)
    else:
        out_text = f"Нет сведений об актёрах для фильма с ID {str_key}!"
        buttons = builder_start("Начнём сначала...")

    await safe_send_message(message, out_text, buttons)
    # return out_text, buttons
    return None


async def _show_one_person(message: Message,
                           data_keys: List,
                           history_id: str
                           ) -> None:
    """
    Вывести информацию об одной персоне.

    Информация об актёрах из фильмов в краткой форме,
    поэтому при отсутствии ключа даты обновления сведений
    или он очень старый (больше недели), то запросить
    информацию с сайта и обновить данные в базе. Затем
    вывести сведения об актёре без внешнего шаблона.

    :param message: Связующий объект с чат-ботом
    :type message: Message

    :param data_keys: Коды фильма и актёра для получения из БД или с сайта.
    :type data_keys: List

    :param history_id: Данные из таблицы истории запросов (id)
    :type history_id: str

    :return: None
    """
    data = dict()

    # Сведения об актёре получить по ID персоны
    info = models.ActorFilms.get_or_none(
        models.ActorFilms.data_key == data_keys[1]
    )
    out_lines = []

    if info:
        log.debug('Получаем сведения из базы данных для актёра. '
                  f'id = {data_keys[1]}')

        # Есть данные в базе - проверить их давность
        data = json.loads(info.data_json)

        # Узнать дату последнего обновления, если данные обновлялись
        last_update_date = data.get('last_update_date')
        if last_update_date:
            try:
                last_update_date = datetime.strptime(last_update_date,
                                                     '%Y-%m-%d').date()

                # Если обновление уже делалось давно, то сброс даты
                days_delta = (datetime.now() - last_update_date).days
                log.debug('Дата обновления "{}". Дельта относительно '
                          'сегодня дней: {}'.format(str(last_update_date),
                                                    str(days_delta)))
                if days_delta > 7:
                    last_update_date = None
            except TypeError:
                last_update_date = None
    else:
        log.debug('Получаем новые сведения для неизвестного актёра. '
                  f'id = {data_keys[1]}')
        last_update_date = None

    if last_update_date is None:
        # Получаем данные с сайта
        out_lines.append(f"Нет сведений о персоне с ID {data_keys[1]} "
                         "или они устаревшие!\n")
        response = site_api.get_person_by_id(data_keys[1])
        if isinstance(response, int):
            await safe_send_message(
                message,
                'Ошибка {} получения сведений о персоне'.format(response)
            )
            return None

        # Переносим полученные данные в словарь data и дополняем текущей датой
        response = json.loads(response.text)
        data['last_update_date'] = '{:%Y-%m-%d}'.format(datetime.now())
        for i_data in response:
            data[i_data] = response.get(i_data)

        # Сохраняем актёра в базу данных
        try:
            if info:
                # Запишем в БД обновлённую информацию
                info.data_json = json.dumps(data, ensure_ascii=False)
                info.save()
            else:
                # Добавим в базу данных актёра
                TGUsersInterface().save_actor_if_absent(data, history_id)
        except (peewee.PeeweeException, IntegrityError) as err:
            log.exception('{0}: Ошибка сохранения актёра: {1}'.
                          format(type(err), str(err)), exc_info=True)

    # Формируем данные для вывода пользователю

    # Изображение актёра
    if 'photo' in data:
        out_photo = data['photo']
        if out_photo:
            await send_photo_by_url(out_photo, action=message)

    # Имя актёра
    if data.get('name'):
        out_lines.append('Имя на русском: {}.\n'.format(data['name']))
    if data.get('enName'):
        out_lines.append('Имя на английском: {}.\n'.format(data['enName']))

    # Дата рождения и смерти
    if data.get('birthday'):
        out_lines.append('Дата рождения: {}.\n'.format(data['birthday']))
        if data.get('birthPlace'):
            places = [i_place.get('value')
                      for i_place in data['birthPlace']]
            out_lines.append('Место рождения: {}.\n'.format(', '.join(places)))
    if data.get('death'):
        out_lines.append('Дата смерти: {}.\n'.format(data['death']))
        if data.get('deathPlace'):
            places = [i_place.get('value') for i_place in data['deathPlace']]
            out_lines.append('Место смерти: {}.\n'.format(', '.join(places)))

    # Профессии
    if data.get('profession'):
        profession_list = []
        professions = data.get('profession', [])
        if professions:
            for i_profession in professions:
                profession_list.append(i_profession.get('value', ''))
            out_lines.append('Профессии: {}.\n'.format(
                ', '.join(profession_list)
            ))

    # Факты
    if data.get('facts'):
        facts_list = []
        facts = data.get('facts', [])
        if facts:
            for i_fact in facts:
                facts_list.append(re.sub('<[^<]+?>', '',
                                         i_fact.get('value', '')))
            out_lines.append('Известные факты: {}.\n'.format(
                '.\n'.join(facts_list)
            ))

    # Фильмы
    if data.get('movies'):
        movies_list = data.get('movies', [])
        if len(movies_list) > 1:
            out_lines.append('Участие в фильмах:')
            for i_number, i_move in enumerate(movies_list, 1):
                move_name = i_move.get('name')
                move_role = i_move.get('description')
                if move_name or move_role:
                    if not move_name:
                        move_name = 'не указано название!'
                    if not move_role:
                        move_role = 'не указана роль'
                    out_lines.append(
                        '{}. {} (персонаж {}).'.format(
                            i_number,
                            move_name,
                            move_role
                        )
                    )

    out_text = '\n'.join(out_lines)

    if data_keys[0] != 'info':
        # Требуется сведения о фильме по ID
        buttons = builder_random_films('Что ещё интересно?', data_keys[0])
    else:
        buttons = builder_start("Начальное меню для начала...")

    await safe_send_message(message, out_text, buttons)
    return


async def get_one_person(action: CallbackQuery | Message,
                         data_key: List = None,
                         history: Dict = None
                         ) -> None:
    """
    Вывести информацию об одной персоне с привязкой к фильму или без таковой

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе
    if history is None:
        history = register_user_action_query(action)
    history_id = history.get('id', '0')

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения об актёре из БД
    film_key = ''
    person_key = ''
    if len(data_key) >= 2:
        # Ключ 1 = ID фильма, ключ 2 = ID персоны
        film_key = data_key[0]
        person_key = data_key[1]

    # Вывести сведения об актёре
    try:
        await _show_one_person(message, [film_key, person_key], history_id)
    except Exception as err:
        log.exception('Ошибка вывода сведений о персоне: {}'.format(str(err)))

    return None


async def get_facts_films(action: CallbackQuery | Message,
                          data_key: List = None,
                          history: Dict = None
                          ) -> None:
    """
    Вывод фактов к фильму.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        register_user_action_query(action)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения о фильме из БД
    out_text = ''
    str_key = ''
    if data_key:
        str_key = data_key[0]

    info = models.FilmInfo.get_or_none(models.FilmInfo.data_key == str_key)
    if info:
        data = json.loads(info.data_json)
        name = data.get(
            'name',
            data.get('names', [{'name': None}])[0].get("name", None)
        )

        try:
            out_text = f'Факты к фильму <b>{name}</b>:'

            # Извлекаем список фактов к выбранному фильму
            facts: List[Dict] = data.get('facts', [])
            fact_count = 0
            for i_fact in facts:
                fact = i_fact.get('value')
                if fact:
                    fact_count += 1
                    out_text = '\n\n'.join(
                        (out_text, f'Факт {fact_count}: <i>{fact}</i>.')
                    )
            else:
                if fact_count:
                    out_text = '\n'.join(
                        (out_text, f'\nВсего фактов: <b>{fact_count}</b>.')
                    )
                else:
                    out_text = '\n'.join(
                        (out_text, 'Факты не указаны на сайте.')
                    )

        except KeyError as err:
            log.exception('Ошибка в шаблоне: ' + str(err), exc_info=True)
        except (aiogram.exceptions.TelegramBadRequest,
                aiogram.exceptions.TelegramNetworkError) as err:
            log.exception('Ошибка с файлом: ' + str(err), exc_info=True)

        # Создаём кнопки
        buttons = builder_random_films('Что ещё интересно?', str_key)
    else:
        out_text = f"Нет сведений о рейтинге для фильма с ID {str_key}!"
        buttons = builder_start("Начнём сначала...")

    await safe_send_message(message, out_text, buttons)
    return None


async def get_trailers_films(action: CallbackQuery | Message,
                             data_key: List = None,
                             history: Dict = None
                             ) -> None:
    """
    Вывод трейлеров к фильму.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        register_user_action_query(action)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения о фильме из БД
    out_text = ''
    str_key = ''
    if data_key:
        str_key = data_key[0]

    info = models.FilmInfo.get_or_none(models.FilmInfo.data_key == str_key)
    if info:
        data = json.loads(info.data_json)
        name = data.get(
            'name',
            data.get('names', [{'name': None}])[0].get("name", None)
        )

        try:
            out_text = f'Трейлеры к фильму <b>{name}</b>:'

            # Извлекаем список трейлеров к выбранному фильму
            trailers: List[Dict] = data.get('videos', {}).get('trailers', [])
            for counter, i_trailer in enumerate(trailers, 1):
                trailer_name = i_trailer.get('name', '<i>(не указано название)</i>')
                trailer_url = i_trailer.get('url', '')
                trailer_site = i_trailer.get('site', '')
                out_text = '\n\n'.join(
                    (out_text, f'{counter}: <b>{trailer_name}</b>\n'
                               f'{trailer_url}\n<i>{trailer_site}</i>.')
                )
            else:
                if trailers:
                    out_text = '\n\n'.join(
                        (out_text, f'Всего трейлеров: <b>{len(trailers)}</b>.')
                    )
                else:
                    out_text = '\n'.join(
                        (out_text, 'Трейлеры не указаны к фильму.')
                    )

        except KeyError as err:
            log.exception('Ошибка в шаблоне: ' + str(err), exc_info=True)
        except (aiogram.exceptions.TelegramBadRequest,
                aiogram.exceptions.TelegramNetworkError) as err:
            log.exception('Ошибка с файлом: ' + str(err), exc_info=True)

        # Создаём кнопки
        buttons = builder_random_films('Что ещё интересно?', str_key)
    else:
        out_text = f"Нет сведений о рейтинге для фильма с ID {str_key}!"
        buttons = builder_start("Начнём сначала...")

    await safe_send_message(message, out_text, buttons)
    return None


async def get_similar_films(action: CallbackQuery | Message,
                            data_key: List = None,
                            history: Dict = None
                            ) -> None:
    """
    Вывод похожих фильмов.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        register_user_action_query(action)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения о фильме из БД
    buttons = None
    buttons_films = []
    out_text = ''
    str_key = ''
    if data_key:
        str_key = data_key[0]

    info = models.FilmInfo.get_or_none(models.FilmInfo.data_key == str_key)
    if info:
        data = json.loads(info.data_json)
        name = data.get(
            'name',
            data.get('names', [{'name': None}])[0].get("name", None)
        )

        try:
            await safe_send_message(message,
                                    f'На фильм <b>{name}</b> '
                                    'похожи следующие картины:')

            # Извлекаем список фильмов
            films: List[Dict] = data.get('similarMovies', [])
            for i_film in films:
                # Название фильма
                film_id = str(i_film.get('id', '0'))
                film_name = i_film.get('name', i_film.get('enName', film_id))

                # Формируем список фильмов в виде набора кнопок
                buttons_films.append(
                    (film_name, f'ap_films.{str_key}.{film_id}')
                )

            # Подготовить набор кнопок
            out_text = 'Список похожих фильмов'
            buttons = builder_custom_buttons(out_text, str_key, buttons_films)

            # Готовим текст результата (статистика)
            out_text = f'Всего похожих фильмов: <b>{len(films)}</b>\n\n{out_text}:'

        except KeyError as err:
            log.exception('Ошибка в шаблоне: ' + str(err), exc_info=True)
        except (aiogram.exceptions.TelegramBadRequest,
                aiogram.exceptions.TelegramNetworkError) as err:
            log.exception('Ошибка с файлом: ' + str(err), exc_info=True)

        # Создаём кнопки, если не создано ранее (список фильмов)
        if not buttons:
            buttons = builder_random_films('Что ещё интересно?', str_key)
    else:
        out_text = f"Нет сведений о похожих фильмов для фильма с ID {str_key}!"
        buttons = builder_start("Начнём сначала...")

    await safe_send_message(message, out_text, buttons)
    return None


async def get_one_film(action: CallbackQuery | Message,
                       data_key: List = None,
                       history: Dict = None
                       ) -> None:
    """
    Получить один фильм.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = register_user_action_query(action)
    history_id = history.get('id')

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Получить сведения о фильме из БД
    film_key = ''
    similar_key = ''
    if len(data_key) >= 2:
        # Ключ 1 = ID фильма, ключ 2 = ID похожего фильма
        film_key = data_key[0]
        similar_key = data_key[1]

    # Сведения о фильме получить по ID похожего фильма из БД
    data: models.FilmInfo = models.FilmInfo.get_or_none(
        models.FilmInfo.data_key == similar_key
    )
    if data:
        response = data.data_json
    else:
        # Нет фильма в БД. Значит требуется запрос с сайта
        # и затем парсим результат
        response = site_api.get_one_film(param_id=similar_key)
        if isinstance(response, int):
            await safe_send_message(
                message,
                'Ошибка {} получения сведений о фильме'.format(response)
            )
            return
        response = response.text

    await send_film_info(message, response, history_id)
    return None


async def search_persons_filter(action: CallbackQuery | Message,
                                state: FSMContext = None,
                                history: Dict = None
                                ) -> None:
    """
    Поиск персон по фильтру.

    :param action: Связующий объект с чат-ботом
    :type action: CallbackQuery | Message

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: None
    """
    # Пример: https://api.kinopoisk.dev/v1/person
    # ?page=1&limit=50
    # &name=%D0%94%D0%B6%D1%83%D0%BB%D0%B8%D1%8F%20%D0%A0%D0%BE%D0%B1

    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        register_user_action_query(action)

    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)

    # Создаём кнопки для работы фильтра в зависимости от накопленных действий
    current_state = await state.get_state()
    if current_state and (current_state == 'FilterState:command_doit'):
        # Выполнить сформированный запрос
        log.debug("Перед запросом. Контроль")

        title_text = 'Первые 50 персон по Вашему запросу:'
        await safe_send_message(message, title_text)
        data = await state.get_data()
        our_filter = dict()
        if 'person_name' in data:
            our_filter['name'] = data.get('person_name')
        if 'person_en_name' in data:
            our_filter['enName'] = data.get('person_en_name')
        if 'person_birthday' in data:
            our_filter['birthday'] = data.get('person_birthday')
        if 'person_age' in data:
            our_filter['age'] = data.get('person_age')

        response = 0
        try:
            response = site_api.get_person_by_filter(our_filter)
        except BaseException as err:
            log.exception(err, exc_info=True)
        log.debug("После запроса. Контроль. {0}".format(type(response)))
        # print('response', type(response), response)

        if isinstance(response, int):
            await safe_send_message(
                message,
                'Ошибка {} получения сведений о фильме'.format(response)
            )
            return
        data: Dict = json.loads(response.text)
        # print('data', type(data), data)

        buttons = list()
        out_text = list()
        for i_item in data.get('docs', []):
            age_text = i_item.get('age')
            if age_text:
                age_text = ' ({} годиков)'.format(age_text)
            else:
                age_text = ''
            name_text = i_item.get('name',
                                   i_item.get('enName',
                                              '! имя не указано !'))
            out_text.append('<b>{}</b>{}'.format(name_text, age_text))
            id_person = i_item.get('id', '0')
            buttons.append((name_text, f'ap_one_person.info.{id_person}'))

        await state.clear()
        out_text = '\n'.join(out_text)
        buttons = builder_custom_buttons(title_text, buttons=buttons)
    else:
        # Подготовить параметры для запроса
        out_text = 'Формируем фильтр для поиска актёров:'
        buttons = builder_custom_buttons(out_text,
                                         buttons=buttons_search_persons)

    await safe_send_message(message, out_text, buttons)
    return None


def retrieve_users() -> models.UserList:
    """
    Вернуть список пользователей из базы данных.

    :return: Список из models.UserList
    """
    result = crud.retrieve(models.UserList)
    return result


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)

if __name__ == "__main__":
    check_admin_rights_in_db()
    register_user_action_query()
    get_random_films()
    get_rating_films()
    get_companies_films()
    get_persons_films()
    get_one_person()
    get_trailers_films()
    get_similar_films()
    get_one_film()
    search_film()
    search_persons_filter()
