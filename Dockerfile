FROM python:3.11-bullseye

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && \
    apt-get -y install libpq-dev libffi-dev && \
    pip install -v -r requirements.txt

COPY . .
RUN python3 setup.py install