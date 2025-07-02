#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pycryptodome",
# ]
# ///
"""
Extract Chrome cookies for a domain and save to storage.json for Playwright.

Usage:
    ./getcookie.py <domain>
    
Examples:
    ./getcookie.py github.com
    ./getcookie.py console.anthropic.com
"""

import os
import sys
import sqlite3
import subprocess
import hashlib
import json
import tempfile
import shutil
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

# Chrome encryption parameters
SALT = b"saltysalt"
IV = b" " * 16  # 16 spaces
LENGTH = 16
ITERATIONS = 1003


class Cookie:
    def __init__(self, name, value, domain, path, encrypted_value, expires_utc, 
                 is_secure, is_httponly, same_site, host_key):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.encrypted = encrypted_value
        self.expires = expires_utc
        self.is_secure = is_secure
        self.is_httponly = is_httponly
        self.same_site = same_site
        self.host_key = host_key
    
    def decrypted(self, password):
        if self.value:
            return self.value
        
        if self.encrypted and len(self.encrypted) > 0:
            # Chrome prefixes encrypted values with 'v10' or 'v11'
            if self.encrypted[:3] in [b'v10', b'v11']:
                encrypted_value = self.encrypted[3:]
                
                # Decrypt using AES-CBC
                key = PBKDF2(password.encode(), SALT, dkLen=LENGTH, count=ITERATIONS)
                cipher = AES.new(key, AES.MODE_CBC, IV)
                decrypted = cipher.decrypt(encrypted_value)
                
                # Remove PKCS7 padding
                try:
                    plaintext = self._unpad(decrypted)
                except:
                    plaintext = decrypted
                
                # There's a SHA-256 hash of the domain value prepended to the encrypted value
                # after https://crrev.com/c/5792044.
                if len(plaintext) >= 32:
                    hash_value = plaintext[:32]
                    computed = hashlib.sha256(self.host_key.encode()).digest()
                    
                    if hash_value == computed:
                        return plaintext[32:].decode('utf-8', errors='ignore')
                    else:
                        # Try without domain hash (older format)
                        return plaintext.decode('utf-8', errors='ignore')
                else:
                    return plaintext.decode('utf-8', errors='ignore')
            else:
                # Not v10/v11 encrypted, return as is
                return self.encrypted.decode('utf-8', errors='ignore')
        
        return ""
    
    def _unpad(self, data):
        """Remove PKCS7 padding"""
        padding = data[-1]
        if padding > 16:
            raise ValueError('Invalid padding')
        # Validate padding
        for i in range(1, padding + 1):
            if data[-i] != padding:
                raise ValueError('Invalid padding')
        return data[:-padding]


def get_password():
    """Get Chrome Safe Storage password from macOS Keychain."""
    import platform
    if platform.system() != "Darwin":
        raise NotImplementedError("This script currently only supports macOS")
    
    try:
        cmd = ["/usr/bin/security", "find-generic-password", "-wga", "Chrome"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to get password from keychain: {e.stderr}")


def get_cookies(domain, profile_name="Default"):
    """Retrieve cookies from Chrome SQLite database."""
    home = os.path.expanduser("~")
    cookies_file = os.path.join(home, "Library", "Application Support", "Google", "Chrome", profile_name, "Cookies")
    
    if not os.path.exists(cookies_file):
        raise FileNotFoundError(f"Cookie file not found: {cookies_file}")
    
    # Create a copy of the cookies file to avoid database lock issues
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        shutil.copy2(cookies_file, tmp_path)
        
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        
        # Build list of domains to query
        domains_to_query = []
        
        # Always include the exact domain
        domains_to_query.append(domain)
        
        # Also include with leading dot
        if not domain.startswith('.'):
            domains_to_query.append('.' + domain)
        
        # If it's a subdomain, also include parent domains
        if '.' in domain and not domain.startswith('.'):
            parts = domain.split('.')
            # For example: console.anthropic.com -> also check .anthropic.com
            for i in range(1, len(parts)):
                parent = '.' + '.'.join(parts[i:])
                domains_to_query.append(parent)
        
        # Build WHERE clause for all domains
        where_conditions = ' OR '.join(['host_key = ?' for _ in domains_to_query])
        
        # Set text factory to bytes to handle binary data
        conn.text_factory = bytes
        
        # Query for cookies
        query = f"""
            SELECT name, value, host_key, path, encrypted_value, 
                   expires_utc, is_secure, is_httponly, samesite
            FROM cookies 
            WHERE {where_conditions}
        """
        cursor.execute(query, domains_to_query)
        
        cookies = []
        for row in cursor.fetchall():
            name, value, host_key, path, encrypted_value, expires_utc, is_secure, is_httponly, same_site = row
            # Decode text fields that are bytes
            if isinstance(name, bytes):
                name = name.decode('utf-8', errors='ignore')
            if isinstance(value, bytes):
                value = value.decode('utf-8', errors='ignore')
            if isinstance(host_key, bytes):
                host_key = host_key.decode('utf-8', errors='ignore')
            if isinstance(path, bytes):
                path = path.decode('utf-8', errors='ignore')
            cookies.append(Cookie(name, value, domain, path, encrypted_value, 
                                expires_utc, is_secure, is_httponly, same_site, host_key))
        
        conn.close()
        return cookies, domains_to_query
    
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    domain = sys.argv[1]
    profile = sys.argv[2] if len(sys.argv) > 2 else "Default"
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_dir = os.path.join(script_dir, 'cookies')
    storage_file = os.path.join(cookies_dir, 'storage.json')
    
    # Ensure cookies directory exists
    os.makedirs(cookies_dir, exist_ok=True)
    
    try:
        # Get Chrome Safe Storage password
        password = get_password()
        
        # Get cookies
        cookies, domains_queried = get_cookies(domain, profile)
        
        if not cookies:
            print(f"Error: No cookies found for domain: {domain}", file=sys.stderr)
            print(f"Make sure you are logged into https://{domain} in Chrome", file=sys.stderr)
            sys.exit(1)
        
        # Read existing storage file
        try:
            with open(storage_file, 'r') as f:
                storage_state = json.load(f)
        except:
            storage_state = {"cookies": [], "origins": []}
        
        # Convert cookies to Playwright format
        new_cookies = []
        for cookie in cookies:
            decrypted_value = cookie.decrypted(password)
            if decrypted_value:
                # __Host- prefixed cookies require specific domain (no leading dot)
                if cookie.name.startswith("__Host-"):
                    domain = cookie.host_key.lstrip('.')
                else:
                    domain = cookie.host_key if cookie.host_key.startswith('.') else '.' + cookie.host_key
                
                cookie_dict = {
                    "name": cookie.name,
                    "value": decrypted_value,
                    "domain": domain,
                    "path": cookie.path,
                    "httpOnly": bool(cookie.is_httponly),
                    "secure": bool(cookie.is_secure),
                    "sameSite": ["None", "Lax", "Strict"][cookie.same_site] if cookie.same_site < 3 else "None"
                }
                
                # Only add expires if it's a persistent cookie (not a session cookie)
                if cookie.expires > 0:
                    cookie_dict["expires"] = int(cookie.expires / 1e6 - 11644473600)
                new_cookies.append(cookie_dict)
        
        # Update storage state with new cookies (replacing existing ones for this domain)
        # Remove old cookies for these domains
        storage_state["cookies"] = [
            c for c in storage_state["cookies"] 
            if not any(c["domain"].endswith(d.lstrip('.')) for d in domains_queried)
        ]
        # Add new cookies
        storage_state["cookies"].extend(new_cookies)
        
        # Save updated storage state
        with open(storage_file, 'w') as f:
            json.dump(storage_state, f, indent=2)
        
        print(f"✓ Extracted {len(new_cookies)} cookies for {domain}")
        print(f"✓ Updated storage.json")
        print(f"\nYou can now restart Claude Code and use Playwright to navigate to https://{domain}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()