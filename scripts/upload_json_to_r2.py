#!/usr/bin/env python3
"""
Script för att ladda upp SFS JSON-filer till Cloudflare R2 (sfs-json bucket)
"""

import os
import sys
import subprocess
import datetime
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ladda miljövariabler från .env-fil
load_dotenv()

def check_required_env_vars():
    """Kontrollera att alla nödvändiga miljövariabler är satta"""
    required_vars = [
        'CLOUDFLARE_R2_ACCESS_KEY_ID',
        'CLOUDFLARE_R2_SECRET_ACCESS_KEY',
        'CLOUDFLARE_R2_RAWDATA_BUCKET_NAME',
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
        print("export CLOUDFLARE_R2_RAWDATA_BUCKET_NAME='sfs-json'")
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

def count_json_files(json_dir):
    """Räkna antal JSON-filer i mappen"""
    json_files = list(Path(json_dir).glob('*.json'))
    return len(json_files)

def upload_json_files(json_dir):
    """Ladda upp alla JSON-filer till Cloudflare R2"""
    bucket_name = os.getenv('CLOUDFLARE_R2_RAWDATA_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    # Kontrollera att mappen finns
    if not Path(json_dir).exists():
        print(f"Error: Mappen {json_dir} finns inte.")
        return False

    # Räkna filer som ska laddas upp
    file_count = count_json_files(json_dir)
    print(f"Laddar upp JSON-filer från {json_dir} ({file_count} filer)...")

    cmd = [
        'aws', 's3', 'sync', f'{json_dir}/', f's3://{bucket_name}/',
        '--endpoint-url', endpoint_url,
        '--exclude', '*',
        '--include', '*.json',
        '--cache-control', 'public, max-age=3600',
        '--content-type', 'application/json',
        '--cli-read-timeout', '0',
        '--cli-connect-timeout', '60'
    ]

    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'

    try:
        print(f"Kör kommando: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        print(f"✓ JSON-filer uppladdade ({file_count} filer)")

        # Visa AWS CLI output om det finns
        if result.stdout.strip():
            print("AWS CLI output:")
            print(result.stdout.strip())

        if result.stderr.strip():
            print("AWS CLI stderr (debug info):")
            print(result.stderr.strip())

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid uppladdning av JSON-filer: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        return False

def upload_summary(json_dir):
    """Skapa och ladda upp sammanfattning"""
    print("Skapar och laddar upp sammanfattning...")

    bucket_name = os.getenv('CLOUDFLARE_R2_RAWDATA_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    file_count = count_json_files(json_dir)

    # Skapa sammanfattning
    summary_content = f"""JSON upload completed at {datetime.datetime.now().isoformat()}
Files uploaded to Cloudflare R2 bucket: {bucket_name}/
Number of JSON files: {file_count}
Source directory: {json_dir}
Upload performed locally via upload_json_to_r2.py script
"""

    # Skriv till fil
    with open('json-upload-summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary_content)

    # Ladda upp sammanfattning
    cmd = [
        'aws', 's3', 'cp', 'json-upload-summary.txt', f's3://{bucket_name}/last-update.txt',
        '--endpoint-url', endpoint_url
    ]

    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'

    try:
        print(f"Kör kommando: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        print("✓ Sammanfattning uppladdad")

        # Visa AWS CLI output om det finns
        if result.stdout.strip():
            print("AWS CLI output:")
            print(result.stdout.strip())
        if result.stderr.strip():
            print("AWS CLI stderr:")
            print(result.stderr.strip())

        # Ta bort lokal fil
        os.remove('json-upload-summary.txt')
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid uppladdning av sammanfattning: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        return False

def main():
    """Huvudfunktion"""
    # Hantera kommandoradsargument
    parser = argparse.ArgumentParser(
        description='Ladda upp SFS JSON-filer till Cloudflare R2 (sfs-json bucket)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  python scripts/upload_json_to_r2.py --json-dir ../sfs-jsondata
  python scripts/upload_json_to_r2.py --json-dir data/sfs_json
        """
    )
    parser.add_argument(
        '--json-dir',
        default='../sfs-jsondata',
        help='Sökväg till mappen med JSON-filer (standard: ../sfs-jsondata)'
    )

    args = parser.parse_args()

    print("=== Cloudflare R2 JSON Upload Script ===")
    print(f"Laddar upp från: {args.json_dir}")
    print(f"Bucket: {os.getenv('CLOUDFLARE_R2_RAWDATA_BUCKET_NAME', 'sfs-json')}")
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

    # Ladda upp JSON-filer
    if not upload_json_files(args.json_dir):
        success = False

    # Ladda upp sammanfattning
    if not upload_summary(args.json_dir):
        success = False

    print()
    if success:
        print("✓ Alla JSON-filer har laddats upp till Cloudflare R2!")
        print(f"Bucket: {os.getenv('CLOUDFLARE_R2_RAWDATA_BUCKET_NAME')}")
        print(f"Källa: {args.json_dir}")
    else:
        print("✗ Något gick fel under uppladdningen")
        sys.exit(1)

if __name__ == "__main__":
    main()
