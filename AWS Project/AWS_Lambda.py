#( modify the code according to how you have named your DB Table and your S3 bucket and how you want your data to be saved in a csv file)
import boto3
import csv
from io import StringIO
import re

def parse_consumption_raw(consumption_raw_str):
    # Use regular expressions to extract relevant data
    timestamp_match = re.search(r'(\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', consumption_raw_str)
    flow_rate_match = re.search(r'FLOW: ([\d.]+) m3/h', consumption_raw_str)
    today_m3_match = re.search(r'TODAY ([\d.]+) m3', consumption_raw_str)

    timestamp = timestamp_match.group(1) if timestamp_match else ''
    flow_rate = flow_rate_match.group(1) if flow_rate_match else ''
    today_m3 = today_m3_match.group(1) if today_m3_match else ''

    return timestamp, flow_rate, today_m3

def lambda_handler(event, context):
    # Define the source table and S3 bucket information
    source_table_name = "WATER-USUAGE"
    s3_bucket_name = "exports-thata"
    s3_key = "transformed_data/09/04/transformed_data.csv"  # Set your desired path here

    # Initialize AWS clients
    dynamodb_client = boto3.client('dynamodb')
    s3_client = boto3.client('s3')

    # Scan the DynamoDB table
    response = dynamodb_client.scan(
        TableName=source_table_name
    )

    # Extract data from the DynamoDB response
    data = response.get("Items", [])

    # Transform the data into a CSV format
    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)

    # Write the CSV header with additional columns
    csv_writer.writerow(["DATA:", "Timestamp", "FLOW RATE (m3/h)", "Daily Usage (m3)"])  # Renamed column header

    # Iterate through the DynamoDB data and write to CSV
    for item in data:
        data_value = item.get("DATA:", {}).get("S", "")
        time_value = item.get("TIME", {}).get("N", "")
        consumption_raw_value = item.get("CONSUMPTION_raw", {}).get("B", b'')

        # Attempt to decode using 'latin-1' encoding
        try:
            consumption_raw_str = consumption_raw_value.decode('latin-1')
        except UnicodeDecodeError:
            consumption_raw_str = "Unable to decode"

        timestamp, flow_rate, today_m3 = parse_consumption_raw(consumption_raw_str)

        csv_writer.writerow([data_value, timestamp, flow_rate, today_m3])

    # Upload the transformed data to S3
    s3_client.put_object(
        Bucket=s3_bucket_name,
        Key=s3_key,
        Body=csv_data.getvalue()
    )

    return {
        "statusCode": 200,
        "body": "Data transformation and upload to S3 successful."
    }
