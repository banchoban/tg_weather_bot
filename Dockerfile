FROM python:3.7

WORKDIR usr/src/app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .

HEALTHCHECK --interval=5m --timeout=2m --start-period=10s \
   CMD curl -f --retry 5 --max-time 5 --retry-delay 30 "http://localhost:3000/health" || bash -c 'kill -s 15 -1 && (sleep 10; kill -s 9 1)'

CMD ["python3.7", "./tg_bot.py", "/etc/db/sqlite3.db", "3000"]