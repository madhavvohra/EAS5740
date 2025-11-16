// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract Source is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");

    mapping( address => bool) public approved; 
    
    address[] public tokens; 

    event Deposit( address indexed token, address indexed recipient, uint256 amount );
    event Withdrawal( address indexed token, address indexed recipient, uint256 amount );
    event Registration( address indexed token );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    /**
     * @notice Allows the bridge operator (ADMIN_ROLE) to register a new token for bridging.
     * @param _token The address of the ERC20 token to register.
     */
    function registerToken(address _token) onlyRole(ADMIN_ROLE) public {
        require(!approved[_token], "Source: Token already registered");
        
        approved[_token] = true;
        tokens.push(_token);
        
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
        require(approved[_token], "Source: Token not registered");
        
        ERC20(_token).transferFrom(msg.sender, address(this), _amount);
        
        emit Deposit(_token, _recipient, _amount);
    }

    /**
     * @notice Executes a withdrawal of the underlying token after a burn on the destination chain.
     * @param _token The address of the ERC20 token being withdrawn.
     * @param _recipient The final address on the source chain to receive the tokens.
     * @param _amount The amount of tokens to send.
     */
    function withdraw(address _token, address _recipient, uint256 _amount ) onlyRole(WARDEN_ROLE) public {
        
        ERC20(_token).transfer(_recipient, _amount);
        
        emit Withdrawal(_token, _recipient, _amount);
    }
}
