FROM python:3.10-slim-buster

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /bot

# Весь проект лежит в одном архиве рядом с этим Dockerfile
COPY kosta-game-bot-master.zip /tmp/bot.zip
RUN python -c "import zipfile; zipfile.ZipFile('/tmp/bot.zip').extractall('/tmp/x')" \
    && cp -a /tmp/x/kosta-game-bot-master/. /bot/ \
    && rm -rf /tmp/x /tmp/bot.zip \
    && (test -f /bot/src/main.py || (echo "ОШИБКА: в архиве нет src/main.py - загрузили не тот архив?" && exit 1))

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "src/main.py"]
