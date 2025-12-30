#!/usr/bin/env python3
"""
Script to run generate_commits in dry run mode and log output.

This script runs the exporters/git/generate_commits.py script with --dry-run flag,
captures all output, and saves it to a log file in the output directory.
"""

import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path


def run_generate_commits_dry_run(
    path: str,
    from_date: str = None,
    to_date: str = None,
    output_dir: str = None
) -> None:
    """
    Run generate_commits with dry run flag, logging output to file.
    
    Args:
        path: Path to markdown file or directory to process
        from_date: Start date (inclusive) in YYYY-MM-DD format
        to_date: End date (inclusive) in YYYY-MM-DD format
        output_dir: Output directory for log file
    """
    # Get script directory
    script_dir = Path(__file__).parent.parent
    generate_commits_path = script_dir / "exporters" / "git" / "generate_commits.py"
    
    if not generate_commits_path.exists():
        print(f"Fel: generate_commits.py hittades inte på {generate_commits_path}")
        return
    
    # Build command
    cmd = [
        sys.executable,
        str(generate_commits_path),
        path,
        "--dry-run"
    ]
    
    if from_date:
        cmd.extend(["--from-date", from_date])
    
    if to_date:
        cmd.extend(["--to-date", to_date])
    
    # Determine output directory for log
    if output_dir:
        output_path = Path(output_dir)
    else:
        # Default output directory
        output_path = script_dir / "logs"
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"generate_commits_dry_run_{timestamp}.log"
    log_path = output_path / log_filename
    
    print("Kör generate_commits i dry-run läge...")
    print(f"Kommando: {' '.join(cmd)}")
    print(f"Loggar output till: {log_path}")
    print("=" * 80)
    
    try:
        # Set up environment with PYTHONPATH
        import os
        env = os.environ.copy()
        env['PYTHONPATH'] = str(script_dir)
        
        # Run the command and capture both stdout and stderr
        with open(log_path, 'w', encoding='utf-8') as log_file:
            # Write header to log file
            log_file.write("Generate Commits Dry Run Log\n")
            log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
            log_file.write(f"Command: {' '.join(cmd)}\n")
            log_file.write("=" * 80 + "\n\n")
            log_file.flush()
            
            # Run process and stream output to both console and log file
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=env
            )
            
            # Stream output line by line
            for line in process.stdout:
                # Print to console
                print(line, end='')
                # Write to log file
                log_file.write(line)
                log_file.flush()
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Write footer to log file
            log_file.write(f"\n" + "=" * 80 + "\n")
            log_file.write(f"Process finished with return code: {return_code}\n")
            log_file.write(f"End time: {datetime.now().isoformat()}\n")
        
        print("\n" + "=" * 80)
        print(f"generate_commits dry run avslutad med returkod: {return_code}")
        print(f"Fullständig logg sparad till: {log_path}")
        
        if return_code != 0:
            print(f"Varning: Processen avslutades med felkod {return_code}")
    
    except subprocess.SubprocessError as e:
        error_msg = f"Fel vid körning av generate_commits: {e}"
        print(error_msg)
        
        # Write error to log file
        try:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\nERROR: {error_msg}\n")
        except Exception:
            pass
    
    except KeyboardInterrupt:
        print("\nAnvändaren avbröt körningen")
        try:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\nINTERRUPTED: User cancelled execution at {datetime.now().isoformat()}\n")
        except Exception:
            pass


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Kör generate_commits med --dry-run och logga output till fil.'
    )
    parser.add_argument(
        'path',
        help='Sökväg till markdown-fil eller katalog att bearbeta'
    )
    parser.add_argument(
        '--from-date',
        help='Startdatum (inklusivt) i formatet YYYY-MM-DD'
    )
    parser.add_argument(
        '--to-date',
        help='Slutdatum (inklusivt) i formatet YYYY-MM-DD'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output-katalog för loggfilen (standard: ./logs)'
    )
    
    args = parser.parse_args()
    
    run_generate_commits_dry_run(
        path=args.path,
        from_date=args.from_date,
        to_date=args.to_date,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()