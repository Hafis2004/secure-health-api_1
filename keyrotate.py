#!/usr/bin/env python3
"""
Key Rotation Script for Secure Health API
Re-encrypts all patient records from old key to new key.
"""
import os
import glob
import json
import sys
import shutil
from cryptography.fernet import Fernet

def rotate_keys():
    """Rotate encryption keys and re-encrypt all patient records."""
    print("[*] Starting key rotation...")
    
    # Paths
    key_file = 'keys/data.key'
    key_backup = 'keys/data.key.backup'
    key_new = 'keys/data.key.new'
    data_dir = 'data'
    
    # Step 1: Read old key
    try:
        with open(key_file, 'rb') as f:
            old_key = f.read()
        print(f"[+] Read old key from {key_file}")
    except FileNotFoundError:
        print(f"[-] Key file not found: {key_file}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Error reading key: {e}")
        sys.exit(1)
    
    # Step 2: Generate new key
    try:
        new_key = Fernet.generate_key()
        with open(key_new, 'wb') as f:
            f.write(new_key)
        print(f"[+] Generated new key and saved to {key_new}")
    except Exception as e:
        print(f"[-] Error generating new key: {e}")
        sys.exit(1)
    
    # Step 3: Create cipher instances
    try:
        old_cipher = Fernet(old_key)
        new_cipher = Fernet(new_key)
        print("[+] Cipher instances created")
    except Exception as e:
        print(f"[-] Error creating cipher: {e}")
        os.remove(key_new)
        sys.exit(1)
    
    # Step 4: Re-encrypt all .bin files
    if not os.path.exists(data_dir):
        print(f"[-] Data directory not found: {data_dir}")
        os.remove(key_new)
        sys.exit(1)
    
    bin_files = glob.glob(os.path.join(data_dir, '*.bin'))
    if not bin_files:
        print(f"[!] No .bin files found in {data_dir}")
    else:
        print(f"[*] Found {len(bin_files)} record(s) to re-encrypt")
    
    failed = []
    for bin_file in bin_files:
        try:
            # Read encrypted data
            with open(bin_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt with old key
            decrypted_data = old_cipher.decrypt(encrypted_data)
            
            # Encrypt with new key
            re_encrypted_data = new_cipher.encrypt(decrypted_data)
            
            # Write back
            with open(bin_file, 'wb') as f:
                f.write(re_encrypted_data)
            
            print(f"[+] Re-encrypted: {bin_file}")
        except Exception as e:
            print(f"[-] Error processing {bin_file}: {e}")
            failed.append(bin_file)
    
    if failed:
        print(f"[-] Failed to re-encrypt {len(failed)} file(s). Aborting rotation.")
        os.remove(key_new)
        sys.exit(1)
    
    # Step 5: Backup old key and replace with new key
    try:
        shutil.copy2(key_file, key_backup)
        print(f"[+] Backed up old key to {key_backup}")
        
        os.replace(key_new, key_file)
        print(f"[+] Replaced old key with new key at {key_file}")
    except Exception as e:
        print(f"[-] Error finalizing key rotation: {e}")
        sys.exit(1)
    
    print("[+] Key rotation completed successfully!")
    print(f"[*] Backup of old key saved to: {key_backup}")

if __name__ == '__main__':
    rotate_keys()