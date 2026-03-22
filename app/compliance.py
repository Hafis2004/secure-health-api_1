import time, json, os
from flask import g, request

AUDIT_FILE = 'audit.log'
RETENTION_DAYS = int(os.environ.get('RETENTION_DAYS','30'))

def audit_log(action, pid):
    user = getattr(g, 'user', {})
    remote_addr = request.remote_addr if request else 'unknown'
    entry = {
        'ts': int(time.time()),
        'user': user.get('preferred_username', 'unknown'),
        'action': action,
        'patient_id': pid,
        'ip': remote_addr
    }
    print(f"[AUDIT] {entry}")
    try:
        with open(AUDIT_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        print(f"Error writing audit log: {e}")
def data_minimize(payload):
    allowed = {k: payload[k] for k in ['id','name','dob','consent'] if k in payload}
    return allowed

def enforce_consent(payload):
    if not payload.get('consent', False):
        raise ValueError('Consent required')

def retention_cleanup():
    cutoff = time.time() - RETENTION_DAYS*24*3600
    # stub: you’d scan files with timestamps and remove older than cutoff
    return cutoff