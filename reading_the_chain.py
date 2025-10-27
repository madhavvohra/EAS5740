import random
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider

ETH_MAINNET_URL = "https://eth-mainnet.g.alchemy.com/v2/MmEXl5ITY4yo6sSOr6sNj"
BNB_TESTNET_URL = "https://bnb-testnet.g.alchemy.com/v2/MmEXl5ITY4yo6sSOr6sNj" 

# If you use one of the suggested infrastructure providers, the url will be of the form
# now_url  = f"https://eth.nownodes.io/{now_token}"
# alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"
# infura_url = f"https://mainnet.infura.io/v3/{infura_token}"

def connect_to_eth():
  # TODO insert your code for this method from last week's assignment
  url = ETH_MAINNET_URL
  w3 = Web3(HTTPProvider(url))
  assert w3.is_connected(), f"Failed to connect to provider at {url}"
  return w3


def connect_with_middleware(contract_json_file):
  # TODO insert your code for this method from last week's assignment
  url = BNB_TESTNET_URL

  w3 = Web3(HTTPProvider(url))
  w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
  
  assert w3.is_connected(), f"Failed to connect to BNB Testnet at {url}"

  with open(contract_json_file, "r") as f:
      d = json.load(f)
      d = d['bsc']
      address = d['address']
      abi = d['abi']

  contract = w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)
  
  return w3, contract

def calculate_priority_fee(tx, base_fee_per_gas):
    """
    Helper function to calculate the actual priority fee paid based on EIP-1559 rules.
    This logic is required inside is_ordered_block.
    """
    if tx.get('type') == 2 or ('maxPriorityFeePerGas' in tx and 'maxFeePerGas' in tx):
        max_priority_fee = tx.get('maxPriorityFeePerGas', 0)
        max_fee = tx.get('maxFeePerGas', 0)
        
        return min(max_priority_fee, max_fee - base_fee_per_gas)
    
    elif 'gasPrice' in tx:
        gas_price = tx.get('gasPrice')
        priority_fee = gas_price - base_fee_per_gas
        return max(0, priority_fee)
    
    return 0


def is_ordered_block(w3, block_num):
  """
  Takes a block number
  Returns a boolean that tells whether all the transactions in the block are ordered by priority fee

  Before EIP-1559, a block is ordered if and only if all transactions are sorted in decreasing order of the gasPrice field

  After EIP-1559, there are two types of transactions
    *Type 0* The priority fee is tx.gasPrice - block.baseFeePerGas
    *Type 2* The priority fee is min( tx.maxPriorityFeePerGas, tx.maxFeePerGas - block.baseFeePerGas )

  Conveniently, most type 2 transactions set the gasPrice field to be min( tx.maxPriorityFeePerGas + block.baseFeePerGas, tx.maxFeePerGas )
  """
  block = w3.eth.get_block(block_num, full_transactions=True)
  ordered = False

  if not block.transactions:
      return True

  priority_fees = []

  # FIX 1: Handle pre-EIP-1559 blocks (which lack baseFeePerGas)
  if hasattr(block, 'baseFeePerGas') and block.baseFeePerGas is not None:
      # Post-EIP-1559 logic: calculate fee based on EIP-1559 rules
      base_fee_per_gas = block.baseFeePerGas
      for tx in block.transactions:
          fee = calculate_priority_fee(tx, base_fee_per_gas)
          priority_fees.append(fee)
  else:
      # Pre-EIP-1559 logic: ordering is based solely on gasPrice
      for tx in block.transactions:
          gas_price = tx.get('gasPrice', 0)
          priority_fees.append(gas_price)
  
  ordered = all(
      priority_fees[i] >= priority_fees[i+1] 
      for i in range(len(priority_fees) - 1)
  )

  return ordered


def get_contract_values(contract, admin_address, owner_address):
  """
  Takes a contract object, and two addresses (as strings) to be used for calling
  the contract to check current on chain values.
  The provided "default_admin_role" is the correctly formatted solidity default
  admin value to use when checking with the contract
  To complete this method you need to make three calls to the contract to get:
    onchain_root: Get and return the merkleRoot from the provided contract
    has_role: Verify that the address "admin_address" has the role "default_admin_role" return True/False
    prime: Call the contract to get and return the prime owned by "owner_address"

  check on available contract functions and transactions on the block explorer at
  https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
  """
  default_admin_role = int.to_bytes(0, 32, byteorder="big")
  # FIX 2: Change contract.web3 to contract.w3 for wider compatibility
  w3 = contract.w3 

  # TODO complete the following lines by performing contract calls
  onchain_root = contract.functions.merkleRoot().call()  
  
  has_role = contract.functions.hasRole(
      default_admin_role,
      w3.to_checksum_address(admin_address)
  ).call()
  
  prime = contract.functions.getPrimeByOwner(
      w3.to_checksum_address(owner_address)
  ).call()

  return onchain_root, has_role, prime


"""
  This might be useful for testing (main is not run by the grader feel free to change 
  this code anyway that is helpful)
"""
if __name__ == "__main__":
  # These are addresses associated with the Merkle contract (check on contract
  # functions and transactions on the block explorer at
  # https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
  admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
  owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
  contract_file = "student_credentials/contract_info.json" 

  try:
      eth_w3 = connect_to_eth()
      cont_w3, contract = connect_with_middleware(contract_file)

      latest_block = eth_w3.eth.get_block_number()
      london_hard_fork_block_num = 12965000
      assert latest_block > london_hard_fork_block_num, f"Error: the chain never got past the London Hard Fork"

      n = 5
      for _ in range(n):
        block_num = random.randint(london_hard_fork_block_num + 1, latest_block) 
        ordered = is_ordered_block(eth_w3, block_num)
      
      root, role, prime = get_contract_values(contract, admin_address, owner_address)

  except Exception as e:
      pass
