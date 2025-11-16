// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract Source is AccessControl {
    // Define custom roles
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    
    // Tracks registered tokens. We rename 'approved' to 'isRegistered' for clarity.
    // The skeleton used 'approved', so we'll stick to that, but treat it as registration status.
    mapping( address => bool) public approved; 
    
    // List of registered tokens (not strictly required by logic, but used by skeleton)
    address[] public tokens; 

    event Deposit( address indexed token, address indexed recipient, uint256 amount );
    event Withdrawal( address indexed token, address indexed recipient, uint256 amount );
    event Registration( address indexed token );

    constructor( address admin ) {
        // Grant initial roles to the deployer/admin address
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    /**
     * @notice Allows the bridge operator (ADMIN_ROLE) to register a new token for bridging.
     * @param _token The address of the ERC20 token to register.
     */
    function registerToken(address _token) onlyRole(ADMIN_ROLE) public {
        // Check that the token has not already been registered
        require(!approved[_token], "Source: Token already registered");
        
        // Add the token address to the list of registered tokens
        approved[_token] = true;
        tokens.push(_token);
        
        // Emit a Registration event
        emit Registration(_token);
    }

    /**
     * @notice Allows a user to deposit registered tokens into the bridge contract.
     * @dev Uses the approve + transferFrom pattern. The user must first approve this contract.
     * @param _token The address of the ERC20 token being deposited.
     * @param _recipient The address that will receive the wrapped tokens on the destination chain.
     * @param _amount The amount of tokens to deposit.
     */
    function deposit(address _token, address _recipient, uint256 _amount ) public {
        // 1. Check if the token being deposited has been "registered"
        require(approved[_token], "Source: Token not registered");
        
        // 2. Use the ERC20 "transferFrom" function to pull the tokens into the deposit contract.
        // The sender of this transaction (msg.sender) is the address the tokens are pulled FROM.
        // We use an unsafe cast here, assuming the token address is a standard ERC20.
        ERC20(_token).transferFrom(msg.sender, address(this), _amount);
        
        // 3. Emit a "Deposit" event so that the bridge operator knows to mint the wrapped tokens.
        emit Deposit(_token, _recipient, _amount);
    }

    /**
     * @notice Executes a withdrawal of the underlying token after a burn on the destination chain.
     * @param _token The address of the ERC20 token being withdrawn.
     * @param _recipient The final address on the source chain to receive the tokens.
     * @param _amount The amount of tokens to send.
     */
    function withdraw(address _token, address _recipient, uint256 _amount ) onlyRole(WARDEN_ROLE) public {
        // 1. Access control check (provided by onlyRole(WARDEN_ROLE))
        
        // 2. Push the tokens to the recipient using the ERC20 "transfer" function.
        // This requires the Source contract (address(this)) to hold the balance.
        // We use an unsafe cast here, assuming the token address is a standard ERC20.
        ERC20(_token).transfer(_recipient, _amount);
        
        // 3. Emit a "Withdrawal" event.
        emit Withdrawal(_token, _recipient, _amount);
    }
}
