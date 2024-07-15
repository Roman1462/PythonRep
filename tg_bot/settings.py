"""
Модуль настройки приложения. Настройки интерфейсов доступа к телеграм и
сайту вынесены в отдельные классы (TelegramSettings и SiteSettings
соответственно). Также настраивается протоколирование (пакет logging).
В каждом модуле приложения используем локальную переменную log,
инициализированную через "log = settings.logger.getLogger(__name__)",
чтобы было видно в каком модуле выполнено логирование.

SiteSettings() - класс доступа к настройкам API сайта
TelegramSettings() - класс доступа к настройкам API телеграм
logger - экземпляр менеджера логирования
"""

import logging
import os
import time
from dotenv import load_dotenv
from pydantic import BaseSettings, SecretStr, StrictStr

# Грузим настройки приложения
load_dotenv()

class SiteSettings(BaseSettings):
    """
    Класс настроек API сайта.
    """
    api_key: SecretStr = os.getenv("SITE_API", None)
    host_api: StrictStr = os.getenv("HOST_API", None)

# Настройка для телеграм-бота
class TelegramSettings(BaseSettings):
    """
    Класс настроек API телеграм.
    """
    api_key: StrictStr = os.getenv("TG_TOKEN", '')
    host_api: StrictStr = os.getenv("TG_HOST", '')

# Создать каталог для хранения протоколов
path_logs = os.path.abspath('logs')
if not os.path.exists(path_logs):
    os.makedirs(path_logs, exist_ok=True)

# Включаем логирование, чтобы не пропустить важные сообщения
file_logs = os.path.join(path_logs, time.strftime('%Y-%m-%d') + '.log')
logger = logging
logger.basicConfig(level=logging.DEBUG,  # filename=file_logs, filemode='a',
                   format='%(asctime)s %(name)s %(levelname)s %(message)s',
                   encoding='utf-8')

# Эта строка нужна в каждом модуле. Обращение через log.info()
log = logger.getLogger(__name__)

if __name__ == "__main__":
    SiteSettings()
    TelegramSettings()
