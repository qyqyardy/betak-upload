import os
import boto3
from datetime import datetime
import sys 
from scripts.utils import get_db_connection, log, load_dotenv
from scripts.notification import send_upload_failure_email

load_dotenv()

def get_s3_key(file_path, meta):
    """Generate structured S3 key based on file metadata"""
    try:
        start_time_obj = meta.get('start_time')
        
        if start_time_obj and isinstance(start_time_obj, datetime):
            date_part = start_time_obj.strftime("%Y/%m/%d")
        else:
            date_part = datetime.now().strftime("%Y/%m/%d")
        
        content_type = "audio" if meta.get('contenttype', '').startswith("audio") else "screen"
        agent_id = meta.get('agent_id', 'unknown_agent').split('\\')[-1]
        
        return f"recordings/{content_type}/{date_part}/{agent_id}/{os.path.basename(file_path)}"
    except Exception as e:
        log(f"Error generating S3 key: {str(e)}", level='error')
        return f"recordings/unknown/{datetime.now().strftime('%Y/%m/%d')}/{os.path.basename(file_path)}"

def upload_to_s3(local_path, bucket, meta):
    """Upload file to S3 with enhanced metadata handling"""
    s3 = boto3.client("s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "ap-southeast-1")
    )
    
    try:
        if not os.path.exists(local_path):
            log(f"[ERROR] File not found: {local_path}", level='error')
            return None 
            
        key = get_s3_key(local_path, meta)
        
        start_time_str = meta.get('start_time')
        if isinstance(start_time_str, datetime):
            start_time_str = start_time_str.isoformat()
        
        extra_args = {
            'Metadata': {
                'agent_id': str(meta.get('agent_id', '')),
                'extension': str(meta.get('extension', '')),
                'caller_id': str(meta.get('caller_id', '')),
                'called_id': str(meta.get('called_id', '')),
                'start_time': start_time_str,
                'duration': str(meta.get('duration', 0))
            }
        }
        
        s3.upload_file(local_path, bucket, key, ExtraArgs=extra_args)
        log(f"[SUCCESS] Uploaded {local_path} to s3://{bucket}/{key}")
        return key
    except Exception as e:
        log(f"[FAILED] {local_path} -> {str(e)}", level='error')
        send_upload_failure_email(os.path.basename(local_path))
        return None 

def process_uploads():
    """Memproses file yang akan diunggah ke S3."""
    conn = None
    has_errors = False
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, filename, local_path, agent_id, extension, caller_id, called_id, start_time, duration
            FROM recordings
            WHERE uploaded = false
            ORDER BY start_time ASC
            LIMIT 100
        """)
        
        rows = cur.fetchall()
        if not rows:
            log("No new files to upload.")
            return
            
        bucket = os.getenv("AWS_S3_BUCKET")
        if not bucket:
            log("AWS_S3_BUCKET environment variable not set", level='error')
            raise ValueError("AWS_S3_BUCKET environment variable not set")
            
        success_count = 0
        for row in rows:
            rec_id, fname, path, agent_id, ext, caller_id, called_id, start_time, duration = row
            
            meta = {
                'agent_id': agent_id,
                'extension': ext,
                'caller_id': caller_id,
                'called_id': called_id,
                'start_time': start_time,
                'duration': duration,
                'contenttype': 'audio/wav'
            }
            
            s3_key = upload_to_s3(path, bucket, meta)
            
            if s3_key:
                cur.execute("""
                    UPDATE recordings 
                    SET uploaded = true, s3_path = %s 
                    WHERE id = %s
                """, (s3_key, rec_id))
                success_count += 1
            else:
                has_errors = True
        
        conn.commit()
        log(f"Upload completed. Success: {success_count}/{len(rows)}")
        
    except Exception as e:
        log(f"[CRITICAL] Error in process_uploads: {str(e)}", level='error')
        if conn:
            conn.rollback()
        sys.exit(1) 
    finally:
        if conn:
            cur.close()
            conn.close()
        if has_errors:
            sys.exit(1) 

if __name__ == "__main__":
    process_uploads()