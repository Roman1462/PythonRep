"""
Модуль интерфейса обработчиков команд и событий.

Ссылки на функции для обработки событий регистрируются в on_event. Вызов 
событий через этот же экземпляр класса. В параметрах указывается CallbackQuery
или Message, список ключей и экземпляр класса машины состояний.


:Functions
    safe_reply_message - отправка ответа на сообщение.

    safe_send_message - отправка сообщения.

    get_message - Из объектов типа CallbackQuery или Message вернуть Message.

    stop_polling - Остановить телеграм-бот.

    empty_function - Функция-заглушка для событий.

    default_action - Функция-заглушка для действий.

    __check_admin_rights_default - Функция-заглушка для проверки
    административных прав у пользователя.

    send_photo_by_url - Отправить графический файл в чат.


:Classes
    OnAnythingDoSomething - Хранение и выполнение обработчиков событий.

    FilterState, FilterStateFilms, FilterStatePersons - фильтры состояний.


:var
    _dp - Диспетчер телеграм-бота.

    _on_event - Интерфейс для обработки событий и выполнения действий.
"""

from typing import List, Callable, Any, Dict
from time import sleep
from ..tg_settings import logger
from aiogram import Dispatcher
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, \
    Message, CallbackQuery, User, URLInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import aiogram.exceptions as aexc


class OnAnythingDoSomething:
    """
    Класс для хранения и обработки событий телеграм-бота.
    Первично регистрируем словарь событий (помощь, информация,
    поиск и т.п.), где каждому событию будет соответствовать свой
    обработчик. Затем регистрируем в словарь обработчики действий
    (чтение и запись в таблицу истории, отправка сообщений в
    телеграм-бот, и т.п.)

    Attributes:
        __events (dict): список обработчиков событий, где для
            каждого ключа назначается своя функция, возвращающая
            результат ИСТИНА или ЛОЖЬ в зависимости от успешности
            обработки события. В параметрах указывается экземпляр
            классов CallbackQuery, User или Message, список ключей (если
            есть или необходимы ключи, иначе пустой список), экземпляр
            класса FSMContext (машина состояний для накопления вводимых
            данных пользователем). Функции событий асинхронные!
        __actions (dict): список обработчиков действий, где для
            каждого ключа назначается своя функция, возвращающая словарь
            с результатом. В параметрах передаются именованные аргументы.
    """

    def __init__(self):
        # Обработчики событий сохраним в словаре
        self.__events = dict()
        self.__events['default'] = empty_function
        self.__actions = dict()
        self.__actions['default'] = default_action

    def register_action(self, name: str, func: Callable) -> None:
        """
        Регистрируем (добавляем в словарь) функцию для выполнения действия.

        :param name: Имя ключа для вызова функции
        :type name: str
        :param func: Функция для выполнения действия
        :type func: Callable

        :return: None
        """
        # Контроль наличия/отсутствия ключа на разработчике.
        # ИМХО возможно динамическое переопределение функций в
        # процессе работы приложения.
        self.__actions[name] = func
        log.debug('Регистрация обработчика "{0}{1}" для события "{2}"'.
                  format(func.__name__, func.__code__.co_varnames, name))

    def register_event(self, name: str, func: Callable) -> None:
        """
        Регистрируем (добавляем в словарь) функцию для обработки событий.

        :param name: Имя ключа для вызова функции
        :type name: str
        :param func: Функция для обработки события
        :type func: Callable

        :return: None
        """
        # Контроль наличия/отсутствия ключа на разработчике.
        # ИМХО возможно динамическое переопределение функций в
        # процессе работы приложения.
        self.__events[name] = func
        log.debug('Регистрация обработчика "{0}{1}" для действия "{2}"'.
                  format(func.__name__, func.__code__.co_varnames, name))

    def do_action(self, name: str, **kwargs) -> Any:
        """
        Выполнить действие.

        :param name: Имя обработчика
        :type name: str
        :param kwargs: Параметры для функции

        :return: Результат работы функции (может быть любой вариант)
        :rtype: Any
        """
        result = None
        try:
            if name in self.__actions.keys():
                result = self.__actions[name](**kwargs)
                log.debug('Выполнение функции {} с параметрами {}'.
                          format(name, str(kwargs)))
            else:
                result = self.__actions['default'](**kwargs)
                log.debug('Выполнение функции по умолчанию (вместо {}) с '
                          'параметрами {}'.format(name, str(kwargs)))
        except BaseException as err:
            log.exception('Ошибка при выполнении действия "{name}": {err}'.
                          format(name=name, err=str(err)))
        return result

    async def do_event(
            self,
            name: str,
            callback: CallbackQuery | Message | User,
            data_key: List = None,
            state: FSMContext = None,
            history: Dict = None
    ) -> bool:
        """
        Выполнить обработку события.

        :param name: Имя обработчика
        :type name: str
        :param callback: Связующий объект с последним событием в телеграм
        :type callback: CallbackQuery | Message | User
        :param data_key: Набор ключей, если есть или необходим
        :type data_key: List
        :param state: Машина состояний для подготовки фильтров при поиске
        :type state: FSMContext
        :param history:
        :type history: Dict

        :return: Результат работы функции (Истина = успешное выполнение)
        :rtype: bool
        """
        result = False

        # Выполняем обработчик из словаря
        try:
            if name in self.__events.keys():
                # result = await self.__events[name](callback, data_key, state, history)
                func = self.__events[name]

                # Добавим аргументы в словарь
                args_in_func = func.__code__.co_varnames
                kwargs: Dict = {}
                if 'data_key' in args_in_func:
                    kwargs['data_key'] = data_key
                if 'state' in args_in_func:
                    kwargs['state'] = state
                if 'history' in args_in_func:
                    kwargs['history'] = history

                # Вызов функции с параметрами, доступными для этой функции
                result = await func(callback, **kwargs)
                log.debug('Выполнение функции {} вернуло результат {}'.
                          format(name, str(result)))
            else:
                result = await self.__events['default'](callback, data_key,
                                                        state, history)
                log.debug('Выполнение функции по умолчанию (вместо {}) '
                          'вернуло результат {}'.format(name, str(result)))
        except BaseException as err:
            log.exception('Ошибка при обработки события "{name}": {err}'.
                          format(name=name, err=str(err)), exc_info=True)
        return result


async def safe_send_message(message: Message, param_text: str = "",
                            param_reply_markup: InlineKeyboardMarkup |
                                                ReplyKeyboardMarkup |
                                                None = None) \
        -> None:
    """
    Безопасная отправка сообщений чат-ботом для пользователя.

    :param message: Связующий объект с чат-ботом
    :type message: Message
    :param param_text: Текстовое сообщение для пользователя
    :type param_text: str
    :param param_reply_markup: Набор кнопок для чата
    :type param_reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None

    :return: None
    """
    try:
        if param_text:
            # Из-за ограничений на размер сообщения в ТГ делаем деление
            # по абзацам и вывод порциями
            paragraphs = param_text.split('\n')
            counter = 0
            out_text = paragraphs[0]
            last_paragraph = len(paragraphs) - 1
            log.debug('Вывод сообщения. Длина текста {}. Параграфов {}.'.
                      format(len(param_text), len(paragraphs)))
            while counter < last_paragraph:
                counter += 1
                if (len(out_text) + len(paragraphs[counter]) > 4096) \
                        or (counter >= last_paragraph):
                    if counter >= last_paragraph:
                        # Выводим последние порции текста
                        out_text = out_text + '\n' + paragraphs[counter]
                        await message.answer(text=out_text,
                                             reply_markup=param_reply_markup)
                        break
                    else:
                        await message.answer(text=out_text)
                    sleep(1)
                    out_text = ''
                out_text = out_text + '\n' + paragraphs[counter]
            else:
                await message.answer(text=out_text,
                                     reply_markup=param_reply_markup)
        else:
            await message.answer(text='Действие выполнено. '
                                      'Жду дальнейших действий.',
                                 reply_markup=param_reply_markup)
    except BaseException as err:
        log.exception("Ошибка отправки сообщения: " + str(err), exc_info=True)


async def safe_reply_message(message: Message, param_text: str = "",
                             param_reply_markup: InlineKeyboardMarkup = None) \
        -> None:
    """
    Безопасная отправка ответа на сообщение чат-ботом для пользователя.

    :param message: Связующий объект с чат-ботом
    :type message: Message
    :param param_text: Текстовое сообщение для пользователя
    :type param_text: str
    :param param_reply_markup: Набор кнопок для чата
    :type param_reply_markup: InlineKeyboardMarkup

    :return: None
    """
    try:
        await message.reply(text=param_text, reply_markup=param_reply_markup)
    except BaseException as err:
        log.exception("Ошибка ответа на сообщение: " + str(err), exc_info=True)


def get_message(action: CallbackQuery | Message) -> Message | None:
    """
    Вернуть определённый тип объекта для дальнейшей обработки.
    В данном случае "Message"

    :param action: Объект, который связан с телеграм (CallBack или Message).
    :type action: CallbackQuery | Message

    :return: Объект типа "Message"
    :rtype: Message | None
    """
    message = None

    if isinstance(action, CallbackQuery):
        message = action.message
    elif isinstance(action, Message):
        message = action

    return message


async def stop_polling() -> None:
    """
    Остановить телеграм-бот
    """
    try:
        await _dp.stop_polling()
    except BaseException as err:
        log.exception('Ошибка запроса на прекращение работы телеграм-бота:'
                      ' {}'.format(str(err)), exc_info=True)


async def empty_function(callback: CallbackQuery | Message | User,
                         data_key: List = None,
                         state: FSMContext = None,
                         history: Dict = None) -> bool:
    """
    Функция-заглушка для обработки CallBack событий, которым ещё не назначен
    основной обработчик.

    :param callback: Связующий объект с чат-ботом
    :type callback: CallbackQuery | Message | User
    :param data_key: Список уточняющих ключей, передаваемых в callback-функции
    :type data_key: List
    :param state: Экземпляр машины состояний для фильтрации в запросах
    :type state: FSMContext
    :param history: Данные из таблицы истории запросов (в основном нужен id)
    :type history: Dict

    :return: Результат работы функции. Истина - успешно, Ложь - в иных случаях
    :rtype: bool
    """
    if isinstance(callback, CallbackQuery):
        name_param = callback.data
    else:
        name_param = callback.text
    text = f'Обработчик не назначен для "{name_param}". ' \
           f'\nКлючи {str(data_key)}.\n'
    if state:
        data = await state.get_data()
        data_len = len(data)
        text += f'Количество значений {data_len} шт.\n'
    if history:
        text += f'ID истории {history.get("id")}.\n'
    log.debug('Сработала функция-заглушка для обработки CallBack событий. '
              'Информация из функции:\n{}'.format(text))
    await safe_send_message(get_message(callback), text)
    return False


def default_action(**kwargs) -> Dict:
    """
    Функция-заглушка для выполнения действий.

    :param kwargs: Любой набор именованных параметров.
    :return: Пустой словарь
    """
    log.debug('Сработала функция-заглушка для выполнения действий. '
              'Параметры функции: {}'.format(str(kwargs)))
    return dict()


def __check_admin_rights_default(from_user: User) -> bool:
    """
    Функция-заглушка для проверки уровня административных прав.

    :param from_user: данные пользователя.
    :type from_user: Message

    :return: False
    :rtype: bool
    """
    log.debug('Сработала функция-заглушка для проверки уровня '
              f'административных прав для {from_user.full_name}.')
    return False


async def send_photo_by_url(url: str, text: str = None,
                            action: CallbackQuery | Message = None) -> None:
    """
    Отправить картинку в ТГ-чат по URL или ID из БД.
    Если ссылка не указана, то просто отправить текст в ТГ.
    Если в БД нет такой ссылки (первичный файл), то добавить в БД.

    Для чтения из базы данных требуется обработчик действия "func_get_id".
    Для сохранения в базу данных требуется обработчик действия "func_save_id".

    :param url: Ссылка на файл (например, на изображение).
    :type url: str
    :param text: Текст сообщения к файлу.
    :type text: str
    :param action: Связь с сообщениями ТГ-бота.
    :type action: CallbackQuery | Message

    :return: None
    """
    # Определяем тип параметра (в зависимости от источника получения
    # сообщения из телеграм)
    message: Message = get_message(action)
    if not message:
        return

    # Получаем ID файла
    if url:
        log.debug(f'Отправка изображения по URL "{url}"')
        try:
            file_id = _on_event.do_action('func_get_id', file_url=url)
            if file_id:
                await message.answer_photo(photo=file_id, caption=text)
            else:
                image_from_url = URLInputFile(url)
                result = await message.answer_photo(photo=image_from_url,
                                                    caption=text)
                _on_event.do_action('func_save_id', file_url=url,
                                    file_id=result.photo[-1].file_id)

            # Сбросить текстовое описание, если уже отправили
            # успешно файл с текстом
            text = None
        except (aexc.TelegramBadRequest,
                aexc.TelegramNetworkError) as err:
            log.exception('Ошибка отправки файла: ' + str(err), exc_info=True)

    # Отправим просто текст без файла
    if text:
        # Дополним URL к тексту, если он указан
        if url:
            text = f'{text}\nURL={url}'
        await safe_send_message(message, text)


class FilterState(StatesGroup):
    """
    Общие элементы фильтров состояния машины: ожидание и выполнение
    """
    wait_command = State()
    command_doit = State()


class FilterStateFilms(FilterState):
    """
    Элементы фильтра для фильмов
    """
    filter_name = State()
    filter_en_name = State()
    filter_type = State()
    filter_year = State()
    filter_rating_kp = State()
    filter_rating_imdb = State()
    filter_age_rating = State()
    filter_genres = State()


class FilterStatePersons(FilterState):
    """
    Элементы фильтров персон
    """
    person_name = State()
    person_en_name = State()
    person_birthday = State()
    person_age = State()


# Диспетчер телеграм-бота
_dp = Dispatcher(storage=MemoryStorage())

# Для доступа к обработчику событий и действий
_on_event = OnAnythingDoSomething()


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)


if __name__ == "__main__":
    OnAnythingDoSomething()
    safe_send_message()
    safe_reply_message()
    get_message()
    empty_function()
    default_action()
    stop_polling()
    send_photo_by_url()
    FilterStateFilms()
    FilterStatePersons()
