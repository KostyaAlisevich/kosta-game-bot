FROM python:3.10-slim-buster

WORKDIR /bot

COPY kosta-game-bot-master.zip /tmp/bot.zip
RUN python -c "import zipfile; zipfile.ZipFile('/tmp/bot.zip').extractall('/tmp/x')" \
    && cp -a /tmp/x/kosta-game-bot-master/. /bot/ \
    && rm -rf /tmp/x /tmp/bot.zip

RUN pip install -r requirements.txt

RUN aerich upgrade

CMD python src/main.py
