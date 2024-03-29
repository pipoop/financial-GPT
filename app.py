import streamlit as st
from openai import OpenAI
import requests
from urllib.request import urlopen
import certifi
import json
import pandas as pd
from chatstock import chat_stock
import yfinance as yf
from researcher import generate_response
from researcher_multi_agent import generate_premium_response

from database import connect_2_db
from pymongo import MongoClient

import os
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()

FMP_API_KEY = os.environ.get('FMP_API_KEY')
ALPHAVANTAGE_API_KEY = os.environ.get('ALPHAVANTAGE_API_KEY')


def get_jsonparsed_data(url):
    try:
        response = urlopen(url, cafile=certifi.where())
        data = response.read().decode("utf-8")
        return json.loads(data)

    except Exception as e:
        print(f"HTTP Error on url {url}: {e}")    
    

# Step 1: Retrieving Financial Statements
def get_financial_statements(ticker, limit, period, statement_type):
    if statement_type == "Income Statement":
        url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period={period}&limit={limit}&apikey={FMP_API_KEY}"
    elif statement_type == "Balance Sheet":
        url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period={period}&limit={limit}&apikey={FMP_API_KEY}"
    elif statement_type == "Cash Flow":
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period={period}&limit={limit}&apikey={FMP_API_KEY}"
    
    data = get_jsonparsed_data(url)
    print(data)
    return data


# Step 1: Retrieving key financial metrics for given periods
def get_key_metrics(ticker, limit, period):
    url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period={period}&limit={limit}&apikey={FMP_API_KEY}"
    data = get_jsonparsed_data(url)
    print(data)
    return data

# Step 1: Retrieving esg info for a company
# "Special Endpoint : This endpoint is not available under your current subscription 
# please visit our subscription page to upgrade your plan at https://site.financialmodelingprep.com/developer/docs/pricing"
def get_esg_info(ticker):
    url = f"https://financialmodelingprep.com/api/v4/esg-environmental-social-governance-data?symbol={ticker}&apikey={FMP_API_KEY}"
    data = get_jsonparsed_data(url)
    print(data)
    # url = f"https://financialmodelingprep.com/api/v4/esg-environmental-social-governance-data-ratings?symbol={ticker}&apikey={FMP_API_KEY}"
    # data = get_jsonparsed_data(url)
    return data

# use researcher instead 
def get_esg_info_by_name(company_name):
    # data = generate_response(f"Scrape relevant ESG website for {company_name} and provide ESG analysis for this company.")
    data = generate_response(f"What is ESG rating and benchmarking score for {company_name}?")
    return data

# use yfinance instead
def get_recommendation(ticker):
    yf_ticker = yf.Ticker(ticker)
    if yf_ticker:
        data = yf_ticker.recommendations.to_json()
        print(data)
        return data

# Step 1: Retrieving financial news for a company
# "Special Endpoint : This endpoint is not available under your current subscription 
# please visit our subscription page to upgrade your plan at https://site.financialmodelingprep.com/developer/docs/pricing"
def get_financial_news(ticker, limit, page):
    url = f"https://financialmodelingprep.com/api/v3/stock_news?symbol={ticker}&limit={limit}&page={page}&apikey={FMP_API_KEY}"
    data = get_jsonparsed_data(url)
    print(data)
    return data

# use yfinance instead
def get_financial_news(ticker):
    yf_ticker = yf.Ticker(ticker)
    if yf_ticker:
        data = yf_ticker.news
        print(data)
        return data


# Step 2: Generate Financial Statements Summary with GPT-4
def generate_financial_statements_summary(financial_statements):
    """
    Generate a summary of financial statements for the statements using GPT-3.5 Turbo or GPT-4.
    """    
    # Create a summary of key financial metrics for all four periods
    summaries = []
    if financial_statements:
        for i in range(len(financial_statements)):
            
            summary = f"""
                For the period ending {financial_statements[i]['date']}, the company reported the following:
                {financial_statements[i]}
                """
            
            print(summary)
            summaries.append(summary)

    # Combine all summaries into a single string
    all_summaries = "\n\n".join(summaries)
    return all_summaries

   
# Step 2: Get Key Metrics directly from FMP API
def generate_key_metrics_summary(key_metrics):
    """
    Get a summary of financial key metrics using FMP API.
    Statement Analysis
    Key Metrics
    - Get key financial metrics for a company, including revenue, net income, earnings per share (EPS), and price-to-earnings ratio (P/E ratio). 
    - Assess a company's financial performance and compare it to its competitors.
    """

    # Use FMP API to get key financial metrics for all four periods
    summaries = []
    if key_metrics:
        for i in range(len(key_metrics)):
            
            summary = f"""
                For the period ending {key_metrics[i]['date']}, the company reported the following:
                {key_metrics[i]}
                """
            
            print(summary)
            summaries.append(summary)

    # Combine all summaries into a single string
    all_summaries = "\n\n".join(summaries)
    return all_summaries


# Step 3: Call GPT-4 for final analysis
def final_analysis(objective, all_summaries):

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=[
            {
                "role": "system",
                "content": f"You are an AI trained to provide financial analysis based on {objective}.",
            },
            {
                "role": "user",
                "content": f"""
                Please analyze the following data and provide insights:\n{all_summaries}.\n 
                Write each section out as instructed in the summary section and then provide analysis of how it's changed over the time period.
                ...
                """
            }
        ]
    )
    return response.choices[0].message.content


# Step 4: Building the Streamlit App
# Selecting financial assistant 1: financial_statements
def financial_statements():
    st.title('GPT 4 Financial Statements :bird:')

    statement_type = st.selectbox("Select financial statement type:", ["Income Statement", "Balance Sheet", "Cash Flow"])

    col1, col2 = st.columns(2)

    with col1:
        period = st.selectbox("Select financial period:", ["Annual", "Quarter"]).lower()

    with col2:
        limit = st.number_input("Number of past financial statements to analyze:", min_value=1, max_value=10, value=4)
    
    ticker_input = st.text_input("Please enter the company ticker (such as MSFT):")
    company_name = st.text_input("Don't know company ticker? Try to enter company name instead (such as Microsoft):")
    
    if st.button('Run'):
        with st.spinner("In progress..."):
            if ticker_input: # always prioritize to use ticker_input
                ticker = ticker_input
            elif company_name:
                ticker = get_ticker_by_gpt(company_name)
                print(f"the company ticker for {company_name} is {ticker}")
            if ticker:
                ticker = ticker.upper()
                financial_statements = get_financial_statements(ticker, limit, period, statement_type)

                with st.expander("View Financial Statements"):
                    st.dataframe(frame_data(financial_statements))

                statements_summary = generate_financial_statements_summary(financial_statements)

                final_statements_summary = final_analysis("Financial Statements", statements_summary)

                st.write(f'Summary for {ticker} {statement_type}:\n\n {final_statements_summary}\n\n')
        st.success('Done!')

# Selecting financial assistant 2: financial_metrics
def financial_metrics():
    st.title('GPT 4 Financial Metrics :bird:')

    col1, col2 = st.columns(2)

    with col1:
        period = st.selectbox("Select financial period:", ["Annual", "Quarter"]).lower()

    with col2:
        limit = st.number_input("Number of past financial metrics to analyze:", min_value=1, max_value=10, value=4)
    
    ticker_input = st.text_input("Please enter the company ticker (such as MSFT):")
    company_name = st.text_input("Don't know company ticker? Try to enter company name instead (such as Microsoft):")
    
    if st.button('Run'):
        with st.spinner("In progress..."):
            if ticker_input: # always prioritize to use ticker_input
                ticker = ticker_input
            elif company_name:
                ticker = get_ticker_by_gpt(company_name)
                print(f"the company ticker for {company_name} is {ticker}")
            if ticker:
                ticker = ticker.upper()
                key_metrics = get_key_metrics(ticker, limit, period)
            
                with st.expander("View Key Metrics"):
                    st.dataframe(frame_data(key_metrics))

                key_metrics_summary = generate_key_metrics_summary(key_metrics)

                final_key_metrics_summary = final_analysis("Financial Metrics", key_metrics_summary)

                st.write(f'Summary for {ticker} key metrics:\n\n {final_key_metrics_summary}\n\n')
        st.success('Done!')

# Selecting financial assistant 3: esg_analysis
def esg_analysis():
    st.title('GPT 4 ESG Analysis :bird:')

    company_name = st.text_input("Please enter the company name (such as Microsoft):")
    # ticker_input = st.text_input("Please enter the company ticker (such as MSFT):")
    # company_name = st.text_input("Don't know company ticker? Try to enter company name instead (such as Microsoft):")
    
    if st.button('Run'):
        with st.spinner("In progress..."):
            # if ticker_input: # always prioritize to use ticker_input
            #     ticker = ticker_input
            # elif company_name:
            #     ticker = get_ticker_by_gpt(company_name)
            #     print(f"the company ticker for {company_name} is {ticker}")  
            # if ticker:
            #     ticker = ticker.upper()
            #     esg_info = get_esg_info(ticker)
            #     final_esg_summary = final_analysis("ESG Analysis", esg_info)
            if company_name:
                final_esg_summary = get_esg_info_by_name(company_name)

                st.write(f'Summary for {company_name} ESG analysis:\n\n {final_esg_summary}\n\n')
        st.success('Done!')


# Selecting financial assistant 4: financial_news
def financial_news():
    st.title('GPT 4 Financial News :bird:')

    # col1, col2 = st.columns(2)

    # with col1:
    #     page = st.number_input("Pages of past financial news to analyze:", min_value=0, max_value=4, value=0)

    # with col2:
    #     limit = st.number_input("Number of past financial news to analyze:", min_value=1, max_value=50, value=4)
    
    ticker_input = st.text_input("Please enter the company ticker (such as MSFT):")
    company_name = st.text_input("Don't know company ticker? Try to enter company name instead (such as Microsoft):")
    
    if st.button('Run'):
        with st.spinner("In progress..."):
            if ticker_input: # always prioritize to use ticker_input
                ticker = ticker_input
            elif company_name:
                ticker = get_ticker_by_gpt(company_name)
                print(f"the company ticker for {company_name} is {ticker}")   
            if ticker:
                ticker = ticker.upper()
                # financial_news = get_financial_news(ticker, limit, page)
                financial_news = get_financial_news(ticker)
                final_financial_news = final_analysis("Financial News", financial_news)

                st.write(f'Summary for {ticker} financial news:\n\n {final_financial_news}\n\n')
        st.success('Done!')

# Selecting financial assistant 5: chat_with_stocks
def chat_with_stocks():
    st.title('GPT 4 Chat With Stocks :bird:')
    st.subheader('(Not Financial Advices)')
    chat_stock()

# Selecting financial assistant 6: premium research
def premium_research():
    st.title('GPT 4 Premium Research :bird:')

    api_key = st.text_input("Please enter your access code to continue (DM me on Linkedin to get access)", type="password")
    if api_key:
        # check if api_key is valid
        users, _ = connect_2_db()
        find_api_key = users.find_one({"api_key": api_key})
        if find_api_key:
            # continue with premium query
            premium_query = st.text_input("Please enter your research question or task")
            
            if st.button('Run'):
                    with st.spinner("In progress..."):
                        if premium_query:
                            data = generate_premium_response(premium_query)
                            st.write(data)
                    st.success('Done!')
        else:
            st.warning("access code is invalid, please retry or get new code")

# Panda frame the data
def frame_data(data):
    if isinstance(data, list) and data:
        return pd.DataFrame(data)
    else:
        st.error("Unable to fetch financial statements. Please ensure the ticker is correct and try again.")
        return pd.DataFrame()


# get company ticker by name
# option 1: yahoo finance api only accepts user-agent by browser request, not by streamlit app
def get_ticker_by_yahoo(company_name):
    yfinance = "https://query2.finance.yahoo.com/v1/finance/search"
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    params = {"q": company_name, "quotes_count": 1, "country": "United States"}

    res = requests.get(url=yfinance, params=params, headers={'User-Agent': user_agent})
    print(res.status_code)
    print(res.text)

    data = res.json()

    company_code = data['quotes'][0]['symbol']

    if company_code:
        print(f"The ticker symbol for {company_name} is {company_code}")
    else:
        print(f"Could not find the ticker symbol for {company_name}")

    return company_code

# option 2: use GPT to get ticker name, works perfectly but with cost
def get_ticker_by_gpt(company_name):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=[
            {
                "role": "system",
                "content": f"""
                You are an Financial expert that knows Stock Ticker Symbol for all listed companies,
                You should only provide the ticker name as response, typically no more than four letters, 
                you should return nothing else than stock ticker symbol for given company {company_name}.
                For example:
                you should return MSFT for microsoft,
                you should return AAPL for apple,
                you should return ERIC for ericsson,
                you should return AMZN for Amazon,
                """
            },
            # {
            #     "role": "user",
            #     "content": f"""
            #     what is Stock Ticker Symbol for {company_name}? 
            #     """
            # }
        ]
    )

    company_code = response.choices[0].message.content

    if company_code:
        print(f"The ticker symbol for {company_name} is {company_code}")
    else:
        print(f"Could not find the ticker symbol for {company_name}")

    return company_code
        
# get company ticker by name
# option 3: use alpha vantage api, but often return wrong infomation
def get_ticker(company_name):
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={company_name}&apikey={ALPHAVANTAGE_API_KEY}"
    res = requests.get(url)
    print(res.status_code)
    print(res.text)
    data = res.json()

    print(data)

    company_code = data['bestMatches'][0]['1. symbol']

    if company_code:
        print(f"The ticker symbol for {company_name} is {company_code}")
    else:
        print(f"Could not find the ticker symbol for {company_name}")

    return company_code

# get_ticker("apple")
# # The ticker symbol for apple is APLE
# get_ticker("microsoft")
# # The ticker symbol for microsoft is MSF0.FRK
# get_ticker("ericsson")
# # The ticker symbol for ericsson is ERIXF
# get_ticker("amazon")
# # The ticker symbol for amazon is AMZN
# get_ticker("china telecom")
# # The ticker symbol for china telecom is ZCH.FRK
# get_ticker("atlas copco")
# # The ticker symbol for atlas copco is ATLCY


# finally, to run main application
def main():
    st.set_page_config(page_title="AI Financial Analyst", page_icon=":bird:")

    st.sidebar.title('AI Financial Analyst :bird:')
    st.sidebar.markdown("Demo by [Qiang Li](https://www.linkedin.com/in/qianglil/). All rights reserved.")

    # this markdown is for hiding "github" button
    st.markdown("<style>#MainMenu{visibility:hidden;}</style>", unsafe_allow_html=True)
    st.markdown("<style>footer{visibility: hidden;}</style>", unsafe_allow_html=True)
    st.markdown("<style>header{visibility: hidden;}</style>", unsafe_allow_html=True)
    st.markdown(
    """
    <style>
    .css-1jc7ptx, .e1ewe7hr3, .viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, .viewerBadge_link__1S137, .viewerBadge_text__1JaDK{display: none;} 
    </style>
    """,
    unsafe_allow_html=True
    )

    st.sidebar.header("Settings")
    app_mode = st.sidebar.selectbox("Choose your AI assistant:",
        ["Chat With Stocks", "Financial Statements", "Financial Metrics", "ESG Analysis", "Financial News", "Premium Insights"])
    if app_mode == 'Financial Statements':
        financial_statements()
    if app_mode == 'Financial Metrics':
        financial_metrics()    
    if app_mode == 'ESG Analysis':
        esg_analysis()   
    if app_mode == 'Financial News':
        financial_news()   
    if app_mode == 'Chat With Stocks':
        chat_with_stocks()
    if app_mode == 'Premium Insights':
        premium_research()   


if __name__ == '__main__':
    main()