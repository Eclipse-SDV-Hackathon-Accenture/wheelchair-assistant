# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
# SPDX-License-Identifier: MIT

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

ARG PYTHON_VERSION=3.9.18
ARG POETRY_VERIONS=1.7.1
ARG POETRY_HOME="/opt/poetry"
ARG APP_PATH="/opt/app"

ARG PROTOC_VERSION=25.1
ARG PROTOC_HOME="/opt/protoc"

################################################################################
# Create a stage for building the application.
FROM docker.io/library/python:${PYTHON_VERSION}-slim-bullseye AS build

ARG POETRY_VERSION
ARG POETRY_HOME
ARG APP_PATH
ARG APP_NAME=wheelchair_assistant_state_manager

ARG PROTOC_VERSION
ARG PROTOC_HOME

ENV POETRY_VERSION=$POETRY_VERSION
ENV POETRY_HOME=$POETRY_HOME
ENV PATH="$PROTOC_HOME/bin:$POETRY_HOME/bin:$PATH"

ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Add Build dependencies.
RUN apt update && \
    apt upgrade -y && \
    apt install -y \
    curl \
    unzip

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN curl -s -o /tmp/protoc.zip -L https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-x86_64.zip
RUN unzip /tmp/protoc.zip -d ${PROTOC_HOME}


RUN mkdir -p ${APP_PATH}
WORKDIR ${APP_PATH}

RUN mkdir -p ank
RUN mkdir -p digital_twin

COPY poetry.lock ${APP_PATH}/
COPY pyproject.toml ${APP_PATH}/
COPY ank/__init__.py ${APP_PATH}/api
COPY ank/ankaios.proto ${APP_PATH}/ank
COPY digital_twin/digital_twin_get_provider.proto ${APP_PATH}/digital_twin

RUN poetry lock &&  \
    poetry install --only main

RUN cd ${APP_PATH} && \
    protoc --python_out=. ank/ankaios.proto && \
    touch ank/__init__.py \

RUN cd ${APP_PATH} && \
    protoc --python_out=. digital_twin/digital_twin_get_provider.proto && \
    touch digital_twin/__init__.py

################################################################################
# Create a new stage for running the application that contains the minimal
# runtime dependencies for the application. This often uses a different base
# image from the build stage where the necessary files are copied from the build
# stage.
#
# The example below uses the debian bullseye image as the foundation for running the app.
# By specifying the "bullseye-slim" tag, it will also use whatever happens to be the
# most recent version of that tag when you build your Dockerfile. If
# reproducability is important, consider using a digest
# (e.g., debian@sha256:ac707220fbd7b67fc19b112cee8170b41a9e97f703f588b2cdbbcdcecdd8af57).
FROM docker.io/library/python:${PYTHON_VERSION}-slim-bullseye AS final
ARG POETRY_HOME
ARG APP_PATH

ENV TZ="Europe/Berlin"
ENV POETRY_HOME=$POETRY_HOME
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV GRPC_SERVER="0.0.0.0:5010"

COPY --from=build $POETRY_HOME $POETRY_HOME
COPY --from=build ${APP_PATH} ${APP_PATH}

COPY wheelchair_asistant_state_manager.py ${APP_PATH}/

WORKDIR ${APP_PATH}

# What the container should run when it is started.
CMD ["poetry", "run" ,"python" , "/opt/app/wheelchair_asistant_state_manager.py"]