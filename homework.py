import sys
import os
from http import HTTPStatus
import requests
import telegram
from dotenv import load_dotenv
import logging
import time
import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщение в Telegram чат."""
    try:
        logging.info('Начало отправки статуса в telegram')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except telegram.error.TelegramError as error:
        logging.error(f'Не удалось отправить сообщение {error}')
        raise exceptions.TelegramError(
            f'Не удалось отправить сообщение {error}')

    else:
        logging.debug(f'Сообщение отправлено {message}')


def get_api_answer(timestamp):
    """Получает статус домашней работы."""
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    message = ('Начало запроса к API. Запрос: {url}, {headers}, {params}.'
               ).format(**params_request)
    logging.info(message)
    try:
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.InvalidResponseCode(
                'Не удалось получить ответ API, '
                f'ошибка: {response.status_code}'
                f'причина: {response.reason}'
                f'текст: {response.text}')
        return response.json()
    except Exception as error:
        message = ('API не возвращает 200. Запрос: {url}, {headers}, {params}.'
                   ).format(**params_request)
        raise exceptions.InvalidResponseCode(message, error)


def check_response(response):
    """Проверить валидность ответа."""
    logging.info('Проверка ответа API на корректность')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является dict')
    if 'homeworks' not in response or 'current_date' not in response:
        raise exceptions.EmptyResponseFromAPI('Нет нужных ключей в ответе API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является list')
    return homeworks


def parse_status(homework):
    """Обарботка ответа API."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {homework_status}')
    return (
        'Изменился статус проверки работы "{homework_name}" {verdict}'
    ).format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = ('Отсутствуют необходимые переменные окружения.',
                   'Бот остановлен!')
        logging.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    start_message = 'Бот активирован'
    send_message(bot, start_message)
    logging.info(start_message)
    last_msg = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Нет новых статусов'
            if message != last_msg:
                send_message(bot, message)
                last_msg = message
            else:
                logging.info(message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            if message != last_msg:
                send_message(bot, message)
                last_msg = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler(
                os.path.abspath('main.log'), mode='a', encoding='UTF-8'),
            logging.StreamHandler(stream=sys.stdout)],
        format='%(asctime)s, %(levelname)s, %(funcName)s, '
               '%(lineno)s, %(name)s, %(message)s'
    )
    main()
