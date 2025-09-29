# ===================================================================
# 1. Builder stage: Menginstall dependensi Python
#
# Di tahap ini, kita menginstall semua paket Python yang dibutuhkan.
# Dengan memisahkannya, image akhir (runtime) akan lebih kecil karena
# tidak perlu membawa build-essential dan library development lainnya.
# ===================================================================
FROM python:3.10-slim AS builder

# ARG untuk kemudahan maintenance versi
ARG PYTHON_VERSION=3.10
ARG AIRFLOW_VERSION=2.9.3

# Mencegah Python membuat file .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies yang dibutuhkan untuk beberapa paket Python (e.g., psycopg2)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

# Selalu upgrade pip sebelum install paket lain
RUN pip install --upgrade pip

# Install dependensi dari requirements.txt DENGAN CONSTRAINTS FILE.
# Ini adalah perbaikan utama untuk menghindari error "resolution-too-deep".
RUN pip install --no-cache-dir \
    -r /requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"


# ===================================================================
# 2. Runtime stage: Image akhir yang akan dijalankan
#
# Tahap ini mengambil hasil instalasi Python dari 'builder' dan
# menambahkan file-file aplikasi. Image ini lebih ringan dan aman
# karena hanya berisi apa yang dibutuhkan untuk berjalan.
# ===================================================================
FROM python:3.10-slim

ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW_UID=50000
ENV PYTHONPATH="${AIRFLOW_HOME}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime dependencies (bukan build dependencies)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Membuat user airflow untuk keamanan (menghindari run as root)
RUN groupadd --gid ${AIRFLOW_UID} airflow && \
    useradd --uid ${AIRFLOW_UID} --gid airflow -m -s /bin/bash airflow && \
    mkdir -p ${AIRFLOW_HOME}/logs ${AIRFLOW_HOME}/plugins /opt/recordings

# [SANGAT PENTING] Salin paket Python yang sudah diinstall dari stage 'builder'
COPY --from=builder /usr/local /usr/local

# Salin file-file proyek
COPY --chown=airflow:airflow ./airflow/dags/ ${AIRFLOW_HOME}/dags/
COPY --chown=airflow:airflow ./scripts/ ${AIRFLOW_HOME}/scripts/
COPY --chown=airflow:airflow init.sql .env email-temp.html ${AIRFLOW_HOME}/
COPY --chown=airflow:airflow entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Atur kepemilikan direktori
RUN chown -R airflow:airflow ${AIRFLOW_HOME} /opt/recordings

# Ganti ke user non-root
USER airflow
WORKDIR ${AIRFLOW_HOME}
EXPOSE 8080

# Gunakan 'tini' sebagai entrypoint untuk menangani sinyal OS dengan benar
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]