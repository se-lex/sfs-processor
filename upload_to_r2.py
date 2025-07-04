#!/usr/bin/env python3
"""
Script för att ladda upp HTML-export till Cloudflare R2
Replikerar funktionaliteten från GitHub Actions workflow utan att köra i CI/CD
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path

def check_required_env_vars():
    """Kontrollera att alla nödvändiga miljövariabler är satta"""
    required_vars = [
        'CLOUDFLARE_R2_ACCESS_KEY_ID',
        'CLOUDFLARE_R2_SECRET_ACCESS_KEY', 
        'CLOUDFLARE_R2_BUCKET_NAME',
        'CLOUDFLARE_R2_ACCOUNT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("Error: Följande miljövariabler saknas:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nExempel på hur du sätter dem:")
        print("export CLOUDFLARE_R2_ACCESS_KEY_ID='your_access_key'")
        print("export CLOUDFLARE_R2_SECRET_ACCESS_KEY='your_secret_key'")
        print("export CLOUDFLARE_R2_BUCKET_NAME='your_bucket_name'")
        print("export CLOUDFLARE_R2_ACCOUNT_ID='your_account_id'")
        return False
    
    print("✓ Alla nödvändiga miljövariabler är konfigurerade")
    return True

def configure_aws_cli():
    """Konfigurera AWS CLI för Cloudflare R2"""
    print("Konfigurerar AWS CLI för Cloudflare R2...")
    
    commands = [
        ['aws', 'configure', 'set', 'aws_access_key_id', os.getenv('CLOUDFLARE_R2_ACCESS_KEY_ID')],
        ['aws', 'configure', 'set', 'aws_secret_access_key', os.getenv('CLOUDFLARE_R2_SECRET_ACCESS_KEY')],
        ['aws', 'configure', 'set', 'region', 'us-east-1'],
        ['aws', 'configure', 'set', 'output', 'json']
    ]
    
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Error vid konfiguration av AWS CLI: {e}")
            return False
    
    print("✓ AWS CLI konfigurerad")
    return True

def upload_sfs_folder():
    """Ladda upp SFS-mappen till Cloudflare R2"""
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    # Kontrollera att SFS-mappen finns
    if not Path('SFS').exists():
        print("Error: SFS-mappen finns inte. Kör först HTML-export.")
        return False
    
    # Räkna HTML-filer som ska laddas upp
    html_files = list(Path('SFS').rglob('*.html'))
    file_count = len(html_files)
    print(f"Laddar upp SFS-mappen ({file_count} HTML-filer)...")
    
    cmd = [
        'aws', 's3', 'sync', 'SFS/', f's3://{bucket_name}/sfs/',
        '--endpoint-url', endpoint_url,
        '--delete',
        '--cache-control', 'public, max-age=3600',
        '--content-type', 'text/html',
        '--exclude', '*.md',
        '--include', '*.html'
    ]
    
    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        print(f"✓ SFS-mappen uppladdad ({file_count} HTML-filer)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid uppladdning av SFS-mappen: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False

def upload_index_pages():
    """Ladda upp index-sidor till Cloudflare R2"""
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    # Kontrollera att index-filerna finns
    index_files = ['index.html', 'latest.html']
    for file in index_files:
        if not Path(file).exists():
            print(f"Error: {file} finns inte. Kör först 'python populate_index_pages.py'")
            return False
    
    print(f"Laddar upp index-sidor ({len(index_files)} filer)...")
    
    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    # Ladda upp index.html
    cmd1 = [
        'aws', 's3', 'cp', 'index.html', f's3://{bucket_name}/index.html',
        '--endpoint-url', endpoint_url,
        '--cache-control', 'public, max-age=1800',
        '--content-type', 'text/html'
    ]
    
    # Ladda upp latest.html
    cmd2 = [
        'aws', 's3', 'cp', 'latest.html', f's3://{bucket_name}/latest.html',
        '--endpoint-url', endpoint_url,
        '--cache-control', 'public, max-age=1800',
        '--content-type', 'text/html'
    ]
    
    try:
        subprocess.run(cmd1, env=env, check=True, capture_output=True)
        subprocess.run(cmd2, env=env, check=True, capture_output=True)
        print(f"✓ Index-sidor uppladdade ({len(index_files)} filer)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid uppladdning av index-sidor: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False

def upload_summary():
    """Skapa och ladda upp sammanfattning"""
    print("Skapar och laddar upp sammanfattning...")
    
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    # Skapa sammanfattning
    summary_content = f"""HTML export completed at {datetime.datetime.now().isoformat()}
Files uploaded to Cloudflare R2 bucket: {bucket_name}/sfs/
Index pages uploaded: index.html (30 senaste), latest.html (10 senaste)
Upload performed locally via upload_to_r2.py script
"""
    
    # Skriv till fil
    with open('upload-summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    # Ladda upp sammanfattning
    cmd = [
        'aws', 's3', 'cp', 'upload-summary.txt', f's3://{bucket_name}/sfs/last-update.txt',
        '--endpoint-url', endpoint_url
    ]
    
    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True)
        print("✓ Sammanfattning uppladdad")
        
        # Ta bort lokal fil
        os.remove('upload-summary.txt')
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid uppladdning av sammanfattning: {e}")
        return False

def main():
    """Huvudfunktion"""
    print("=== Cloudflare R2 Upload Script ===")
    print()
    
    # Kontrollera att AWS CLI är installerat
    try:
        subprocess.run(['aws', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: AWS CLI är inte installerat eller inte tillgängligt i PATH")
        print("Installera med: pip install awscli")
        sys.exit(1)
    
    # Kontrollera miljövariabler
    if not check_required_env_vars():
        sys.exit(1)
    
    # Konfigurera AWS CLI
    if not configure_aws_cli():
        sys.exit(1)
    
    # Utför uppladdningar
    print()
    success = True
    
    if not upload_sfs_folder():
        success = False
    
    if not upload_index_pages():
        success = False
    
    if not upload_summary():
        success = False
    
    print()
    if success:
        print("✓ Alla filer har laddats upp till Cloudflare R2!")
        print(f"Bucket: {os.getenv('CLOUDFLARE_R2_BUCKET_NAME')}")
    else:
        print("✗ Något gick fel under uppladdningen")
        sys.exit(1)

if __name__ == "__main__":
    main()
