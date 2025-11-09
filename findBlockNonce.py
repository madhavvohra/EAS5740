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

    # 1. Prepare the static part of the block data (prev_hash + transactions)
    
    # Start the SHA256 hasher
    m = hashlib.sha256()
    
    # Add the previous block's hash (must be bytes)
    m.update(prev_hash)
    
    # Add all transactions (strings must be encoded to bytes)
    for line in transactions:
        m.update(line.encode('utf-8'))
        
    # The static_data_hasher now holds the hash state of (prev_hash + transactions)
    # We will clone this state for each nonce attempt to avoid recalculating the static part.

    # 2. Brute-force the Nonce
    nonce_counter = 0
    
    # A mask to check the k LSBs. 
    # For k LSBs to be zero, the hash's integer value must be divisible by 2^k.
    # The condition is: hash_int_value % (2**k) == 0
    # A faster, equivalent check is: hash_int_value & ((1 << k) - 1) == 0
    # where ((1 << k) - 1) is a bitmask of k ones.
    # For example, if k=5, (1 << 5) - 1 = 31, which is 0b11111. 
    # This is slightly more complex, so we'll use the simpler modulo check.
    target_divisor = 2**k

    while True:
        # Convert the counter (integer) to bytes to be used as the nonce
        # Nonce format: little-endian byte representation (e.g., 4 bytes)
        # We use a fixed-length encoding to keep the block data consistent.
        nonce_bytes = nonce_counter.to_bytes(4, 'little')
        
        # 3. Create a copy of the hasher state and add the nonce
        # We need to perform SHA256( (prev_hash + rand_lines) + nonce )
        
        # A simple way to do this without deep copying the hash object is to 
        # concatenate the pre-hashed data and the nonce bytes.
        
        # NOTE: A more efficient method in a real-world scenario is to clone the 'm' 
        # hash state, update the clone with 'nonce_bytes', and get the digest.
        # Since the problem asks for SHA256(prev_hash + rand_lines + nonce), 
        # let's rebuild the final hash for clarity:
        
        final_hasher = hashlib.sha256()
        final_hasher.update(prev_hash)
        for line in transactions:
            final_hasher.update(line.encode('utf-8'))
        final_hasher.update(nonce_bytes)
        
        # Get the hash in bytes
        block_hash_bytes = final_hasher.digest()
        
        # 4. Check the LSBs
        # Convert the hash (bytes) to a large integer
        # The 'big' endian is standard for hash representation.
        hash_int = int.from_bytes(block_hash_bytes, byteorder='big')

        # Check if the integer hash value is divisible by 2^k
        if hash_int % target_divisor == 0:
            nonce = nonce_bytes
            print(f"Nonce found: {nonce_counter} (Nonce Bytes: {nonce_bytes.hex()})")
            print(f"Hash in Hex: {final_hasher.hexdigest()}")
            print(f"Hash in Binary (LSBs checked): ...{bin(hash_int)[-k:]}")
            # Ensure the nonce is of type bytes before returning
            assert isinstance(nonce, bytes)
            return nonce

        nonce_counter += 1
        
        # Optional: Add a check to prevent infinite loops during testing higher difficulty
        # if nonce_counter > 5000000: # Example limit for safety
        #     print("Exceeded nonce limit, stopping.")
        #     return b'\x00'


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
    # Ensure quantity does not exceed the number of available lines
    num_available_lines = len(lines)
    actual_quantity = min(quantity, num_available_lines)
    
    for x in range(actual_quantity):
        # Use a random line from the whole list
        random_lines.append(lines[random.randint(0, num_available_lines - 1)])
        
    return random_lines


if __name__ == '__main__':
    # This code will be helpful for your testing
    filename = "bitcoin_text.txt"
    num_lines = 10  # The number of "transactions" included in the block

    # The "difficulty" level. 
    # The grader will not exceed 20 bits of "difficulty" 
    diff = 20
    
    # We need a previous hash (32 bytes)
    prev_hash = os.urandom(32) 
    
    start_time = time.time()
    
    transactions = get_random_lines(filename, num_lines)
    print(f"Starting mining for k={diff}...")
    nonce = mine_block(diff, prev_hash, transactions)

    end_time = time.time()
    
    if nonce != b'\x00':
        print(f"\nMining successful! Nonce: {nonce.hex()}")
        print(f"Time taken: {end_time - start_time:.2f} seconds")
        
        # Verification step
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
