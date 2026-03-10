from algotradecamp import birdeye_bot
import pandas as pd
import openai_key
import datetime
import dontshare as d 
import requests 
import time
import nice_funcs as n
new_data = True # THIS ONLY RUNS FOR NEW DATA IF THIS IS TRUE
'''
MARKET_CAP_MAX = 30000  # max market cap *ONLY APPLIES IF TRUE*
NUM_TOKENS_2SEARCH = 15000  # number of tokens to search
MIN_24HR_VOLUME = 1000  # min 24 hour volume *ONLY APPLIES IF TRUE*

MAX_SELL_PERCENTAGE = 70  # if the sell % more than MAX_SELL_PERCENTAGE
MIN_TRADES_LAST_HOUR = 9  # if there are less than MIN_TRADES_LAST_HOUR
MIN_UNQ_WALLETS2hr = 30  # if there are less than MIN_UNQ_WALLETS2hr
MIN_VIEW24h = 15  # if there are less than MIN_VIEW24h views
MIN_LIQUIDITY = 400  # if there is less than MIN_LIQUIDITY


'''
MAX_SELL_PERCENTAGE = 70 # Maximum allowed sell percentage
MIN_TRADES_LAST_HOUR = 5 # Minimum number of trades in the last hour 

# THIS ONLY RUN IF NEW DATA TRUE
if new_data:
    # Run BirdEye bot to get meme token data
    data = birdeye_bot()
else:
    # Load the data from CSV
    data = pd.read_csv('filtered_pricechange_with_urls.csv')
    print(data)

# In the df, if the v24hUSD column has a number in it, drop it from the data and make a new df
def new_launches(data):
    # Create a new DataFrame with rows where 'v24hChangePercent' is NaN (empty)
    new_launches = data[data['v24hChangePercent'].isna()]

    # Generate a timestamp for the current date and time
    timestamp = datetime.datetime.now().strftime("%m-%d-%H")

    # Construct the CSV file name with the timestamp
    csv_filename = f'new_launches-{timestamp}.csv'

    # Save the new launches DataFrame as a CSV file with the generated filename
    new_launches.to_csv(csv_filename, index=False)

    print(new_launches)

    return new_launches


new_launches(data)

'''
THIS OUTPUTS THE LAST 250 ORDERS FROM THE CONTRACTS ADDRESS
THE LAST OUPUT IS THE FURDHEST BACK IN TIME
THE FIRST OUTPUT IS THE MOST RECENT
'''
# Function to nicely print the response

    for item in response_data['items']:
        print(f"Transaction Hash: {item['txHash']}")
        print(f"Source: {item['source']}")
        print(f"Block Time: {item['blockUnixTime']}")
        print(f"From: {item['from']['symbol']} (Amount: {item['from']['uiAmount']})")
        print(f"To: {item['to']['symbol']} (Amount: {item['to']['uiAmount']})")
        print("-" * 30)



new_launches = new_launches(data)

def analyze_trades(transactions):
    buy_count = 0
    sell_count = 0
    trades_last_hour = 0
    current_time = datetime.datetime.now(datetime.timezone.utc)

    for item in transactions:
        # Check if the trade is a buy or sell
        if item['from']['symbol'] == 'SOL':
            buy_count += 1
        elif item['to']['symbol'] == 'SOL':
            sell_count += 1

        # Check if the trade occurred in the last hour
        trade_time = datetime.datetime.fromtimestamp(item['blockUnixTime'])
        if (current_time - trade_time).total_seconds() < 3600:
            trades_last_hour += 1

    # Calculate percentages
    total_trades = buy_count + sell_count
    buy_percentage = (buy_count / total_trades * 100) if total_trades else 0
    sell_percentage = (sell_count / total_trades * 100) if total_trades else 0

    print(f"Buy Percentage: {buy_percentage:.2f}%")
    print(f"Sell Percentage: {sell_percentage:.2f}%")
    print(f"Trades in the last hour: {trades_last_hour}")

    sell_condition = sell.percentage > MAX_SELL_PERCENTAGE
    trade_condition = trades_last_hour < MIN_TRADES_LAST_HOUR

    return sell_condition, trade_condition


def analyze_trades(transactions):
    buy_count = 0
    sell_count = 0
    trades_last_hour = 0
    current_time = datetime.datetime.now(datetime.timezone.utc)

    for item in transactions:
        # Check if the trade is a buy or sell
        if item['from']['symbol'] == 'SOL':
            buy_count += 1
        elif item['to']['symbol'] == 'SOL':
            sell_count += 1

        # Check if the trade occurred in the last hour
        trade_time = datetime.datetime.fromtimestamp(item['blockUnixTime'])
        if (current_time - trade_time).total_seconds() < 3600:
            trades_last_hour += 1

    # Calculate percentages
    total_trades = buy_count + sell_count
    buy_percentage = (buy_count / total_trades * 100) if total_trades else 0
    sell_percentage = (sell_count / total_trades * 100) if total_trades else 0

    print(f"Buy Percentage: {buy_percentage:.2f}%")
    print(f"Sell Percentage: {sell_percentage:.2f}%")
    print(f"Trades in the last hour: {trades_last_hour}")

new_launches = new_launches(data)
filtered_data = new_launches.copy()

if new_data == True: 
# Loop through the DataFrame
for index, row in new_launches.iterrows():
    transactions = []
    token_url = row['token_url']
    for offset in range(0, 250, 50):  # Loop to get 250 trades, 50 at a time
        # Construct the URL with the address from the current row, including offset
        url = f"https://public-api.birdeye.so/defi/txs/token?address={row['address']}&offset={offset}"

        # Headers including your API key
        headers = {"X-API-KEY": d.birdeye}

        # Make the GET request
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            response_data = json.loads(response.text)
            transactions.extend(response_data['data']['items'])  # Extend the transactions list
        else:
            print(f"Failed to retrieve data for address {row['address']} at offset {offset}")
            time.sleep(1)  # Sleep to avoid hitting rate limits

    # After retrieving all transactions for a contract address, analyze them
    print(f"Analysis for contract address {row['address']}:")

    # Call analyze_trades once and use its results
    sell_condition, trade_condition = analyze_trades(transactions, token_url)

    # Print the analysis results
    print('')
    print('------------------------')

    # Use the results for condition checking
    if sell_condition or trade_condition:
filtered_data.drop(index, inplace=True)

time.sleep(1)

filtered_data.to_csv('data/sol_new_removed_trash.csv', index=False)

# Load the CSV with addresses
df = pd.read_csv('/Users/tc/Dropbox/dev/github/On-Chain-Solana-Trading-Bot/data/nice_addresses.csv')

# Create an empty DataFrame for the results
results_df = pd.DataFrame()

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    # Use the 'token_overview' function from 'nice_funcs' for each address
    address = row['address']
    token_data = n.token_overview(address)

    # If token_data is not None, append the data to the results DataFrame
    if token_data is not None:
        token_data['address'] = address  # Add the address to the data

        # Check for rug_pull; if True, skip this entry
        if not token_data.get('rug_pull', False):
            # Create a copy to avoid SettingWithCopyWarning in pandas
            temp_data = token_data.copy()

            # Drop the priceChangesXhrs field from the copy
            temp_data.pop('priceChangesXhrs', None)

            # Create the URL and add it to the temp_data
            temp_data['url'] = f"https://dexscreener.com/solana/{address}"

            # Append the modified copy to the results DataFrame
            results_df = results_df.append(temp_data, ignore_index=True)

# Save the results to a CSV file
csv_file_path = '/Users/tc/Dropbox/dev/github/On-Chain-Solana-Trading-Bot/data/nice_results.csv'
results_df.to_csv(csv_file_path, index=False)

# Print the final DataFrame
print(results_df)

#LOOK AT THE LAST 250 ORDERS AND IF THEY MOSTLY BUYS OR MOSTLY SELLS RETURN PROCENTATGE BUYS VS SELLS 
#LOOK HOW MANY TRADES WERE IN THE LAST HOUR AND RETURN THAT NUMBER 

# if the sell % > 70% then drop the token and whole row from the list
# if there are less than 5 trades in the last hour, drop the token and whole row from the list
# after doing the above 2 things, save new list as 'sol_new_launches-mm-dd-hh.csv'


'''
STRATEGY

STEP 1 to build sniper bot
- get a constant stream of the new tokens launched and then we can loops through the functions below in order to filter out the trash and find the gems

1. pull all data from bird and get the volume, tvl, 24h trade, 24h vies, market cap (under 500k)
   - list of fresh tokens
     - get their contract address
       == address
     - get their market cap
       == mcap
     - get their volume
       == v24hUSD
     - get their price
     - get their 24 hour trades
     - get their tvl == liquidity in output
       liquidity == tvl
     - check recent sells and buys to make sure there is vol

       lastTradeUnixTime == the time last trade, make sure there are trades
       v24hUSD == volume in last 24 hours
       mc == market cap

2. analyze that data to decide which is best to buy
   - use llms
   - use gpt vision

3. buy 5 top memes of the day after data analysis

IDEAS
- follow traders profiles, especially other bots
- will birdeye ever have airdrops? - probably gotta log in to birdeye
- looking at 24 hour volume could be solid if we filter out big tokens
  - but its not really the sniper that we want, just an idea for later
- looking at 24 hours price change will give us tokens after they pump
# filter to make sure last trade was recent
# filter to make sure liquidity is over Y
- look into the token security of them on the api to see if liq locked
- get the number of holders
- see all last trades aka recent trades and read the book a bit cayse we can see if people are buying and selling
- run all the different ways we can sort, and then put them together based on their contract address

API


'''





















# now we have the new_launches csv but there could also be some goodies up in the filtered_

#### RULES FOR SNIPER BOT #####
# if v24hchangepercent is NaN == new launch
# look through API and send in the contract addresses 1 by 1 to try to fulfill the rules
# Add GPT Vision to analyze the chart and recent orders.

# Chart analysis should look for an uptrend on the 5 min, 15 min, and 1 hour timeframes.

# Determine the launch date.

# Check if the token has a website. If it does, verify that it works. If not — likely a rug.

# Recent orders should show many transactions (more than 5–10 per hour).
# Double-check that they are not all from the same wallet address.
# If most orders are red and more than 60% are sells, avoid it.

# Check the holders, the change in holders over time, and the rate of that change.

# GPT Vision should look at the rubric in the top-left to see the 24-hour change.

# When there is no 24-hour change in the output, we know the token has just launched.

