#!/bin/bash
# Wrapper script to run 3-year commits with 10-minute timeout

# Set the timeout to 10 minutes (600 seconds)
TIMEOUT=600

# Run the Python script with timeout
# Pass all command-line arguments to the Python script
exec timeout $TIMEOUT python scripts/run_3year_commits.py "$@"