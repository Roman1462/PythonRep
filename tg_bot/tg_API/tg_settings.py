"""
Файл, содержащий ссылки на объекты для доступа в пределах телеграм-бота.
Использует модуль settings основного приложения телеграм-бота.

logger - доступ к менеджеру логирования. В каждом модуле приложения
    используем локальную переменную log, инициализированную через
    "log = settings.logger.getLogger(__name__)"

api_key - ключ доступа к телеграм-боту (получить ключ нужно через
    https://t.me/BotFather).
host_api - url для доступа к телеграм API
"""

import settings


# Для связи с протоколированием
logger = settings.logger

# Настройка для телеграм-бота
api_key = settings.TelegramSettings().api_key
host_api = settings.TelegramSettings().host_api


if __name__ == "__main__":
    pass
