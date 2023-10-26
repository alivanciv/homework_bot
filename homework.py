import datetime
import logging
import os
import sys
import time

import dotenv
import requests
import telegram
from exceptions import (Api400Exception, Api401Exception, ApiStatusException,
                        UnhandledApiException, HomeworkStatusException,
                        UnhandledStatusException)

dotenv.load_dotenv()

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

logging.basicConfig(
    filename='main.log',
    filemode='w',
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности требуемых переменных окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.critical(
            'Ошибка при загрузке токенов. Убедитсеь, '
            'что PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID '
            'определены в пространстве переменных окружения.'
            'Текущее пространтсво переменных содержит: '
            f'{list(dotenv.dotenv_values(".env").keys())}')
        return False
    return True


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение в Telegram отправлено')
    except Exception as error:
        message = f'Ошибка при отправке сообщения в Telegram: {error}'
        logger.error(message)


def get_api_answer(timestamp):
    """Отправка запроса и получение ответа от API."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS,
                                params={'from_date': timestamp})
        if response.status_code == 400:
            message = 'В запросе передано что-то неожиданное для сервиса.'
            raise Api400Exception(message)
        if response.status_code == 401:
            message = 'Запрос с недействительным или некорректным токеном.'
            raise Api401Exception(message)
        if response.status_code != 200:
            message = 'Запрос к API вернул статус код отличный от 200'
            raise ApiStatusException(message)
    except Exception as error:
        message = f'Ошибка при запросе к API: {error}'
        raise UnhandledApiException(message)
    return response.json()


def check_response(response):
    """Проверка соответствия ответа API документации."""
    try:
        if response['current_date']:
            if not response['homeworks']:
                logger.debug('Новых статусов нет')
                return False
            if type(response['homeworks']) is not list:
                message = ('Ошибка в типе ключа "homewroks" ответe от API')
                raise TypeError(message)
            return True
    except KeyError as error:
        message = f'Ошибка в ключах ответа от API: {error}'
        raise KeyError(message)


def parse_status(homework):
    """Извлечение статуса работы из полученого ответа API."""
    try:
        homework_name = homework['homework_name']
        status = homework['status']
        if status not in list(HOMEWORK_VERDICTS.keys()):
            message = 'Получен неожиданный статус работы.'
            raise HomeworkStatusException(message)
        verdict = HOMEWORK_VERDICTS[status]
    except Exception as error:
        message = f'Ошибка при извлечении статуса работы: {error}'
        raise UnhandledStatusException(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    exception_count = 0
    send_message(bot, 'Запуск бота. Последнее изменение за все время:')
    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                homework = response['homeworks'][0]
                send_message(bot, parse_status(homework))
                dt = datetime.datetime.strptime(
                    homework['date_updated'], "%Y-%m-%dT%H:%M:%SZ")
                dt += datetime.timedelta(days=1)
                timestamp = int(dt.timestamp())
                exception_count = 0
        except Exception as error:
            message = f'Сбой в работе программы: {error}: {exception_count+1}'
            if exception_count == 0:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
            exception_count += 1
            logger.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
