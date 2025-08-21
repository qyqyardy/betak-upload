FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt



FROM python:3.10-slim

ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW_UID=50000
ENV PYTHONPATH="${AIRFLOW_HOME}:${AIRFLOW_HOME}/dags:${AIRFLOW_HOME}/scripts"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid ${AIRFLOW_UID} airflow && \
    useradd --uid ${AIRFLOW_UID} --gid airflow -m -s /bin/bash airflow && \
    mkdir -p ${AIRFLOW_HOME}/logs ${AIRFLOW_HOME}/plugins /mnt/recordings

COPY --from=builder /root/.local /home/airflow/.local
ENV PATH=/home/airflow/.local/bin:$PATH

COPY --chown=airflow:airflow ./airflow/dags/ ${AIRFLOW_HOME}/dags/
COPY --chown=airflow:airflow ./scripts/ ${AIRFLOW_HOME}/scripts/
COPY --chown=airflow:airflow init.sql .env email-temp.html ${AIRFLOW_HOME}/
COPY --chown=airflow:airflow entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN chown -R airflow:airflow ${AIRFLOW_HOME} /mnt/recordings

USER airflow

WORKDIR ${AIRFLOW_HOME}
EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]