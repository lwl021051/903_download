import requests
import os
import time
from datetime import datetime
from urllib.parse import urlparse


def fetch_and_combine_last_audio(api_url, combined_file_path, processed_files):
    """
    Fetch the last audio file from the API, download it, combine it into the current period file,
    and delete the temporary .aac file.

    :param api_url: URL of the API returning the m3u8 data.
    :param combined_file_path: Path to the combined audio file for the current period.
    :param processed_files: Set of already processed (downloaded and combined) files.
    """
    try:
        # Derive the base URL dynamically
        parsed_url = urlparse(api_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{os.path.dirname(parsed_url.path)}/"

        # Fetch the playlist
        response = requests.get(api_url)
        response.raise_for_status()
        lines = response.text.splitlines()
        audio_urls = [line for line in lines if ".aac" in line]

        if not audio_urls:
            print("No audio URLs found in the playlist.")
            return

        # Get the last .aac file in the playlist
        last_url = audio_urls[-1]
        timestamp = last_url.split('_')[2].split('.')[0]
        file_name = f"audio_{timestamp}.aac"

        # Skip if the file has already been processed
        if file_name in processed_files:
            print(f"Skipping already processed file: {file_name}")
            return

        # Download the last file
        try:
            response = requests.get(f"{base_url}{last_url}", stream=True)
            response.raise_for_status()
            temp_file_path = os.path.join("temp", file_name)

            # Ensure temp directory exists
            os.makedirs("temp", exist_ok=True)

            # Save the downloaded file temporarily
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(response.content)

            print(f"Downloaded: {file_name}")

            # Append to the combined file
            with open(temp_file_path, "rb") as temp_file:
                with open(combined_file_path, "ab") as combined_file:
                    combined_file.write(temp_file.read())

            print(f"Appended {file_name} to {combined_file_path}")

            # Mark as processed and delete the temp file
            processed_files.add(file_name)
            os.remove(temp_file_path)

        except requests.RequestException as e:
            print(f"Failed to download {last_url}: {e}")

    except requests.RequestException as e:
        print(f"Error fetching playlist: {e}")


def load_schedule_conf(schedule_file):
    """
    Load the schedule configuration from a file.

    :param schedule_file: Path to the schedule configuration file.
    :return: List of schedule periods (start_time, end_time).
    """
    if not os.path.exists(schedule_file):
        print(f"Schedule file '{schedule_file}' not found.")
        return []

    schedule = []
    try:
        with open(schedule_file, "r") as f:
            for line in f:
                # Expecting lines in the format: "HH:MM-HH:MM"
                parts = line.strip().split('-')
                if len(parts) == 2:
                    start_time = datetime.strptime(parts[0], "%H:%M").time()
                    end_time = datetime.strptime(parts[1], "%H:%M").time()
                    schedule.append((start_time, end_time))
    except Exception as e:
        print(f"Failed to load schedule: {e}")

    return schedule


def get_current_period(schedule):
    """
    Determine the current period based on the schedule.

    :param schedule: List of (start_time, end_time) tuples.
    :return: The current period tuple (start_time, end_time) or None if no period is active.
    """
    current_time = datetime.now().time()
    for start, end in schedule:
        if start <= end:  # Normal period (e.g., 10:00-12:00)
            if start <= current_time <= end:
                return start, end
        else:  # Wrap-around period (e.g., 22:00-00:00)
            if current_time >= start or current_time <= end:
                return start, end
    return None


def load_api_url(api_file):
    """
    Load the API URL from a file.

    :param api_file: Path to the file containing the API URL.
    :return: The API URL as a string.
    """
    if not os.path.exists(api_file):
        print(f"API file '{api_file}' not found.")
        return None

    try:
        with open(api_file, "r") as f:
            return f.readline().strip()
    except Exception as e:
        print(f"Failed to load API URL: {e}")
        return None


# Configuration
OUTPUT_DIR = "sound"  # Relative path to sound folder
SCHEDULE_FILE = "schedule.txt"  # Relative path to schedule file
API_FILE = "api_link.txt"  # Relative path to the file containing the API URL
PROCESSED_FILES = set()

# Keep track of the current period and file
current_period = None
current_combined_file = None

while True:
    # Load the schedule
    schedule = load_schedule_conf(SCHEDULE_FILE)

    # Load the API URL
    API_URL = load_api_url(API_FILE)
    if not API_URL:
        print("No valid API URL. Waiting...")
        time.sleep(10)
        continue

    # Determine the current period
    period = get_current_period(schedule)

    if period != current_period:
        # If the period has changed, start a new combined file
        current_period = period
        if current_period:
            today_date = datetime.now().strftime("%Y%m%d")
            current_combined_file = os.path.join(
                OUTPUT_DIR,
                f"combined_{today_date}_{current_period[0].strftime('%H%M')}_{current_period[1].strftime('%H%M')}.aac"
            )
            print(f"New period detected: {current_period}. Combined file: {current_combined_file}")

    if current_period:
        # Fetch the last file and combine it
        fetch_and_combine_last_audio(API_URL, current_combined_file, PROCESSED_FILES)
    else:
        print("No active period. Waiting...")

    time.sleep(10)
