FROM python:3.11-slim-bullseye AS build

RUN apt-get update && \
    apt-get -y install build-essential

RUN mkdir -p /usr/src/app/azuretests

WORKDIR /usr/src/app/azuretests

RUN pip install --upgrade pip
RUN pip install poetry==2.1.1

RUN --mount=type=secret,id=art_user,target=/run/secrets/art_user \
    --mount=type=secret,id=art_pass,target=/run/secrets/art_pass \
    poetry config repositories.biocatch "https://biocatchdev.jfrog.io/biocatchdev/api/pypi/pypi/simple" && \
    poetry config http-basic.biocatch $(cat /run/secrets/art_user) $(cat /run/secrets/art_pass) && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install

COPY . /usr/src/app/azuretests

RUN export APP_VERSION=$(poetry version | cut -d' ' -f2) && echo "__version__ = '$APP_VERSION'" > azuretests/__init__.py

FROM python:3.11-slim-bullseye

# Copy only the necessary files from the build stage
COPY --from=build /usr/local/lib/ /usr/local/lib/
COPY --from=build /usr/src/app/azuretests /usr/src/app/azuretests
COPY --from=build /usr/local/bin/ /usr/local/bin/

# Rookout vars

ARG COMMIT_HASH

ENV PYTHONPATH=${PYTHONPATH}:/app/
ENV PYTHONOPTIMIZE=1

ENV PYTHONNODEBUGRANGES=0

WORKDIR /usr/src/app/azuretests

CMD ["uvicorn", "azuretests.main:app", "--host", "0.0.0.0", "--port", "80"]
