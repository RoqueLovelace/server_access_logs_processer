FROM python:3.13-slim-bookworm

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY slog_processer_serv.py ./

EXPOSE 8000

CMD ["uvicorn","slog_processer_serv:app","--reload","--host","0.0.0.0"]
