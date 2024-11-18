FROM python:3.10.4
WORKDIR /app

COPY . /app
RUN pip install -r requirements.txt

COPY . .

RUN useradd app
USER app

# Adicionar versionamento baseado no commit
LABEL version="1.0.0-${GIT_COMMIT_HASH}"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]