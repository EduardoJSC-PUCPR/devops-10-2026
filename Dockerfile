FROM python:3.14-slim

RUN mkdir /app

WORKDIR /app

COPY app ./app
COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8001

CMD ["fastapi", "run", "app/api.py", "--port", "8001"]