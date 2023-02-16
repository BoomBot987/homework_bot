class InvalidResponseCode(Exception):
    """Не верный код ответа."""
    pass


class TelegramError(Exception):
    """Ошибка телеграма."""
    pass


class EmptyResponseFromAPI(Exception):
    """Пустой ответ от API."""
    pass


