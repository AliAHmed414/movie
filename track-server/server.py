from flask import Flask, jsonify, request
import pandas as pd
import threading
import os
from datetime import datetime, timedelta

app = Flask(__name__)
LOCK = threading.Lock()

def get_csv_path(category):
    return os.path.join(os.path.dirname(__file__), f"{category}.csv")

def process_get(category):
    csv_path = get_csv_path(category)
    with LOCK:
        df = pd.read_csv(csv_path, dtype=str)  # ✅ Read all as string to avoid dtype issues

        # Ensure required columns
        df['status'] = df.get('status', '').fillna('').astype(str)
        if 'last_updated' not in df.columns:
            df['last_updated'] = ''
        else:
            df['last_updated'] = df['last_updated'].astype(str)  # ✅ Ensure this is a string column

        # Convert 'last_updated' to datetime
        def parse_date(x):
            try:
                return datetime.strptime(x.strip(), '%Y-%m-%d %H:%M:%S UTC')
            except:
                return None
        df['last_updated_dt'] = df['last_updated'].apply(parse_date)

        # Mark "working" items older than 4 hours as "failed"
        four_hours_ago = datetime.utcnow() - timedelta(hours=4)
        stale_mask = (df['status'] == 'working') & (df['last_updated_dt'].notnull()) & (df['last_updated_dt'] < four_hours_ago)
        df.loc[stale_mask, 'status'] = 'failed'

        df.drop(columns=['last_updated_dt'], inplace=True)
        df.to_csv(csv_path, index=False)

        # Select a pending item
        pending = df[df['status'].str.strip() == '']
        if pending.empty:
            return jsonify({'message': f'No pending {category} found.'}), 404

        item = pending.iloc[0]
        idx = item.name

        # Mark as working
        df.at[idx, 'status'] = 'working'
        df.at[idx, 'last_updated'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        df.to_csv(csv_path, index=False)

        return jsonify({'title': item['title']})

def process_post(category, title):
    csv_path = get_csv_path(category)
    with LOCK:
        df = pd.read_csv(csv_path, dtype=str)
        df['status'] = df.get('status', '').fillna('').astype(str)
        if 'last_updated' not in df.columns:
            df['last_updated'] = ''
        else:
            df['last_updated'] = df['last_updated'].astype(str)

        matched = df['title'].str.strip().str.lower() == title.strip().lower()

        if not matched.any():
            return jsonify({'message': f'{category.capitalize()} not found.'}), 404

        df.loc[matched, 'status'] = 'done'
        df.to_csv(csv_path, index=False)

        return jsonify({'message': f'"{title}" marked as done in {category}.'})

def process_long_status(category, title):
    """Mark item as taking long time to download"""
    csv_path = get_csv_path(category)
    with LOCK:
        df = pd.read_csv(csv_path, dtype=str)
        df['status'] = df.get('status', '').fillna('').astype(str)
        if 'last_updated' not in df.columns:
            df['last_updated'] = ''
        else:
            df['last_updated'] = df['last_updated'].astype(str)

        matched = df['title'].str.strip().str.lower() == title.strip().lower()

        if not matched.any():
            return jsonify({'message': f'{category.capitalize()} not found.'}), 404

        df.loc[matched, 'status'] = 'long_download'
        df.loc[matched, 'last_updated'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        df.to_csv(csv_path, index=False)

        return jsonify({'message': f'"{title}" marked as long download in {category}.'})

# Routes for movies
@app.route('/movie', methods=['GET'])
def get_movie():
    return process_get('movies')

@app.route('/movie/<title>', methods=['POST'])
def post_movie(title):
    return process_post('movies', title)

@app.route('/movie/<title>/long', methods=['POST'])
def post_movie_long(title):
    return process_long_status('movies', title)

# Routes for tvshows
@app.route('/tvshow', methods=['GET'])
def get_tvshow():
    return process_get('tvshows')

@app.route('/tvshow/<title>', methods=['POST'])
def post_tvshow(title):
    return process_post('tvshows', title)

@app.route('/tvshow/<title>/long', methods=['POST'])
def post_tvshow_long(title):
    return process_long_status('tvshows', title)

# Routes for series
@app.route('/series', methods=['GET'])
def get_series():
    return process_get('series')

@app.route('/series/<title>', methods=['POST'])
def post_series(title):
    return process_post('series', title)

@app.route('/series/<title>/long', methods=['POST'])
def post_series_long(title):
    return process_long_status('series', title)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=8080)