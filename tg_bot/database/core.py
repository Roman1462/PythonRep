from settings import logger

from database.utils.crud import CRUDInterface
from database.common.models import db, tables_list


db.connect()
db.create_tables(tables_list)

crud = CRUDInterface()


def close_database() -> None:
    """
    Закрыть базу данных, если она ещё не закрыта.

    :return: None
    """
    if not db.is_closed():
        db.close()
    return


# Начинаем работу с определения логирования и сообщение в протокол
log = logger.getLogger(__name__)


if __name__ == "__main__":
    crud()
