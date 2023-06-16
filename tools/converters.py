from typing import Iterable

from pymorphy2.shapes import restore_capitalization

from loader import morph


def degress_to_side(deg: float) -> str:
    if 338 <= deg <= 360 or 0 <= deg <= 22:
        return 'северный'
    elif 22 <= deg <= 67:
        return 'северо-восточный'
    elif 67 <= deg <= 112:
        return 'восточный'
    elif 112 <= deg <= 157:
        return 'юго-восточный'
    elif 157 <= deg <= 202:
        return 'южный'
    elif 202 <= deg <= 247:
        return 'юго-западный'
    elif 247 <= deg <= 292:
        return 'западный'
    elif 292 <= deg <= 337:
        return 'северо-западный'


def weather_id_to_icon(id_: int) -> str:
    match id_ // 100:
        case 2:
            return '⛈️'
        case 3:
            return '🌦️'
        case 5:
            return '🌧️'
        case 6:
            return '🌨️'
        case 7:
            match id_ % 100 // 10:
                case 3 | 5 | 6:
                    return '💨'
                case _:
                    return '🌫️'
    match id_ % 10:
        case 0:
            return '☀️'
        case 1:
            return '🌤️'
        case 2:
            return '⛅'
        case 3 | 4:
            return '🌥️'


def inflect_city(text: str, required_grammemes: Iterable[str]) -> str:
    """
    Эта функция принимает название города и список тегов граммем и возвращает склонённое название города на основе
    предоставленных тегов. Входная строка разбивается на токены, и каждый токен изменяется на основе предоставленных
    граммем с помощью pymorphy2. Восстановление заглавных букв токенов осуществляется с помощью
    pymorphy2.shapes.restore_capitalization(), прежде чем токены снова объединяются в строку, которая подаётся на выход.

    :param text: Название города для изменения.
    :type text: str
    :param required_grammemes: Список тегов граммем для использования при изменении.
    :type required_grammemes: Iterable[str]

    :return: Склонённое название города в соответствии с граммемами.
    :rtype: str
    """

    tokens = text.split()
    inflected = [
        restore_capitalization(
            morph.parse(tok)[0].inflect(required_grammemes).word,
            tok
        )
        for tok in tokens
    ]
    return " ".join(inflected)
