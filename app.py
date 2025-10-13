from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import dns.resolver
import smtplib
import socket
import csv
import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

print("="*60)
print("WAYNE'S PRO EMAIL VERIFIER - INITIALIZED")
print("8 Simultaneous Verification Modules Active")
print("="*60 + "\n")

import re
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
MAX_WORKERS = 8

RESULTS_DIR = 'results'
os.makedirs(RESULTS_DIR, exist_ok=True)

def validate_email_format(email):
    return bool(EMAIL_REGEX.match(email.strip()))

def check_mx_record(domain):
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except:
        return False

def verify_smtp(email):
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_host = str(mx_records[0].exchange)
        server = smtplib.SMTP(timeout=10)
        server.set_debuglevel(0)
        server.connect(mx_host)
        server.helo('newtpfn.com')
        server.mail('verify@newtpfn.com')
        code, message = server.rcpt(email)
        server.quit()
        return code == 250
    except socket.timeout:
        return True
    except Exception as e:
        error_str = str(e).lower()
        if 'blocked' in error_str or 'denied' in error_str:
            return True
        return False

def verify_single_email(email):
    email = email.strip().lower()
    if not validate_email_format(email):
        return {'email': email, 'valid': False, 'reason': 'Invalid format'}
    domain = email.split('@')[1]
    if not check_mx_record(domain):
        return {'email': email, 'valid': False, 'reason': 'No MX records'}
    if not verify_smtp(email):
        return {'email': email, 'valid': False, 'reason': 'Mailbox does not exist'}
    return {'email': email, 'valid': True, 'reason': 'Valid email'}

@app.route('/verify', methods=['POST'])
def verify_emails():
    print("\n" + "="*60)
    print("NEW VERIFICATION REQUEST")
    print("="*60)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    client_name = request.args.get('client', '').strip()
    dedupe = request.args.get('dedupe') == '1'
    
    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        emails = []
        headers = next(csv_reader, None)
        email_col_index = 0
        if headers:
            for i, header in enumerate(headers):
                if 'email' in header.lower():
                    email_col_index = i
                    break
        for row in csv_reader:
            if row and len(row) > email_col_index:
                email = row[email_col_index].strip()
                if email:
                    emails.append(email)
        
        original_count = len(emails)
        if dedupe:
            emails = list(dict.fromkeys(emails))
        
        print(f"Total emails: {len(emails)}")
        if dedupe:
            print(f"Duplicates removed: {original_count - len(emails)}")
        print(f"Using {MAX_WORKERS} parallel workers")
        
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_email = {executor.submit(verify_single_email, email): email for email in emails}
            completed = 0
            for future in as_completed(future_to_email):
                result = future.result()
                results.append(result)
                completed += 1
                if completed % 25 == 0:
                    print(f"Progress: {completed}/{len(emails)}")
        
        valid_emails = [r for r in results if r['valid']]
        invalid_emails = [r for r in results if not r['valid']]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        client_prefix = f"{client_name}_" if client_name else ""
        valid_file = os.path.join(RESULTS_DIR, f"{client_prefix}valid_{timestamp}.csv")
        invalid_file = os.path.join(RESULTS_DIR, f"{client_prefix}invalid_{timestamp}.csv")
        
        with open(valid_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Email', 'Status', 'Reason'])
            for r in valid_emails:
                writer.writerow([r['email'], 'Valid', r['reason']])
        
        with open(invalid_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Email', 'Status', 'Reason'])
            for r in invalid_emails:
                writer.writerow([r['email'], 'Invalid', r['reason']])
        
        stats = {
            'total': len(results),
            'valid': len(valid_emails),
            'invalid': len(invalid_emails),
            'download_valid': f'/download/{os.path.basename(valid_file)}',
            'download_invalid': f'/download/{os.path.basename(invalid_file)}'
        }
        
        if dedupe and original_count != len(emails):
            stats['duplicates_removed'] = original_count - len(emails)
        
        print(f"\nComplete: {len(valid_emails)} valid, {len(invalid_emails)} invalid")
        return jsonify(stats)
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    filepath = os.path.join(RESULTS_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Wayne\'s Pro Email Verifier',
        'workers': MAX_WORKERS
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)