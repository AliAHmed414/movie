import os
import csv
import json
import subprocess

VIDEO_PATH = "/workspaces/tools/downloads/tt31691389/1080p/tt31691389/1080p_tt31691389.mp4"
CSV_PATH = "/workspaces/tools/bot/uploader/pixel_auth.csv"

def upload_with_curl(file_path, api_key, username):
    try:
        result = subprocess.run(
            [
                "curl", "-s",
                "--connect-timeout", "10",
                "--max-time", "300",
                "--retry", "3",
                "--retry-delay", "1",
                "--compressed",
                "--http2",
                "-T", file_path,
                "-u", f":{api_key}",
                "https://pixeldrain.com/api/file/"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        response_json = json.loads(result.stdout)
        file_id = response_json.get("id")
        if file_id:
            print(f"✅ {username}: https://pixeldrain.com/api/file/{file_id}")
        else:
            print(f"❌ {username}: Upload failed, no file ID returned.")
    except Exception as e:
        print(f"❌ {username}: Error uploading file: {e}")

def read_instances_from_csv(csv_file_path):
    instances = []
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            instances.append((row["username"], row["auth_key"]))
    return instances

if __name__ == "__main__":
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ File not found: {VIDEO_PATH}")
    elif not os.path.exists(CSV_PATH):
        print(f"❌ CSV file not found: {CSV_PATH}")
    else:
        instances = read_instances_from_csv(CSV_PATH)
        for username, api_key in instances:
            upload_with_curl(VIDEO_PATH, api_key, username)