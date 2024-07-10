import os
import pandas as pd
import datetime
import schedule
import time
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
import zipfile
import pytz  # Import pytz for timezone handling

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

# Initialize the Slack client
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

# Define your timezone, for example, 'America/New_York'
TIMEZONE = 'America/Chicago'
local_tz = pytz.timezone(TIMEZONE)

def join_channel(channel_id):
    try:
        response = client.conversations_join(channel=channel_id)
        if response["ok"]:
            logging.info(f"Joined channel {channel_id} successfully.")
        else:
            logging.error(f"Failed to join channel {channel_id}: {response['error']}")
    except SlackApiError as e:
        logging.error(f"Error joining channel {channel_id}: {e.response['error']}")

def fetch_messages(channel_id, start_time=None, end_time=None):
    messages = []
    try:
        if start_time and end_time:
            response = client.conversations_history(channel=channel_id, oldest=start_time, latest=end_time)
        else:
            response = client.conversations_history(channel=channel_id)

        if not response['ok']:
            logging.error(f"Error in fetching messages: {response['error']}")
        else:
            messages.extend(response['messages'])
            logging.debug(f"Fetched {len(response['messages'])} messages from channel {channel_id}.")
            logging.debug(f"Messages: {response['messages']}")
    except SlackApiError as e:
        logging.error(f"Error fetching messages from {channel_id}: {e.response['error']}")
    return messages

def fetch_all_channels():
    channels = []
    try:
        response = client.conversations_list(types="public_channel,private_channel")
        if response["ok"]:
            channels.extend(response['channels'])
        else:
            logging.error(f"Error fetching channels: {response['error']}")
    except SlackApiError as e:
        logging.error(f"Error fetching channels: {e.response['error']}")
    return channels

def download_file(file_info, date_time, user_name):
    formatted_time = date_time.strftime('%Y-%m-%d_%H-%M')
    file_name = f"{formatted_time}_{user_name}_{file_info['name']}"
    file_path = os.path.join("media", file_name)

    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))

    headers = {'Authorization': 'Bearer ' + os.getenv('SLACK_BOT_TOKEN')}
    response = requests.get(file_info['url_private'], headers=headers, stream=True)

    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        logging.info(f"File downloaded successfully: {file_path}")
        return file_path
    else:
        logging.error(f"Failed to download file: {response.status_code} - {response.text}")
        return None

def open_dm_channel(user_id):
    try:
        response = client.conversations_open(users=[user_id])
        if response["ok"]:
            return response["channel"]["id"]
        else:
            logging.error(f"Error opening DM channel with user {user_id}: {response['error']}")
            return None
    except SlackApiError as e:
        logging.error(f"Error opening DM channel with user {user_id}: {e.response['error']}")
        return None

def get_user_name(user_id):
    try:
        response = client.users_info(user=user_id)
        if response["ok"]:
            return response["user"]["real_name"]
        else:
            logging.error(f"Error fetching user info for {user_id}: {response['error']}")
            return user_id
    except SlackApiError as e:
        logging.error(f"Error fetching user info for {user_id}: {e.response['error']}")
        return user_id

def get_workspace_name():
    try:
        response = client.team_info()
        if response["ok"]:
            return response['team']['name']
        else:
            logging.error(f"Error fetching workspace info: {response['error']}")
            return "workspace"
    except SlackApiError as e:
        logging.error(f"Error fetching workspace info: {e.response['error']}")
        return "workspace"

def zip_media_files(files_to_zip):
    media_directory = "media"  # Define the media directory
    if not os.path.exists(media_directory):
        os.makedirs(media_directory)  # Create the media directory if it does not exist

    zip_filename = "media_files.zip"
    zip_path = os.path.join(media_directory, zip_filename)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in files_to_zip:
            arcname = os.path.basename(file_path)
            zipf.write(file_path, arcname=arcname)
    return zip_path

def archive_messages():
    now = datetime.datetime.now(local_tz)
    first_day_of_current_month = now.replace(day=1)
    last_month_end = first_day_of_current_month - datetime.timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1)

    # Use accurate timestamps for the last month
    start_time = (now - datetime.timedelta(days=30)).timestamp()
    end_time = now.timestamp()

    logging.info("Fetching channels...")
    channels = fetch_all_channels()
    all_messages = []
    files_to_zip = []

    for channel in channels:
        channel_id = channel['id']
        channel_name = channel['name']
        join_channel(channel_id)
        messages = fetch_messages(channel_id, start_time, end_time)
        for message in messages:
            date_time = datetime.datetime.fromtimestamp(float(message['ts']), local_tz)
            user = message.get('user', 'N/A')
            text = message.get('text', 'N/A')  # Default to 'N/A' if no text is present
            files = message.get('files', [])
            user_name = get_user_name(user)
            file_paths = []

            if files:
                for file in files:
                    file_path = download_file(file, date_time, user_name)
                    file_paths.append(file_path)  # Collect file paths to zip later
                    files_to_zip.append(file_path)  # Add the file path to the list for zipping
            else:
                file_paths.append('No File')  # Indicate no file in the file path list for this message

            # Append a list containing message details, whether or not files are present
            all_messages.append([
                date_time.strftime('%m-%d-%Y'), date_time.strftime('%H:%M'), 
                user_name, text, channel_name, ', '.join(file_paths)
            ])

    if all_messages:
        df = pd.DataFrame(all_messages, columns=['Date', 'Time', 'User', 'Message', 'Channel', 'File Path'])
        workspace_name = get_workspace_name()
        file_name = f"{workspace_name}_{last_month_start.strftime('%Y_%m')}.csv"
        df.to_csv(file_name, index=False)
        # Create a zip file of only the relevant media files
        zip_path = zip_media_files(files_to_zip)  

        # Send CSV and zip file via Slack DM
        user_id = os.getenv('SLACK_ARCHIVE_USER_ID')
        dm_channel_id = open_dm_channel(user_id)
        if dm_channel_id:
            try:
                # Send CSV
                with open(file_name, "rb") as file_content:
                    client.files_upload_v2(file=file_content, filename=file_name, title=file_name, initial_comment="Monthly archive CSV.", channel=dm_channel_id)
                # Send zip file
                with open(zip_path, "rb") as zip_content:
                    client.files_upload_v2(file=zip_content, filename=os.path.basename(zip_path), title="Media files archive.", initial_comment="Attached zip file contains all media files from the specified month.", channel=dm_channel_id)
            except SlackApiError as e:
                logging.error(f"Error uploading files: {e.response['error']}")

def run_manual_test():
    logging.info("Running manual test...")
    archive_messages()

def schedule_monthly_task():
    now = datetime.datetime.now(local_tz)
    if now.day == 1 and now.hour == 0:
        archive_messages()

if __name__ == "__main__":
    # Uncomment the next line to run a manual test
    # run_manual_test()

    # Schedule the task to run every hour and check for the first day of the month at midnight
    schedule.every().hour.at(":00").do(schedule_monthly_task)

    while True:
        schedule.run_pending()
        time.sleep(60)
