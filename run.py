import uvicorn
import socket
import os
import sys

def find_free_port(start_port=8000, max_attempts=50):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return start_port

if __name__ == "__main__":
    port = find_free_port(8000)
    print("=" * 70)
    print("  DecisionMemory — Business Decision Memory & Intelligence Platform")
    print(f"  Local Server: http://127.0.0.1:{port}")
    print("=" * 70)
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False, log_level="info")
