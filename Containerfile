FROM python:3.14-slim

WORKDIR /compilador

RUN pip install --no-cache-dir poetry

COPY pyproject.toml .
COPY poetry.lock .
COPY README.md .
COPY src/ ./src

RUN poetry install --no-cache


ENTRYPOINT ["poetry", "run", "compilador"]
CMD ["/dev/stdin"]
