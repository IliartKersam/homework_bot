# Bot assistant.
## Description
A Telegram bot that accesses the Yandex Praktikum Homework API and finds out the status of your homework: whether your homework was reviewed, whether it was checked, and if it was checked, then it was accepted by the reviewer or returned for revision. Markdown is a lightweight markup language based on the formatting conventions that people naturally use in email.
#### What does the bot do:
- polls the Practicum.Homework service API every 10 minutes and checks the status of the homework submitted for review;
- when updating the status, it analyzes the API response and sends you a corresponding notification in Telegram;
- logs its work and informs you about important problems with a message in Telegram.
### How to run the project:
Clone repository and go to it's derictory on your computer:
```
git clone https://github.com/IliartKersam/homework_bot.git
```
```
cd homework_bot/
```
Create and activate virtual environment:

```
python -m venv venv
```
```
source venv/Scripts/activate
```
```
python -m pip install --upgrade pip
```
Install the requirements from requirements.txt:
```
pip install -r requirements.txt
```
Create a file for secret keys in the root folder of the project
```
touch .env
```
Fill in the **.env** file according to the template:
> PRACTICUM_TOKEN= <Get token here - https://oauth.yandex.ru/authorize?response_type=token&client_id=1d0b9dd4d652455a9eb710d450ff456a>
> TELEGRAM_TOKEN= <Your Telegram Bot token>
> TELEGRAM_CHAT_ID= <Your Telegram chat ID>

Run the project:
```
python homework.py
```
### Author
Kashtanov Nikolay

Kazan, 2022
