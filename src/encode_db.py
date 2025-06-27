import base64
import argparse
import gzip
from pathlib import Path

def encode_database(db_path):
    """Encode SQLite database to compressed base64 for Streamlit secrets"""
    db_path = Path(db_path)
    
    if not db_path.exists():
        print(f"Error: Database file {db_path} not found")
        return
    
    print(f"Encoding database: {db_path}")
    
    with open(db_path, 'rb') as f:
        db_data = f.read()
    
    print(f"Original size: {len(db_data):,} bytes ({len(db_data)/1024/1024:.2f} MB)")
    
    # Compress with maximum compression
    compressed = gzip.compress(db_data, compresslevel=9)
    print(f"Compressed size: {len(compressed):,} bytes ({len(compressed)/1024/1024:.2f} MB)")
    print(f"Compression ratio: {(1-len(compressed)/len(db_data))*100:.1f}% reduction")
    
    # Encode to base64
    encoded = base64.b64encode(compressed).decode('utf-8')
    print(f"Final encoded size: {len(encoded):,} bytes ({len(encoded)/1024/1024:.2f} MB)")
    
    # Check if it fits in Streamlit secrets (1MB limit)
    if len(encoded) > 1024*1024:
        print("⚠️  WARNING: Still exceeds 1MB limit for Streamlit Cloud secrets!")
        print("Consider using external hosting or splitting the data.")
    else:
        print("✅ Will fit in Streamlit Cloud secrets!")
    
    # Split into chunks for better readability in secrets
    chunk_size = 76
    chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
    
    print("\n" + "="*50)
    print("Copy this to your .streamlit/secrets.toml file:")
    print("="*50)
    print("[database]")
    print('compressed_data = """')
    for chunk in chunks:
        print(chunk)
    print('"""')
    print("="*50)
    
    # Also save to file for convenience
    secrets_file = db_path.parent / "secrets_database.txt"
    with open(secrets_file, 'w') as f:
        f.write("[database]\n")
        f.write('compressed_data = """\n')
        for chunk in chunks:
            f.write(chunk + '\n')
        f.write('"""\n')
    
    print(f"\nAlso saved to: {secrets_file}")
    print("Add this file to your .gitignore!")
    
    return len(encoded) <= 1024*1024

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Encode SQLite database for Streamlit secrets')
    parser.add_argument('db_path', help='Path to SQLite database file')
    
    args = parser.parse_args()
    encode_database(args.db_path)