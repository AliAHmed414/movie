#!/usr/bin/env python3
import requests
import os
import sys
import time
import datetime
import subprocess
import json

def parse_cookie_string(cookie_str):
    return {pair.split('=')[0]: '='.join(pair.split('=')[1:]) for pair in cookie_str.split('; ')}

def get_session_token(cookie_string):
    cookie = parse_cookie_string(cookie_string)
    headers = {
        'accept': '*/*',
        'origin': 'https://app.mediafire.com',
        'referer': 'https://app.mediafire.com/',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    }

    response = requests.post(
        'https://www.mediafire.com/application/get_session_token.php',
        headers=headers,
        cookies=cookie
    )

    if response.status_code != 200:
        raise Exception("❌ Failed to get session token")

    try:
        token = response.json()['response']['session_token']
        return token
    except Exception:
        print("⚠️ Full response:", response.text)
        raise Exception("❌ Failed to parse session token")

def get_action_token(session_token):
    r = requests.post('https://www.mediafire.com/api/1.5/user/get_action_token.php',
                      data={'type': 'upload', 'response_format': 'json', 'session_token': session_token})
    return r.json()['response']['action_token']

def upload_file(file_path, session_token):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    token = get_action_token(session_token)
    print(token)
    
    import subprocess
    import json
    
    curl_command = [
        'curl',
        '-X', 'POST',
        f'https://www.mediafire.com/api/1.5/upload/simple.php?session_token={session_token}&action_token={token}&response_format=json',
        '-F', f'file=@{file_path}'
    ]
    
    result = subprocess.run(curl_command, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Curl command failed: {result.stderr}")
    
    response = json.loads(result.stdout)['response']
    if response['result'] == 'Success':
        return response['doupload']['key']
    else:
        raise Exception(f"Upload failed: {response.get('message', 'Unknown error')}")


def get_free_space(session_token):
    """Get available free space from MediaFire account"""
    r = requests.post('https://www.mediafire.com/api/1.5/user/get_info.php',
                      data={'response_format': 'json', 'session_token': session_token})
    
    if r.status_code != 200:
        raise Exception("❌ Failed to get user info")
    
    response = r.json()['response']
    if response['result'] != 'Success':
        raise Exception(f"❌ API error: {response.get('message', 'Unknown error')}")
    
    user_info = response['user_info']
    used_space = int(user_info['used_storage_size'])
    total_space = int(user_info['storage_limit'])
    free_space = total_space - used_space
    
    # Convert bytes to human readable format
    def format_bytes(bytes_val):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    print(f"💾 Storage Info:")
    print(f"   Used: {format_bytes(used_space)}")
    print(f"   Total: {format_bytes(total_space)}")
    print(f"   Free: {format_bytes(free_space)}")
    
    return free_space
def get_quickkey_from_upload(filename, session_token, upload_time_threshold=30):
    time.sleep(3)

    r = requests.post('https://www.mediafire.com/api/1.5/folder/get_content.php',
                      data={'response_format': 'json', 'session_token': session_token,
                            'folder_key': 'myfiles', 'content_type': 'files'})

    files = r.json()['response']['folder_content']['files']
    now = datetime.datetime.utcnow()
    base_filename = os.path.splitext(filename)[0]

    candidates = []
    for f in files:
        file_time = datetime.datetime.strptime(f['created_utc'], '%Y-%m-%dT%H:%M:%SZ')
        time_diff = (now - file_time).total_seconds()
        file_base = os.path.splitext(f['filename'])[0]

        if time_diff <= upload_time_threshold and (f['filename'] == filename or file_base == base_filename):
            candidates.append((f, time_diff))

    if candidates:
        best_match = min(candidates, key=lambda x: x[1])[0]
        return best_match['quickkey'], best_match['links']['normal_download']

    if files:
        latest = max(files, key=lambda x: x['created_utc'])
        return latest['quickkey'], latest['links']['normal_download']

    raise Exception("No files found")

def upload_to_mediafire(file_path, cookie_string):
    filename = os.path.basename(file_path)
    print(f"📤 Uploading: {filename}")

    session_token = get_session_token(cookie_string)
    upload_key = upload_file(file_path, session_token)
    print("✅ Upload complete, fetching link...")

    quickkey, url = get_quickkey_from_upload(filename, session_token)
    free_space = get_free_space(session_token)
    print(f"\n✅ Upload successful!")
    print(f"📁 File: {filename}")
    print(f"🔑 QuickKey: {quickkey}")
    print(f"🔗 Download URL: {url}")
    return quickkey, free_space

# CLI entry
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python upload.py <file_path> <cookie_string>")
        sys.exit(1)

    try:
        upload_to_mediafire(sys.argv[1], sys.argv[2])
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
