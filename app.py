from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import csv
import re
import dns.resolver
import smtplib
import socket
from io import StringIO, Bytes5IO
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import threading

app = Flask(__name__)
CORS(app, origins=["*"])

# Global storage for progress tracking
progress_data = {}
progress_lock = threading.Lock()

def extract_contact_info(row):
    """Extract emails and phone numbers from any CSV row."""
    contact = {
        'first_name': '',
        'last_name': '',
        'emails': [],
        'phones': []
    }
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # Phone pattern (various formats)
    phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-.\s]?[(]?[0-9]{1,4}[)]?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}'
    
    for key, value in row.items():
        if value and isinstance(value, str):
            # Look for name fields
            if key and 'first' in key.lower():
                contact['first_name'] = value.strip()
            elif key and 'last' in key.lower():
                contact['last_name'] = value.strip()
            
            # Find all emails in this field
            found_emails = re.findall(email_pattern, value)
            contact['emails'].extend(found_emails)
            
            # Find all phones in this field
            found_phones = re.findall(phone_pattern, value)
            # Clean up phone numbers
            cleaned_phones = []
            for phone in found_phones:
                # Remove non-digit chars and check length
                digits = re.sub(r'\D', '', phone)
                if 7 <= len(digits) <= 15:  # Valid phone length
                    cleaned_phones.append(phone)
            contact['phones'].extend(cleaned_phones)
    
    # Remove duplicates
    contact['emails'] = list(dict.fromkeys(contact['emails']))
    contact['phones'] = list(dict.fromkeys(contact['phones']))
    
    return contact

def check_mx_records(domain):
    """Check if domain has valid MX records."""
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return len(mx_records) > 0
    except:
        return False

def verify_smtp(email, mx_host, timeout=10):
    """Verify email via SMTP conversation."""
    try:
        with smtplib.SMTP(timeout=timeout) as server:
            server.connect(mx_host, 25)
            server.helo('verifier.com')
            code, _ = server.mail('test@verifier.com')
            if code != 250:
                return False
            code, _ = server.rcpt(email)
            server.quit()
            return code == 250
    except:
        return False

def verify_email_advanced(email):
    """Advanced email verification with multiple checks."""
    result = {
        'email': email,
        'valid': False,
        'checks': {
            'format': False,
            'domain': False,
            'mx': False,
            'smtp': False
        }
    }
    
    # Format check
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return result
    result['checks']['format'] = True
    
    # Domain check
    domain = email.split('@')[1]
    try:
        socket.gethostbyname(domain)
        result['checks']['domain'] = True
    except:
        return result
    
    # MX records check
    if check_mx_records(domain):
        result['checks']['mx'] = True
    else:
        return result
    
    # SMTP check (with MX hosts)
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records])
        
        for _, mx_host in mx_hosts[:3]:  # Try first 3 MX hosts
            if verify_smtp(email, mx_host):
                result['checks']['smtp'] = True
                result['valid'] = True
                break
    except:
        pass
    
    # If no SMTP but has MX, consider it valid
    if not result['checks']['smtp'] and result['checks']['mx']:
        result['valid'] = True
    
    return result

def verify_phone_basic(phone):
    """Basic phone validation."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (7-15 digits)
    if 7 <= len(digits) <= 15:
        # Check for obviously invalid patterns
        if digits == '0' * len(digits) or digits == '1' * len(digits):
            return False
        if digits.startswith('555') and len(digits) == 10:  # Fake US numbers
            return False
        return True
    return False

def process_contact(contact, max_emails=2, max_phones=3):
    """Process a single contact with verification."""
    # Verify emails (up to max_emails)
    emails_to_verify = contact['emails'][:max_emails]
    email_results = []
    
    for email in emails_to_verify:
        verification = verify_email_advanced(email)
        email_results.append({
            'email': email,
            'valid': verification['valid']
        })
    
    # Verify phones (up to max_phones)
    phones_to_verify = contact['phones'][:max_phones]
    phone_results = []
    
    for phone in phones_to_verify:
        phone_results.append({
            'phone': phone,
            'valid': verify_phone_basic(phone)
        })
    
    return {
        'first_name': contact['first_name'],
        'last_name': contact['last_name'],
        'email_results': email_results,
        'phone_results': phone_results
    }

@app.route('/verify', methods=['POST', 'OPTIONS'])
def verify_contacts():
    """Main endpoint for verification."""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Get parameters
        max_emails = min(int(request.args.get('max_emails', 2)), 3)
        max_phones = min(int(request.args.get('max_phones', 3)), 5)
        
        # Get CSV file
        file = request.files['file']
        content = file.read().decode('utf-8-sig')  # Handle BOM
        
        # Parse CSV
        csv_reader = csv.DictReader(StringIO(content))
        rows = list(csv_reader)
        
        if not rows:
            return jsonify({'error': 'Empty CSV file'}), 400
        
        # Extract contacts
        contacts = []
        for row in rows:
            contact = extract_contact_info(row)
            if contact['emails'] or contact['phones']:  # Only process if has data
                contacts.append(contact)
        
        # Initialize progress
        task_id = str(time.time())
        with progress_lock:
            progress_data[task_id] = {
                'total': len(contacts),
                'processed': 0,
                'results': []
            }
        
        # Process contacts with workers
        results = []
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = []
            for contact in contacts:
                future = executor.submit(process_contact, contact, max_emails, max_phones)
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                # Update progress
                with progress_lock:
                    if task_id in progress_data:
                        progress_data[task_id]['processed'] += 1
                        progress_data[task_id]['results'] = results
        
        # Generate output CSV
        output = StringIO()
        fieldnames = ['first_name', 'last_name']
        
        # Add email fields
        for i in range(max_emails):
            fieldnames.extend([f'email_{i+1}', f'email_{i+1}_valid'])
        
        # Add phone fields
        for i in range(max_phones):
            fieldnames.extend([f'phone_{i+1}', f'phone_{i+1}_valid'])
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Count statistics
        total_rows = len(results)
        valid_emails = 0
        invalid_emails = 0
        valid_phones = 0
        invalid_phones = 0
        
        for result in results:
            row = {
                'first_name': result['first_name'],
                'last_name': result['last_name']
            }
            
            # Add email results
            for i, email_result in enumerate(result['email_results'][:max_emails]):
                row[f'email_{i+1}'] = email_result['email']
                row[f'email_{i+1}_valid'] = '✓' if email_result['valid'] else '✗'
                if email_result['valid']:
                    valid_emails += 1
                else:
                    invalid_emails += 1
            
            # Add phone results
            for i, phone_result in enumerate(result['phone_results'][:max_phones]):
                row[f'phone_{i+1}'] = phone_result['phone']
                row[f'phone_{i+1}_valid'] = '✓' if phone_result['valid'] else '✗'
                if phone_result['valid']:
                    valid_phones += 1
                else:
                    invalid_phones += 1
            
            writer.writerow(row)
        
        # Save output
        output_content = output.getvalue()
        output_filename = f'verified_contacts_{int(time.time())}.csv'
        
        # Store for download
      with open(f'./{output_filename}', 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        # Clean up progress data
        with progress_lock:
            if task_id in progress_data:
                del progress_data[task_id]
        
        return jsonify({
            'success': True,
            'total_rows': total_rows,
            'valid_emails': valid_emails,
            'invalid_emails': invalid_emails,
            'valid_phones': valid_phones,
            'invalid_phones': invalid_phones,
            'download': f'/download/{output_filename}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download verified results."""
    try:
        return send_file(
            f'/tmp/{filename}',
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
    except:
        return jsonify({'error': 'File not found'}), 404

@app.route('/test')
def test():
    """Test endpoint."""
    return jsonify({'status': 'Email verifier is running!'})

@app.route('/')
def home():
    """Home endpoint."""
    return jsonify({
        'service': 'Advanced Email & Phone Verifier',
        'version': '2.0',
        'endpoints': ['/verify', '/test', '/download/<filename>']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)


