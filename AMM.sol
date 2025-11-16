// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol"; // Use SafeMath for clarity on overflow/underflow protection

contract AMM is AccessControl{
    using SafeMath for uint256; // Use SafeMath for all uint256 operations
    
    bytes32 public constant LP_ROLE = keccak256("LP_ROLE");
    uint256 public invariant;
    address public tokenA;
    address public tokenB;
    uint256 feebps = 3; // The fee in basis points (i.e., the fee should be feebps/10000)

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
      Use the ERC20 transferFrom to "pull" amtA of tokenA and amtB of tokenB from the sender
    */
    function provideLiquidity( uint256 amtA, uint256 amtB ) public {
        require( amtA > 0 || amtB > 0, 'Cannot provide 0 liquidity' );
        
        // 1. Pull tokens from the sender using transferFrom
        // The sender must have approved this AMM contract prior to this call.
        if (amtA > 0) {
            ERC20(tokenA).transferFrom(msg.sender, address(this), amtA);
        }
        if (amtB > 0) {
            ERC20(tokenB).transferFrom(msg.sender, address(this), amtB);
        }

        // 2. Update the invariant.
        // On the very first liquidity provision, the invariant is simply R_A * R_B.
        // For subsequent provisions, the invariant is updated implicitly by the balances.
        uint256 currentBalanceA = ERC20(tokenA).balanceOf(address(this));
        uint256 currentBalanceB = ERC20(tokenB).balanceOf(address(this));
        
        // Check if this is the initial liquidity provision
        if (invariant == 0) {
            invariant = currentBalanceA.mul(currentBalanceB);
        } else {
            // For simplicity in this assignment, we allow any amount to be added, 
            // and the invariant is simply updated by the new balances.
            // A real AMM would check ratio integrity here.
            invariant = currentBalanceA.mul(currentBalanceB);
        }
        
        emit LiquidityProvision( msg.sender, amtA, amtB );
    }

    /*
      The main trading function.
      
      User provides sellToken and sellAmount.
      The contract must calculate buyAmount using the Uniswap V2 invariant formula with fees.
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
        // Fee is feebps / 10000. Amount in after fee is sellAmount * (10000 - feebps) / 10000
        // (10000 - feebps) is the multiplier that remains after the fee is taken.
        uint256 amountInAfterFee = sellAmount.mul(10000..sub(feebps)).div(10000);

        // 2. Calculate the amountOut using the invariant formula: (R_in + A_in) * (R_out - A_out) = R_in * R_out
        // A_out = R_out - (R_in * R_out) / (R_in + A_in)
        // Since we are using the invariant K: A_out = R_out - K / (R_in + A_in)
        
        // New reserve of In token: R_in' = reserveIn + amountInAfterFee
        // New reserve of Out token: R_out' = invariant / R_in'
        
        // The Uniswap formula for amountOut:
        // amountOut = (reserveOut * amountInAfterFee) / (reserveIn + amountInAfterFee)
        
        uint256 numerator = reserveOut.mul(amountInAfterFee);
        uint256 denominator = reserveIn.add(amountInAfterFee);
        
        uint256 amountOut = numerator.div(denominator);
        
        // 3. Ensure the calculated output amount is valid (must be less than the reserve)
        require(amountOut > 0, 'Trade requires more liquidity');
        require(reserveOut >= amountOut, 'Insufficient output reserve');

        // 4. Pull the sellToken into the contract
        ERC20(sellToken).transferFrom(msg.sender, address(this), sellAmount);
        
        // 5. Push the buyToken out to the sender
        ERC20(buyToken).transfer(msg.sender, amountOut);
        
        // 6. Update the invariant with the new, actual balances
        // The actual balances reflect the full sellAmount deposited and amountOut sent
        uint256 newBalanceA = ERC20(tokenA).balanceOf(address(this));
        uint256 newBalanceB = ERC20(tokenB).balanceOf(address(this));
        
        // The invariant K = R_A * R_B should hold true or increase due to the fee.
        uint256 new_invariant = newBalanceA.mul(newBalanceB);
        
        require( new_invariant >= invariant, 'Bad trade: Invariant violation' ); // Safety check
        invariant = new_invariant;
        
        emit Swap( sellToken, buyToken, sellAmount, amountOut );
    }

    /*
      Use the ERC20 transfer function to send amtA of tokenA and amtB of tokenB to the target recipient
      The modifier onlyRole(LP_ROLE) restricts access to the initial liquidity provider.
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
        invariant = ERC20(tokenA).balanceOf(address(this)).mul(ERC20(tokenB).balanceOf(address(this)));
        
        emit Withdrawal( msg.sender, recipient, amtA, amtB );
    }
}
