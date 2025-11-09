#!/bin/python
import hashlib
import os
import random
import time 

def mine_block(k, prev_hash, transactions):
    """
        k - Number of trailing zeros in the binary representation (integer)
        prev_hash - the hash of the previous block (bytes)
        transactions - a set of "transactions," i.e., data to be included in this block (list of strings)

        Complete this function to find a nonce such that 
        sha256( prev_hash + rand_lines + nonce )
        has k trailing zeros in its *binary* representation
    """
    if not isinstance(k, int) or k < 0:
        print("mine_block expects positive integer")
        return b'\x00'

    m = hashlib.sha256()
    
    m.update(prev_hash)
    
    for line in transactions:
        m.update(line.encode('utf-8'))
        
    nonce_counter = 0
    
   
    target_divisor = 2**k

    while True:

        nonce_bytes = nonce_counter.to_bytes(4, 'little')
        
        final_hasher = hashlib.sha256()
        final_hasher.update(prev_hash)
        for line in transactions:
            final_hasher.update(line.encode('utf-8'))
        final_hasher.update(nonce_bytes)
        
        block_hash_bytes = final_hasher.digest()

        hash_int = int.from_bytes(block_hash_bytes, byteorder='big')

        # Check if the integer hash value is divisible by 2^k
        if hash_int % target_divisor == 0:
            nonce = nonce_bytes
            print(f"Nonce found: {nonce_counter} (Nonce Bytes: {nonce_bytes.hex()})")
            print(f"Hash in Hex: {final_hasher.hexdigest()}")
            print(f"Hash in Binary (LSBs checked): ...{bin(hash_int)[-k:]}")
            assert isinstance(nonce, bytes)
            return nonce

        nonce_counter += 1


def get_random_lines(filename, quantity):
    """
    This is a helper function to get the quantity of lines ("transactions")
    as a list from the filename given. 
    Do not modify this function
    """
    lines = []
    # Use the absolute path if running in an environment where files might not be in the root
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                lines.append(line.strip())
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found. Ensure it's in the correct directory.")
        return []
        
    if not lines:
        return []

    random_lines = []
    num_available_lines = len(lines)
    actual_quantity = min(quantity, num_available_lines)
    
    for x in range(actual_quantity):
        random_lines.append(lines[random.randint(0, num_available_lines - 1)])
        
    return random_lines


if __name__ == '__main__':
    filename = "bitcoin_text.txt"
    num_lines = 10

    # The "difficulty" level. 
    # The grader will not exceed 20 bits of "difficulty" 
    diff = 20
    
    prev_hash = os.urandom(32) 
    
    start_time = time.time()
    
    transactions = get_random_lines(filename, num_lines)
    print(f"Starting mining for k={diff}...")
    nonce = mine_block(diff, prev_hash, transactions)

    end_time = time.time()
    
    if nonce != b'\x00':
        print(f"\nMining successful! Nonce: {nonce.hex()}")
        print(f"Time taken: {end_time - start_time:.2f} seconds")
        
        verifier = hashlib.sha256()
        verifier.update(prev_hash)
        for line in transactions:
            verifier.update(line.encode('utf-8'))
        verifier.update(nonce)
        
        final_hash_int = int.from_bytes(verifier.digest(), byteorder='big')
        
        if final_hash_int % (2**diff) == 0:
            print(f"Verification: PASS (Last {diff} bits are zero)")
        else:
            print(f"Verification: FAIL")
    else:
        print("Mining failed or returned default nonce.")
