FROM python:3.10-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 8000

RUN mkdir -p /app/instance

CMD ["python3", "app.py"]