import base64
import argparse
from pathlib import Path

def encode_database(db_path):
    """Encode SQLite database to base64 for Streamlit secrets"""
    db_path = Path(db_path)
    
    if not db_path.exists():
        print(f"Error: Database file {db_path} not found")
        return
    
    print(f"Encoding database: {db_path}")
    print(f"File size: {db_path.stat().st_size / 1024:.1f} KB")
    
    with open(db_path, 'rb') as f:
        db_data = f.read()
    
    encoded = base64.b64encode(db_data).decode('utf-8')
    
    # Split into chunks for better readability in secrets
    chunk_size = 76
    chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
    
    print("\n" + "="*50)
    print("Copy this to your .streamlit/secrets.toml file:")
    print("="*50)
    print("[database]")
    print('data = """')
    for chunk in chunks:
        print(chunk)
    print('"""')
    print("="*50)
    
    # Also save to file for convenience
    secrets_file = db_path.parent / "secrets_database.txt"
    with open(secrets_file, 'w') as f:
        f.write("[database]\n")
        f.write('data = """\n')
        for chunk in chunks:
            f.write(chunk + '\n')
        f.write('"""\n')
    
    print(f"\nAlso saved to: {secrets_file}")
    print("Add this file to your .gitignore!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Encode SQLite database for Streamlit secrets')
    parser.add_argument('db_path', help='Path to SQLite database file')
    
    args = parser.parse_args()
    encode_database(args.db_path)