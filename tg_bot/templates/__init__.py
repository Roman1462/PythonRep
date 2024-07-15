"""
Набор шаблонов для формирования ответов пользователю.
"""

from settings import logger
from os import path


def load_template(name: str) -> str:
    """
    Загрузить шаблон из файла и вернуть содержимое как строку.

    :param name: Имя файла, из которого грузим шаблон.
    :type name: str

    :return: Содержимое файла
    :rtype: str
    """
    result = ''

    try:
        full_name: str = path.abspath(name)
        with open(full_name, 'rt', encoding='utf-8') as text:
            result = text.read()
    except FileNotFoundError as err:
        log.exception('Ошибка загрузки файла: ' + str(err), exc_info=True)

    return result


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)


if __name__ == '__main__':
    load_template()
