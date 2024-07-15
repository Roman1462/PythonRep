"""
Модуль с наборами кнопок для чат-бота.


:Functions
    builder_start() - Стартовый набор кнопок (главное меню).

    builder_random_films() - Набор кнопок для фильма.

    builder_custom_buttons() - Пользовательский набор кнопок.


:var
    buttons_start - Список кнопок главного меню.

    buttons_after_films - Список кнопок для уточнения сведений по фильму.

    buttons_search_films - Список кнопок для поиска фильмов.

    buttons_search_persons - Список кнопок для поиска актёров.

    buttons_after_film_filter - Список кнопок для добавления после фильтра.

    buttons_after_person_filter - Список кнопок для добавления после фильтра.

    buttons_title_types - Список кнопок для выбора вариантов тайтла.
"""

from typing import List, Tuple
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Клавиатура с 7 кнопками для главного меню (после кнопки старта, Main Menu)
buttons_start = [
    ("Помощь", "mm_help_me"),
    ("Кто ты, БОТ?", "mm_who_are_you"),
    ("Поиск фильма", "mm_search_film"),
    ("Актёры", "mm_search_person"),
    ("Статистика", "mm_statistic"),
    ("История", "mm_history"),
    ("Предложи случайный фильм", "mm_want_film")
]

# Клавиатура для уточнения сведений по предложенному фильму
buttons_after_films = [
    ("Рейтинги", "af_rating."),
    ("В ролях", "af_persons."),
    ("Компании", "af_companies."),
    ("Факты", "af_facts."),
    ("Трейлеры", "af_trailers."),
    ("Похожие фильмы", "af_similar."),
    ("Предложи другой фильм", "mm_want_film")
]

# Клавиатура для поиска фильмов по фильтру - каждая кнопка элемент фильтра
buttons_search_films = [
    ("Название", "bf_name"),
    ("Название на английском", "bf_enName"),

    # Тип тайтла.
    # Доступны: movie | tv-series | cartoon | anime | animated-series | tv-show
    ("Тип тайтла", "bf_type"),

    # Год премьеры. При поиске по этому полю, можно использовать
    # интервалы 1860-2030
    ("Год премьеры", "bf_year"),

    ("Рейтинг кинопоиска", "bf_ratingKp"),
    ("Рейтинг IMDB", "bf_ratingImdb"),
    ("Возрастной рейтинг", "bf_ageRating"),
    ("Жанр", "bf_genres")
]

# Клавиатура для поиска актёров по фильтру - каждая кнопка элемент фильтра
buttons_search_persons = [
    ("Имя", "bp_name"),
    ("Имя на английском", "bp_enName"),
    ("Дата рождения", "bp_birthday"),
    ("Возраст", "bp_age")
]

# Клавиатура для добавления после первого выбранного фильтра
buttons_after_film_filter = [
    ("Выполнить поиск", "bf_doit"),
    ("Сбросить фильтр", "bf_reset")
]
buttons_after_person_filter = [
    ("Выполнить поиск", "bp_doit"),
    ("Сбросить фильтр", "bp_reset")
]

# Кнопки для выбора вариантов тайтла фильма
buttons_title_types = ["movie", "tv-series", "cartoon", "anime",
                       "animated-series", "tv-show"]


def _builder_prepare(buttons: List[Tuple[str, str]], text: str = "") \
        -> InlineKeyboardMarkup:
    """
    Функция подготовки наборов кнопок.

    :param buttons: Список кнопок в виде кортежей (название, действие).
    :param text: Всплывающий текст, выводимый над кнопками.

    :return: Экземпляр класса для Inline клавиатуры.
    """
    builder = InlineKeyboardBuilder()
    for i_button in buttons:
        builder.add(InlineKeyboardButton(
            text=i_button[0],
            callback_data=i_button[1])
        )

    # Расположение по 2 кнопки в ряд
    builder.adjust(2)
    reply_markup = builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=text
    )
    return reply_markup


def builder_start(text: str = "") -> InlineKeyboardMarkup:
    """
    Подготовить стартовый набор кнопок (для главного меню).

    :param text: Всплывающий текст, выводимый над кнопками.

    :return: Экземпляр класса для Inline клавиатуры.
    """
    # Набор кнопок для основного меню
    return _builder_prepare(buttons_start, text)


def builder_random_films(text: str = "", data_key: str = "") -> \
        InlineKeyboardMarkup:
    """
    Создать клавиатуру для получения сведений по фильму.

    :param text: Всплывающий текст, выводимый над кнопками.
    :param data_key: Код (ID) для фильма, по которому формируем клавиатуру.

    :return: Экземпляр класса для Inline клавиатуры.
    """
    # Набор кнопок после выдачи случайного фильма с добавлением ключа
    # после точек в кодах событий.
    result = builder_custom_buttons(text, data_key, buttons_after_films)
    return result


def builder_custom_buttons(text: str = "", data_key: str = "",
                           buttons: List[Tuple[str, str]] = None) -> \
        InlineKeyboardMarkup:
    """
    Создать клавиатуру с любым набором кнопок

    :param text: Всплывающий текст, выводимый над кнопками
    :param data_key: Код (ID) для элемента, по которому формируем клавиатуру.
    :param buttons: Список кнопок в виде кортежей (название, действие).

    :return: Экземпляр класса для Inline клавиатуры
    """
    # Набор кнопок пользователя с добавлением ключа после точек в кодах
    # событий.
    buttons_with_key = []
    for i_button in buttons:
        if i_button[1].endswith('.'):
            buttons_with_key.append((i_button[0], f'{i_button[1]}{data_key}'))
        else:
            buttons_with_key.append((i_button[0], i_button[1]))
    return _builder_prepare(buttons_with_key, text)


if __name__ == "__main__":
    builder_start()
    builder_random_films()
    builder_custom_buttons()
