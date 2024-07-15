"""
Модуль обработчиков событий от телеграм-бота.

:Functions
    process_all_callback - Обработчик CallBack событий от телеграм-бота.

    process_stop_command - Обработчик события по команде `/stop` в телеграм.

    process_start_command - Обработчик события по команде `/start` в телеграм.

    process_start_handler - Вызов главного меню чат-бота.

    process_help_command - Вызов помощи по чат-боту.

    process_info_command - Вызов информации про чат-бот.

    _check_not_text_type - Проверка на тип данных "текст".

    __make_answer_by_filter - Подготовить приглашение для выбора фильтров
    и вывод уже введённых параметров

    set_filter_name - Установить фильтр поиска по имени фильма.

    set_filter_en_name - Установить фильтр поиска по англоязычному имени
    фильма

    set_filter_type - Установить фильтр поиска по типу фильма

    set_filter_year - Установить фильтр поиска по году премьеры фильма

    set_filter_genres - Установить фильтр поиска по жанру фильма

    set_filter_age_rating - Установить фильтр поиска по возрастному
    ограничению фильма

    set_filter_rating_imdb - Установить фильтр поиска по рейтингу фильма IMDB

    set_filter_rating_kp - Установить фильтр поиска по рейтингу фильма KP

    __make_answer_for_person - Формируем текст приглашения для выбора
    фильтров поиска персон

    set_filter_person_name - Установить фильтр поиска по имени персоны

    set_filter_person_enname - Установить фильтр поиска по англоязычному
    имени персоны

    set_filter_person_age - Установить фильтр поиска по возрасту персоны

    set_filter_person_birthday - Установить фильтр поиска по дате рождения
    персоны

    process_stop_handler - Обработчик события запроса на завершение сеанса
    работы с ботом

    process_all_handler - Обработчик текстовых запросов в произвольной форме

    message_with_sticker - Обработчик стикеров

    message_with_gif - Обработчик анимации

    get_statistic - Функция получения статистики из базы данных

    get_history - Получить историю действий пользователя
"""

from ..tg_settings import logger
from typing import List, Dict
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, \
    CallbackQuery, ReplyKeyboardRemove, User
from aiogram.filters import Command, Text, StateFilter
from aiogram.fsm.context import FSMContext
from .commands import _on_event as on_event, safe_send_message, \
    safe_reply_message, FilterStateFilms, FilterStatePersons, \
    stop_polling, get_message
from .keys import builder_start, buttons_title_types, \
    buttons_search_persons, buttons_after_person_filter, \
    builder_custom_buttons, buttons_search_films, buttons_after_film_filter


router_callback = Router()
router_command = Router()
router_filter = Router()


@router_callback.callback_query()
async def process_all_callback(callback: CallbackQuery | Message | User,
                               state: FSMContext = None,
                               history: Dict = None
                               ) -> bool:
    """
    Обработчик CallBack событий от телеграм-бота.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Запишем в БД сведения о событии
    if history is None:
        history: Dict = on_event.do_action('register_user_action_query',
                                           action=callback)
    log.debug('Обратный вызов (ID пользователя {}; ID истории {}): "{}"'.
              format(str(callback.from_user.id),
                     history.get('id', 'n/a'),
                     callback.data))
    message = get_message(callback)

    # Разделим "callback.data" на части для извлечения кодов для точного
    # определения принадлежности меню для разных сведений.
    data_event, *data_key = callback.data.split('.')

    # Выполнение действий в зависимости от назначенных функций, которые
    # возвращают Истина при успешном вызове или Ложь при ошибках
    result = False
    if data_event.startswith(('mm', 'af', 'ap')):
        # Группа событий основного или дополнительного меню.
        # Сбрасываем машины состояний и вызываем обработчик
        await state.clear()
        result = await on_event.do_event(data_event, callback, data_key,
                                         state, history)
    elif data_event.startswith('bf'):
        # Группа для формирования фильтра поиска фильмов.
        # Через ключи передаём состояние для ожидаемого запроса
        if data_event == 'bf_name':
            # Ждём имя для поиска
            await safe_send_message(message,
                                    "Введите название фильма:")
            await state.set_state(FilterStateFilms.filter_name.state)
        elif data_event == 'bf_enName':
            # Ждём имя по-английски для поиска
            await safe_send_message(message,
                                    "Введите англоязычное название фильма:")
            await state.set_state(FilterStateFilms.filter_en_name.state)
        elif data_event == 'bf_type':
            # Ждём выбор тайтла для поиска (показ вариантов в виде
            # набора кнопок или ввод с клавиатуры)
            button = ReplyKeyboardMarkup(
                resize_keyboard=True,
                one_time_keyboard=True,
                keyboard=[
                    [KeyboardButton(text=item) for item in buttons_title_types]
                ]
            )
            await safe_send_message(message, "Введите тип тайтла:",
                                    button)
            await state.set_state(FilterStateFilms.filter_type.state)
        elif data_event == 'bf_year':
            # Ждём год для поиска
            await safe_send_message(message,
                                    "Введите год премьеры:")
            await state.set_state(FilterStateFilms.filter_year.state)
        elif data_event == 'bf_ratingKp':
            # Ждём рейтинг кинопоиска для поиска
            await safe_send_message(message,
                                    "Введите рейтинг кинопоиска:")
            await state.set_state(FilterStateFilms.filter_rating_kp.state)
        elif data_event == 'bf_ratingImdb':
            # Ждём рейтинг IMDB для поиска
            await safe_send_message(message,
                                    "Введите рейтинг IMDB:")
            await state.set_state(FilterStateFilms.filter_rating_imdb.state)
        elif data_event == 'bf_ageRating':
            # Ждём возрастной рейтинг для поиска
            await safe_send_message(message,
                                    "Введите возрастной рейтинг:")
            await state.set_state(FilterStateFilms.filter_age_rating.state)
        elif data_event == 'bf_genres':
            # Ждём жанр для поиска
            await safe_send_message(message,
                                    "Введите жанр:")
            await state.set_state(FilterStateFilms.filter_genres.state)
        elif data_event == 'bf_reset':
            # Сброс фильтров поиска
            await state.clear()
            result = await on_event.do_event('mm_search_film', callback,
                                             data_key, state, history)
        elif data_event == 'bf_doit':
            # Запуск поиска фильма по указанным параметрам
            await state.set_state(FilterStateFilms.command_doit.state)
            result = await on_event.do_event('mm_search_film', callback,
                                             data_key, state, history)
        else:
            # Не найден обработчик вовсе
            result = await on_event.do_event(data_event, callback,
                                             data_key, state, history)
    elif data_event.startswith('bp'):
        # Группа для формирования фильтра поиска актёров.
        # Через ключи передаём состояние для ожидаемого запроса
        if data_event == 'bp_name':
            # Ждём имя для поиска
            await safe_send_message(message,
                                    "Введите имя актёра:")
            await state.set_state(FilterStatePersons.person_name.state)
        elif data_event == 'bp_enName':
            # Ждём англоязычное имя для поиска
            await safe_send_message(message,
                                    "Введите имя актёра по английски:")
            await state.set_state(FilterStatePersons.person_en_name.state)
        elif data_event == 'bp_birthday':
            # Ждём дату рождения для поиска
            await safe_send_message(message,
                                    "Введите дату рождения актёра:")
            await state.set_state(FilterStatePersons.person_birthday.state)
        elif data_event == 'bp_age':
            # Ждём англоязычное имя для поиска
            await safe_send_message(message,
                                    "Введите возраст актёра:")
            await state.set_state(FilterStatePersons.person_age.state)
        elif data_event == 'bp_reset':
            # Сброс фильтров поиска
            await state.clear()
            result = await on_event.do_event('mm_search_person', callback,
                                             data_key, state, history)
        elif data_event == 'bp_doit':
            # Запуск поиска персоны по указанным параметрам
            await state.set_state(FilterStatePersons.command_doit.state)
            result = await on_event.do_event('mm_search_person', callback,
                                             data_key, state, history)
        else:
            # Не найден обработчик вовсе
            result = await on_event.do_event(data_event, callback, data_key,
                                             state, history)
    else:
        # Не найдена группа событий
        result = await on_event.do_event('default', callback, data_key,
                                         state, history)

    if result and isinstance(result, tuple) and (len(result) >= 2):
        await safe_send_message(message, result[0], result[1])

    await callback.answer()  # Убрать "часы" в кнопке меню
    return True


@router_command.message(Command(commands=["stop"], ignore_case=True))
async def process_stop_command(callback: CallbackQuery | Message | User,
                               history: Dict = None
                               ) -> bool:
    """
    Обработчик события по команде `/stop` в телеграм.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """

    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    await process_stop_handler(message, history=history)
    return True


@router_command.message(Command(commands=["start"], ignore_case=True))
async def process_start_command(callback: CallbackQuery | Message | User,
                                history: Dict = None
                                ) -> bool:
    """
    Обработчик события по команде `/start` в телеграм.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    # Most event objects have aliases for API methods that can be called
    # in events' context. For example if you want to answer to incoming
    # message you can use `message.answer(...)` alias and the target chat
    # will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via Bot instance:
    # `bot.send_message(chat_id=message.chat.id, ...)`
    # Приветствуем пользователя
    await safe_send_message(
        message,
        f"Привет, <b>{message.from_user.full_name}!</b>"
    )
    await safe_send_message(
        message,
        "Для получения помощи используйте соответствущую кнопку или "
        "введите <b>/help</b>"
    )
    await safe_send_message(
        message,
        "Для знакомства со мной используйте кнопку \"<b>Кто ты, "
        "БОТ?</b>\" или введите <b>/info</b>"
    )

    # Создаем клавиатуру с 7 кнопками
    try:
        # Отправляем сообщение с клавиатурой
        await safe_send_message(
            message,
            "Выберите желаемое действие:",
            builder_start(text="Выберите действие или введите текст")
        )
        main_keyboard = [[KeyboardButton(text="Главное меню")]]
        main_text = ""
        if on_event.do_action('check_admin_rights',
                              from_user=message.from_user):
            main_keyboard.append([KeyboardButton(text="Завершить скрипт")])
            main_text = "Админ!"
        button = ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True,
            keyboard=main_keyboard
        )
        await safe_send_message(message, main_text, button)
    except Exception as err:
        log.exception(err, exc_info=True)
        await safe_send_message(message,
                                "Nice try! " + str(err))
    return True


@router_command.message(Text("Главное меню", ignore_case=True))
async def process_start_handler(callback: CallbackQuery | Message | User,
                                history: Dict = None
                                ) -> bool:
    """
    Вызов главного меню чат-бота.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    await process_start_command(message, history=history)
    return True


@router_command.message(Command(commands=['help'], ignore_case=True))
async def process_help_command(callback: CallbackQuery | Message | User,
                               history: Dict = None
                               ) -> bool:
    """
    Вызов помощи по чат-боту.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    if history is None:
        history = on_event.do_action('register_user_action_query', action=callback)
    message: Message = get_message(callback)

    text = "Внимание! Этот учебный бот ограничен по количеству функций" \
           " и количеству запросов.\n    Каждая кнопка меню выполняет " \
           "определённые запросы к сайту <u>Кинопоиск</u> и выводит в " \
           "чат полученные данные. Также предусмотрена небольшая статистика" \
           " по топ-10 частых запросов в каждой категории.\n    История " \
           "запросов отображается индивидуально для каждого абонента. " \
           "Администратор видит полную историю по всем абонентам."

    await safe_reply_message(message, "Как работать с ботом:")
    await safe_send_message(message, text)
    return True


@router_command.message(Command(commands=['info'], ignore_case=True))
async def process_info_command(callback: CallbackQuery | Message | User,
                               history: Dict = None
                               ) -> bool:
    """
    Вызов информации про чат-бот.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    text = "Бот выполнен в рамках итоговой работы по основам Python " \
           "(часть 2).\n    Основная функция: получение информации о " \
           "фильмах и актёрах через API кинопоиска и формирование " \
           "ответа для пользователей. Работает скрипт исключительно на " \
           "ресурсах, доступных автору. Поэтому, если Вам удалось получить" \
           " эти строки, то Вы удачно зашли.\n    Автор (он же исполнитель" \
           " итоговой работы):\nЕвгений Тявкин (Амурская область, город " \
           "Тында).\nОтправить сообщение автору можно тут https://t.me/" \
           "etyavkin."

    await safe_reply_message(message,
                             "Информация об этом боте:")
    await safe_send_message(message, text)
    return True


async def _check_not_text_type(message: Message) -> bool:
    """
    Проверка на тип данных "текст". Если что-то другое, то сообщить абоненту

    :param message: Связующий объект с чат-ботом
    :type message: Message

    :return: Истина, если тип не текст. А если тип текст, то ЛОЖЬ вернётся
    """
    if message.content_type != 'text':
        await safe_send_message(message, "Только текст понимаю я.")
        return True
    return False


async def __make_answer_by_filter(message: Message, state: FSMContext) -> None:
    """
    Подготовить приглашение для выбора фильтров и вывод уже введённых
    параметров.

    :param message: Связующий объект с чат-ботом
    :type message: Message

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext
    """
    await safe_send_message(message, f"Это {message.text}!")
    out_text = 'Формируем фильтр для поиска фильмов:\n'
    flag_add_command_button = False
    data = await state.get_data()
    if 'filter_name' in data:
        out_text += 'По имени <b>' + data.get('filter_name') + '</b>;\n'
        flag_add_command_button = True
    if 'filter_en_name' in data:
        out_text += 'По англоязычному имени <b>' + \
                    data.get('filter_en_name') + '</b>;\n'
        flag_add_command_button = True
    if 'filter_type' in data:
        out_text += 'По типу <b>' + \
                    data.get('filter_type') + '</b>;\n'
        flag_add_command_button = True
    if 'filter_year' in data:
        out_text += 'По году премьеры <b>' + \
                    data.get('filter_year') + '</b>;\n'
        flag_add_command_button = True
    if 'filter_rating_kp' in data:
        out_text += 'По рейтингу кинопоиска <b>' + \
                    data.get('filter_rating_kp') + '</b>;\n'
        flag_add_command_button = True
    if 'filter_rating_imdb' in data:
        out_text += 'По рейтингу IMDB <b>' + \
                    data.get('filter_rating_imdb') + '</b>;\n'
        flag_add_command_button = True
    if 'filter_age_rating' in data:
        out_text += 'По возрастным ограничениям <b>' + \
                    data.get('filter_age_rating') + '</b>;\n'
        flag_add_command_button = True
    if 'filter_genres' in data:
        out_text += 'По жанру <b>' + \
                    data.get('filter_genres') + '</b>;\n'
        flag_add_command_button = True
    show_buttons = buttons_search_films.copy()
    if flag_add_command_button:
        show_buttons.extend(buttons_after_film_filter)
    buttons = builder_custom_buttons(out_text, buttons=show_buttons)
    await safe_send_message(message, out_text, buttons)
    await state.set_state(FilterStateFilms.wait_command.state)


@router_filter.message(StateFilter(FilterStateFilms.filter_name))
async def set_filter_name(callback: CallbackQuery | Message | User,
                          state: FSMContext = None,
                          history: Dict = None
                          ) -> bool:
    """
    Установить фильтр поиска по имени фильма.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)
    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_name=message.text)
    await __make_answer_by_filter(message, state)
    return True


@router_filter.message(StateFilter(FilterStateFilms.filter_en_name))
async def set_filter_en_name(callback: CallbackQuery | Message | User,
                             state: FSMContext = None,
                             history: Dict = None
                             ) -> bool:
    """
    Установить фильтр поиска по англоязычному имени фильма

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_en_name=message.text)
    await __make_answer_by_filter(message, state)
    return True


@router_filter.message(StateFilter(FilterStateFilms.filter_type))
async def set_filter_type(callback: CallbackQuery | Message | User,
                          state: FSMContext = None,
                          history: Dict = None
                          ) -> bool:
    """
    Установить фильтр поиска по типу фильма

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_type=message.text)
    await __make_answer_by_filter(message, state)
    return True


@router_filter.message(StateFilter(FilterStateFilms.filter_year))
async def set_filter_year(callback: CallbackQuery | Message | User,
                          state: FSMContext = None,
                          history: Dict = None
                          ) -> bool:
    """
    Установить фильтр поиска по году премьеры фильма

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_year=message.text)
    await __make_answer_by_filter(message, state)
    return True


@router_filter.message(StateFilter(FilterStateFilms.filter_genres))
async def set_filter_genres(callback: CallbackQuery | Message | User,
                            state: FSMContext = None,
                            history: Dict = None
                            ) -> bool:
    """
    Установить фильтр поиска по жанру фильма

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_genres=message.text)
    await __make_answer_by_filter(message, state)
    return True


@router_filter.message(StateFilter(FilterStateFilms.filter_age_rating))
async def set_filter_age_rating(callback: CallbackQuery | Message | User,
                                state: FSMContext = None,
                                history: Dict = None
                                ) -> bool:
    """
    Установить фильтр поиска по возрастному ограничению фильма

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_age_rating=message.text)
    await __make_answer_by_filter(message, state)
    return True


@router_filter.message(StateFilter(FilterStateFilms.filter_rating_imdb))
async def set_filter_rating_imdb(callback: CallbackQuery | Message | User,
                                 state: FSMContext = None,
                                 history: Dict = None
                                 ) -> bool:
    """
    Установить фильтр поиска по рейтингу фильма IMDB

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_rating_imdb=message.text)
    await __make_answer_by_filter(message, state)
    return True


@router_filter.message(StateFilter(FilterStateFilms.filter_rating_kp))
async def set_filter_rating_kp(callback: CallbackQuery | Message | User,
                               state: FSMContext = None,
                               history: Dict = None
                               ) -> bool:
    """
    Установить фильтр поиска по рейтингу фильма KP

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(filter_rating_kp=message.text)
    await __make_answer_by_filter(message, state)
    return True


async def __make_answer_for_person(callback: CallbackQuery | Message | User,
                                   state: FSMContext = None
                                   ) -> bool:
    """
    Формируем текст приглашения для выбора фильтров поиска персон

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    message: Message = get_message(callback)

    await safe_send_message(message, f"Это {message.text}!")
    out_text = 'Формируем фильтр для поиска персон:\n'
    flag_add_command_button = False
    data = await state.get_data()
    if 'person_name' in data:
        out_text += 'По имени <b>' + data.get('person_name') + '</b>;\n'
        flag_add_command_button = True
    if 'person_en_name' in data:
        out_text += 'По англоязычному имени <b>' + \
                    data.get('person_en_name') + '</b>;\n'
        flag_add_command_button = True
    if 'person_birthday' in data:
        out_text += 'По дате рождения <b>' + \
                    data.get('person_birthday') + '</b>;\n'
        flag_add_command_button = True
    if 'person_age' in data:
        out_text += 'По возрасту <b>' + \
                    data.get('person_age') + '</b>;\n'
        flag_add_command_button = True
    show_buttons = buttons_search_persons.copy()
    if flag_add_command_button:
        show_buttons.extend(buttons_after_person_filter)
    buttons = builder_custom_buttons(out_text, buttons=show_buttons)
    await safe_send_message(message, out_text, buttons)
    await state.set_state(FilterStatePersons.wait_command.state)
    return True


@router_filter.message(StateFilter(FilterStatePersons.person_name))
async def set_filter_person_name(callback: CallbackQuery | Message | User,
                                 state: FSMContext = None,
                                 history: Dict = None
                                 ) -> bool:
    """
    Установить фильтр поиска по имени персоны

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(person_name=message.text)
    await __make_answer_for_person(message, state)
    return True


@router_filter.message(StateFilter(FilterStatePersons.person_en_name))
async def set_filter_person_enname(callback: CallbackQuery | Message | User,
                                   state: FSMContext = None,
                                   history: Dict = None
                                   ) -> bool:
    """
    Установить фильтр поиска по англоязычному имени персоны

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(person_en_name=message.text)
    await __make_answer_for_person(message, state)
    return True


@router_filter.message(StateFilter(FilterStatePersons.person_age))
async def set_filter_person_age(callback: CallbackQuery | Message | User,
                                state: FSMContext = None,
                                history: Dict = None
                                ) -> bool:
    """
    Установить фильтр поиска по возрасту персоны

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(person_age=message.text)
    await __make_answer_for_person(message, state)
    return True


@router_filter.message(StateFilter(FilterStatePersons.person_birthday))
async def set_filter_person_birthday(callback: CallbackQuery | Message | User,
                                     state: FSMContext = None,
                                     history: Dict = None
                                     ) -> bool:
    """
    Установить фильтр поиска по дате рождения персоны

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    if await _check_not_text_type(message):
        return False
    await state.update_data(person_birthday=message.text)
    await __make_answer_for_person(message, state)
    return True


@router_filter.message(Text("Завершить скрипт", ignore_case=True))
async def process_stop_handler(callback: CallbackQuery | Message | User,
                               history: Dict = None
                               ) -> bool:
    """
    Обработчик события запроса на завершение сеанса работы с ботом.


    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool

    :return: Истина, если нет исключения, которые в функции не обрабатываются.
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    await safe_reply_message(message,
                             "Больше не хочу работать с ботом!")
    if on_event.do_action('check_admin_rights',
                          from_user=message.from_user):
        await safe_send_message(message, "Возможно позже",
                                ReplyKeyboardRemove())
        await stop_polling()
    else:
        await safe_send_message(message,
                                "Но никто никого не заставляет. "
                                "Только вы не админ!",
                                ReplyKeyboardRemove())
    return True


@router_filter.message(F.text)
async def process_all_handler(callback: CallbackQuery | Message | User,
                              state: FSMContext = None,
                              history: Dict = None
                              ) -> bool:
    """
    Обработчик текстовых запросов в произвольной форме.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    try:
        # Получаем название кнопки
        button_name = message.text

        # Отправляем сообщение с названием кнопки
        await safe_reply_message(message, f'Ввели текст {button_name}')
        await safe_send_message(message, 'Не назначен парсер обычного текста')

        # Возможный вариант развития поиска по названию фильма, если введённый
        # текст содержит слово фильм (кино, смотреть, и т.п.) или это слово
        # не найдено среди ранее найденных актёров

    except TypeError as err:
        log.exception(err, exc_info=True)
        # But not all the types is supported to be copied so need to handle it
        await safe_send_message(message, 'Nice try! ' + str(err))

    return True


@router_filter.message(F.sticker)
async def message_with_sticker(callback: CallbackQuery | Message | User,
                               history: Dict = None
                               ) -> bool:
    """
    Обработчик стикеров. Но в рамках задачи их не требуется распознавать

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    await safe_send_message(message, "Это стикер!")
    return True


@router_filter.message(F.animation)
async def message_with_gif(callback: CallbackQuery | Message | User,
                           history: Dict = None
                           ) -> bool:
    """
    Обработчик анимации. Но в рамках задачи её не требуется распознавать

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    # Записать сведения о пользователе, если их ещё нет
    if history is None:
        history = on_event.do_action('register_user_action_query',
                                     action=callback)
    message: Message = get_message(callback)

    await safe_send_message(message, "Это GIF!")
    return True


async def get_statistic(callback: CallbackQuery | Message) -> bool:
    """
    Функция получения статистики из базы данных по запросам (действиям)
    пользователя.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    message = get_message(callback)

    out_text_lines = ['Статистика Ваших запросов:', '']
    user_id = str(message.chat.id)

    # Подсчитать сколько запросил пользователь фильмов (st.want_film)
    total_films = on_event.do_action('calculation_of_statistical_data',
                                     query_string='st_want_film%',
                                     user_id=user_id)
    temp_text = 'Предложено фильмов: {}.'.format(total_films)
    out_text_lines.append(temp_text)

    # Подсчитать сколько запросил пользователь фильмов сегодня
    total_films = on_event.do_action('calculation_of_statistical_data',
                                     query_string='st_want_film%',
                                     user_id=user_id,
                                     use_today=True)
    temp_text = '{}из них сегодня: {}.'.format(' ' * 4, total_films)
    out_text_lines.append(temp_text)

    # Подсчитать сколько искал пользователь фильмов (bf.doit)
    total_films = on_event.do_action('calculation_of_statistical_data',
                                     query_string='bf_doit%',
                                     user_id=user_id)
    temp_text = 'Поиск фильмов запущен: {} раз.'.format(total_films)
    out_text_lines.append(temp_text)

    # Подсчитать сколько искал пользователь фильмов сегодня
    total_films = on_event.do_action('calculation_of_statistical_data',
                                     query_string='bf_doit%',
                                     user_id=user_id,
                                     use_today=True)
    temp_text = '{}из них сегодня: {}.'.format(' ' * 4, total_films)
    out_text_lines.append(temp_text)

    # Подсчитать сколько загружено в БД персон (__.persons.%)
    total_persons = on_event.do_action('calculation_of_statistical_data',
                                       query_string='___persons.%',
                                       user_id=user_id)
    temp_text = 'Загружено в БД персон: {}.'.format(total_persons)
    out_text_lines.append(temp_text)

    # Подсчитать сколько запросил пользователь персон сегодня
    total_persons = on_event.do_action('calculation_of_statistical_data',
                                       query_string='___persons.%',
                                       user_id=user_id,
                                       use_today=True)
    temp_text = '{}из них сегодня: {}.'.format(' ' * 4, total_persons)
    out_text_lines.append(temp_text)

    # Подсчитать сколько искал пользователь персон (bp.doit)
    total_persons = on_event.do_action('calculation_of_statistical_data',
                                       query_string='bp_doit%',
                                       user_id=user_id)
    temp_text = 'Поиск персон запущен: {} раз.'.format(total_persons)
    out_text_lines.append(temp_text)

    # Подсчитать сколько искал пользователь фильмов сегодня
    total_persons = on_event.do_action('calculation_of_statistical_data',
                                       query_string='bp_doit%',
                                       user_id=user_id,
                                       use_today=True)
    temp_text = '{}из них сегодня: {}.'.format(' ' * 4, total_persons)
    out_text_lines.append(temp_text)

    # Вернуть результат для вывода пользователю
    out_text = '\n'.join(out_text_lines)
    buttons = builder_start(out_text_lines[0])
    await safe_send_message(message=message,
                            param_text=out_text,
                            param_reply_markup=buttons)
    return True


async def get_history(callback: CallbackQuery | Message,
                      data_key: List = None,
                      state: FSMContext = None) -> bool:
    """
    Получить историю действий пользователя за дату, которую выбирает
    пользователь. По умолчанию сегодня.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User

    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List

    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """

    result = await on_event.do_action('get_history_info', callback=callback,
                                      data_key=data_key, state=state)
    return result


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)


if __name__ == "__main__":
    process_all_callback()
    process_stop_command()
    process_start_command()
    process_start_handler()
    process_help_command()
    process_info_command()
    _check_not_text_type()
    __make_answer_by_filter()
    set_filter_name()
    set_filter_en_name()
    set_filter_type()
    set_filter_year()
    set_filter_genres()
    set_filter_age_rating()
    set_filter_rating_imdb()
    set_filter_rating_kp()
    __make_answer_for_person()
    set_filter_person_name()
    set_filter_person_enname()
    set_filter_person_age()
    set_filter_person_birthday()
    process_stop_handler()
    process_all_handler()
    message_with_sticker()
    message_with_gif()
    get_statistic()
    get_history()
