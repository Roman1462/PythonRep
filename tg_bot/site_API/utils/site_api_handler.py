"""
Модуль для получения информации с сайта (связующая часть).
"""

from settings import logger
import requests
from typing import Dict, Callable, List
from urllib.parse import quote


def _make_response(url: str, headers: Dict, params: Dict) -> \
        int | requests.Response:
    """
    Получение ответа от сайта с информацией.

    :param url: Адрес сайте, где информация лежит.
    :type url: str
    :param headers: Заголовки в запросе.
    :type headers: Dict
    :param params: Параметры запроса.
    :type params: Dict

    :return: Код ошибки (если код <> OK) или ответ от сервера
    :rtype: int | requests.Response
    """

    # В качестве констант время отклика и код ошибки
    timeout: int = 5
    success: int = 200

    # Запрашиваем ресурс в сети
    response = requests.request('GET', url, headers=headers,
                                params=params, timeout=timeout)

    # Проверяем код ответа и возвращаем результат или код ответа
    status_code = response.status_code
    if status_code == success:
        return response
    return status_code


class SiteApiInterface:
    """
    Интерфейс для работы с API сайта.
    """

    def __init__(self, param_url: str, param_headers: Dict) -> None:
        self.__base_url: str = param_url
        self.__headers: Dict = param_headers

    @classmethod
    def get_film_by_name(cls, base_url: str, headers: Dict, params: str,
                         func: Callable = _make_response) \
            -> int | requests.Response:
        """
        Поиск фильма по части его названия.

        :param base_url: Базовый адрес сайте, где берём данные.
        :type base_url: str
        :param headers: Заголовок (ключи доступа).
        :type headers: Dict
        :param params: Строка запроса, по которой ищем фильм.
        :type params: str
        :param func: Функция для выполнения запроса и получения данных.
        :type func: Callable

        :return: Код ошибки (если код <> OK) или ответ от сервера
        :rtype: int | requests.Response
        """

        # Формируем полный адрес для получения данных и словарь запроса
        url: str = "{0}/{1}".format(base_url, 'auto-complete')
        querystring: Dict = {"q": params}

        # Получить данные с ресурса в сети и вернуть их
        response = func(url, headers=headers, params=querystring)
        return response

    def get_person_by_id(self, param_id: str) -> int | requests.Response:
        """
        Получить информацию об актёре с сайта по id

        :param param_id: ID актёра (персоны)

        :return: response
        """

        # Формируем полный адрес для получения данных и словарь запроса
        url: str = "/".join((self.__base_url, 'v1', 'person', param_id))
        query_string: Dict = {}

        # Получить данные с ресурса в сети и вернуть их
        response = _make_response(url, self.__headers, query_string)

        return response

    def get_random_films(self):
        """
        Получить данные по рандомному фильму.

        :return: response
        """
        # Формируем полный адрес для получения данных и словарь запроса
        url: str = "/".join((self.__base_url, 'v1.3', 'movie', 'random'))
        query_string: Dict = {}

        # Получить данные с ресурса в сети и вернуть их
        response = _make_response(url, self.__headers, query_string)

        return response

    def get_one_film(self, param_id: str | int):
        """
        Получить фильм по ID с сайта.

        :param param_id: ID искомого файла

        :return: response
        """
        # Формируем полный адрес для получения данных и словарь запроса
        url: str = "/".join((self.__base_url, 'v1.3', 'movie', param_id))
        query_string: Dict = {}

        # Получить данные с ресурса в сети и вернуть их
        response = _make_response(url, self.__headers, query_string)

        return response

    def get_film_by_filter(self, param_filter: Dict[str, str | List]):
        """
        Получить фильм по фильтру.

        :param param_filter: Словарь для фильтрации значений.

        :return: response
        """
        # Формируем полный адрес для получения данных и словарь запроса
        full_filter: List = [self.__base_url, 'v1.3',
                             'movie?page=1&limit=10&selectFields=id%20type'
                             '%20name%20shortDescription%20description'
                             '%20distributors%20premiere%20year%20rating'
                             '%20votes%20movieLength%20images'
                             '%20productionCompanies%20budget%20poster'
                             '%20facts%20genres%20countries%20videos'
                             '%20persons%20enName%20ageRating%20logo%20'
                             'names&sortField=year%20rating.kp%20name&'
                             'sortType=-1%20-1%201&']

        # Формируем список параметров запроса
        query_filter: List = []
        for i_key in param_filter:
            value = param_filter.get(i_key, None)
            if value:
                if isinstance(value, list):
                    for i_value in value:
                        i_value = quote(i_value)
                        query_filter.append(f'{i_key}={i_value}')
                else:
                    value = quote(value)
                    query_filter.append(f'{i_key}={value}')

        # Объединяем в одну строку (url) для запроса
        url: str = "/".join(full_filter) + "&".join(query_filter)
        query_string: Dict = {}

        # Получить данные с ресурса в сети и вернуть их
        response = 0
        try:
            response = _make_response(url, self.__headers, query_string)
        except BaseException as err:
            log.exception(err, exc_info=True)

        return response

    def get_person_by_filter(self, param_filter: Dict[str, str | List]):
        """
        Получить сведения о персонах по фильтру.

        :param param_filter: Словарь с элементами фильтра.

        :return: response
        """
        # Формируем полный адрес для получения данных и словарь запроса
        full_filter: List = [self.__base_url, 'v1',
                             'person?page=1&limit=50&']

        # Формируем список параметров запроса
        query_filter: List = []
        for i_key in param_filter:
            value = param_filter.get(i_key, None)
            if value:
                if isinstance(value, list):
                    for i_value in value:
                        i_value = quote(i_value)
                        query_filter.append(f'{i_key}={i_value}')
                else:
                    value = quote(value)
                    query_filter.append(f'{i_key}={value}')

        # Объединяем в одну строку (url) для запроса
        url: str = "/".join(full_filter) + "&".join(query_filter)
        query_string: Dict = {}

        # Получить данные с ресурса в сети и вернуть их
        response = 0
        try:
            response = _make_response(url, self.__headers, query_string)
        except BaseException as err:
            log.exception(err, exc_info=True)

        return response


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)


if __name__ == "__main__":
    _make_response()

    SiteApiInterface()
