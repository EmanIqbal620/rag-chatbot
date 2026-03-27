#!/usr/bin/env python3
"""Simple HTTP server for chatbot API"""
import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.rag_agent import run_agent

class ChatHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/':
            self.send_json({
                "message": "Humanoid Robotics RAG API is running",
                "version": "2.0.0",
                "features": ["Pre-computed answers", "Multi-level caching", "Fast responses"]
            })
        elif parsed.path == '/health':
            self.send_json({"status": "healthy", "timestamp": asyncio.get_event_loop().time()})
        elif parsed.path == '/api/v1/health':
            self.send_json({"status": "healthy", "timestamp": asyncio.get_event_loop().time()})
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        if self.path.startswith('/api/v1/chat'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body)
                question = data.get('question', '')
                selected_text = data.get('selected_text')
                
                # Run agent
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(run_agent(question, selected_text, True))
                loop.close()
                
                response = {
                    "status": "ok",
                    "data": {
                        "answer": result["answer"],
                        "sources": result.get("sources", [])
                    }
                }
                self.send_json(response)
                
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, 500)
        else:
            self.send_error(404, "Not Found")
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

def run_server(port=8000):
    server = HTTPServer(('0.0.0.0', port), ChatHandler)
    print(f"🤖 Robotics Tutor API running on http://0.0.0.0:{port}")
    print("Endpoints:")
    print("  GET  /              - API info")
    print("  GET  /health        - Health check")
    print("  POST /api/v1/chat   - Chat endpoint")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
