import requests
import json

# --- Configuration with Pinata Credentials ---
PINATA_API_KEY = "465a11f9bea9c377eb98"
PINATA_SECRET_API_KEY = "1ba9ed8912bd4028b35322386eda900cc360c897cdade3763536c384dfec4911"

# Pinata IPFS Upload Endpoint for JSON data
PINATA_IPFS_UPLOAD_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

# Public IPFS Gateway (Working for retrieval)
IPFS_GATEWAY_URL = "https://ipfs.io/ipfs/{content ID}"

def pin_to_ipfs(data):
  assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
  #YOUR CODE HERE

  # Convert the Python dictionary to JSON
  json_data = json.dumps(data)
  
  # Pinata requires the JSON data to be sent directly in the request body
  # with specific headers for authentication.
  headers = {
      'Content-Type': 'application/json',
      # Pinata uses custom header names for API key authentication
      'pinata_api_key': PINATA_API_KEY,
      'pinata_secret_api_key': PINATA_SECRET_API_KEY
  }
  
  # The request sends the JSON string in the 'data' parameter, using the headers for authentication
  response = requests.post(PINATA_IPFS_UPLOAD_URL, data=json_data, headers=headers)
  response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

  # Pinata's response is JSON and contains the CID in the 'IpfsHash' field
  cid = response.json()['IpfsHash']

  return cid

def get_from_ipfs(cid,content_type="json"):
  assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
  #YOUR CODE HERE 

  # Construct the retrieval URL using the working public gateway
  url = IPFS_GATEWAY_URL.replace("{content ID}", cid)

  # Use a simple GET request to retrieve the content
  response = requests.get(url)
  response.raise_for_status() 

  # The content is returned as a JSON string; convert it to a Python dictionary
  data = response.json()

  assert isinstance(data,dict), f"get_from_ipfs should return a dict"
  return data
