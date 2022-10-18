FROM python:3.8-alpine as builder

WORKDIR /app
ENV PYTHONUNBUFFERED 1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade \
    fastapi \
    uvicorn \
    jinja2 \
    python-multipart \
    sonic-client

FROM python:3.8-alpine as runtime

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENV SONIC_HOST="host.docker.internal"
ENV RUNTIME='prod'

EXPOSE 5000
COPY ./app.py /app/
COPY ./secrets.json /app/
COPY ./html_templates/ /app/html_templates
CMD ["python", "app.py"]
