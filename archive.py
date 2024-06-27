import os
import pandas as pd
import datetime
import schedule
import time
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

# Initialize the Slack client
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

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

def download_file(file_info):
    url = file_info['url_private']
    headers = {'Authorization': 'Bearer ' + os.getenv('SLACK_BOT_TOKEN')}
    response = requests.get(url, headers=headers)
    file_path = os.path.join("media", file_info['name'])
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(response.content)
    return file_path

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

def archive_messages():
    now = datetime.datetime.now()
    first_day_of_current_month = now.replace(day=1)
    last_month_end = first_day_of_current_month - datetime.timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1)

    # For debugging, set start_time and end_time to a recent period
    start_time = (now - datetime.timedelta(days=10)).timestamp()
    end_time = now.timestamp()


    # uncomment these when ready to run 
    # start_time = last_month_start.timestamp()
    # end_time = last_month_end.timestamp()

    logging.info("Fetching channels...")
    channels = fetch_all_channels()
    all_messages = []

    for channel in channels:
        channel_id = channel['id']
        channel_name = channel['name']
        logging.info(f"Ensuring membership in channel: {channel_name}")
        join_channel(channel_id)
        logging.info(f"Fetching messages from channel: {channel_name}")
        messages = fetch_messages(channel_id, start_time, end_time)
        for message in messages:
            date_time = datetime.datetime.fromtimestamp(float(message['ts']))
            user = message.get('user', 'N/A')
            text = message.get('text', 'N/A')
            files = message.get('files', [])
            user_name = get_user_name(user)
            if files:
                for file in files:
                    file_path = download_file(file)
                    all_messages.append([date_time.strftime('%m-%d-%Y'), date_time.strftime('%H:%M'), user_name, file['name'], channel_name])
            else:
                all_messages.append([date_time.strftime('%m-%d-%Y'), date_time.strftime('%H:%M'), user_name, text, channel_name])
            logging.debug(f"Processed message: {message}")

    logging.debug(f"Total messages fetched: {len(all_messages)}")
    
    if all_messages:
        df = pd.DataFrame(all_messages, columns=['Date', 'Time', 'User', 'Message', 'Channel'])
        workspace_name = get_workspace_name()
        file_name = f"{workspace_name}_{last_month_start.strftime('%Y_%m')}.csv"
        df.to_csv(file_name, index=False)
        logging.info(f"CSV file {file_name} created successfully.")

        # Send the file via DM using files_upload_v2
        user_id = os.getenv('SLACK_ARCHIVE_USER_ID')
        dm_channel_id = open_dm_channel(user_id)
        if dm_channel_id:
            try:
                with open(file_name, "rb") as file_content:
                    upload_response = client.files_upload_v2(
                        file=file_content,
                        filename=file_name,
                        title=file_name,
                        initial_comment="Here is the monthly archive.",
                        channel=dm_channel_id
                    )
                logging.info(f"Archive file {file_name} sent to user {user_id} via channel {dm_channel_id}")
            except SlackApiError as e:
                logging.error(f"Error uploading file: {e.response['error']}")
    else:
        logging.info("No messages fetched, skipping CSV creation.")

def run_manual_test():
    logging.info("Running manual test...")
    archive_messages()

def schedule_monthly_task():
    if datetime.datetime.now().day == 1:
        archive_messages()

if __name__ == "__main__":
    # Uncomment the next line to run a manual test
    run_manual_test()

    # Schedule the task to run daily and check for the first day of the month
    schedule.every().day.at("00:00").do(schedule_monthly_task)

    while True:
        schedule.run_pending()
        time.sleep(60)