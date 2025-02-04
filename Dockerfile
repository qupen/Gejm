FROM python:3.10-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

RUN mkdir -p /app/instance

ENTRYPOINT ["/app/entrypoint.sh"]

#CMD ["python3", "app.py"]