#!/usr/bin/env python3
"""
Script för att ta bort alla filer i Cloudflare R2 bucket
"""

import os
import sys
import subprocess
import argparse

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

def delete_web_folder():
    """Ta bort alla filer i Cloudflare R2 bucket"""
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    print(f"Tar bort alla filer i bucket {bucket_name}...")

    cmd = [
        'aws', 's3', 'rm', f's3://{bucket_name}/',
        '--endpoint-url', endpoint_url,
        '--recursive'
    ]

    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'

    try:
        print(f"Kör kommando: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        print("✓ Alla filer har tagits bort från bucketen")

        # Visa AWS CLI output om det finns
        if result.stdout.strip():
            print("\nAWS CLI output:")
            print(result.stdout.strip())

        if result.stderr.strip():
            print("\nAWS CLI stderr:")
            print(result.stderr.strip())

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid borttagning av filer: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        return False

def main():
    """Huvudfunktion"""
    parser = argparse.ArgumentParser(
        description='Ta bort alla filer i Cloudflare R2 bucket'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Hoppa över bekräftelse'
    )
    args = parser.parse_args()

    print("=== Ta bort alla filer från Cloudflare R2 ===")
    print()

    # Bekräfta med användaren om inte --force används
    if not args.force:
        print("VARNING: Detta kommer att ta bort ALLA filer i R2 bucketen.")
        print("Detta kan inte ångras!")
        response = input("Är du säker på att du vill fortsätta? (ja/nej): ")

        if response.lower() not in ['ja', 'j', 'yes', 'y']:
            print("Avbruten.")
            sys.exit(0)

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

    # Ta bort filerna
    print()
    if delete_web_folder():
        print("\n✓ Klart!")
    else:
        print("\n✗ Något gick fel")
        sys.exit(1)

if __name__ == "__main__":
    main()
