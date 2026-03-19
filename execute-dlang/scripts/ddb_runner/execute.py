# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "dolphindb",
#     "python-dotenv",
#     "pandas",
# ]
# ///
# execute.py
import sys
import os
import argparse
import socket
import tempfile
try:
    import pandas as pd
except ImportError:
    pd = None

# Check for required packages
try:
    import dolphindb as ddb
    from dotenv import load_dotenv
except ImportError as e:
    print(f"[Error] Missing required package '{e.name}'.", file=sys.stderr)
    print("Please install dependencies: pip install dolphindb python-dotenv", file=sys.stderr)
    sys.exit(1)

def load_config(args):
    """Load configuration from args, .env files or environment variables."""
    # 1. Try loading from current directory .env
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(current_dir, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    
    # 2. Try loading from parent directory (legacy support potentially)
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) 
    parent_dotenv_path = os.path.join(parent_dir, ".env")
    if os.path.exists(parent_dotenv_path):
        load_dotenv(parent_dotenv_path)

    # 3. Read from environment
    host = (args.host or os.getenv("DDB_HOST") or "").strip()
    port = str(args.port or os.getenv("DDB_PORT") or "").strip()
    user = (args.user or os.getenv("DDB_USER") or "").strip()
    password = (args.password or os.getenv("DDB_PASSWORD") or os.getenv("DDB_PASS") or "").strip()

    missing = [
        name
        for name, value in (("DDB_HOST", host), ("DDB_PORT", port), ("DDB_USER", user), ("DDB_PASSWORD", password))
        if not value
    ]
    if missing:
        print(f"[Error] Missing required settings: {', '.join(missing)}. Set them via arguments, .env file or environment variables.")
        sys.exit(1)
        
    return host, int(port), user, password

def connect_ddb(args):
    """Connect to DolphinDB and return the session object."""
    try:
        host, port, user, password = load_config(args)
    except SystemExit:
        return None
        
    print(f"[Info] Connecting to {host}:{port}...")
    try:
        s = ddb.session()
        s.connect(host, port, user, password)
        print(f"[Success] Connected to {host}:{port}")
        return s
    except Exception as e:
        print(f"[Error] Connection Failed: {e}")
        return None

def run_via_server(code_str):
    """Attempt to run code via the persistent server."""
    HOST = '127.0.0.1'
    PORT = 65432
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2) # Short timeout to detect if server is down quickly
            s.connect((HOST, PORT))
            s.sendall(code_str.encode('utf-8'))
            
            # Receive response
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            
            print("[Success] Execution Successful (via Server)")
            print("--- Result ---")
            print(data.decode('utf-8'))
            print("--------------")
            return True
    except (ConnectionRefusedError, socket.timeout):
        return False
    except Exception as e:
        print(f"[Warning] Server connection error: {e}")
        return False

def create_temp_dos(code_str):
    """Persist a code snippet to a temporary .dos file for safer execution."""
    fd, temp_path = tempfile.mkstemp(prefix="ddb_exec_", suffix=".dos", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            temp_file.write(code_str)
        return temp_path
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise

def cleanup_temp_file(file_path):
    """Best-effort cleanup for temporary script files."""
    if not file_path:
        return

    try:
        os.unlink(file_path)
    except OSError:
        pass

def read_code_from_stdin():
    """Read a DolphinDB script from stdin."""
    if sys.stdin.isatty():
        print("[Error] --stdin requires piped input.")
        return None

    code_str = sys.stdin.read()
    if not code_str.strip():
        print("[Error] No code received from stdin.")
        return None

    return code_str

def run_code(session, code_str, args, print_output=True, use_server=False):
    """Execute a raw code string."""
    if use_server:
        if run_via_server(code_str):
            return "Executed via server"
            
        # Fallback to local connection if server failed
        print("[Warning] Persistent server not found. Falling back to new session.")
        
    if session is None:
        session = connect_ddb(args)
        if not session:
            return None

    try:
        if print_output:
            print(f"Executing code snippet...")
        result = session.run(code_str)
        if print_output:
            print("[Success] Execution Successful")
            print("--- Result ---")
            if pd is not None and isinstance(result, pd.DataFrame):
                # Format DataFrame nicely
                print(result.to_string(index=False))
            elif isinstance(result, list) or isinstance(result, dict):
                import pprint
                pprint.pprint(result)
            else:
                print(result)
            print("--------------")
        return result
    except Exception as e:
        print(f"[Error] Code Execution Failed: {e}")
        return None

def run_code_via_temp_file(session, code_str, args, use_server=False):
    """Execute code by first persisting it to a temporary .dos file."""
    temp_path = None
    try:
        temp_path = create_temp_dos(code_str)
        print(f"[Info] Saved code snippet to temporary file: {temp_path}")
        return run_dos_file(session, temp_path, args, use_server=use_server)
    finally:
        cleanup_temp_file(temp_path)

def run_dos_file(session, file_path, args, use_server=False):
    """Read and execute a .dos file."""
    # Try to resolve relative paths against workspace root if possible
    if not os.path.exists(file_path):
        # Try to find it relative to the current working directory
        cwd_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(cwd_path):
            file_path = cwd_path
        else:
            print(f"[Error] File not found: {file_path}")
            return None
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            script_content = f.read()
            
        print(f"Executing file: {file_path}")
        return run_code(session, script_content, args, use_server=use_server)
    except Exception as e:
        print(f"[Error] File Execution Failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="DolphinDB Script Executor")
    parser.add_argument("file", nargs="?", help="Path to .dos or .txt script file")
    parser.add_argument("-c", "--code", help="Direct code string to execute")
    parser.add_argument("--stdin", action="store_true", help="Read code from stdin and execute it via a temporary .dos file")
    parser.add_argument("--use-server", action="store_true", help="Use persistent server session")
    parser.add_argument("--host", help="DolphinDB host address")
    parser.add_argument("--port", help="DolphinDB port")
    parser.add_argument("--user", help="DolphinDB username")
    parser.add_argument("--password", help="DolphinDB password")
    
    args = parser.parse_args()
    
    if sum(bool(value) for value in (args.file, args.code, args.stdin)) != 1:
        print("Please provide exactly one input source: file, -c/--code, or --stdin.")
        parser.print_help()
        sys.exit(1)

    session = None
    if not args.use_server:
        session = connect_ddb(args)
        if not session:
            sys.exit(1)
            
    if args.file:
        run_dos_file(session, args.file, args, use_server=args.use_server)
    elif args.code:
        run_code_via_temp_file(session, args.code, args, use_server=args.use_server)
    elif args.stdin:
        code_str = read_code_from_stdin()
        if code_str is None:
            sys.exit(1)
        run_code_via_temp_file(session, code_str, args, use_server=args.use_server)

if __name__ == "__main__":
    main()
