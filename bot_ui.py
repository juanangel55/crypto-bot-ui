# bot_ui.py
import streamlit as st
import pandas as pd
from bot_logic import EnhancedDexScreenerBot

# Initialize the bot
bot = EnhancedDexScreenerBot()

# Streamlit App Title
st.title("Crypto Trading Bot Dashboard")

# Sidebar for Controls
st.sidebar.header("Bot Controls")
bot_status = st.sidebar.radio("Bot Status", ["Running", "Stopped"])

# Main Dashboard
st.header("Real-Time Data")

# Display Token Data
st.subheader("Token Data")
token_data = pd.read_sql_query("SELECT * FROM pairs", bot.engine)
st.dataframe(token_data)

# Display Blacklisted Tokens
st.subheader("Blacklisted Tokens")
blacklisted_tokens = pd.read_sql_query("SELECT * FROM blacklist", bot.engine)
st.dataframe(blacklisted_tokens)

# Display Logs
st.subheader("Bot Logs")
log_placeholder = st.empty()

# Simulate Real-Time Updates
if bot_status == "Running":
    log_placeholder.text("Bot is running... Fetching latest data.")
    bot.run()
else:
    st.write("Bot is stopped.")
