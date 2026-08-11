FROM python:3.12-slim

WORKDIR /app  

COPY requirements.txt . 

RUN pip install -r requirements.txt --no-cache-dir

COPY app.py .

EXPOSE 8080 

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers" , "2" , "--access-logfile" , "-" , "app:app"]


