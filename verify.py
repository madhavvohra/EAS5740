import json
import time
import random
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
import os

# Avalanche Fuji Testnet RPC URL (Using a common public link for reliability)
AVAX_FUJI_RPC_URL = "https://avalanche-fuji.g.alchemy.com/v2/MmEXl5ITY4yo6sSOr6sNj" 

# Private key of the funded account (from gen_keys.py)
# This key will pay for the gas fees.
MINTER_PRIVATE_KEY = "0xb26f9c4751e702ac2aa81e4fd4c0581a02fcbab086755b49c97c4dc06338457a"

# NFT Contract details on Avalanche Fuji Testnet
NFT_CONTRACT_ADDRESS = "0x85ac2e065d4526FBeE6a2253389669a12318A412"
# ABI for the contract (Assumed to be loaded from a file or predefined)
# Since the ABI file is not provided, we will define a minimal one with the 'claim' function.

NFT_ABI = [
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "nonce",
                "type": "bytes32"
            }
        ],
        "name": "claim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "owner",
                "type": "address"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
# ---------------------------------------------------------


def connect_avax_middleware(rpc_url):
    """Connects to Avalanche Fuji Testnet and injects PoA middleware."""
    w3 = Web3(HTTPProvider(rpc_url))
    # Avalanche uses a PoA-compatible consensus, requiring this middleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    assert w3.is_connected(), f"Failed to connect to Avalanche at {rpc_url}"
    return w3

def get_nonce_and_gas(w3, minter_address):
    """Calculates the nonce and estimates gas parameters."""
    # Get the next valid transaction nonce
    nonce = w3.eth.get_transaction_count(minter_address)
    
    # Simple gas estimation (often safer to use slightly higher values for testnets)
    gas_price = w3.eth.gas_price
    
    return nonce, gas_price

def send_transaction(w3, contract, minter_address, private_key):
    """
    Builds, signs, and sends the 'claim' transaction.
    Attempts to mint an NFT with a random nonce.
    """
    
    # 1. Generate a random nonce (32 bytes) for the claim function
    nonce_bytes = os.urandom(32) 

    # 2. Build the transaction
    try:
        # Build the transaction using the contract function
        tx_claim = contract.functions.claim(nonce_bytes).build_transaction({
            'from': minter_address,
            'nonce': w3.eth.get_transaction_count(minter_address), # Use the latest nonce
            'gas': 300000, # Sufficient gas limit for a mint operation
            'gasPrice': w3.eth.gas_price,
        })
    except Exception as e:
        print(f"Error building transaction (may mean tokenId is taken): {e}")
        return None

    # 3. Sign the transaction
    signed_tx = w3.eth.account.sign_transaction(tx_claim, private_key)

    # 4. Send the transaction
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transaction Hash: {w3.to_hex(tx_hash)}")
        
        # Wait for the transaction to be mined
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status == 1:
            print(f"SUCCESS! NFT Claimed. Gas Used: {tx_receipt.gasUsed}")
            return True
        else:
            print(f"FAILURE: Transaction reverted. Status: {tx_receipt.status}")
            return False
            
    except Exception as e:
        print(f"Error sending transaction: {e}")
        return False

if __name__ == "__main__":
    if "YOUR_AVALANCHE_FUJI_RPC_URL_HERE" in AVAX_FUJI_RPC_URL or "YOUR_MINTER_PRIVATE_KEY_HERE" in MINTER_PRIVATE_KEY:
        print("!!! ERROR: Please update AVAX_FUJI_RPC_URL and MINTER_PRIVATE_KEY with your actual credentials. !!!")
    else:
        print("--- NFT Minting Attempt Started ---")
        
        # Connect to Avalanche
        w3 = connect_avax_middleware(AVAX_FUJI_RPC_URL)
        
        # Load minter address
        minter_account = Account.from_key(MINTER_PRIVATE_KEY)
        minter_address = minter_account.address
        print(f"Minter Address: {minter_address}")
        
        # Instantiate the NFT contract
        contract = w3.eth.contract(address=Web3.to_checksum_address(NFT_CONTRACT_ADDRESS), abi=NFT_ABI)
        
        # Check initial NFT balance
        try:
            initial_balance = contract.functions.balanceOf(minter_address).call()
            print(f"Initial NFT Balance: {initial_balance}")
        except Exception as e:
            print(f"Could not check initial balance: {e}")
            
        # Loop to attempt minting until successful
        max_attempts = 10
        success = False
        for i in range(max_attempts):
            print(f"\nAttempt {i+1} to claim NFT...")
            if send_transaction(w3, contract, minter_address, MINTER_PRIVATE_KEY):
                success = True
                break
            time.sleep(1) # Small delay between attempts

        if success:
            final_balance = contract.functions.balanceOf(minter_address).call()
            print(f"\nFinal NFT Balance: {final_balance}")
            print("Successfully minted an NFT! Now update verify.py with your private key.")
        else:
            print(f"\nFailed to mint NFT after {max_attempts} attempts. Check your RPC URL and token balance.")
