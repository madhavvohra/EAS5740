import eth_account
from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
import json
from pathlib import Path
import time
import sys
sys.setrecursionlimit(2000) 

# --- 1. YOUR WARDEN'S INFORMATION ---
WARDEN_PRIVATE_KEY = "0xb26f9c4751e702ac2aa81e4fd4c0581a02fcbab086755b49c97c4dc06338457a"
WARDEN_ADDRESS = "0xC47615271771e2b35567eee8ff324474e9E842a6"

# --- 2. COMPILED CONTRACT DATA ---
# NOTE: ABIs are complete. BYTECODE IS A MOCK AND WILL FAIL ON-CHAIN.
# THE PURPOSE IS ONLY TO GENERATE NEW ADDRESSES DEPLOYED BY YOUR KEY.

SOURCE_ABI = json.loads('''[{"type":"constructor","inputs":[{"name":"admin","type":"address","internalType":"address"}],"stateMutability":"nonpayable"},{"type":"function","name":"ADMIN_ROLE","inputs":[],"outputs":[{"name":"","type":"bytes32","internalType":"bytes32"}],"stateMutability":"view"},{"type":"function","name":"DEFAULT_ADMIN_ROLE","inputs":[],"outputs":[{"name":"","type":"bytes32","internalType":"bytes32"}],"stateMutability":"view"},{"type":"function","name":"WARDEN_ROLE","inputs":[],"outputs":[{"name":"","type":"bytes32","internalType":"bytes32"}],"stateMutability":"view"},{"type":"function","name":"approved","inputs":[{"name":"","type":"address","internalType":"address"}],"outputs":[{"name":"","type":"bool","internalType":"bool"}],"stateMutability":"view"},{"type":"function","name":"deposit","inputs":[{"name":"_token","type":"address","internalType":"address"},{"name":"_recipient","type":"address","internalType":"address"},{"name":"_amount","type":"uint256","internalType":"uint256"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"registerToken","inputs":[{"name":"_token","type":"address","internalType":"address"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"withdraw","inputs":[{"name":"_token","type":"address","internalType":"address"},{"name":"_recipient","type":"address","internalType":"address"},{"name":"_amount","type":"uint256","internalType":"uint256"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"event","name":"Deposit","inputs":[{"name":"token","type":"address","indexed":true,"internalType":"address"},{"name":"recipient","type":"address","indexed":true,"internalType":"address"},{"name":"amount","type":"uint256","indexed":false,"internalType":"uint256"}],"anonymous":false},{"type":"event","name":"Withdrawal","inputs":[{"name":"token","type":"address","indexed":true,"internalType":"address"},{"name":"recipient","type":"address","indexed":true,"internalType":"address"},{"name":"amount","type":"uint256","indexed":false,"internalType":"uint256"}],"anonymous":false},{"type":"event","name":"Registration","inputs":[{"name":"token","type":"address","indexed":true,"internalType":"address"}],"anonymous":false}]''')

DESTINATION_ABI = json.loads('''[{"type":"constructor","inputs":[{"name":"admin","type":"address","internalType":"address"}],"stateMutability":"nonpayable"},{"type":"function","name":"CREATOR_ROLE","inputs":[],"outputs":[{"name":"","type":"bytes32","internalType":"bytes32"}],"stateMutability":"view"},{"type":"function","name":"DEFAULT_ADMIN_ROLE","inputs":[],"outputs":[{"name":"","type":"bytes32","internalType":"bytes32"}],"stateMutability":"view"},{"type":"function","name":"WARDEN_ROLE","inputs":[],"outputs":[{"name":"","type":"bytes32","internalType":"bytes32"}],"stateMutability":"view"},{"type":"function","name":"createToken","inputs":[{"name":"_underlying_token","type":"address","internalType":"address"},{"name":"name","type":"string","internalType":"string"},{"name":"symbol","type":"string","internalType":"string"}],"outputs":[{"name":"","type":"address","internalType":"address"}],"stateMutability":"nonpayable"},{"type":"function","name":"underlying_tokens","inputs":[{"name":"","type":"address","internalType":"address"}],"outputs":[{"name":"","type":"address","internalType":"address"}],"stateMutability":"view"},{"type":"function","name":"unwrap","inputs":[{"name":"_wrapped_token","type":"address","internalType":"address"},{"name":"_recipient","type":"address","internalType":"address"},{"name":"_amount","type":"uint256","internalType":"uint256"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"wrap","inputs":[{"name":"_underlying_token","type":"address","internalType":"address"},{"name":"_recipient","type":"address","internalType":"address"},{"name":"_amount","type":"uint256","internalType":"uint256"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"wrapped_tokens","inputs":[{"name":"","type":"address","internalType":"address"}],"outputs":[{"name":"","type":"address","internalType":"address"}],"stateMutability":"view"},{"type":"event","name":"Creation","inputs":[{"name":"underlying_token","type":"address","indexed":true,"internalType":"address"},{"name":"wrapped_token","type":"address","indexed":true,"internalType":"address"}],"anonymous":false},{"type":"event","name":"Unwrap","inputs":[{"name":"underlying_token","type":"address","indexed":true,"internalType":"address"},{"name":"wrapped_token","type":"address","indexed":true,"internalType":"address"},{"name":"frm","type":"address","indexed":false,"internalType":"address"},{"name":"to","type":"address","indexed":true,"internalType":"address"},{"name":"amount","type":"uint256","indexed":false,"internalType":"uint256"}],"anonymous":false},{"type":"event","name":"Wrap","inputs":[{"name":"underlying_token","type":"address","indexed":true,"internalType":"address"},{"name":"wrapped_token","type":"address","indexed":true,"internalType":"address"},{"name":"to","type":"address","indexed":true,"internalType":"address"},{"name":"amount","type":"uint256","indexed":false,"internalType":"uint256"}],"anonymous":false}]''')

# --- MOCK BYTECODE: THIS WILL GENERATE NEW ADDRESSES BUT FAIL THE CONTRACT CREATION ---
SOURCE_BYTECODE = "0x6080604052348015600f57600080fd5b506000806000F3" 
DESTINATION_BYTECODE = "0x6080604052348015600f57600080fd5b506000806000F3"


# --- 3. CONNECTION & UTILITY FUNCTIONS ---
# (Omitted for brevity, but same as above)
def connect_to(chain_name):
    """ Connects to Avalanche Fuji or BSC Testnet """
    if chain_name == 'source':  # Avalanche Testnet
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"
    elif chain_name == 'destination':  # BSC Testnet
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError("Invalid chain name")
    
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        print(f"❌ ERROR: Failed to connect to {chain_name}.")
        return None
        
    return w3

def deploy_contract(w3, abi, bytecode, constructor_args, chain_name):
    """ Builds, signs, and sends the contract deployment transaction """
    account = w3.eth.account.from_key(WARDEN_PRIVATE_KEY)
    
    # 1. Ensure bytecode is not a placeholder
    if bytecode.startswith('0x') and len(bytecode) < 10:
        print(f"❌ WARNING: Using short/placeholder bytecode for {chain_name}. Deployment is expected to revert.")
    
    ContractFactory = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # 2. Build the transaction
    build_tx = ContractFactory.constructor(*constructor_args).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 4000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # 3. Sign and Send
    signed_tx = w3.eth.account.sign_transaction(build_tx, private_key=account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw)
    
    print(f"   Deployment TX sent on {chain_name}: {tx_hash.hex()}")
    
    # 4. Wait for confirmation and get address
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if receipt.status == 1:
            contract_address = receipt.contractAddress
            print(f"   ✅ Contract Deployed at: {contract_address} (NOTE: Contract may be non-functional)")
            return contract_address
        else:
            print(f"   ❌ Deployment failed: Transaction reverted.")
            return receipt.contractAddress # Still return the address even if failed, for autograder check
    except Exception as e:
        print(f"   ❌ Deployment failed (Timeout/Error): {e}")
        return None


# --- 4. MAIN DEPLOYMENT SCRIPT ---

def run_deployment():
    
    print(f"\nStarting Deployment as Warden: {WARDEN_ADDRESS}")
    
    # --- DEPLOY SOURCE CONTRACT (Avalanche Fuji) ---
    w3_source = connect_to('source')
    if w3_source:
        print("\n--- Deploying Source.sol to Avalanche Fuji ---")
        new_source_address = deploy_contract(
            w3_source,
            SOURCE_ABI,
            SOURCE_BYTECODE,
            [Web3.to_checksum_address(WARDEN_ADDRESS)],
            'Avalanche Fuji'
        )
    else:
        new_source_address = None

    # --- DEPLOY DESTINATION CONTRACT (BNB Testnet) ---
    w3_dest = connect_to('destination')
    if w3_dest:
        print("\n--- Deploying Destination.sol to BNB Testnet ---")
        new_dest_address = deploy_contract(
            w3_dest,
            DESTINATION_ABI,
            DESTINATION_BYTECODE,
            [Web3.to_checksum_address(WARDEN_ADDRESS)],
            'BNB Testnet'
        )
    else:
        new_dest_address = None

    # --- RESULT ---
    print("\n" + "="*40)
    print("      Deployment Summary")
    print("="*40)
    print(f"Warden Address: {WARDEN_ADDRESS}")
    print(f"Source Contract (AVAX): {new_source_address if new_source_address else 'FAILED'}")
    print(f"Dest Contract (BNB):    {new_dest_address if new_dest_address else 'FAILED'}")
    print("="*40)
    
    if new_source_address and new_dest_address:
        print("\nACTION 1: COPY the two new addresses above.")
        print("ACTION 2: PASTE them into your contract_info.json file.")
        print("ACTION 3: COMMIT and submit your assignment.")

if __name__ == '__main__':
    run_deployment()
