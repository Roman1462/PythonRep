"""
Пакет tg_API.utils. Модули общего назначения для интерфейса с телеграм.


:var
    dp - экземпляр класса диспетчера телеграм-бота.

    on_event - обработчик событий и действий (связь с функциями в других пакетах).


:module
    commands - Набор общих функций бота (отправка сообщений, файлов и т.п.)

    keys - Наборы ключей для формирования меню и наборов кнопок для всех
    возможных ситуаций

    tg_api_handlers - Обработчики событий от телеграм-бота
"""

from .commands import _dp as dp, _on_event as on_event
from .tg_api_handler import router_callback, router_filter, router_command


# Регистрация роутеров
dp.include_router(router_command)  # Команды /start и /help
dp.include_router(router_callback)  # Обратные вызовы (менюшка)
dp.include_router(router_filter)  # Произвольные иные типы данных


if __name__ == "__main__":
    print(type(dp), type(on_event))
