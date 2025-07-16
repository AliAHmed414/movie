import subprocess
import json

def get_video_formats(url):
    # Run yt-dlp with -j to get JSON output
    result = subprocess.run(
        ['yt-dlp', '-j', url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"yt-dlp error: {result.stderr.strip()}")

    data = json.loads(result.stdout)

    hls_url = None
    dash_url = None
    mp4_formats = []

    formats = data.get('formats', [])
    
    # Sort formats by resolution (height)
    sorted_formats = sorted(formats, key=lambda f: f.get('height') or 0)

    for fmt in sorted_formats:
        url = fmt.get('url')
        ext = fmt.get('video_ext')
        protocol = fmt.get('protocol')
        width = fmt.get('width') 

        if not url or not ext:
            continue

        # Get first matching HLS
        if not hls_url and protocol == 'm3u8_native':
            hls_url = fmt.get('manifest_url') 

        # Get first matching DASH
        elif not dash_url and protocol == 'http_dash_segments' or protocol =="https" and not  fmt.get('manifest_url'):
            dash_url = fmt.get('manifest_url')

        # Collect mp4 formats
        elif ext == 'mp4' and width and protocol =="https" or protocol == 'http_dash_segments' :
            mp4_formats.append({'resolution': f'{width}p', 'url': url})

    return {
        'hls': hls_url,
        'dash': dash_url,
        'mp4': mp4_formats
    }

# Example
if __name__ == "__main__":
    test_url = "https://ok.ru/video/10445147409137"
    result = get_video_formats(test_url)
    print(json.dumps(result, indent=1))