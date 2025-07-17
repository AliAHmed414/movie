import requests, os, time, json

# --- Configuration ---
VK_API = 'https://api.vk.com/method/'
VERSION = '5.199'
TOKENS_FILE = os.path.join(os.path.dirname(__file__), 'doc.json')


def upload_doc(file_path: str, title: str = None):
    if not os.path.exists(file_path):
        print("❌ File not found.")
        return None

    name = title or os.path.basename(file_path)

    # Load tokens list from JSON
    with open(TOKENS_FILE, 'r') as f:
        tokens = json.load(f)

    for entry in tokens:
        if not entry.get("working", True):
            continue

        token = entry["token"]
        group_id = entry["id"]

        try:
            def vk_call(method, params, delay=0):
                if delay:
                    time.sleep(delay)
                params.update({'access_token': token, 'v': VERSION})
                r = requests.get(VK_API + method, params=params)
                r.raise_for_status()
                data = r.json()
                if 'error' in data:
                    raise Exception(f"VK Error {data['error']['error_code']}: {data['error']['error_msg']}")
                return data.get('response')

            # Get upload server for this group
            upload_info = vk_call('docs.getWallUploadServer', {'group_id': group_id})

            # Upload file to the server
            with open(file_path, 'rb') as f:
                res = requests.post(upload_info['upload_url'], files={'file': (name, f)})
                res.raise_for_status()
                file_data = res.json().get('file')
                if not file_data:
                    raise Exception("❌ Upload failed.")

            # Save the document to VK
            saved = vk_call('docs.save', {'file': file_data, 'title': name, 'group_id': group_id}, delay=1)
            doc = saved.get('doc') if isinstance(saved, dict) else saved[0]

            # Mark this token as working and save status
            entry["working"] = True
            entry["message"] = ""
            with open(TOKENS_FILE, "w") as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)

            return f"doc{doc['owner_id']}_{doc['id']}"

        except Exception as e:
            print(f"⚠️  Token failed ({entry.get('id')}): {e}")
            entry["working"] = False
            entry["message"] = str(e)
            with open(TOKENS_FILE, "w") as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)

    print("❌ All tokens failed.")
    return None

if __name__ == "__main__":
    doc_id = upload_doc("/home/kda/Pictures/bot/steup.sh")
    print(doc_id)