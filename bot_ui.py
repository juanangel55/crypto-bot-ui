import streamlit as st
import sqlite3
import pandas as pd
import time

# Streamlit App Title
st.title("Crypto Trading Bot Dashboard")

# Sidebar for Controls
st.sidebar.header("Bot Controls")
bot_status = st.sidebar.radio("Bot Status", ["Running", "Stopped"])
manual_trade_token = st.sidebar.text_input("Enter Token Address for Manual Trade")
manual_trade_amount = st.sidebar.number_input("Enter Trade Amount", min_value=0.0)
if st.sidebar.button("Execute Manual Trade"):
    st.sidebar.write(f"Executing trade for {manual_trade_amount} of token {manual_trade_token}")

# Main Dashboard
st.header("Real-Time Data")

# Connect to the SQLite database
conn = sqlite3.connect("dex_data.db")

# Display Token Data
st.subheader("Token Data")
token_data = pd.read_sql_query("SELECT * FROM tokens", conn)
st.dataframe(token_data)

# Display Blacklisted Tokens
st.subheader("Blacklisted Tokens")
blacklisted_tokens = pd.read_sql_query("SELECT token_address, name FROM tokens WHERE is_rugged = 1", conn)
st.dataframe(blacklisted_tokens)

# Display Logs
st.subheader("Bot Logs")
log_placeholder = st.empty()

# Simulate Real-Time Updates
while bot_status == "Running":
    # Fetch latest data
    token_data = pd.read_sql_query("SELECT * FROM tokens", conn)
    blacklisted_tokens = pd.read_sql_query("SELECT token_address, name FROM tokens WHERE is_rugged = 1", conn)

    # Update DataFrames
    st.dataframe(token_data)
    st.dataframe(blacklisted_tokens)

    # Simulate logs
    log_placeholder.text("Bot is running... Fetching latest data.")
    time.sleep(5)  # Refresh every 5 seconds

# Stop the bot
if bot_status == "Stopped":
    st.write("Bot is stopped.")

# Close the database connection
conn.close()
