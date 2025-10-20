import requests
import json
import base64 # <-- Added for explicit Base64 authentication

# --- Configuration with Your Credentials ---
INFURA_PROJECT_ID = "155d356f9c664c86b0f76bdd4cf3a362"
INFURA_PROJECT_SECRET = "jHeJ6AV8QfloPuusDT19gMVV3TwK3EzfZJ22UqFwBiC8WSD2v2hIeQ"

# Infura IPFS Upload Endpoint
INFURA_IPFS_UPLOAD_URL = "https://ipfs.infura.io:5001/api/v0/add"

# Public IPFS Gateway (SWITCHED TO IPFS.IO)
IPFS_GATEWAY_URL = "https://ipfs.io/ipfs/{content ID}"

def pin_to_ipfs(data):
  assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
  #YOUR CODE HERE

  # Convert the Python dictionary to a JSON string
  json_data = json.dumps(data)
  
  # Explicitly format credentials for Basic Authentication header
  credentials = f"{INFURA_PROJECT_ID}:{INFURA_PROJECT_SECRET}"
  encoded_credentials = base64.b64encode(credentials.encode()).decode()
  
  headers = {
      'Authorization': f'Basic {encoded_credentials}'
  }
  
  # Prepare the data as a file-like object for the POST request
  files = {
      'file': ('data.json', json_data, 'application/json')
  }
  
  # Send the request using the custom headers
  response = requests.post(INFURA_IPFS_UPLOAD_URL, files=files, headers=headers)
  response.raise_for_status() 

  # The response is JSON and contains the Hash (CID)
  cid = response.json()['Hash']

  return cid

def get_from_ipfs(cid,content_type="json"):
  assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
  #YOUR CODE HERE 

  # Construct the retrieval URL using the new ipfs.io public gateway
  url = IPFS_GATEWAY_URL.replace("{content ID}", cid)

  # Use a simple GET request to retrieve the content
  response = requests.get(url)
  response.raise_for_status() # Raise an exception for bad status codes

  # The content is returned as a JSON string; convert it to a Python dictionary
  data = response.json()

  assert isinstance(data,dict), f"get_from_ipfs should return a dict"
  return data
