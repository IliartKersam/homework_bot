import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from my_exception import TokenError, EndpointError

logging.basicConfig(
    level=logging.INFO,
    filename='bot.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправки сообщения, логируем успех и ошибку отправки."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение "{message}", отправлено успешно')
    except Exception:
        logging.exception('Ошибка отправки сообщения')


def get_api_answer(current_timestamp):
    """Получаем ответ от API Яндекса, логируем ответ отличный от 200."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    response = requests.get(ENDPOINT, headers=headers, params=params)
    if response.status_code != 200:
        logging.error(
            f'Эндпоинт https://practicum.yandex.ru/api/user_api/'
            f'homework_statuses/ недоступен, '
            f'код ошибки - {response.status_code}'
        )
        raise EndpointError
    response = response.json()
    return response


def check_response(response):
    """Получаем из ответа от API список с домашней работой,
    логируем все неожиданности."""
    if type(response) != dict:
        logging.error(
            f'Получен не верный тип данных - '
            f'{type(response)}, а ожидался словарь')
        raise TypeError
    if len(response) == 0:
        logging.error('В ответ от сервера получен пустой словарь')
        raise ValueError
    if 'homeworks' not in response:
        logging.error('В полученном словаре нет ключа homeworks')
        raise KeyError
    homework = response.get('homeworks')
    if type(homework) != list:
        logging.error(
            f'Получен не верный тип данных - '
            f'{type(homework)}, а ожидался список')
        raise TypeError
    return homework


def parse_status(homework):
    """Парсим значения из полученного списка,
    логтруем отсутствие ожидаемых значений"""
    if homework.get('homework_name') is None:
        logging.error('В списке нет ключа homework_name')
        raise KeyError
    homework_name = homework.get('homework_name')
    if homework.get('status') is None:
        logging.error('В списке нет ключа status')
        raise KeyError
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Неизвестный статус работы')
        raise ValueError
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, что токены доступны, лотгурем отсутствие"""
    if ((PRACTICUM_TOKEN != None) and (TELEGRAM_TOKEN != None) and (
            TELEGRAM_CHAT_ID != None)) == True:
        return True
    else:
        return False
        logging.critical('Ошибка чтения токенов')
        raise TokenError


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0

    while check_tokens():
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework != []:
                message = parse_status(homework[0])
                send_message(bot, message)
            logging.debug(
                'Отсутствует новый статус домашней работы.'
            )
            current_timestamp = 0
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
