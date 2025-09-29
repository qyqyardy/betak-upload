# Proyek Migrasi Rekaman Panggilan (AXA Testing)

Proyek ini adalah sebuah *pipeline* data yang dirancang untuk mengotomatisasi proses validasi, pengindeksan, dan migrasi file rekaman panggilan beserta metadatanya ke *cloud storage* (AWS S3). Dibangun menggunakan **Apache Airflow**, proyek ini memastikan proses migrasi berjalan secara andal, termonitor, dan dapat diulang.

## 📜 Ringkasan

Sistem ini secara otomatis memindai direktori penyimpanan lokal (`/opt/recordings`) untuk file rekaman baru (dalam format `.wav` dan `.xml`). Metadata dari file XML diekstrak dan disimpan dalam basis data PostgreSQL. Selanjutnya, file `.wav` diunggah ke *bucket* AWS S3 dengan struktur direktori yang terorganisir. Jika terjadi kegagalan, sistem akan mengirimkan notifikasi email secara otomatis.

## ✨ Fitur Utama

* **Orkestrasi Alur Kerja**: Menggunakan **Apache Airflow** untuk mengelola dan menjadwalkan *pipeline* migrasi data.
* **Pengindeksan Otomatis**: Secara otomatis memindai, mem-parsing file metadata (`.xml`), dan memasukkannya ke dalam basis data PostgreSQL.
* **Migrasi ke AWS S3**: Mengunggah file rekaman (`.wav`) ke *bucket* AWS S3 dengan metadata yang relevan.
* **Notifikasi Kegagalan**: Mengirimkan notifikasi email secara otomatis ketika terjadi kegagalan pada *task* Airflow atau proses unggah file.
* **Logging & Monitoring Terpusat**: Terintegrasi dengan *stack* **Grafana Loki** untuk agregasi log dan pemantauan secara *real-time*.
* **Lingkungan Tercontainerisasi**: Seluruh layanan (Airflow, Postgres, Grafana, dll.) dijalankan menggunakan **Docker** dan **Docker Compose** untuk kemudahan instalasi dan portabilitas.
* **CI/CD Pipeline**: Dilengkapi dengan alur kerja CI/CD menggunakan GitLab CI untuk proses *build* dan *deploy* otomatis.

## 🏗️ Arsitektur Sistem

Proyek ini terdiri dari beberapa layanan yang bekerja sama, didefinisikan dalam file `docker-compose.yml`:

1.  **Airflow**: Komponen inti yang berfungsi sebagai orkestrator alur kerja.
    * `airflow-webserver`: Antarmuka pengguna (UI) untuk mengelola dan memonitor DAG.
    * `airflow-scheduler`: Bertanggung jawab untuk menjadwalkan dan menjalankan *task* DAG.
2.  **PostgreSQL**: Digunakan sebagai *backend database* untuk Airflow dan juga untuk menyimpan metadata file rekaman.
3.  **Redis**: Berfungsi sebagai *message broker* untuk Airflow.
4.  **Loki**: Sistem agregasi log yang mengumpulkan log dari semua layanan.
5.  **Promtail**: Agen yang mengirim log dari direktori lokal ke Loki.
6.  **Grafana**: *Platform* visualisasi untuk membuat dasbor pemantauan dari data log yang ada di Loki.

## 🚀 Cara Menjalankan

### Prasyarat

* **Docker**: [Link Instalasi](https://docs.docker.com/get-docker/)
* **Docker Compose**: [Link Instalasi](https://docs.docker.com/compose/install/)

### Langkah-langkah Instalasi

1.  **Clone Repositori**
    ```bash
    git clone <URL_REPOSITORI_ANDA>
    cd <NAMA_DIREKTORI_PROYEK>
    ```

2.  **Konfigurasi Lingkungan**
    Buat file `.env` dengan menyalin dari file `.env` yang sudah ada. Sesuaikan nilainya sesuai dengan kebutuhan Anda.

    ```bash
    cp .env .env
    ```

    Pastikan variabel berikut telah diisi dengan benar:
    * **PostgreSQL**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
    * **Airflow Connection**: `AIRFLOW__CORE__SQL_ALCHEMY_CONN` (sesuaikan dengan kredensial Postgres)
    * **AWS Credentials**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET`
    * **SMTP for Notifications**: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFICATION_EMAIL`

3.  **Siapkan Direktori Data**
    Pastikan direktori untuk menyimpan file rekaman tersedia dan memiliki data di dalamnya. Secara default, sistem akan memindai direktori `/opt/recordings`. Anda dapat mengubah *path* ini di file `docker-compose.yml`.

    ```bash
    mkdir -p /opt/recordings
    # Salin file .wav dan .xml Anda ke direktori ini
    ```

4.  **Jalankan dengan Docker Compose**
    Bangun dan jalankan semua layanan dalam mode *detached*.

    ```bash
    docker-compose up --build -d
    ```

5.  **Akses Layanan**
    * **Airflow Web UI**: Buka `http://localhost:8080`
        * **Username**: `Administrator`
        * **Password**: `Admin2025!!`
    * **Grafana Dashboard**: Buka `http://localhost:3000`
        * **Username**: `admin`
        * **Password**: `admin`

### Penggunaan

Setelah semua layanan berjalan, DAG `migrasi_recording_dag` akan otomatis aktif. Anda dapat memicu eksekusinya secara manual melalui Airflow UI atau menunggu jadwal eksekusi (jika dikonfigurasi).

1.  Buka **Airflow UI**.
2.  Cari DAG `migrasi_recording_dag`.
3.  Klik tombol "Play" untuk memicu proses migrasi secara manual.
4.  Pantau status eksekusi pada tab "Grid" atau "Graph". Log dari setiap *task* dapat dilihat langsung dari UI.

## 🔧 Konfigurasi Tambahan

### DAG `migrasi_recording_dag`

DAG utama dalam proyek ini memiliki dua *task* utama:

1.  `validate_and_index`: Menjalankan skrip `validate_and_index.py` untuk memindai file baru, memvalidasi metadata, dan menyimpannya ke database.
2.  `upload_to_s3`: Menjalankan skrip `uploader.py` untuk mengambil data dari database dan mengunggah file yang belum dimigrasi ke S3.

### CI/CD

Proyek ini menggunakan GitLab CI untuk otomatisasi *build* dan *deploy*. *Pipeline* didefinisikan dalam file `.gitlab-ci.txt` dan terdiri dari dua tahap:

* `build`: Membangun *image* Docker dan mendorongnya ke GitLab Container Registry.
* `deploy`: Menarik *image* terbaru dari *registry* dan menjalankan ulang kontainer pada server produksi melalui SSH.