# pipeline_08_push_to_hf.py
# Pushes new clean monthly CSV files to Hugging Face dataset repo
# Called automatically by run_pipeline.py after processing new data
# Also pushes pipeline_state.json so the app can read it

import os
import sys
import json
import re
from datetime import datetime
from huggingface_hub import HfApi, upload_file, list_repo_files

# ── CONFIG ────────────────────────────────────────────────────────────────────

HF_REPO_ID  = "Babbi21SA/airline-otp-data"
HF_REPO_TYPE = "dataset"

CLEAN_DIR   = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Clean"
STATE_FILE  = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\pipeline_state.json"

MONTH_NAMES = {
    1:'January', 2:'February', 3:'March', 4:'April',
    5:'May', 6:'June', 7:'July', 8:'August',
    9:'September', 10:'October', 11:'November', 12:'December'
}


def get_local_clean_files():
    """List all local clean files."""
    files = []
    for f in sorted(os.listdir(CLEAN_DIR)):
        if f.startswith('OTP_') and f.endswith('.csv'):
            files.append(f)
    return files


def get_hf_files():
    """List files already on Hugging Face."""
    try:
        api = HfApi()
        hf_files = list(list_repo_files(HF_REPO_ID, repo_type=HF_REPO_TYPE))
        return set(hf_files)
    except Exception as e:
        print(f"  Warning — could not list HF files: {e}")
        return set()


def push_file(local_path, filename):
    """Push one file to Hugging Face."""
    try:
        upload_file(
            path_or_fileobj=local_path,
            path_in_repo=f"Data/Clean/{filename}",
            repo_id=HF_REPO_ID,
            repo_type=HF_REPO_TYPE,
        )
        return True
    except Exception as e:
        print(f"  Error pushing {filename}: {e}")
        return False


def push_state_file():
    """Push pipeline state JSON to HF so app can read it."""
    if not os.path.exists(STATE_FILE):
        return
    try:
        upload_file(
            path_or_fileobj=STATE_FILE,
            path_in_repo="Data/pipeline_state.json",
            repo_id=HF_REPO_ID,
            repo_type=HF_REPO_TYPE,
        )
        print("  State file pushed to HF")
    except Exception as e:
        print(f"  Warning — could not push state file: {e}")


def main():
    print()
    print("=" * 60)
    print("  PUSH TO HUGGING FACE")
    print("=" * 60)
    print(f"  Repo: {HF_REPO_ID}")
    print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    local_files  = get_local_clean_files()
    hf_files     = get_hf_files()

    print(f"  Local clean files : {len(local_files)}")
    print(f"  Already on HF     : {len([f for f in hf_files if 'Clean' in f])}")

    # Find files that need pushing
    to_push = []
    for filename in local_files:
        hf_path = f"Data/Clean/{filename}"
        if hf_path not in hf_files:
            to_push.append(filename)

    print(f"  Files to push     : {len(to_push)}")
    print()

    if not to_push:
        print("  HF dataset is already up to date.")
        push_state_file()
        print()
        print("  Done.")
        return

    success_count = 0
    fail_count    = 0

    for i, filename in enumerate(to_push, 1):
        local_path = os.path.join(CLEAN_DIR, filename)
        size_mb = os.path.getsize(local_path) / 1024 / 1024
        print(f"  [{i}/{len(to_push)}] Pushing {filename} ({size_mb:.1f} MB)...")
        success = push_file(local_path, filename)
        if success:
            success_count += 1
            print(f"    Done")
        else:
            fail_count += 1

    push_state_file()

    print()
    print("=" * 60)
    print("  PUSH COMPLETE")
    print("=" * 60)
    print(f"  Successful : {success_count}")
    print(f"  Failed     : {fail_count}")
    print(f"  HF repo    : https://huggingface.co/datasets/{HF_REPO_ID}")
    print()


if __name__ == '__main__':
    main()