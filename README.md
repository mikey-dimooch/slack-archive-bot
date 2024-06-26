Slack Archiving Bot
Overview
The Slack Archiving Bot is a Python script that automatically archives messages from all channels in a Slack workspace and stores them in a CSV file. The CSV file is then sent to a specified user via a direct message (DM) on Slack. This script is scheduled to run daily and perform the archiving task on the first day of each month.
Features
  Automatically joins channels to fetch messages.
  Archives messages from all public and private channels.
  Saves messages to a CSV file with the date, time, user, message content, and channel name.
  Sends the CSV file to a specified user via DM.
  Logs all operations for easy debugging and monitoring.
  Requirements
Python 3.x
Slack API Token with the necessary permissions:
  channels:history
  channels:read
  chat:write
  files:write
  groups:history
  groups:read
  im:history
  im:write
  users:read
  team:read
Required Python libraries: slack_sdk, pandas, requests, schedule


Installation
Clone this repository:

git clone https://github.com/mikey-dimooch/slack-archive-bot.git
cd <repository_directory>


Install the required Python libraries:

pip install slack_sdk pandas requests schedule


Set the necessary environment variables:

export SLACK_BOT_TOKEN=<your_slack_bot_token>
export SLACK_ARCHIVE_USER_ID=<slack_archive_user_id>


Configuration
  Ensure the Slack API token and the Slack user ID for receiving the archive are set as environment variables:
  SLACK_BOT_TOKEN: The token for your Slack bot.
  SLACK_ARCHIVE_USER_ID: The user ID of the Slack user who will receive the CSV file.
Usage
  Manual Testing
  To manually test the script and verify it works correctly, you can run it directly:
  python your_script.py



Scheduling
  The script uses the schedule library to run daily and check if it's the first day of the month to perform the archiving task. For the scheduling to work, the script needs to be continuously running. You can achieve this by running it in the background or setting it up as a service.
  Running in the Background (Linux/Mac)
  You can use nohup to run the script in the background:
  nohup python your_script.py &

Running as a Service (Linux)
To run the script as a service, create a systemd service file:
Create a service file:
sudo nano /etc/systemd/system/slack_archive.service


Add the following content to the file:
[Unit]
Description=Slack Archive Service

[Service]
ExecStart=/usr/bin/python3 /path/to/your_script.py
Restart=always
User=your_username
Environment="SLACK_BOT_TOKEN=<your_slack_bot_token>"
Environment="SLACK_ARCHIVE_USER_ID=<slack_archive_user_id>"

Replace /path/to/your_script.py with the actual path to your script and your_username with your username.
Enable and start the service:
sudo systemctl enable slack_archive
sudo systemctl start slack_archive


Logging
  The script logs all operations, which can help in debugging and monitoring the process. The logs will show:
  Channel joining status
  Message fetching details
  CSV creation status
  File uploading status
Troubleshooting
  No messages fetched: Ensure the time range is correct and there are messages in that range. Check if the bot has the necessary permissions to read messages from the channels.
  CSV file not created: If no messages are fetched, the CSV file will not be created. Verify the logs for any errors or warnings.
  Error uploading file: Check the logs for specific Slack API errors and ensure the bot has the files:write permission.
  Bot not joining channels: Ensure the bot has the channels:join and groups:read permissions.
Contributing
  Contributions are welcome! Please create a pull request or open an issue for any improvements or bug fixes.
License
  This project is licensed under the MIT License.
