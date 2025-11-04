from web3 import Web3
from eth_account.messages import encode_defunct
import eth_account
import os

def sign_message(challenge, filename="secret_key.txt"):
    """
    challenge - byte string
    filename - filename of the file that contains your account secret key
    To pass the tests, your signature must verify, and the account you use
    must have testnet funds on both the bsc and avalanche test networks.
    """
    # This code will read your "sk.txt" file
    # If the file is empty, it will raise an exception
    with open(filename, "r") as f:
        key = f.readlines()
    assert(len(key) > 0), "Your account secret_key.txt is empty"

    w3 = Web3()
    message = encode_defunct(challenge)

    # TODO recover your account information for your private key and sign the given challenge
    # Use the code from the signatures assignment to sign the given challenge
    
    # Extract the private key string (assuming it's on the first line)
    private_key = key[0].strip()

    # Recover the account from the private key
    account = eth_account.Account.from_key(private_key)
    eth_addr = account.address
    
    # Sign the message
    signed_message = account.sign_message(message)
    

    assert eth_account.Account.recover_message(message,signature=signed_message.signature.hex()) == eth_addr, f"Failed to sign message properly"

    #return signed_message, account associated with the private key
    return signed_message, eth_addr


if __name__ == "__main__":
    
    # FIX: Use the absolute path that the test runner expects for persistence
    key_filename = "/home/codio/workspace/.guides/student_code/EAS5740/secret_key.txt"
    
    # --- CRITICAL: Key Generation and Persistence for Assignment ---
    # This block ensures the key file exists and is populated for the autograder.
    if not os.path.exists(key_filename) or os.stat(key_filename).st_size == 0:
        # Ensure the directories exist before attempting to write the file
        os.makedirs(os.path.dirname(key_filename), exist_ok=True)
        
        # Generate new account
        acct = eth_account.Account.create()
        private_key = acct.key.hex()
        
        with open(key_filename, 'w') as f:
            f.write(private_key)
        
        print(f"Generated new key for address: {acct.address} and saved to {key_filename}")
        print("Please fund this address on BSC and Avalanche testnets.")
    # ---------------------------------------------------------------------------------
    
    for i in range(4):
        challenge = os.urandom(64)
        # Pass the full key_filename path to ensure it reads the file we just created
        sig, addr= sign_message(challenge=challenge, filename=key_filename)
        print( addr )
