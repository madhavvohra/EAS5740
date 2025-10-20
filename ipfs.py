import requests
import json
import time


PINATA_API_KEY = "465a11f9bea9c377eb98"
PINATA_SECRET_API_KEY = "1ba9ed8912bd4028b35322386eda900cc360c897cdade3763536c384dfec4911"

PINATA_IPFS_UPLOAD_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

IPFS_GATEWAY_URL = "https://ipfs.io/ipfs/{content ID}"

def pin_to_ipfs(data):
  assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
  #YOUR CODE HERE

  json_data = json.dumps(data)
  
  headers = {
      'Content-Type': 'application/json',
      'pinata_api_key': PINATA_API_KEY,
      'pinata_secret_api_key': PINATA_SECRET_API_KEY
  }
  
  response = requests.post(PINATA_IPFS_UPLOAD_URL, data=json_data, headers=headers)
  response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

  cid = response.json()['IpfsHash']

  return cid

def get_from_ipfs(cid,content_type="json"):
  assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
  #YOUR CODE HEREE
	
  time.sleep(10)

  url = IPFS_GATEWAY_URL.replace("{content ID}", cid)

  response = requests.get(url)
  response.raise_for_status() 

  data = response.json()

  assert isinstance(data,dict), f"get_from_ipfs should return a dict"
  return data
