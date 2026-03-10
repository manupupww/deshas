'''this successfully outputs the tokens per addy inputted
put this in nice_funcs later
'''
import requests
import pandas as pd

def fetch_wallet_holdings(address):
    url = "https://api.mainnet-beta.solana.com/"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            address,
            {
                "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            },
            {
                "encoding": "jsonParsed"
            }
        ]
    }

    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()

    mint_addresses = []
    amounts = []

    if 'result' in response_data and 'value' in response_data['result']:
        for item in response_data['result']['value']:
            mint_address = item['account']['data']['parsed']['info']['mint']
            balance = item['account']['data']['parsed']['info']['tokenAmount']['uiAmount']
            if balance > 0:  # Only add rows where balance is greater than 0
                mint_addresses.append(mint_address)
                amounts.append(balance)

    # Create a DataFrame with mint addresses and amounts where amount > 0
    df = pd.DataFrame({'Mint Address': mint_addresses, 'Amount': amounts})

    return df

# Example usage
address = "5iuidX4HRaS3uhNKLKWYJdSmh7DZsTGjcJ4aC3GNAT8m"
dataframe = fetch_wallet_holdings(address)
    print(dataframe)

    # Save the filtered DataFrame to a CSV file
    dataframe.to_csv('data/token_per_addy.csv', index=False)

def get_token_balance(dataframe, token_mint_address):
    """
    Fetches the balance of a specific token given its mint address from a DataFrame.

    Parameters:
    - dataframe: A pandas DataFrame containing token balances with columns ['Mint Address', 'Amount']
    - token_mint_address: The mint address of the token to find the balance for.

    Returns:
    - The balance of the specified token if found, otherwise a message indicating the token is not found.
    """
    # Check if the token mint address exists in the DataFrame
    if token_mint_address in dataframe['Mint Address'].values:
        # Get the balance for the specified token
        balance = dataframe.loc[dataframe['Mint Address'] == token_mint_address, 'Amount'].iloc[0]
        return balance
    else:
        # If the token mint address is not found in the DataFrame, return a message indicating so
        return f"Token {token_mint_address} not found in the wallet." 

# Example usage, assuming 'dataframe' is the DataFrame returned by fetch_wallet_holdings function
token_mint_address = "TokenMintAddressHere"  # Replace 'TokenMintAddressHere' with the actual mint address
balance_message = get_token_balance(dataframe, token_mint_address)

print(f'balance: {balance_message}  for {token_mint_address}')
