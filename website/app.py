from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from dotenv import load_dotenv
import requests
import json
from requests.exceptions import RequestException, Timeout
import urllib3
import sys
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import sqlite3
from pathlib import Path

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Configure Heygen API
HEYGEN_API_KEY = os.getenv('HEYGEN_API_KEY')

# Configure requests session with retry logic
session = requests.Session()
retry_strategy = Retry(
    total=3,  # number of retries
    backoff_factor=1,  # wait 1, 2, 4 seconds between retries
    status_forcelist=[500, 502, 503, 504]  # HTTP status codes to retry on
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Database setup
DB_PATH = Path(__file__).parent / 'videos.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            thumbnail_url TEXT,
            video_url TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            duration TEXT,
            error TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database
init_db()

def test_api_connection():
    """Test the connection to Heygen API"""
    print("\nTesting Heygen API connection...")
    print(f"API Key being used: {HEYGEN_API_KEY}")
    
    headers = {
        'x-api-key': HEYGEN_API_KEY,
        'accept': 'application/json'
    }
    
    try:
        print("Making test request to Heygen API...")
        response = session.get(
            'https://api.heygen.com/v2/avatars',
            headers=headers,
            timeout=30,  # increased timeout
            verify=False
        )
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text[:500]}...")
        
        if response.status_code == 200:
            print("Successfully connected to Heygen API!")
            return True
        else:
            print(f"Failed to connect to Heygen API. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error testing API connection: {str(e)}")
        return False

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/avatars')
def avatars():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            headers = {
                'x-api-key': HEYGEN_API_KEY,
                'accept': 'application/json'
            }
            
            print(f"\nFetching avatars from Heygen API (attempt {attempt + 1}/{max_retries})...")
            response = session.get(
                'https://api.heygen.com/v2/avatars',
                headers=headers,
                timeout=30,
                verify=False
            )
            
            print(f"Response Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Get all avatars and talking photos
                all_avatars = data.get('data', {}).get('avatars', [])
                all_talking_photos = data.get('data', {}).get('talking_photos', [])
                
                # Calculate total counts
                total_avatars = len(all_avatars)
                total_talking_photos = len(all_talking_photos)
                
                # Calculate pagination
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                
                # Get paginated avatars
                paginated_avatars = all_avatars[start_idx:end_idx]
                
                # Calculate total pages
                total_pages = (total_avatars + per_page - 1) // per_page
                
                print(f"\nFound {total_avatars} avatars and {total_talking_photos} talking photos")
                print(f"Showing page {page} of {total_pages}")
                
                return render_template('avatars.html', 
                                    avatars=paginated_avatars,
                                    talking_photos=all_talking_photos,
                                    current_page=page,
                                    total_pages=total_pages,
                                    total_avatars=total_avatars,
                                    total_talking_photos=total_talking_photos,
                                    error=None)
            else:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                print(f"\nError: {error_msg}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # exponential backoff
                    continue
                return render_template('avatars.html', 
                                    avatars=[], 
                                    talking_photos=[],
                                    error=error_msg)
                
        except Exception as e:
            error_msg = f"Error fetching avatars (attempt {attempt + 1}/{max_retries}): {str(e)}"
            print(f"\nException: {error_msg}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # exponential backoff
                continue
            return render_template('avatars.html', 
                                avatars=[], 
                                talking_photos=[],
                                error=error_msg)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    try:
        headers = {
            'x-api-key': HEYGEN_API_KEY,
            'accept': 'application/json'
        }
        
        response = session.get(
            'https://api.heygen.com/v2/avatars',
            headers=headers,
            timeout=30,
            verify=False
        )
        
        if response.status_code != 200:
            return render_template('submit.html', 
                                error="Failed to fetch avatars",
                                avatars=[])
        
        avatars_data = response.json()
        avatars_list = avatars_data.get('data', {}).get('avatars', [])
        
        if request.method == 'POST':
            avatar_id = request.form.get('avatar_id')
            input_text = request.form.get('input_text')
            voice_id = request.form.get('voice_id')
            dimension = request.form.get('dimension')
            caption = request.form.get('caption') == 'on'
            
            width, height = map(int, dimension.split('x'))
            
            payload = {
                "video_inputs": [
                    {
                        "character": {
                            "type": "avatar",
                            "avatar_id": avatar_id,
                            "avatar_style": "normal"
                        },
                        "voice": {
                            "type": "text",
                            "input_text": input_text,
                            "voice_id": voice_id
                        }
                    }
                ],
                "caption": caption,
                "dimension": {
                    "width": width,
                    "height": height
                }
            }
            
            print(f"\nSending video generation request with payload: {json.dumps(payload, indent=2)}")
            
            response = session.post(
                'https://api.heygen.com/v2/video/generate',
                headers={
                    'x-api-key': HEYGEN_API_KEY,
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                video_data = response.json()
                print(f"\nVideo creation response: {json.dumps(video_data, indent=2)}")
                
                # Get video ID from response
                video_id = video_data.get('data', {}).get('video_id')
                if not video_id:
                    return render_template('submit.html',
                                        error="Failed to get video ID from response",
                                        avatars=avatars_list,
                                        selected_avatar_id=avatar_id)
                
                # Store video information in database
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                now = datetime.now().isoformat()
                
                c.execute('''
                    INSERT INTO videos (id, name, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (video_id, f"Video {now}", 'PROCESSING', now, now))
                
                conn.commit()
                conn.close()
                
                return redirect(url_for('videos'))
            else:
                error_msg = f"Failed to create video: {response.status_code} - {response.text}"
                print(f"\nError: {error_msg}")
                return render_template('submit.html',
                                    error=error_msg,
                                    avatars=avatars_list,
                                    selected_avatar_id=avatar_id)
        
        selected_avatar_id = request.args.get('avatar')
        return render_template('submit.html',
                            avatars=avatars_list,
                            selected_avatar_id=selected_avatar_id)
                            
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        return render_template('submit.html',
                            error=error_msg,
                            avatars=[])

@app.route('/videos')
def videos():
    try:
        # Get videos from Heygen API
        headers = {
            'x-api-key': HEYGEN_API_KEY,
            'accept': 'application/json'
        }
        
        print("Fetching video list from Heygen...")
        # Get video list from Heygen
        response = session.get(
            'https://api.heygen.com/v1/video.list?limit=10',
            headers=headers,
            timeout=30,
            verify=False
        )
        
        print(f"Video list response: {response.text}")
        
        if response.status_code != 200:
            return render_template('videos.html', error=f"Failed to fetch videos from Heygen: {response.text}", videos=[])
            
        videos_data = response.json()
        videos = []
        
        # Process each video
        for video in videos_data.get('data', {}).get('videos', []):
            try:
                video_id = video.get('video_id')
                if not video_id:
                    print(f"Skipping video with no ID: {video}")
                    continue
                    
                print(f"\nProcessing video: {video_id}")
                
                # Format created_at properly
                try:
                    created_timestamp = video.get('created_at', '')
                    if isinstance(created_timestamp, (int, float)):
                        created_at = datetime.fromtimestamp(created_timestamp).isoformat()
                    else:
                        created_at = datetime.now().isoformat()
                except Exception as e:
                    print(f"Error formatting date: {e}")
                    created_at = datetime.now().isoformat()
                
                status = video.get('status', 'PROCESSING').upper()
                video_url = video.get('video_url', '')
                thumbnail_url = video.get('thumbnail_url', '')
                
                print(f"Video details: status={status}, url={video_url}, created_at={created_at}")
                
                # Update database with latest info
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                
                # Check if video exists in database
                c.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
                existing_video = c.fetchone()
                
                if existing_video:
                    # Update existing video
                    c.execute('''
                        UPDATE videos 
                        SET status = ?, video_url = ?, thumbnail_url = ?, 
                            updated_at = ?
                        WHERE id = ?
                    ''', (status, video_url, thumbnail_url, 
                          datetime.now().isoformat(), video_id))
                else:
                    # Insert new video
                    c.execute('''
                        INSERT INTO videos (id, name, status, thumbnail_url, video_url, 
                                         created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (video_id, f"Video {video_id}", status, thumbnail_url, 
                          video_url, created_at, datetime.now().isoformat()))
                
                conn.commit()
                
                videos.append({
                    'id': video_id,
                    'name': f"Video {video_id}",
                    'status': status,
                    'thumbnail_url': thumbnail_url,
                    'video_url': video_url,
                    'created_at': datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': video.get('duration', ''),
                    'error': video.get('error', '')
                })
                
                conn.close()
                
            except Exception as e:
                print(f"Error processing video {video.get('video_id', 'unknown')}: {str(e)}")
                continue
        
        if not videos:
            print("No videos found in the response")
            
        return render_template('videos.html', videos=videos)
        
    except Exception as e:
        print(f"Error in videos route: {str(e)}")
        return render_template('videos.html', error=str(e), videos=[])

@app.route('/play_video/<video_id>')
def play_video(video_id):
    try:
        headers = {
            'x-api-key': HEYGEN_API_KEY,
            'accept': 'application/json'
        }
        
        print(f"\nFetching status for video: {video_id}")
        # Get video status with video_id
        response = session.get(
            f'https://api.heygen.com/v1/video_status.get?video_id={video_id}',
            headers=headers,
            timeout=30,
            verify=False
        )
        
        print(f"Status response: {response.text}")
        
        if response.status_code == 200:
            status_data = response.json()
            video_data = status_data.get('data', {})
            video_url = video_data.get('video_url', '')
            status = video_data.get('status', '').upper()
            
            print(f"Video URL: {video_url}")
            print(f"Status: {status}")
            
            if video_url:
                # Update the video URL and status in the database
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute('''
                    UPDATE videos 
                    SET video_url = ?, status = ?, updated_at = ?
                    WHERE id = ?
                ''', (video_url, status, datetime.now().isoformat(), video_id))
                conn.commit()
                conn.close()
                
                return redirect(video_url)
            else:
                # If video is not ready, try getting it from the video list
                list_response = session.get(
                    'https://api.heygen.com/v1/video.list?limit=10',
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                
                if list_response.status_code == 200:
                    videos = list_response.json().get('data', {}).get('videos', [])
                    for video in videos:
                        if video.get('video_id') == video_id:
                            video_url = video.get('video_url', '')
                            if video_url:
                                return redirect(video_url)
                
                return jsonify({'error': 'Video not ready yet'}), 404
        else:
            print(f"Error response from API: {response.text}")
            return jsonify({'error': f'Failed to fetch video status: {response.text}'}), response.status_code
            
    except Exception as e:
        print(f"Error playing video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check_video_status/<video_id>')
def check_video_status(video_id):
    try:
        headers = {
            'x-api-key': HEYGEN_API_KEY,
            'accept': 'application/json'
        }
        
        # Get video status with video_id
        response = session.get(
            f'https://api.heygen.com/v1/video_status.get?video_id={video_id}',
            headers=headers,
            timeout=30,
            verify=False
        )
        
        if response.status_code == 200:
            status_data = response.json()
            video_data = status_data.get('data', {})
            video_url = video_data.get('video_url', '')
            status = video_data.get('status', '').upper()
            
            # Update database if status changed
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                UPDATE videos 
                SET video_url = ?, status = ?, updated_at = ?
                WHERE id = ?
            ''', (video_url, status, datetime.now().isoformat(), video_id))
            conn.commit()
            conn.close()
            
            return jsonify({
                'status': status,
                'video_url': video_url
            })
        else:
            return jsonify({'error': 'Failed to fetch video status'}), response.status_code
            
    except Exception as e:
        print(f"Error checking video status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/update_video_details/<video_id>', methods=['POST'])
def update_video_details(video_id):
    try:
        title = request.form.get('title', '').strip()
        if not title:
            return jsonify({'error': 'Title cannot be empty'}), 400
            
        # Update video title in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE videos 
            SET name = ?, updated_at = ?
            WHERE id = ?
        ''', (title, datetime.now().isoformat(), video_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'title': title})
        
    except Exception as e:
        print(f"Error updating video details: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Test API connection before starting the server
    if not HEYGEN_API_KEY:
        print("Error: HEYGEN_API_KEY not set in .env file")
        sys.exit(1)
        
    print("\nTesting API connection before starting server...")
    if not test_api_connection():
        print("\nFailed to connect to Heygen API. Please check your API key and internet connection.")
        sys.exit(1)
        
    print("\nStarting Flask application...")
    # Allow connections from any IP address
    app.run(debug=True, host='0.0.0.0', port=5004)
