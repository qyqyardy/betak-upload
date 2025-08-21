import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def send_email(subject, body, to_email):
    """
    Mengirim email menggunakan konfigurasi dari environment variables.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, smtp_user, smtp_password, to_email]):
        print("ERROR: Konfigurasi SMTP tidak lengkap. Email tidak dapat dikirim.")
        return False

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"Email notifikasi berhasil dikirim ke {to_email}")
        return True
    except Exception as e:
        print(f"Gagal mengirim email: {e}")
        return False

def send_failure_notification(context):
    """
    Callback Airflow untuk mengirim notifikasi jika sebuah task gagal.
    """
    task_instance = context.get('task_instance')
    dag_id = task_instance.dag_id
    task_id = task_instance.task_id
    log_url = task_instance.log_url
    
    subject = f"🚨 Kegagalan pada Airflow Task: {task_id}"
    body = f"""
    <h3>Halo Tim,</h3>
    <p>Terdeteksi kegagalan pada salah satu task Airflow:</p>
    <ul>
        <li><strong>DAG:</strong> {dag_id}</li>
        <li><strong>Task:</strong> {task_id}</li>
        <li><strong>Waktu Eksekusi:</strong> {task_instance.execution_date}</li>
        <li><strong>Log:</strong> <a href="{log_url}">Lihat Log Detail</a></li>
    </ul>
    <p>Mohon segera diperiksa.</p>
    """
    to_email = os.getenv("NOTIFICATION_EMAIL")
    if to_email:
        send_email(subject, body, to_email)
    else:
        print("ERROR: NOTIFICATION_EMAIL tidak diatur, email notifikasi task gagal tidak dikirim.")


def send_upload_failure_email(filename):
    """
    Mengirim email notifikasi spesifik untuk unggahan file S3 yang gagal.
    """
    template_path = '/opt/airflow/email-temp.html'
    try:
        with open(template_path, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"ERROR: Template email tidak ditemukan di {template_path}")
        template = """
        <div class="header">🚨 Migrasi File Gagal</div>
        <div class="details">
            <p>Halo Tim,</p>
            <p>Terdeteksi kegagalan dalam proses migrasi file recording ke AWS S3:</p>
            <ul>
                <li><strong>File:</strong> {{ filename }}</li>
                <li><strong>Status:</strong> Gagal upload</li>
                <li><strong>Waktu:</strong> {{ timestamp }}</li>
            </ul>
        </div>
        """

    body = template.replace("{{ filename }}", filename).replace("{{ timestamp }}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    subject = f"🚨 Gagal Unggah File: {filename}"
    to_email = os.getenv("NOTIFICATION_EMAIL")

    if to_email:
        print(f"Mempersiapkan notifikasi kegagalan untuk file: {filename}")
        send_email(subject, body, to_email)
    else:
        print("ERROR: NOTIFICATION_EMAIL tidak diatur, email notifikasi unggah gagal tidak dikirim.")