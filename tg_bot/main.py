"""
Главный модуль телеграм-бота. Настройки в файле ".env".
Доступ к настройкам в используемых пакетах через модуль settings.
Назначение обработчиков событий и ссылок на функции выполняем до запуска.
Запуск телеграм-бота через "tg_api.run()".
"""

from settings import logger

from tg_API import tg_api, on_event
import tg_API.utils.tg_api_handler as tg_commands

from site_API.core import site_api

import database.utils.crud
from database.core import crud, close_database

import users_data

# Методы для записи в БД и чтения данных из БД
# db_write = crud.create
# db_read = crud.retrieve

# Регистрируем обработчики задач

# Функции для получения данных из ресурсов в сети
on_event.register_action('film_by_name', site_api.get_film_by_name)
# Проверка на уровень администратора у абонента
on_event.register_action('check_admin_rights',
                         users_data.check_admin_rights_in_db)
# Получение ID файла и сохранение файла (с ID) в базе данных
on_event.register_action('func_get_id', database.utils.crud.get_file_id)
on_event.register_action('func_save_id', database.utils.crud.save_file_id)
# Статистика и история запросов пользователя
on_event.register_action('calculation_of_statistical_data',
                         users_data.calculation_of_statistical_data)
on_event.register_action('get_history_info', users_data.get_history_info)
# Регистрация действий пользователя
on_event.register_action('register_user_action_query',
                         users_data.register_user_action_query)
# Получить список пользователей
on_event.register_action('retrieve_users', users_data.retrieve_users)

# По команде /help
on_event.register_event('mm_help_me', tg_commands.process_help_command)
# По команде /info
on_event.register_event('mm_who_are_you', tg_commands.process_info_command)
# Поиск фильмов по фильтру
on_event.register_event('mm_search_film', users_data.search_film)
# Поиск актёров по фильтру
on_event.register_event('mm_search_person', users_data.search_persons_filter)
# Получение статистики
on_event.register_event('mm_statistic', tg_commands.get_statistic)
# Показать историю запросов за период
on_event.register_event('mm_history', tg_commands.get_history)
# Предложить случайный фильм
on_event.register_event('mm_want_film', users_data.get_random_films)

# Для фильма показать рейтинги
on_event.register_event('af_rating', users_data.get_rating_films)
# Для фильма показать компании
on_event.register_event('af_companies', users_data.get_companies_films)
# Для фильма показать актёров
on_event.register_event('af_persons', users_data.get_persons_films)
# Для фильма показать одного актёра ??? ap_persons
on_event.register_event('ap_one_person', users_data.get_one_person)
# Для фильма показать факты
on_event.register_event('af_facts', users_data.get_facts_films)
# Для фильма показать трейлеры
on_event.register_event('af_trailers', users_data.get_trailers_films)
# Для фильма показать похожие фильмы
on_event.register_event('af_similar', users_data.get_similar_films)

# Показать один фильм по ID
on_event.register_event('one_film', users_data.get_one_film)
on_event.register_event('ap_films', users_data.get_one_film)


# Работаем только в основном коде.
if __name__ == '__main__':
    # Начинаем работу с определения логирования и сообщение в протокол
    log = logger.getLogger(__name__)
    log.info('Сеанс работы с чат-ботом запущен')

    # Запустить телеграм-бот
    tg_api.run()

    # Закрыть базу данных
    close_database()

    # Сообщить об окончании работы
    log.info('Сеанс работы с чат-ботом завершён')
