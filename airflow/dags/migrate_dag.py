from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from scripts.notification import send_failure_notification

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': send_failure_notification
}

with DAG('migrasi_recording_dag',
         default_args=default_args,
         schedule_interval=None,
         catchup=False,
         max_active_runs=1) as dag:

    validate_and_index = BashOperator(
        task_id='validate_and_index',
        bash_command='python /opt/airflow/scripts/validate_and_index.py',
        retries=2
    )

    upload_to_s3 = BashOperator(
        task_id='upload_to_s3',
        bash_command='python /opt/airflow/scripts/uploader.py',
        retries=2
    )

    validate_and_index >> upload_to_s3