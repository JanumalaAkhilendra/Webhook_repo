from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client.github_webhooks
events_collection = db.events

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-GitHub-Event') == 'ping':
        return jsonify({'message': 'pong'}), 200

    data = request.json
    event_type = request.headers.get('X-GitHub-Event')
    
    # Process different event types
    if event_type == 'push':
        process_push_event(data)
    elif event_type == 'pull_request':
        process_pull_request_event(data)
    elif event_type == 'merge':
        process_merge_event(data)
    
    return jsonify({'message': 'Event received'}), 200

def process_push_event(data):
    author = data['pusher']['name']
    to_branch = data['ref'].split('/')[-1]
    timestamp = datetime.utcnow().isoformat()
    
    event = {
        'request_id': data['head_commit']['id'],
        'author': author,
        'action': 'PUSH',
        'from_branch': None,
        'to_branch': to_branch,
        'timestamp': timestamp
    }
    
    events_collection.insert_one(event)

def process_pull_request_event(data):
    pr_data = data['pull_request']
    author = pr_data['user']['login']
    from_branch = pr_data['head']['ref']
    to_branch = pr_data['base']['ref']
    timestamp = datetime.utcnow().isoformat()
    
    event = {
        'request_id': str(pr_data['id']),
        'author': author,
        'action': 'PULL_REQUEST',
        'from_branch': from_branch,
        'to_branch': to_branch,
        'timestamp': timestamp
    }
    
    events_collection.insert_one(event)

def process_merge_event(data):
    # Note: GitHub doesn't have a specific 'merge' event type
    # This would typically be detected from a pull_request event with merged=true
    pr_data = data['pull_request']
    if pr_data.get('merged', False):
        author = pr_data['merged_by']['login']
        from_branch = pr_data['head']['ref']
        to_branch = pr_data['base']['ref']
        timestamp = datetime.utcnow().isoformat()
        
        event = {
            'request_id': str(pr_data['id']),
            'author': author,
            'action': 'MERGE',
            'from_branch': from_branch,
            'to_branch': to_branch,
            'timestamp': timestamp
        }
        
        events_collection.insert_one(event)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/events')
def get_events():
    events = list(events_collection.find().sort('timestamp', -1).limit(50))
    
    # Convert ObjectId to string for JSON serialization
    for event in events:
        event['_id'] = str(event['_id'])
    
    return jsonify(events)

if __name__ == '__main__':
    app.run(debug=True)