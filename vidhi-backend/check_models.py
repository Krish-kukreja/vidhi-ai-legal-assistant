import os
import json
from dotenv import load_dotenv
import boto3

load_dotenv()

client = boto3.client('bedrock', region_name='ap-south-1', 
                      aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'), 
                      aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

response = client.list_foundation_models()
models = []
for m in response['modelSummaries']:
    if 'titan' in m['modelId'].lower() or 'embed' in m['modelId'].lower() or 'claude' in m['modelId'].lower():
        models.append(m['modelId'])

with open("models.json", "w", encoding="utf-8") as f:
    json.dump({"models": models}, f)
