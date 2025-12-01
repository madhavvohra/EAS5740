from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from pathlib import Path
import json
from datetime import datetime
import pandas as pd


def scan_blocks(chain, start_block, end_block, contract_address, eventfile='deposit_logs.csv'):
    """
    chain - string (Either 'bsc' or 'avax')
    start_block - integer first block to scan
    end_block - integer last block to scan
    contract_address - the address of the deployed contract

    This function reads "Deposit" events from the specified contract, 
    and writes information about the events to the file "deposit_logs.csv"
    """
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" 

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"

    if chain in ['avax','bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    else:
        raise ValueError(f"Unsupported chain: {chain}")

    DEPOSIT_ABI = json.loads('[ { "anonymous": false, "inputs": [ { "indexed": true, "internalType": "address", "name": "token", "type": "address" }, { "indexed": true, "internalType": "address", "name": "recipient", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "Deposit", "type": "event" }]')
    contract = w3.eth.contract(address=contract_address, abi=DEPOSIT_ABI)

    arg_filter = {}

    if start_block == "latest":
        start_block = w3.eth.get_block_number()
    if end_block == "latest":
        end_block = w3.eth.get_block_number()

    start_block = int(start_block)
    end_block = int(end_block)

    if end_block < start_block:
        print( f"Error end_block < start_block!" )
        print( f"end_block = {end_block}" )
        print( f"start_block = {start_block}" )
        return

    if start_block == end_block:
        print( f"Scanning block {start_block} on {chain}" )
    else:
        print( f"Scanning blocks {start_block} - {end_block} on {chain}" )

    all_events = []
    
    if end_block - start_block < 30:
        # Small range: query all at once
        event_filter = contract.events.Deposit.create_filter(from_block=start_block,to_block=end_block,argument_filters=arg_filter)
        events = event_filter.get_all_entries()
        all_events.extend(events)
    else:
        # Large range: iterate block by block
        for block_num in range(start_block,end_block+1):
            event_filter = contract.events.Deposit.create_filter(from_block=block_num,to_block=block_num,argument_filters=arg_filter)
            events = event_filter.get_all_entries()
            all_events.extend(events)

    # Process all collected events
    final_data = []
    for evt in all_events:
        date_str = "N/A" 
        try:
            block = w3.eth.get_block(evt.blockNumber)
            timestamp = block.timestamp
            date_str = datetime.fromtimestamp(timestamp).strftime('%m/%d/%Y %H:%M:%S')
        except Exception:
            pass
            
        data_entry = {
            'chain': chain,
            'token': evt.args['token'],
            'recipient': evt.args['recipient'],
            'amount': evt.args['amount'],
            'transactionHash': evt.transactionHash.hex(),
            'address': evt.address,
            'date': date_str
        }
        final_data.append(data_entry)

    # Write the data to CSV using pandas
    df = pd.DataFrame(final_data)
    
    REQUIRED_COLUMNS = ['chain', 'token', 'recipient', 'amount', 'transactionHash', 'address', 'date']
    
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    
    df.to_csv(
        eventfile,
        index=False,
        columns=REQUIRED_COLUMNS
    )
    
    print(f"Successfully processed {len(all_events)} Deposit events and wrote to {eventfile}")
