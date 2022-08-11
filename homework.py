from http import HTTPStatus
import logging
from logging.handlers import RotatingFileHandler
import os
import time
import telegram
import requests
from dotenv import load_dotenv


class HTTPException(Exception):
    """Ошибка HTTP."""

    pass


logging.basicConfig(
    filename='log.txt',
    filemode='w',
    level=logging.DEBUG,
    format='%(asctime)s, %(lineno)s, %(levelname)s, %(message)s',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('log.txt',
                              encoding='UTF-8',
                              maxBytes=50000000,
                              backupCount=5
                              )
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s'
)
handler.setFormatter(formatter)
load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщений бота."""
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        logging.error(f'Ошибка {status_code}')
        raise HTTPException(f'Ошибка {status_code}')
    try:
        return response.json()
    except ValueError:
        logger.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API.
    Ответ приведен к типам данных Python.
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ (он может бытьnи пустым), доступный в ответе
    API по ключу 'homeworks'
    """
    if type(response) is not dict:
        raise TypeError('ОТвет API отличен от словаря')
    try:
        list_homework = response['homeworks']
    except KeyError:
        logging.error('Нет ключа homeworks')
        raise KeyError('Нет ключа homeworks')
    try:
        homework = list_homework[0]
    except IndexError:
        logging.error('Список пуст')
        raise IndexError('Список пуст')
    return homework


def parse_status(homework):
    """Извлекает статус.
    Из информации о конкретной
    домашней работе извлекает статус этой работы.
    """
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logging.error(f'Статус работы некорректен: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return (
        f'Изменился статус проверки работы "{homework_name}". {verdict}'
    )


def check_tokens():
    """Проверка доступности переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    logging.debug('Bot open')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 14000000
    dict = ''
    ERROR_CACHE_MESSAGE = ''
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != dict:
                send_message(bot, message)
                dict = message
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(error)
            message_er = str(error)
            if message_er != ERROR_CACHE_MESSAGE:
                send_message(bot, message_er)
                ERROR_CACHE_MESSAGE = message_er
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
