from web3 import Web3
from eth_account.messages import encode_defunct
import random

def sign_challenge( challenge ):

    w3 = Web3()

    sk = "0xb26f9c4751e702ac2aa81e4fd4c0581a02fcbab086755b49c97c4dc06338457a" 

    acct = w3.eth.account.from_key(sk)

    # Convert challenge to a hexadecimal string before encoding. This resolves type ambiguity
    # when the challenge is passed as raw bytes from the autograder.
    challenge_hex = Web3.to_hex(challenge)
    
    # Encode the message using the hex string.
    message_to_sign = encode_defunct(challenge_hex) 
    
    # Sign the encoded message using the account's private key (acct.key is the private key bytes)
    signed_message = w3.eth.account.sign_message( message_to_sign , private_key = acct.key )

    return acct.address, signed_message.signature


def verify_sig():
    
    challenge_bytes = random.randbytes(32)

    # We pass the raw bytes (challenge_bytes) to sign_challenge.
    # We DO NOT pre-encode it here, as that causes type issues when calling sign_challenge.
    address, sig = sign_challenge( challenge_bytes ) 

    w3 = Web3()

    # The recover function needs the *original* message, which must be encoded.
    # Since sign_challenge converted the challenge to hex, we must do the same here 
    # for the recovery to match the hash.
    challenge_hex = Web3.to_hex(challenge_bytes)
    
    return w3.eth.account.recover_message( encode_defunct(challenge_hex) , signature=sig ) == address


if __name__ == '__main__':
    if verify_sig():
        print( f"You passed the challenge!" )
    else:
        print( f"You failed the challenge!" )
