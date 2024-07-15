"""
Модуль для работы с API телеграм (интерфейс).

TelegramApiInterface - класс, содержащий методы для запуска телеграм-бота
"""

import asyncio
from typing import Callable
from aiogram import Bot
import aiogram.exceptions as aexc

from .tg_settings import host_api, api_key, logger
from .utils import dp, on_event


class TelegramApiInterface:
    """
    Класс для доступа к телеграм-боту. При запуске (run) можно указать
    свой функцию в качестве параметра. По умолчанию работает функция __main
    """

    def __init__(self):
        # Initialize Bot instance with a default parse mode which will
        # be passed to all API calls
        self.__bot = Bot(token=api_key, parse_mode="HTML")

    def run(self, func: Callable = None) -> None:
        """
        Запуск телеграм-бота

        :param func: Пользовательская функция для запуска бота
        :type func: Callable

        :return: None

        :exception ValueError: Если не инициализированы переменные в
            модуле настроек телеграм-бота
        """
        if not logger:
            raise ValueError('Нет связи с логгером!')
        if not api_key or not host_api:
            raise ValueError('Нет связи с токеном АПИ телеграм!')
        try:
            if func:
                asyncio.run(func())
            asyncio.run(self.__main())
        except BaseException as err:
            log.exception('Обнаружено исключение: {}'.format(str(err)),
                          exc_info=True)

    async def __main(self) -> None:
        """
        Главный (по умолчанию) обработчик для запуска телеграм-бота.

        :return: None
        """
        # Запускаем бота и пропускаем все накопленные входящие
        await self.__bot.delete_webhook(drop_pending_updates=True)
        await self.send_message_for_all_users(
            "Запуск бота инициирован.\nКеш команд сброшен.\n\nГлавное "
            "меню - /start\nЗавершить скрипт - /stop\nПолучить помощь - "
            "/help\nИнформация о боте - /info\nДругих команд нет. "
            "Работайте через кнопки меню."
        )
        await dp.start_polling(self.__bot)
        await self.send_message_for_all_users(
            "Завершение работы бота. При запуске скрипта вы будете "
            "проинформированы. До связи!"
        )

    async def send_message(self, user_id: int, out_message: str):
        """
        Отправка сообщений абоненту.

        :param user_id: ID абонента (или группы)
        :type user_id: int
        :param out_message: Текст сообщения
        :type out_message: str
        """
        await self.__bot.send_message(user_id, out_message)

    async def send_message_for_all_users(self, message: str) -> None:
        """
        Массовая рассылка текста сообщения всем пользователям из базы
        данных, за исключением тех, кто не согласен на информирование.

        :param message: Текст сообщения для рассылки всем абонентам.
        :type message: str
        """
        try:
            users = on_event.do_action('retrieve_users')
            for i_user in users:
                if i_user.id_user and i_user.is_agree:
                    try:
                        await self.send_message(i_user.id_user, message)
                    except aexc.TelegramForbiddenError as err:
                        log.exception('Блокировка у пользователя {}: {}'.
                                      format(i_user.username, str(err)),
                                      exc_info=False)
                    finally:
                        # Маленькая пауза перед посылкой сообщения
                        await asyncio.sleep(1)
        except BaseException as err:
            log.exception('Ошибка при массовом оповещении запуска! {}'.
                          format(str(err)), exc_info=True)


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)


if __name__ == "__main__":
    TelegramApiInterface()
