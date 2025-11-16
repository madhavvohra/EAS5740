// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract AMM is AccessControl{
    
    bytes32 public constant LP_ROLE = keccak256("LP_ROLE");
    uint256 public invariant;
    address public tokenA;
    address public tokenB;
    uint256 feebps = 3;
    event Swap( address indexed _inToken, address indexed _outToken, uint256 inAmt, uint256 outAmt );
    event LiquidityProvision( address indexed _from, uint256 AQty, uint256 BQty );
    event Withdrawal( address indexed _from, address indexed recipient, uint256 AQty, uint256 BQty );

    /*
      Constructor sets the addresses of the two tokens
    */
    constructor( address _tokenA, address _tokenB ) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender );
        _grantRole(LP_ROLE, msg.sender);

        require( _tokenA != address(0), 'Token address cannot be 0' );
        require( _tokenB != address(0), 'Token address cannot be 0' );
        require( _tokenA != _tokenB, 'Tokens cannot be the same' );
        tokenA = _tokenA;
        tokenB = _tokenB;
    }


    function getTokenAddress( uint256 index ) public view returns(address) {
        require( index < 2, 'Only two tokens' );
        if( index == 0 ) {
            return tokenA;
        } else {
            return tokenB;
        }
    }

    /*
      The main trading functions
      
      User provides sellToken and sellAmount

      The contract must calculate buyAmount using the formula:
    */
    function tradeTokens( address sellToken, uint256 sellAmount ) public {
        require( invariant > 0, 'No liquidity' );
        require( sellToken == tokenA || sellToken == tokenB, 'Invalid token' );
        require( sellAmount > 0, 'Cannot trade 0' );

        address buyToken = sellToken == tokenA ? tokenB : tokenA;
        
        // Define the reserve quantities based on the tokens
        uint256 reserveIn;  // Reserve of the token being sold (In)
        uint256 reserveOut; // Reserve of the token being bought (Out)
        
        if (sellToken == tokenA) {
            reserveIn = ERC20(tokenA).balanceOf(address(this));
            reserveOut = ERC20(tokenB).balanceOf(address(this));
        } else { // sellToken == tokenB
            reserveIn = ERC20(tokenB).balanceOf(address(this));
            reserveOut = ERC20(tokenA).balanceOf(address(this));
        }
        
        // 1. Calculate the fee-adjusted amount being deposited
        uint256 amountInAfterFee = sellAmount * (10000 - feebps) / 10000;

        // 2. Calculate the amountOut using the Uniswap formula: amountOut = (reserveOut * amountInAfterFee) / (reserveIn + amountInAfterFee)
        uint256 numerator = reserveOut * amountInAfterFee;
        uint256 denominator = reserveIn + amountInAfterFee;
        
        uint256 amountOut = numerator / denominator;
        
        // 3. Ensure the calculated output amount is valid
        require(amountOut > 0, 'Trade requires more liquidity');
        require(reserveOut >= amountOut, 'Insufficient output reserve');

        // 4. Pull the sellToken into the contract (full amount)
        ERC20(sellToken).transferFrom(msg.sender, address(this), sellAmount);
        
        // 5. Push the buyToken out to the sender
        ERC20(buyToken).transfer(msg.sender, amountOut);
        
        // 6. Update the invariant with the new, actual balances
        uint256 newBalanceA = ERC20(tokenA).balanceOf(address(this));
        uint256 newBalanceB = ERC20(tokenB).balanceOf(address(this));
        
        uint256 new_invariant = newBalanceA * newBalanceB;
        
        require( new_invariant >= invariant, 'Bad trade: Invariant violation' );
        invariant = new_invariant;
        
        emit Swap( sellToken, buyToken, sellAmount, amountOut );
    }

    /*
      Use the ERC20 transferFrom to "pull" amtA of tokenA and amtB of tokenB from the sender
    */
    function provideLiquidity( uint256 amtA, uint256 amtB ) public {
        require( amtA > 0 || amtB > 0, 'Cannot provide 0 liquidity' );
        
        // 1. Pull tokens from the sender using transferFrom
        if (amtA > 0) {
            ERC20(tokenA).transferFrom(msg.sender, address(this), amtA);
        }
        if (amtB > 0) {
            ERC20(tokenB).transferFrom(msg.sender, address(this), amtB);
        }

        // 2. Update the invariant.
        uint256 currentBalanceA = ERC20(tokenA).balanceOf(address(this));
        uint256 currentBalanceB = ERC20(tokenB).balanceOf(address(this));
        
        // Check if this is the initial liquidity provision
        if (invariant == 0) {
            invariant = currentBalanceA * currentBalanceB;
        } else {
            // For simplicity, update invariant with new total reserves
            invariant = currentBalanceA * currentBalanceB;
        }
        
        emit LiquidityProvision( msg.sender, amtA, amtB );
    }

    /*
      Use the ERC20 transfer function to send amtA of tokenA and amtB of tokenB to the target recipient
      The modifier onlyRole(LP_ROLE) 
    */
    function withdrawLiquidity( address recipient, uint256 amtA, uint256 amtB ) public onlyRole(LP_ROLE) {
        require( amtA > 0 || amtB > 0, 'Cannot withdraw 0' );
        require( recipient != address(0), 'Cannot withdraw to 0 address' );
        
        // Check contract balances before transferring
        if( amtA > 0 ) {
            require(ERC20(tokenA).balanceOf(address(this)) >= amtA, 'Insufficient TokenA balance in AMM');
            ERC20(tokenA).transfer(recipient, amtA);
        }
        if( amtB > 0 ) {
            require(ERC20(tokenB).balanceOf(address(this)) >= amtB, 'Insufficient TokenB balance in AMM');
            ERC20(tokenB).transfer(recipient, amtB);
        }
        
        // Re-calculate and update the invariant with the new, reduced reserves
        invariant = ERC20(tokenA).balanceOf(address(this)) * ERC20(tokenB).balanceOf(address(this));
        
        emit Withdrawal( msg.sender, recipient, amtA, amtB );
    }
}
