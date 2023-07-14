import slack
import config
import os
import json
import requests
import csv
from io import StringIO


def lambda_handler(event, context):
    
    raw_event = json.loads(event['Records'][0]['body'])
    
    slack_event = json.loads(raw_event['body'])

    print(f"Event body check: {slack_event}")

    if'bot_id' not in slack_event['event']:
	    
	    # Instantiate a Web API client
	    client = slack.WebClient(token=config.BOT_USER_TOKEN)
	    
	    # Extract the channel ID
	    channel_id = slack_event['event']['channel']
	    
	    client.chat_postMessage(
	            channel=channel_id,
	            text="Processing..."
	        )
	    
	    # Check if the event contains a file
	    if 'files' in slack_event['event']:
	        # The message contains a file
	        file_info = slack_event['event']['files'][0]
	        download_url = file_info['url_private_download']
	        
	        # Download the file
	        response = requests.get(download_url, headers={'Authorization': 'Bearer ' + config.BOT_USER_TOKEN})
	        response.raise_for_status()
	        
	        # Parse the CSV contents
	        csv_file = StringIO(response.text)
	        csv_reader = csv.reader(csv_file)
	        next(csv_reader, None)  # Skip the header
	        order_numbers = [row[0] for row in csv_reader]  # Use the first column
	    else:
	        # Extract the message text
	        message_text = slack_event['event']['text']
	        order_numbers = parse_message(message_text)
	    
	    print(f"Order numbers check: {order_numbers}")
	    
	    payload = {
	        "orders": order_numbers
	    }

	    # Send POST request
	    response = requests.post(
	        config.endpoint,
	        data=json.dumps(payload),
	        headers={"Content-Type": "application/json"}
	    )

	    response_data = response.json()

	    if response.status_code == 200:
	        # Send a message with the order processing results
	        client.chat_postMessage(
	            channel=channel_id,
	            text=f"Order numbers processed! Results:\n"
	                 f"Succeeded on {len(response_data['success'])} orders: {response_data['success']}\n"
	                 f"Difference between full list and success list is {len(response_data['differences'])} order(s): {response_data['differences']}\n"
	                 f"Failed on {len(response_data['failed'])} orders: {response_data['failed']}\n"
	                 f"Rate-limited on {len(response_data['rate_limited'])} orders: {response_data['rate_limited']}"
	        )
	    else:
	        print(f"Error {response.status_code} sending message: {response.text}")
    return


def parse_message(message_text):
    
    message_text = message_text.strip()
    order_numbers = []

    if "•" in message_text:
        # Message is a bulleted list
        order_numbers = [line.strip()[1:].strip() for line in message_text.split("\n") if line.strip().startswith("•")]
    elif "," in message_text:
        # Message is a comma-separated string
        order_numbers = [part.strip() for part in message_text.split(",")]
    else:
        # Message is a single number
        order_numbers = [message_text]

    # Clean the order numbers: if the number begins with '#', remove it
    order_numbers = [num[1:] if num.startswith("#") else num for num in order_numbers]

    return order_numbers
