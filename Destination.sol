// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    // Define the custom roles
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
    
    // Mapping: Source Chain Underlying Address => Destination Chain Wrapped Address
    mapping( address => address) public underlying_tokens;
    
    // Mapping: Destination Chain Wrapped Address => Source Chain Underlying Address
    mapping( address => address) public wrapped_tokens;
    
    // Array of all deployed BridgeToken addresses
    address[] public tokens;

    // Events for auditing and off-chain monitoring
    event Creation( address indexed underlying_token, address indexed wrapped_token );
    event Wrap( address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount );
    event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );

    constructor( address admin ) {
        // Grant initial roles to the admin address
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    /**
     * @notice Allows the WARDEN to mint wrapped tokens after a deposit on the source chain.
     * @param _underlying_token The address of the asset on the source chain.
     * @param _recipient The address that will receive the newly wrapped tokens on the destination chain.
     * @param _amount The amount of tokens to mint.
     */
    function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
        // 1. Check if the underlying asset is registered.
        address wrappedTokenAddress = underlying_tokens[_underlying_token];
        require(wrappedTokenAddress != address(0), "Destination: Underlying asset not registered");
        
        // 2. Mint the tokens using the BridgeToken contract instance.
        BridgeToken wrappedToken = BridgeToken(wrappedTokenAddress);
        
        // The BridgeToken contract's 'mint' function is restricted to the MINTER_ROLE,
        // which was granted to this Destination contract (the admin in BridgeToken constructor).
        wrappedToken.mint(_recipient, _amount);
        
        // 3. Emit the Wrap event
        emit Wrap(_underlying_token, wrappedTokenAddress, _recipient, _amount);
    }

    /**
     * @notice Allows any token holder to burn wrapped tokens to trigger a withdrawal on the source chain.
     * @param _wrapped_token The address of the BridgeToken being unwrapped (on the destination chain).
     * @param _recipient The address on the source chain that will receive the underlying tokens.
     * @param _amount The amount of tokens to burn.
     */
    function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
        // 1. Check if the wrapped token is registered (optional but safe).
        require(wrapped_tokens[_wrapped_token] != address(0), "Destination: Invalid wrapped token address");
        
        // 2. Get the BridgeToken instance.
        BridgeToken wrappedToken = BridgeToken(_wrapped_token);
        
        // 3. Burn the tokens from the caller's account.
        // The ERC20 standard requires burning from msg.sender.
        // The standard ERC20Burnable `burn` function is inherited by BridgeToken.
        // We use burnFrom to handle potential allowance/approvals for flexibility, but for a user burning their own tokens, the simple `burn` function would suffice. 
        // However, the `BridgeToken.sol` provided already includes an overridden `burnFrom` which allows the owner to burn without allowance, 
        // but here we want *any user* to burn their *own* tokens. The standard `ERC20Burnable.burn(amount)` is the correct simplest approach for the user burning their own tokens.
        // Since we are interacting with the `BridgeToken` instance, we call `wrappedToken.burn()`.
        
        // NOTE: BridgeToken inherits ERC20Burnable, which provides the `burn` function:
        wrappedToken.burn(_amount);
        
        // 4. Emit the Unwrap event
        address underlyingTokenAddress = wrapped_tokens[_wrapped_token];
        emit Unwrap(underlyingTokenAddress, _wrapped_token, msg.sender, _recipient, _amount);
    }

    /**
     * @notice Allows the CREATOR to deploy a new BridgeToken contract instance for a new underlying asset.
     * @param _underlying_token The address of the asset on the source chain.
     * @param name The name of the underlying asset.
     * @param symbol The symbol of the underlying asset.
     * @return The address of the newly deployed BridgeToken contract.
     */
    function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
        // 1. Ensure the asset is not already registered.
        require(underlying_tokens[_underlying_token] == address(0), "Destination: Underlying asset already registered");
        
        // 2. Deploy a new BridgeToken contract.
        // We pass the Destination contract's address (address(this)) as the admin/minter role 
        // so that this contract can call `mint` and `clawBack` on the new BridgeToken.
        BridgeToken newToken = new BridgeToken(_underlying_token, name, symbol, address(this));
        
        address newTokenAddress = address(newToken);
        
        // 3. Update the registration mappings and token list.
        underlying_tokens[_underlying_token] = newTokenAddress;
        wrapped_tokens[newTokenAddress] = _underlying_token;
        tokens.push(newTokenAddress);
        
        // 4. Emit the Creation event.
        emit Creation(_underlying_token, newTokenAddress);
        
        return newTokenAddress;
    }

}
