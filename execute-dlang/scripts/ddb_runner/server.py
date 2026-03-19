# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "dolphindb",
#     "python-dotenv",
#     "pandas",
# ]
# ///
import dolphindb as ddb
import socket
import sys
import os
from dotenv import load_dotenv
import pandas as pd

import argparse

# Load config
current_dir = os.path.dirname(os.path.abspath(__file__))
# Check for .env in parent directories
dotenv_path = os.path.join(os.path.dirname(current_dir), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

HOST = '127.0.0.1'
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)


def require_setting(value, name):
    text = str(value or "").strip()
    if not text:
        raise SystemExit(f"Missing required setting: {name}")
    return text


def load_ddb_config(args):
    ddb_host = require_setting(args.host or os.getenv("DDB_HOST"), "DDB_HOST")
    ddb_port = int(require_setting(args.port or os.getenv("DDB_PORT"), "DDB_PORT"))
    ddb_user = require_setting(args.user or os.getenv("DDB_USER"), "DDB_USER")
    ddb_pass = require_setting(
        args.password or os.getenv("DDB_PASSWORD") or os.getenv("DDB_PASS"),
        "DDB_PASSWORD",
    )
    return ddb_host, ddb_port, ddb_user, ddb_pass

def start_server(args):
    ddb_host, ddb_port, ddb_user, ddb_pass = load_ddb_config(args)
    print(f"[Info] Connecting to DolphinDB {ddb_host}:{ddb_port}...")
    
    try:
        session = ddb.session()
        session.connect(ddb_host, ddb_port, ddb_user, ddb_pass)
        print("[Success] Connected to DolphinDB!")
    except Exception as e:
        print(f"[Error] Failed to connect to DolphinDB: {e}")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
            s.listen()
            print(f"[Info] Server listening on {HOST}:{PORT}")
            
            while True:
                conn, addr = s.accept()
                with conn:
                    # extensive buffer for large scripts
                    data = b""
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                        if len(chunk) < 4096:
                            break
                    
                    if not data:
                        continue
                        
                    script = data.decode('utf-8')
                    print(f"[Info] Executing script length: {len(script)}")
                    
                    try:
                        result = session.run(script)
                        if isinstance(result, pd.DataFrame):
                            output = result.to_string(index=False)
                        elif isinstance(result, list) or isinstance(result, dict):
                            import pprint
                            output = pprint.pformat(result)
                        else:
                            output = str(result)
                        conn.sendall(output.encode('utf-8'))
                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        conn.sendall(error_msg.encode('utf-8'))
        except OSError as e:
            if e.errno == 10048: # Address already in use
                print(f"[Error] Port {PORT} is already in use. Server might be running.")
            else:
                print(f"[Error] Socket error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DolphinDB Persistent Server")
    parser.add_argument("--host", help="DolphinDB host address")
    parser.add_argument("--port", help="DolphinDB port")
    parser.add_argument("--user", help="DolphinDB username")
    parser.add_argument("--password", help="DolphinDB password")
    args = parser.parse_args()
    
    start_server(args)
