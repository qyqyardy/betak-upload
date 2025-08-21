#!/bin/bash
set -e

echo "Initializing/upgrading the database..."
airflow db migrate


echo "Creating admin user..."
airflow users create \
    --username Administrator \
    --password 'Admin2025!!' \
    --firstname Administrator \
    --lastname Administrator \
    --role Admin \
    --email your-email@gmail.com || true


echo "Starting scheduler..."
airflow scheduler &


echo "Waiting for DAG 'migrasi_recording_dag' to be parsed..."
max_retries=10
retry_count=0
while [ $retry_count -lt $max_retries ]
do
  if airflow dags list | grep -q migrasi_recording_dag; then
    echo "DAG 'migrasi_recording_dag' found!"
    break
  fi
  echo "DAG not found yet. Retrying in 10 seconds..."
  sleep 10
  retry_count=$((retry_count+1))
done

if [ $retry_count -eq $max_retries ]; then
  echo "ERROR: Failed to find DAG 'migrasi_recording_dag' after several retries."
  exit 1
fi

echo "Unpausing DAG 'migrasi_recording_dag'..."
airflow dags unpause migrasi_recording_dag


echo "Starting webserver..."
exec airflow webserver