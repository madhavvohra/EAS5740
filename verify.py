from web3 import Web3
from eth_account.messages import encode_defunct
import random

def sign_challenge( challenge ):

    w3 = Web3()

    sk = "0xb26f9c4751e702ac2aa81e4fd4c0581a02fcbab086755b49c97c4dc06338457a" 

    acct = w3.eth.account.from_key(sk)

    # Encode the message for signing (must be done before signing)
    message_to_sign = encode_defunct(challenge) 
    
    # Sign the encoded message using the account's private key (acct.key is the private key bytes)
    signed_message = w3.eth.account.sign_message( message_to_sign , private_key = acct.key )

    return acct.address, signed_message.signature


def verify_sig():
    
    challenge_bytes = random.randbytes(32)

    challenge = encode_defunct(challenge_bytes)
    address, sig = sign_challenge( challenge )

    w3 = Web3()

    return w3.eth.account.recover_message( challenge , signature=sig ) == address


if __name__ == '__main__':
    if verify_sig():
        print( f"You passed the challenge!" )
    else:
        print( f"You failed the challenge!" )
