import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from my_exception import EndpointError, SendMessageError, RequestError

logger = logging.getLogger(__name__)
load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: telegram.bot.Bot, message: str) -> None:
    """Функция отправки сообщения, логируем успех и ошибку отправки."""
    logger.debug('Попытка отправки сообщения в Telegam')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение "{message}", отправлено успешно')
    except Exception:
        raise SendMessageError('Ошибка отправки сообщения в телеграмм')


def get_api_answer(current_timestamp: int) -> dict:
    """Получаем ответ от API Яндекса, логируем ответ отличный от 200."""
    timestamp = current_timestamp
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    endpoint = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    params = {'from_date': timestamp}
    data = {'url': endpoint, 'headers': headers, 'params': params}
    logger.debug('Направляем запрос к серверу Яндекс')
    try:
        response = requests.get(**data)
        if response.status_code != HTTPStatus.OK:
            error_message = response.text.split('\"')[-1]
            raise EndpointError(
                f'Эндпоинт https://practicum.yandex.ru/api/user_api/'
                f'homework_statuses/ недоступен, '
                f'код ошибки - {response.status_code}. {error_message}'
            )
        logger.debug('Получен ответ от сервера')
    except Exception as error:
        raise RequestError(f'Ошибка при запросе к серверу - {error}')
    return response.json()


def check_response(response: dict) -> list:
    """Получаем из ответа от API, логируем все неожиданности."""
    logger.debug('Начинаем проверку ответа от сервера')
    if not isinstance(response, dict):
        raise TypeError(
            f'Получен не верный тип данных - '
            f'{type(response)}, а ожидался словарь'
        )
    if not response:
        raise ValueError('В ответ от сервера получен пустой словарь')
    if 'homeworks' not in response:
        raise KeyError('В полученном словаре нет ключа homeworks')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError(
            f'Получен не верный тип данных - '
            f'{type(homework)}, а ожидался список'
        )
    return homework


def parse_status(homework: dict) -> str:
    """Парсим значения, логируем отсутствие ожидаемых значений."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError('В списке нет ключа homework_name')
    homework_status = homework.get('status')
    homework_comment = homework.get('reviewer_comment')
    if not homework_status:
        raise KeyError('В списке нет ключа status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Неизвестный статус работы')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict} Комментарий ревьюреа: {homework_comment}'


def check_tokens() -> bool:
    """Проверяем, что токены доступны, логируем отсутствие."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main() -> None:
    """Основная логика работы бота."""
    logger.debug('Запуск бота...')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME
    last_message = None
    last_message_error = None
    if not check_tokens():
        logger.critical('Ошибка чтения токенов')
        sys.exit('Ошибка чтения токенов')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
                else:
                    logger.debug(
                        'Получен повтор последнего сообщения, '
                        'отправка отменена'
                    )
            else:
                logger.debug('Отсутствует новый статус домашней работы')
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_message_error:
                try:
                    send_message(bot, message)
                except Exception as error:
                    logger.error(f'{error}')
                last_message_error = message
            else:
                logger.debug(
                    'Повтор последнего сообщения об ошибке, '
                    'отправка отменена'
                )
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='bot.log',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    logger.setLevel(logging.DEBUG)
    streamHandler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    main()
