from flask import Flask, render_template, request, jsonify
import asyncio
import os
import sys
import json
import threading
import queue
import logging
import re
from logging.config import dictConfig

# Configure logging
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# Import our client - adjust path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import SolarWindsClient

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Initialize Queue for async communication
message_queue = queue.Queue()
response_queue = queue.Queue()

# Global client object
client = None
server_path = None

@app.route('/')
def index():
    """Render the main chat interface"""
    return render_template('index.html', 
                          bot_name="SolarWinds Assistant", 
                          company_name="Your Company")

@app.route('/api/chat', methods=['POST'])
def handle_chat():  # Changed function name to avoid conflict
    """API endpoint to handle chat messages"""
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Put the message in the queue for the background worker
    message_queue.put(user_message)
    
    # Wait for the response with a timeout
    try:
        response = response_queue.get(timeout=60)
        
        # Post-process response to ensure formatting
        ai_message_count = sum(1 for m in list(message_queue.queue) if isinstance(m, str) and not m.startswith('__'))
        
        # Ensure response follows the pattern
        if not re.match(r'^\*\*Response \d+:\*\*', response):
            response = f"**Response {ai_message_count + 1}:**\n{response}"
        
        return jsonify({'response': response})
    except queue.Empty:
        return jsonify({'error': 'Response timeout'}), 504

@app.route('/api/status', methods=['GET'])
def status():
    """Check if the server is connected"""
    global client
    if client and hasattr(client, 'session') and client.session:
        return jsonify({'status': 'connected'})
    return jsonify({'status': 'disconnected'})

def background_worker():
    """Background worker to process messages asynchronously"""
    global client, server_path
    
    # Run the event loop in this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Initialize the client
    client = SolarWindsClient()
    
    # Connect to the server
    try:
        loop.run_until_complete(client.connect_to_server(server_path))
        app.logger.info("Connected to server successfully")
    except Exception as e:
        app.logger.error(f"Failed to connect to server: {e}")
        return
    
    # Process messages from the queue
    while True:
        try:
            message = message_queue.get()
            if message == "__TERMINATE__":
                break
                
            # Process the message
            response = loop.run_until_complete(client.process_query_with_langchain(message))
            
            # Put the response in the response queue
            response_queue.put(response)
            
        except Exception as e:
            app.logger.error(f"Error processing message: {e}")
            response_queue.put(f"Error: {str(e)}")
    
    # Clean up
    loop.run_until_complete(client.cleanup())
    loop.close()

def start_background_worker(server_script_path):
    """Start the background worker thread"""
    global server_path
    server_path = os.path.abspath(server_script_path)
    
    worker_thread = threading.Thread(target=background_worker)
    worker_thread.daemon = True
    worker_thread.start()
    
    return worker_thread

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python app.py <path_to_server_script>")
        print("\nExample:")
        print("  python app.py server.py")
        sys.exit(1)
    
    server_script_path = sys.argv[1]
    worker_thread = start_background_worker(server_script_path)
    
    # Start the Flask app
    app.run(debug=True, use_reloader=False)
    
    # Send termination signal to the worker thread
    message_queue.put("__TERMINATE__")
    worker_thread.join(timeout=5)