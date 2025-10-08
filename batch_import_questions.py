#!/usr/bin/env python3
"""
Batch Question Import Script

This script processes all JSON files in the question_json/ directory and creates
question graphs in Neo4j using the Django management command.

Features:
- Fully automated processing - no user prompts required
- Loops through all JSON files in the question_json/ directory
- Runs the create_question_graph Django management command with --yes flag
- Automatically continues processing even if some files fail
- Tracks processing time for each file
- Moves successfully processed files to already_imported/ folder
- Moves failed files to error_import/ folder with detailed error logs
- Displays progress messages and status for each file
- Shows comprehensive summary statistics at the end

Usage:
    python batch_import_questions.py

Requirements:
- Django project with create_question_graph management command
- Neo4j database connection configured
- JSON files in question_json/ directory
"""

from pathlib import Path
import sys
import subprocess
import shutil
from datetime import datetime
import time


def main():
    """Main function to process all JSON files."""
    # Folder where manage.py lives
    PROJECT_DIR = Path(r"/Users/puttisanaekkapornpisan/Projects/ez_ram")
    MANAGE_PY = PROJECT_DIR / "manage.py"

    # Directory containing JSON files
    JSON_DIR = Path(r"/Users/puttisanaekkapornpisan/Projects/ez_ram/question_json")

    # Create organization folders
    ALREADY_IMPORTED_DIR = JSON_DIR / "already_imported"
    ERROR_IMPORT_DIR = JSON_DIR / "error_import"

    # Create folders if they don't exist
    ALREADY_IMPORTED_DIR.mkdir(exist_ok=True)
    ERROR_IMPORT_DIR.mkdir(exist_ok=True)

    print(f"📁 Organization folders ready:")
    print(f"   ✓ {ALREADY_IMPORTED_DIR}")
    print(f"   ✓ {ERROR_IMPORT_DIR}\n")

    # Get all JSON files in the main directory (excluding subdirectories)
    json_files = sorted([f for f in JSON_DIR.glob("*.json") if f.is_file()])
    total_files = len(json_files)

    if total_files == 0:
        print(f"No JSON files found in {JSON_DIR}")
        print(f"All files may have already been processed.")
        return

    print(f"Found {total_files} JSON file(s) to process\n")

    # Track statistics
    successful_count = 0
    error_count = 0

    for index, json_file in enumerate(json_files, start=1):
        print(f"\n{'='*60}")
        print(f"Processing file {index} of {total_files}: {json_file.name}")
        print(f"{'='*60}\n")

        # Start timing for this file
        start_time = time.time()

        # Set INPUT_DIR to current file
        INPUT_DIR = json_file

        cmd = [
            sys.executable,          # use the current Python (works with your venv)
            str(MANAGE_PY),
            "create_question_graph",
            "--file",
            str(INPUT_DIR),
            "--yes",  # Skip confirmation prompt
        ]

        try:
            # Run with the working dir set to the project so manage.py resolves settings
            subprocess.run(cmd, check=True, cwd=PROJECT_DIR)

            # Calculate processing time
            elapsed_time = time.time() - start_time

            print(f"\n✓ Successfully processed: {json_file.name}")
            print(f"⏱️  Processing time: {elapsed_time:.2f} seconds")
            print(f"📊 Status: FINISHED")

            # Move file to already_imported folder
            destination = ALREADY_IMPORTED_DIR / json_file.name
            shutil.move(str(json_file), str(destination))
            print(f"📦 Moved to: already_imported/{json_file.name}")
            successful_count += 1

        except subprocess.CalledProcessError as e:
            # Calculate processing time even for errors
            elapsed_time = time.time() - start_time

            print(f"\n✗ Error processing {json_file.name}")
            print(f"   Error details: {e}")
            print(f"⏱️  Processing time: {elapsed_time:.2f} seconds")
            print(f"📊 Status: FAILED")

            # Move file to error_import folder
            destination = ERROR_IMPORT_DIR / json_file.name
            shutil.move(str(json_file), str(destination))
            print(f"📦 Moved to: error_import/{json_file.name}")

            # Create error log file
            error_log_path = ERROR_IMPORT_DIR / f"{json_file.stem}_error.log"
            with open(error_log_path, 'w') as log_file:
                log_file.write(f"Error Log for: {json_file.name}\n")
                log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
                log_file.write(f"Processing time: {elapsed_time:.2f} seconds\n")
                log_file.write(f"{'='*60}\n\n")
                log_file.write(f"Command executed:\n")
                log_file.write(f"{' '.join(cmd)}\n\n")
                log_file.write(f"Error:\n")
                log_file.write(f"{str(e)}\n\n")
                log_file.write(f"Return code: {e.returncode}\n")
            print(f"📝 Error log created: {error_log_path.name}")
            error_count += 1

            # Continue to next file automatically (no user prompt)
            print(f"🔄 Continuing to next file...\n")
            continue

    # All files processed
    print(f"\n{'='*60}")
    print(f"All {total_files} files have been processed!")
    print(f"{'='*60}")

    # Print summary statistics
    print(f"\n\n{'='*60}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"✓ Successfully imported: {successful_count} file(s)")
    print(f"✗ Failed imports: {error_count} file(s)")
    print(f"Total processed: {successful_count + error_count} of {total_files}")
    print(f"{'='*60}")
    print(f"\n📂 Check folders:")
    print(f"   • already_imported/ - {successful_count} file(s)")
    print(f"   • error_import/ - {error_count} file(s)")


if __name__ == "__main__":
    main()

