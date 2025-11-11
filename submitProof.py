import eth_account
import random
import string
import json
from pathlib import Path
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account.messages import encode_defunct


NUM_OF_PRIMES = 8192
PRIME_BYTE_LENGTH = 32


def generate_primes(num_primes):
    """
        Function to generate the first 'num_primes' prime numbers.
        The assignment specifies the last prime is 84017.
        Returns list (with length n) of primes (as ints) in ascending order.
    """
    primes_list = []
    
    limit = 85000 
    is_prime = [True] * limit
    is_prime[0] = is_prime[1] = False
    
    for p in range(2, int(limit**0.5) + 1):
        if is_prime[p]:
            for multiple in range(p * p, limit, p):
                is_prime[multiple] = False

    for p in range(2, limit):
        if is_prime[p]:
            primes_list.append(p)
            if len(primes_list) == num_primes:
                break

    return primes_list


def convert_leaves(primes_list):
    """
        Converts the leaves (primes_list) to bytes32 format (32 bytes, big-endian).
        Returns list of primes where list entries are bytes32 encodings of primes_list entries.
    """
    leaves = []
    for prime in primes_list:
        leaf_bytes = prime.to_bytes(PRIME_BYTE_LENGTH, 'big')
        leaves.append(leaf_bytes)
        
    return leaves


def build_merkle(leaves):
    """
        Function to build a Merkle Tree from the list of prime numbers in bytes32 format.
        Returns the Merkle tree (tree) as a list of lists where tree[0] is the leaves,
        tree[1] is the parent hashes, and so on until tree[n] which is the root hash.
        Uses the 'hash_pair' helper function which sorts input before hashing.
    """
    tree = [leaves]
    current_level = leaves

    while len(current_level) > 1:
        next_level = []
        
        for i in range(0, len(current_level), 2):
            a = current_level[i]
            
            if i + 1 == len(current_level):
                b = a
            else:
                b = current_level[i+1]
            
            next_level.append(hash_pair(a, b))
        
        tree.append(next_level)
        current_level = next_level

    return tree


def prove_merkle(merkle_tree, random_indx):
    """
        Takes a random_index to create a proof of inclusion for and a complete Merkle tree.
        Returns a proof of inclusion as list of hash values (bytes32).
    """
    merkle_proof = []
    current_hash = merkle_tree[0][random_indx]

    for i in range(len(merkle_tree) - 1):
        current_level = merkle_tree[i]
        
        is_left_node = random_indx % 2 == 0
        
        if is_left_node:
            sibling_index = random_indx + 1
            if sibling_index < len(current_level):
                sibling_hash = current_level[sibling_index]
            else:
                sibling_hash = current_hash 
        else:
            sibling_index = random_indx - 1
            sibling_hash = current_level[sibling_index]

        merkle_proof.append(sibling_hash)
        
        current_hash = hash_pair(current_hash, sibling_hash)

        random_indx //= 2

    return merkle_proof


def sign_challenge(challenge):
    """
        Takes a challenge (string)
        Returns address, sig (in hex)
        This method is to allow the auto-grader to verify that you have
        claimed a prime
    """
    acct = get_account()

    addr = acct.address
    eth_sk = acct.key

    eth_encoded_msg = encode_defunct(text=challenge)
    
    eth_sig_obj = eth_account.Account.sign_message(eth_encoded_msg, private_key=eth_sk)

    return addr, eth_sig_obj.signature.hex()


def send_signed_msg(proof, random_leaf):
    """
        Takes a Merkle proof of a leaf, and that leaf (in bytes32 format)
        builds signs and sends a transaction claiming that leaf (prime)
        on the contract
    """
    chain = 'bsc'

    acct = get_account()
    address, abi = get_contract_info(chain)
    w3 = connect_to(chain)

    contract = w3.eth.contract(address=address, abi=abi)
    
    transaction = contract.functions.submit(proof, random_leaf).build_transaction({
        'from': acct.address,
        'nonce': w3.eth.get_transaction_count(acct.address),
        'gas': 300000, 
        'gasPrice': w3.eth.gas_price
    })

    signed_tx = w3.eth.account.sign_transaction(transaction, private_key=acct.key)

    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    except AttributeError:
        print("Warning: Failed to find 'rawTransaction', trying 'raw_transaction'.")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print(f"\nTransaction sent! Waiting for confirmation (Hash: {tx_hash.hex()})...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        print("✅ SUCCESS! Prime claimed on BNB Testnet.")
        print(f"Transaction Receipt: {receipt}")
    else:
        print("❌ FAILURE! Transaction reverted. Check if the prime was already claimed.")

    return tx_hash.hex()


def merkle_assignment():
    """
        The only modifications you need to make to this method are to assign
        your "random_leaf_index" and uncomment the last line when you are
        ready to attempt to claim a prime. You will need to complete the
        methods called by this method to generate the proof.
    """
    primes = generate_primes(NUM_OF_PRIMES)

    leaves = convert_leaves(primes)

    tree = build_merkle(leaves)

    random_leaf_index = random.randint(1, NUM_OF_PRIMES - 1) 
    
    # Get the Merkle proof for that leaf
    proof = prove_merkle(tree, random_leaf_index)
    
    print(f"--- Merkle Proof Generated ---")
    print(f"Prime (Leaf): {primes[random_leaf_index]}")
    print(f"Index: {random_leaf_index}")
    print(f"Proof Length (Steps): {len(proof)}")
    print(f"Root Hash: {tree[-1][0].hex()}")
    print("-" * 30)

    challenge = ''.join(random.choice(string.ascii_letters) for i in range(32))
    
    addr, sig = sign_challenge(challenge)

    if sign_challenge_verify(challenge, addr, sig):
        tx_hash = send_signed_msg(proof, leaves[random_leaf_index])
        print(f"Submission Transaction Hash: {tx_hash}")


def connect_to(chain):
    if chain not in ['avax','bsc']:
        print(f"{chain} is not a valid option for 'connect_to()'")
        return None
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"
    else:
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_account():
    cur_dir = Path(__file__).parent.absolute()
    with open(cur_dir.joinpath('sk.txt'), 'r') as f:
        sk = f.readline().rstrip()
    if sk[0:2] == "0x":
        sk = sk[2:]
    return eth_account.Account.from_key(sk)


def get_contract_info(chain):
    contract_file = Path(__file__).parent.absolute() / "contract_info.json"
    if not contract_file.is_file():
        contract_file = Path(__file__).parent.parent.parent / "tests" / "contract_info.json"
    with open(contract_file, "r") as f:
        d = json.load(f)
        d = d[chain]
    return d['address'], d['abi']


def sign_challenge_verify(challenge, addr, sig):
    eth_encoded_msg = eth_account.messages.encode_defunct(text=challenge)

    if eth_account.Account.recover_message(eth_encoded_msg, signature=sig) == addr:
        print(f"Success: signed the challenge {challenge} using address {addr}!")
        return True
    else:
        print(f"Failure: The signature does not verify!")
        print(f"signature = {sig}\naddress = {addr}\nchallenge = {challenge}")
        return False


def hash_pair(a, b):
    if a < b:
        return Web3.solidity_keccak(['bytes32', 'bytes32'], [a, b])
    else:
        return Web3.solidity_keccak(['bytes32', 'bytes32'], [b, a])


if __name__ == "__main__":
    merkle_assignment()
