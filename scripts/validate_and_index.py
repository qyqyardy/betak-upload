import os
import xml.etree.ElementTree as ET
from datetime import datetime
import sys 
from scripts.utils import get_db_connection, log

def parse_xml(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
        
        segment = root.find('ns:segment', namespaces=ns) or root.find('segment')
        start_time = segment.findtext('ns:starttime', namespaces=ns) if segment else None
        content_type = segment.findtext('ns:contenttype', namespaces=ns) if segment else None
        duration = segment.findtext('ns:duration', namespaces=ns) if segment else None
        
        agent_id = ""
        ani = ""
        dnis = ""
        extension = ""
        
        contacts = root.find('ns:contacts', namespaces=ns) or root.find('contacts')
        if contacts:
            contact = contacts.find('ns:contact', namespaces=ns) or contacts.find('contact')
            if contact:
                sessions = contact.find('ns:sessions', namespaces=ns) or contact.find('sessions')
                if sessions:
                    session = sessions.find('ns:session', namespaces=ns) or sessions.find('session')
                    if session:
                        ani = session.findtext('ns:ani', namespaces=ns) or ""
                        dnis = session.findtext('ns:dnis', namespaces=ns) or ""
                        extension = session.findtext('ns:extension', namespaces=ns) or ""
                        pbx_login = session.findtext('ns:pbx_login_id', namespaces=ns) or ""
                        
                        if not agent_id:
                            tags = session.find('ns:tags', namespaces=ns) or session.find('tags')
                            if tags:
                                for tag in tags.findall('ns:tag', namespaces=ns) or tags.findall('tag'):
                                    agent_attr = tag.find('ns:attribute[@key="agentid"]', namespaces=ns)
                                    if agent_attr is not None:
                                        agent_id = agent_attr.get('x:value') or agent_attr.text or ""
                                        break
                                    agent_attr = tag.find('attribute[@key="agentid"]')
                                    if agent_attr is not None:
                                        agent_id = agent_attr.get('value') or agent_attr.text or ""
                                        break
        
        return {
            "agent_id": agent_id or pbx_login,
            "extension": extension,
            "caller_id": ani,
            "called_id": dnis,
            "start_time": start_time,
            "duration": duration,
            "contenttype": content_type
        }
    except Exception as e:
        log(f"[ERROR] Failed to parse {file_path}: {str(e)}", level='error')
        return None

def index_files(storage_path="/opt/recordings"):
    conn = None
    has_errors = False
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if not os.path.exists(storage_path):
            log(f"[ERROR] Storage path not found: {storage_path}", level='error')
            
            sys.exit(1)
            
        processed = 0
        skipped = 0
        
        for root_dir, _, files in os.walk(storage_path):
            for file in files:
                if file.endswith(".xml"):
                    base = os.path.splitext(file)[0]
                    wav_file = base + ".wav"
                    xml_path = os.path.join(root_dir, file)
                    wav_path = os.path.join(root_dir, wav_file)
                    
                    if not os.path.exists(wav_path):
                        log(f"[WARNING] WAV file not found for {xml_path}")
                        skipped += 1
                        continue
                        
                    meta = parse_xml(xml_path)
                    if not meta:
                        has_errors = True
                        continue
                    
                    try:
                        cur.execute("""
                            INSERT INTO recordings (
                                filename, agent_id, extension, caller_id, called_id, 
                                start_time, duration, local_path, uploaded
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false)
                            ON CONFLICT (filename) DO NOTHING;
                        """, (
                            base,
                            meta["agent_id"],
                            meta["extension"],
                            meta["caller_id"],
                            meta["called_id"],
                            meta["start_time"],
                            meta["duration"],
                            wav_path
                        ))
                        
                        if cur.rowcount > 0:
                            processed += 1
                            log(f"Indexed: {wav_path}")
                        else:
                            log(f"Skipped (already exists): {wav_path}")
                    except Exception as e:
                        log(f"[ERROR] Failed to index {wav_path}: {str(e)}", level='error')
                        has_errors = True
                        conn.rollback() 

        
        if not has_errors:
            conn.commit()
            
        
        log(f"Indexing completed. Processed: {processed}, Skipped: {skipped}, Errors: {int(has_errors)}")
        
    except Exception as e:
        log(f"[CRITICAL] Error in index_files: {str(e)}", level='error')
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
    index_files(storage_path="/opt/recordings")