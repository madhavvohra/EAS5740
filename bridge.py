import eth_account
from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
import time # For transaction waiting

# --- Global Constants ---
# NOTE: The warden's private key must be in sk.txt
Warden_SK = "" # This will be loaded from sk.txt
GAS_LIMIT = 400000 
GAS_PRICE_MULTIPLIER = 1.2 # Safety buffer for gas price/limit

# --- ABIs for Event Filtering ---
# Deposit event (Source Contract)
DEPOSIT_ABI = json.loads('[ { "anonymous": false, "inputs": [ { "indexed": true, "internalType": "address", "name": "token", "type": "address" }, { "indexed": true, "internalType": "address", "name": "recipient", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "Deposit", "type": "event" }]')

# Unwrap event (Destination Contract)
UNWRAP_ABI = json.loads('[ { "anonymous": false, "inputs": [ { "indexed": true, "internalType": "address", "name": "underlying_token", "type": "address" }, { "indexed": true, "internalType": "address", "name": "wrapped_token", "type": "address" }, { "indexed": false, "internalType": "address", "name": "frm", "type": "address" }, { "indexed": true, "internalType": "address", "name": "to", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "Unwrap", "type": "event" }]')

# --- Helper Functions ---
def get_account():
    """Returns an account object recovered from the secret key in "sk.txt" """
    global Warden_SK
    cur_dir = Path(__file__).parent.absolute()
    # Assuming sk.txt is in the current directory
    with open(cur_dir.joinpath('sk.txt'), 'r') as f:
        sk = f.readline().rstrip()
    if sk[0:2] == "0x":
        Warden_SK = sk
        sk = sk[2:]
    return eth_account.Account.from_key(sk)


def connect_to(chain):
    if chain == 'source':  # Avalanche Testnet
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'destination':  # BSC Testnet
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError(f"Invalid chain identifier: {chain}")

    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info="contract_info.json"):
    """ Load the contract_info file into a dictionary """
    try:
        cur_dir = Path(__file__).parent.absolute()
        with open(cur_dir.joinpath(contract_info), 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info: {e}" )
        return None
    return contracts[chain]


def get_erc20s(erc20_file="erc20s.csv"):
    """ Reads the list of tokens to be registered from erc20s.csv """
    try:
        cur_dir = Path(__file__).parent.absolute()
        df = pd.read_csv(cur_dir.joinpath(erc20_file))
        return df
    except Exception as e:
        print(f"Failed to read ERC20 list: {e}")
        return pd.DataFrame()


def send_transaction(w3, account, contract, func_name, args):
    """ Helper to build, sign, and send a transaction """
    try:
        func = getattr(contract.functions, func_name)(*args)
        
        # Estimate gas
        gas_estimate = func.estimate_gas({'from': account.address})
        
        # Build transaction
        tx = func.build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': int(gas_estimate * GAS_PRICE_MULTIPLIER),
            'gasPrice': w3.eth.gas_price
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"   TX SENT ({func_name}): {tx_hash.hex()}")
        
        # Wait for confirmation (optional but highly recommended)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            print(f"   TX CONFIRMED ({func_name}) at block {receipt.blockNumber}")
            return receipt
        else:
            print(f"   TX FAILED ({func_name}): Reverted.")
            return None

    except Exception as e:
        print(f"   TX ERROR ({func_name}): {e}")
        return None


# --- Bridge Setup (Run Once) ---
def register_tokens():
    """ Registers tokens on both Source (Avalanche) and Destination (BNB) chains """
    warden_account = get_account()
    erc20_df = get_erc20s()

    # 1. Source Chain (Avalanche) - Registration
    source_info = get_contract_info("source")
    w3_source = connect_to("source")
    source_contract = w3_source.eth.contract(address=source_info['address'], abi=source_info['abi'])

    # 2. Destination Chain (BNB) - Creation
    destination_info = get_contract_info("destination")
    w3_dest = connect_to("destination")
    dest_contract = w3_dest.eth.contract(address=destination_info['address'], abi=destination_info['abi'])

    # Get the tokens unique to the Source chain (Avalanche)
    source_tokens = erc20_df[erc20_df['chain'] == 'avax']['address'].unique()
    
    print("\n--- STARTING TOKEN REGISTRATION ---")

    for token_address in source_tokens:
        token_address = Web3.to_checksum_address(token_address)
        
        # Assume token name/symbol is generic or must be retrieved (Using placeholders for simplicity)
        token_name = f"Token-{token_address[-4:]}"
        token_symbol = f"T{token_address[-4:]}"

        # A. Register on Source (Avalanche)
        print(f"1. Registering {token_symbol} on Source (Avalanche)...")
        send_transaction(
            w3_source, warden_account, source_contract, 
            'registerToken', [token_address]
        )

        # B. Create/Wrap on Destination (BNB)
        print(f"2. Creating wrapped {token_symbol} on Destination (BNB)...")
        send_transaction(
            w3_dest, warden_account, dest_contract, 
            'createToken', [token_address, token_name, token_symbol]
        )
    
    print("--- TOKEN REGISTRATION COMPLETE ---")


# --- Bridge Monitoring/Execution (Run by Autograder) ---
def scan_blocks(chain, contract_info="contract_info.json"):
    """
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit'/'Unwrap' events and call the corresponding function on the other chain.
    """
    warden_account = get_account()
    
    if chain == 'source': # Monitor Source (Avalanche) for Deposit -> Call Destination (BNB) wrap()
        # --- Source Chain Setup ---
        monitor_chain = "source"
        exec_chain = "destination"
        monitor_info = get_contract_info(monitor_chain)
        exec_info = get_contract_info(exec_chain)
        
        w3_monitor = connect_to(monitor_chain)
        w3_exec = connect_to(exec_chain)

        monitor_contract = w3_monitor.eth.contract(address=monitor_info['address'], abi=monitor_info['abi'])
        exec_contract = w3_exec.eth.contract(address=exec_info['address'], abi=exec_info['abi'])
        
        event_abi = DEPOSIT_ABI
        event_name = 'Deposit'
        
        # Get blocks to scan (last 5 blocks)
        end_block = w3_monitor.eth.get_block_number()
        start_block = end_block - 5
        
        # --- Scan for Deposit Events ---
        print(f"\n--- Scanning {monitor_chain} for {event_name} events ({start_block}-{end_block}) ---")
        event_filter = monitor_contract.events.Deposit.create_filter(from_block=start_block, to_block=end_block, argument_filters={})
        events = event_filter.get_all_entries()

        for evt in events:
            # Data needed for wrap(underlying_token, recipient, amount)
            underlying_token = evt.args['token']
            recipient = evt.args['recipient']
            amount = evt.args['amount']
            
            print(f"   [DEPOSIT FOUND] Token: {underlying_token}, Recipient: {recipient}, Amount: {amount}")

            # Execute: wrap() on Destination (BNB)
            send_transaction(
                w3_exec, warden_account, exec_contract, 
                'wrap', [underlying_token, recipient, amount]
            )

    elif chain == 'destination': # Monitor Destination (BNB) for Unwrap -> Call Source (Avalanche) withdraw()
        # --- Destination Chain Setup ---
        monitor_chain = "destination"
        exec_chain = "source"
        monitor_info = get_contract_info(monitor_chain)
        exec_info = get_contract_info(exec_chain)
        
        w3_monitor = connect_to(monitor_chain)
        w3_exec = connect_to(exec_chain)

        monitor_contract = w3_monitor.eth.contract(address=monitor_info['address'], abi=monitor_info['abi'])
        exec_contract = w3_exec.eth.contract(address=exec_info['address'], abi=exec_info['abi'])
        
        event_abi = UNWRAP_ABI
        event_name = 'Unwrap'

        # Get blocks to scan (last 5 blocks)
        end_block = w3_monitor.eth.get_block_number()
        start_block = end_block - 5

        # --- Scan for Unwrap Events ---
        print(f"\n--- Scanning {monitor_chain} for {event_name} events ({start_block}-{end_block}) ---")
        event_filter = monitor_contract.events.Unwrap.create_filter(from_block=start_block, to_block=end_block, argument_filters={})
        events = event_filter.get_all_entries()
        
        for evt in events:
            # Data needed for withdraw(token, recipient, amount)
            underlying_token = evt.args['underlying_token']
            recipient = evt.args['to'] # 'to' is the intended recipient on the source chain
            amount = evt.args['amount']
            
            print(f"   [UNWRAP FOUND] Token: {underlying_token}, Recipient: {recipient}, Amount: {amount}")

            # Execute: withdraw() on Source (Avalanche)
            send_transaction(
                w3_exec, warden_account, exec_contract, 
                'withdraw', [underlying_token, recipient, amount]
            )
    
    print("--- SCAN COMPLETE ---")
