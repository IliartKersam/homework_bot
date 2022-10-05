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
    """The function of sending a message, we log the success and error of sending."""
    logger.debug('Trying to send a message to Telegram.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Message "{message}", sent successfully')
    except Exception:
        raise SendMessageError('Error sending message to Telegram')


def get_api_answer(current_timestamp: int) -> dict:
    """We receive a response from the Yandex API, log a response other than 200."""
    timestamp = current_timestamp
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    endpoint = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    params = {'from_date': timestamp}
    data = {'url': endpoint, 'headers': headers, 'params': params}
    logger.debug('Sending a request to the Yandex server')
    try:
        response = requests.get(**data)
        if response.status_code != HTTPStatus.OK:
            error_message = response.text.split('\"')[-2]
            raise EndpointError(
                f'Эндпоинт https://practicum.yandex.ru/api/user_api/'
                f'homework_statuses/ not available, '
                f'error code - {response.status_code}. {error_message}'
            )
        logger.debug('Received a response from the server')
    except Exception as error:
        raise RequestError(f'Error while requesting the server - {error}')
    return response.json()


def check_response(response: dict) -> list:
    """We get from the response from the API, we log all surprises."""
    logger.debug('We start checking the response from the server.')
    if not isinstance(response, dict):
        raise TypeError(
            f'Wrong data type received - '
            f'{type(response)}, dictionary expected'
        )
    if not response:
        raise ValueError('Received an empty dictionary in response from the server.')
    if 'homeworks' not in response:
        raise KeyError('The resulting dictionary does not contain the homeworks key.')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError(
            f'Wrong data type received - '
            f'{type(homework)}, expected list'
        )
    return homework


def parse_status(homework: dict) -> str:
    """Parsing values, logging the absence of expected values."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError('There is no homework_name key in the list.')
    homework_status = homework.get('status')
    homework_comment = homework.get('reviewer_comment')
    if not homework_status:
        raise KeyError('There is no status key in the list.')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Unknown homework status.')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Homework verification status changed "{homework_name}". {verdict} {homework_comment}'


def check_tokens() -> bool:
    """Checking that tokens are available, logging the absence."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main() -> None:
    """The main logic of the bot."""
    logger.debug('Start the bot...')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME
    last_message = None
    last_message_error = None
    if not check_tokens():
        logger.critical('Error reading tokens.')
        sys.exit('Error reading tokens.')
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
                        'Received a repeat of the last message, '
                        'sending message canceled'
                    )
            else:
                logger.debug('Missing new homework status.')
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Program crash: {error}'
            logger.error(message)
            if message != last_message_error:
                try:
                    send_message(bot, message)
                except Exception as error:
                    logger.error(f'{error}')
                last_message_error = message
            else:
                logger.debug(
                    'Received a repeat of the last error message, '
                    'sending message canceled'
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
