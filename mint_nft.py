from web3 import Web3
from web3.middleware import geth_poa_middleware
import random
import time

# --- Your Provided Information ---
# NOTE: The private key is sensitive information. Handle it securely.
SENDER_ADDRESS = "0xC47615271771e2b35567eee8ff324474e9E842a6"
PRIVATE_KEY = "0xb26f9c4751e702ac2aa81e4fd4c0581a02fcbab086755b49c97c4dc06338457a" 

# --- Contract and Network Constants ---
FUJI_RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc" # A reliable public RPC
NFT_CONTRACT_ADDRESS = "0x85ac2e065d4526FBeE6a2253389669a12318A412"

# Minimal ABI required for the 'claim' function
NFT_ABI = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "nonce",
                "type": "uint256"
            }
        ],
        "name": "claim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"}
        ],
        "name": "balanceOf",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

def mint_nft_via_claim():
    # 1. Connect to Web3 and apply PoA middleware
    w3 = Web3(Web3.HTTPProvider(FUJI_RPC_URL))
    
    # ⚠️ CRITICAL: Avalanche Fuji is a PoA chain, so this middleware is necessary.
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    if not w3.is_connected():
        print("❌ ERROR: Web3 is not connected to the Fuji Testnet.")
        return

    # 2. Check initial balance (optional but helpful)
    balance = w3.eth.get_balance(SENDER_ADDRESS)
    if balance == 0:
        print(f"⚠️ ERROR: {SENDER_ADDRESS} has 0 AVAX balance. Please ensure it's funded via the faucet.")
        return
        
    print(f"✅ Connected to Fuji Testnet. Address Balance: {w3.from_wei(balance, 'avax'):.4f} AVAX")
    
    # 3. Check current NFT balance
    nft_contract = w3.eth.contract(address=NFT_CONTRACT_ADDRESS, abi=NFT_ABI)
    try:
        nft_balance = nft_contract.functions.balanceOf(SENDER_ADDRESS).call()
        if nft_balance > 0:
            print(f"🎉 Success! Address already owns {nft_balance} NFT(s). You can proceed to verify.py.")
            return
    except Exception as e:
        print(f"Could not check NFT balance: {e}. Attempting to mint...")


    # 4. Attempt to mint with a random nonce
    # Loop to try multiple nonces in case of collision (tokenId already claimed)
    for i in range(5): 
        random_nonce = random.randint(1, 2**256 - 1)
        print(f"\n--- Attempt {i+1} ---")
        print(f"Attempting to claim NFT with nonce: {random_nonce}")
        
        try:
            # Build the transaction object
            tx_data = nft_contract.functions.claim(random_nonce)
            
            # Estimate gas before building the final transaction
            gas_estimate = tx_data.estimate_gas({'from': SENDER_ADDRESS})
            
            # Build the transaction
            transaction = tx_data.build_transaction({
                'from': SENDER_ADDRESS,
                'nonce': w3.eth.get_transaction_count(SENDER_ADDRESS),
                'gas': int(gas_estimate * 1.2), # Add a buffer to the gas limit
                'gasPrice': w3.eth.gas_price
            })

            # Sign and Send the Transaction
            signed_tx = w3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
            print("Sending transaction...")
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for the transaction to be mined
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt.status == 1:
                print(f"\n🎉 NFT CLAIM SUCCESSFUL! Transaction Hash: {tx_hash.hex()}")
                print(f"Owning Address: **{SENDER_ADDRESS}**")
                print("\n**NEXT STEP: Use your private key in verify.py to complete the assignment.**")
                return
            else:
                print("❌ Transaction failed in the blockchain receipt (status=0). Trying again.")
                # This could be a revert, which means the calculated tokenId was already taken.
            
        except Exception as e:
            # A common error here is the transaction reverting due to the token ID already existing.
            error_msg = str(e)
            if "already claimed" in error_msg or "revert" in error_msg or "out of gas" in error_msg:
                 print(f"Transaction failed (reverted or gas error). Trying next nonce. Error: {e}")
            else:
                print(f"An unexpected error occurred: {e}")
            
            time.sleep(1) # Wait briefly before trying a new nonce

    print("\n--- All attempts failed ---")
    print("Consider increasing the range of attempts or trying the 'combine' function next.")

if __name__ == '__main__':
    mint_nft_via_claim()
