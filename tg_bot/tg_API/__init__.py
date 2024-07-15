"""
Пакет tg_API для доступа к интерфейсу телеграм-бота.

:var
    tg_api - экземпляр класса для взаимодействия с телеграм-ботом.

    dp - экземпляр класса диспетчера телеграм-бота.

    on_event - обработчик событий и действий (связь с функциями в других пакетах).
"""

from .core import TelegramApiInterface
from .utils import dp as _dp, on_event as _on_event


# Экземпляр класса для взаимодействия с телеграм-ботом.
tg_api = TelegramApiInterface()

# Связующий элемент с диспетчером и обработчиком
dp = _dp
on_event = _on_event


if __name__ == "__main__":
    print(type(tg_api), type(dp), type(on_event))
