#!/usr/bin/env python3
"""
Script för att ladda upp HTML-export till Cloudflare R2
Replikerar funktionaliteten från GitHub Actions workflow utan att köra i CI/CD
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

def upload_html_site(output_base_dir=""):
    """Ladda upp hela HTML-siten (eli/ + index-sidor) till Cloudflare R2"""
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    # Kontrollera att mappen finns
    if not Path(output_base_dir).exists():
        print(f"Error: Mappen {output_base_dir} finns inte. Kör först HTML-export.")
        return False

    # Räkna filer som ska laddas upp
    html_files = list(Path(output_base_dir).rglob('*.html'))
    css_files = list(Path(output_base_dir).rglob('*.css'))
    js_files = list(Path(output_base_dir).rglob('*.js'))
    file_count = len(html_files) + len(css_files) + len(js_files)
    print(f"Laddar upp HTML-siten från {output_base_dir} ({len(html_files)} HTML, {len(css_files)} CSS, {len(js_files)} JS-filer)...")

    cmd = [
        'aws', 's3', 'sync', f'{output_base_dir}/', f's3://{bucket_name}/',
        '--endpoint-url', endpoint_url,
        '--delete',
        '--cache-control', 'public, max-age=3600',
        '--exclude', '*.md',
        '--exclude', '.DS_Store',
        '--cli-read-timeout', '0',
        '--cli-connect-timeout', '60'
    ]

    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'

    try:
        print(f"Kör kommando: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        print(f"✓ HTML-siten uppladdad ({file_count} filer)")

        # Visa AWS CLI output om det finns
        if result.stdout.strip():
            print("AWS CLI output:")
            print(result.stdout.strip())

        if result.stderr.strip():
            print("AWS CLI stderr (debug info):")
            print(result.stderr.strip())

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid uppladdning av HTML-siten: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        return False

def upload_index_pages(output_base_dir="", json_input_dir=None):
    """Ladda upp index-sidor till Cloudflare R2"""
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    # Hitta JSON-filerna för att generera index-sidor
    if json_input_dir is None:
        # Försök hitta JSON-mappen automatiskt
        possible_paths = ["../sfs-jsondata", "sfs_json", "data/sfs_json"]
        json_input_dir = None
        for path in possible_paths:
            if Path(path).exists():
                json_input_dir = path
                break

        if json_input_dir is None:
            print(f"Varning: Kunde inte hitta JSON-mappen. Hoppar över index-sidor.")
            print(f"Prövade sökvägarna: {', '.join(possible_paths)}")
            return True  # Inte ett kritiskt fel

    if not Path(json_input_dir).exists():
        print(f"Varning: JSON-mappen {json_input_dir} finns inte. Hoppar över index-sidor.")
        return True  # Inte ett kritiskt fel

    # Generera index-sidor i output_base_dir
    print(f"Genererar index-sidor i {output_base_dir}...")
    print(f"Använder JSON-katalog: {json_input_dir}")

    # Konvertera till absoluta sökvägar
    json_input_abs = str(Path(json_input_dir).resolve())
    output_base_abs = str(Path(output_base_dir).resolve())

    # Skapa index.html (30 senaste)
    index_file = Path(output_base_abs) / "index.html"
    latest_file = Path(output_base_abs) / "latest.html"

    try:
        # Kör populate_index_pages.py för att skapa index-sidor
        result1 = subprocess.run([
            'python', 'exporters/html/populate_index_pages.py',
            '--input', json_input_abs,
            '--output', str(index_file),
            '--limit', '30'
        ], check=True, capture_output=True, text=True)

        result2 = subprocess.run([
            'python', 'exporters/html/populate_index_pages.py',
            '--input', json_input_abs,
            '--output', str(latest_file),
            '--limit', '10'
        ], check=True, capture_output=True, text=True)

        print(f"✓ Index-sidor genererade: {index_file}, {latest_file}")

        # Visa output från populate_index_pages.py om det finns
        if result1.stdout.strip():
            print("Output från index.html-generering:")
            print(result1.stdout.strip())
        if result2.stdout.strip():
            print("Output från latest.html-generering:")
            print(result2.stdout.strip())

    except subprocess.CalledProcessError as e:
        print(f"Error vid generering av index-sidor: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        return False

    # Kontrollera att index-filerna nu finns
    index_files = [index_file, latest_file]
    for file in index_files:
        if not file.exists():
            print(f"Error: {file} kunde inte genereras.")
            return False
    
    print(f"Laddar upp index-sidor ({len(index_files)} filer)...")
    
    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    # Ladda upp index.html
    cmd1 = [
        'aws', 's3', 'cp', str(index_file), f's3://{bucket_name}/index.html',
        '--endpoint-url', endpoint_url,
        '--cache-control', 'public, max-age=1800',
        '--content-type', 'text/html'
    ]
    
    # Ladda upp latest.html
    cmd2 = [
        'aws', 's3', 'cp', str(latest_file), f's3://{bucket_name}/latest.html',
        '--endpoint-url', endpoint_url,
        '--cache-control', 'public, max-age=1800',
        '--content-type', 'text/html'
    ]
    
    try:
        print(f"Kör kommando: {' '.join(cmd1)}")
        result1 = subprocess.run(cmd1, env=env, check=True, capture_output=True, text=True)
        print(f"Kör kommando: {' '.join(cmd2)}")
        result2 = subprocess.run(cmd2, env=env, check=True, capture_output=True, text=True)
        print(f"✓ Index-sidor uppladdade ({len(index_files)} filer)")
        
        # Visa AWS CLI output om det finns
        for i, result in enumerate([result1, result2], 1):
            if result.stdout.strip():
                print(f"AWS CLI output (fil {i}):")
                print(result.stdout.strip())
            if result.stderr.strip():
                print(f"AWS CLI stderr (fil {i}):")
                print(result.stderr.strip())
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error vid uppladdning av index-sidor: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        return False

def upload_summary():
    """Skapa och ladda upp sammanfattning"""
    print("Skapar och laddar upp sammanfattning...")
    
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
    account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    # Skapa sammanfattning
    summary_content = f"""HTML export completed at {datetime.datetime.now().isoformat()}
Files uploaded to Cloudflare R2 bucket: {bucket_name}/
Index pages uploaded: index.html (30 senaste), latest.html (10 senaste)
Upload performed locally via upload_to_r2.py script
"""
    
    # Skriv till fil
    with open('upload-summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    # Ladda upp sammanfattning
    cmd = [
        'aws', 's3', 'cp', 'upload-summary.txt', f's3://{bucket_name}/last-update.txt',
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
        os.remove('upload-summary.txt')
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
        description='Ladda upp HTML-export till Cloudflare R2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  python upload_to_r2.py --output-base-dir output/html_site  # Ladda upp från output/html_site
  python upload_to_r2.py --output-base-dir output/html_site --json-dir ../sfs-jsondata  # Med JSON-mapp
        """
    )
    parser.add_argument(
        '--output-base-dir',
        default='output/html_site',
        help='Baskatalog som innehåller HTML-filerna (eli/, index.html, etc.)'
    )
    parser.add_argument(
        '--json-dir',
        default=None,
        help='Sökväg till JSON-mappen (för att generera index-sidor)'
    )

    args = parser.parse_args()

    print("=== Cloudflare R2 Upload Script ===")
    print(f"Laddar upp från: {args.output_base_dir}")
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

    # Generera och ladda upp index-sidor först
    if not upload_index_pages(args.output_base_dir, args.json_dir):
        success = False

    # Ladda upp hela HTML-siten (eli/ + index-sidor)
    if not upload_html_site(args.output_base_dir):
        success = False

    # Ladda upp sammanfattning
    if not upload_summary():
        success = False

    print()
    if success:
        print("✓ Alla filer har laddats upp till Cloudflare R2!")
        print(f"Bucket: {os.getenv('CLOUDFLARE_R2_BUCKET_NAME')}")
        print(f"Källa: {args.output_base_dir}")
    else:
        print("✗ Något gick fel under uppladdningen")
        sys.exit(1)

if __name__ == "__main__":
    main()
