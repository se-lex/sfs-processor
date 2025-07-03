#!/bin/bash
# Script to download SFS documents from Regeringskansliet from 2013 back to 1919

# Create output directory
OUTPUT_DIR="/Users/martin/Code/sfs-data"
mkdir -p "$OUTPUT_DIR"

# Loop from 2001 down to 1900
for year in $(seq 2001 -1 1900)
do
  echo "==================================="
  echo "Downloading documents for year $year"
  echo "==================================="
  
  # Run the download script with the current year and rkrattsbaser as source
  python3 download_sfs_documents.py --year "$year" --source rkrattsbaser --out "$OUTPUT_DIR"
  
  # Add a pause between years to be nice to the server
  echo "Pausing for 3 seconds before next year..."
  sleep 3
done

echo "Download complete for all years from 2001 to 1900!"
