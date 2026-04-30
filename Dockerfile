FROM python:3.8

WORKDIR /app

COPY requirements.txt start_server.py ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY server/ server/
COPY migrations/ migrations/
COPY characters/ characters/
COPY config/ config/
COPY storage/ storage/
COPY logs/ logs/
COPY music/ music/

CMD ["python", "-u", "./start_server.py"]

