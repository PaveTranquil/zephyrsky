from datetime import datetime

from sqlalchemy import ARRAY, JSON, Column, Float, Integer, Time, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """
    Класс, представляющий SQLAlchemy-модель пользователя из базы данных.

    :param tg_id: Telegram ID пользователя.
    :type tg_id: int (колонка по SQLAlchemy)
    :param geo: Координаты пользователя.
    :type geo: list[float] (колонка по SQLAlchemy)
    :param notify_time: Время уведомлений пользователя.
    :type notify_time: list[datetime.time] (колонка по SQLAlchemy)
    :param state: Словарь состояний пользователя.
    :type state: dict (колонка по SQLAlchemy)
    """

    __tablename__ = "users"
    tg_id = Column(Integer, primary_key=True)
    geo = Column(ARRAY(Float))
    notify_time = Column(ARRAY(Time))
    state = Column(JSON)


class Database:
    def __init__(self, url):
        """
        Инициализирует новый экземпляр базы данных.

        :param url: URL базы данных для подключения.
        :type url: str
        """
        self.engine = create_engine(url)
        self.session = Session(bind=self.engine)
        
    # GETTERS

    async def get_user(self, tg_id: int) -> User | None:
        """
        Извлекает объект пользователя из базы данных на основе заданного ID в Telegram.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int

        :return: объект пользователя или None, если пользователь не существует.
        :rtype: Union[User, None]
        """
        return self.session.query(User).filter(User.tg_id == tg_id).first()

    async def get_users(self) -> list[User]:
        """
        Получает всех пользователей из базы данных.

        :return: Список объектов типа User.
        """
        return self.session.query(User).all()
    
    # SETTERS

    async def create_user(self, tg_id: int, geo: list[float] = None, notify_time: str = None, state: dict = None):
        """
        Создаёт нового пользователя в базе данных.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int
        :param geo: Список из двух чисел, представляющий географические координаты пользователя (необязательно).
        :type geo: list[float]
        :param notify_time: Строка, представляющая время уведомления в формате 'HH:MM' (необязательно).
        :type notify_time: str
        :param state: Словарь, представляющий состояние пользователя внутри чат-бота (необязательно).
        :type state: dict
        """
        data = {k: v for k, v in list(locals().items())[1:] if v is not None}
        if notify_time := data.get("notify_time"):
            data["notify_time"] = datetime.strptime(notify_time, "%H:%M").time()
        user = User(**data)
        self.session.add(user)
        self.session.commit()

    async def set_geo(self, tg_id: int, geo: list[float]):
        """
        Устанавливает географические координаты для заданного пользователя Telegram.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int
        :param geo: Список из двух чисел с плавающей точкой, представляющий географические координаты.
        :type geo: list[float]

        :raises KeyError: Если пользователя с заданным Telegram ID не существует.
        """
        if user := await self.get_user(tg_id):
            user.geo = geo
            self.session.add(user)
            return self.session.commit()
        raise KeyError

    async def set_notify(self, tg_id: int, notify_time: str):
        """
        Устанавливает время уведомления для заданного пользователя Telegram.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int
        :param notify_time: Время, когда должно быть отправлено уведомление, в формате 'HH:MM'.
        :type notify_time: str

        :raises KeyError: Если пользователя с заданным Telegram ID не существует.
        """
        if user := await self.get_user(tg_id):
            user.notify_time.append(datetime.strptime(notify_time, "%H:%M").time())
            self.session.add(user)
            return self.session.commit()
        raise KeyError

    async def set_state(self, tg_id: int, key, value):
        """
        Устанавливает новое состояние в словаре состояний заданного пользователя Telegram.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int
        :param key: Ключ для установки в словаре состояний пользователя.
        :param value: Значение для установки для указанного ключа в словаре состояний пользователя.

        :raises KeyError: Если пользователя с заданным Telegram ID не существует.
        """
        if user := await self.get_user(tg_id):
            user.state.data[key] = value
            self.session.add(user)
            return self.session.commit()
        raise KeyError

    # DELETERS

    async def delete_geo(self, tg_id: int):
        """
        Удаляет географические координаты заданного пользователя Telegram.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int

        :raises KeyError: Если пользователя с заданным Telegram ID не существует.
        """
        if user := await self.get_user(tg_id):
            user.geo = None
            self.session.add(user)
            return self.session.commit()
        raise KeyError

    async def delete_notify(self, tg_id: int, notify_time: str):
        """
        Удаляет время уведомления для заданного пользователя Telegram.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int
        :param notify_time: Время отправки уведомления в формате 'HH:MM'.
        :type notify_time: str

        :raises KeyError: Если пользователя с заданным Telegram ID не существует.
        :raises ValueError: Если предоставленное время уведомления не существует в списке.
        """
        if user := await self.get_user(tg_id):
            user.notify_time.remove(datetime.strptime(notify_time, "%H:%M").time())
            self.session.add(user)
            return self.session.commit()
        raise KeyError

    async def delete_state(self, tg_id: int, key):
        """
        Удаляет ключ и значение из словаря состояний пользователя.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int
        :param key: Ключ для удаления из словаря состояний пользователя.

        :raises KeyError: Если пользователя с заданным Telegram ID не существует.
        :raises ValueError: Если предоставленный ключ не существует в словаре состояний пользователя.
        """
        if user := await self.get_user(tg_id):
            if user.state.data[key]:
                user.state.data.pop(key)
                self.session.add(user)
                return self.session.commit()
            raise ValueError
        raise KeyError

    async def delete_user(self, tg_id: int):
        """
        Удаляет пользователя из базы данных, если он существует.

        :param tg_id: Telegram ID пользователя.
        :type tg_id: int

        :raises KeyError: Если пользователя с заданным Telegram ID не существует.
        """
        if user := await self.get_user(tg_id):
            self.session.delete(user)
            return self.session.commit()
        raise KeyError
