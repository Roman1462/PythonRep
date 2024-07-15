"""
Модуль для работы с API сайта (интерфейс).
"""

from settings import logger, SiteSettings
from site_API.utils.site_api_handler import SiteApiInterface


site = SiteSettings()

headers = {
    "accept": "application/json",
    "X-API-KEY": site.api_key.get_secret_value()
}

url = site.host_api

site_api = SiteApiInterface(site.host_api, headers)


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)


if __name__ == "__main__":
    site_api()
