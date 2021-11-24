FROM python:3.7

WORKDIR usr/src/app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .

CMD ["python3.7", "./tg_bot.py"]