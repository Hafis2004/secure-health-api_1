import os
import glob
from flask import Flask, request, jsonify
from auth import verify_jwt, require_roles
from compliance import audit_log
from storage import save_record, get_record
from prometheus_client import Counter, Histogram, generate_latest

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
REQ_LATENCY = Histogram('api_request_latency_seconds', 'Latency', ['endpoint'])

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/records', methods=['GET'])
@verify_jwt
@require_roles(['viewer', 'editor'])
def get_all_patients():
    """Get all patient records."""
    try:
        with REQ_LATENCY.labels('/records').time():
            records = []
            data_dir = 'data'
            if os.path.exists(data_dir):
                for bin_file in glob.glob(os.path.join(data_dir, '*.bin')):
                    try:
                        pid = os.path.basename(bin_file).replace('.bin', '')
                        data = get_record(pid)
                        if data:
                            records.append(data)
                    except Exception as e:
                        print(f"Error reading record {bin_file}: {e}")
                        pass
        audit_log('READ_ALL', 'all')
        REQUEST_COUNT.labels('/records', 'GET', '200').inc()
        return jsonify({'records': records, 'count': len(records)}), 200
    except Exception as e:
        print(f"Error in get_all_patients: {e}")
        REQUEST_COUNT.labels('/records', 'GET', '500').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/records/<pid>', methods=['GET'])
@verify_jwt
@require_roles(['viewer', 'editor'])
def get_patient(pid):
    with REQ_LATENCY.labels('/records').time():
        data = get_record(pid)
    audit_log('READ', pid)
    status = 200 if data else 404
    REQUEST_COUNT.labels('/records', 'GET', str(status)).inc()
    return (jsonify(data), status) if data else (jsonify({'error': 'not found'}), 404)

@app.route('/records', methods=['POST'])
@verify_jwt
@require_roles(['editor'])
def create_patient():
    payload = request.get_json()
    pid = save_record(payload)
    audit_log('CREATE', pid)
    REQUEST_COUNT.labels('/records', 'POST', '201').inc()
    return jsonify({'id': pid}), 201

if __name__ == "__main__":
    # Run with HTTPS on port 8443
    app.run(
        host="0.0.0.0",
        port=8443,
        ssl_context=('certs/server.crt', 'certs/server.key'),
        debug=False
    )