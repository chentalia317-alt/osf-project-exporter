'''
## =================================================================================================
## Title: Streamlit App to Download OSF Project to PDF                                            ##
## Project:                                                                                       ##
##      Export OSF Project to PDF - Centre for Open Science (CoS) & University of Manchester (UoM)##
## UoM Team:                                                                                      ##
##      Ramiro Bravo, Sarah Jaffa, Benito Matischen                                               ##
## Author(s):                                                                                     ##
##       Ramiro Bravo - ramiro.bravo@manchester.ac.uk - ramirobravo@gmail.com                     ##
## Create date:                                                                                   ##
##       July-2025                                                                                ##
## Description:                                                                                   ##
##      The Streamlit app serves as the front end application allowing users to download OSF      ##
##      project in PDF format.                                                                    ##
## Parameters:                                                                                    ##
##      OSF Project URL: Provide the URL of the project fro exapmle: https://osf.io/kzc68/        ##
##      Select API environment: Production or Test                                                ##
##      Token Source: Provided via .env file or entering the OSF API token.                       ##
##      OSF API Key: Allows users to enter (paste) the API key for private repositories           ##
## Running App locally: After setting up the docker container                                     ##
##    $ docker compose run -p 8501:8501 cli streamlit <script>                                    ##                                                   ##
##                                                                                                ##
## =================================================================================================
'''

import os
from datetime import datetime

import streamlit as st

import exporter.exporter as exporter

#page configuration
st.set_page_config(page_title="Export & Download OSF project to PDF",
                   #page_icon=":outbox_tray:",
                   page_icon=":arrow_down:",
                   layout="centered")

#REMOVE THE SETTING OPTIONS
st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)


st.title("📄 OSF Project PDF Exporter")

# Input fields
url = None
url = st.text_input("Enter OSF Project URL:", max_chars=30)
if url!="":
    osf_id = url.split(".io/")[1].strip("/")
    st.write(osf_id)


api_choice = st.radio("Select API Environment:", ["Production", "Test"])
is_test = True if api_choice == "Test" else False


st.subheader("🔐 OSF Project type")
project_type = st.radio("Choose project visibility: ", ["Public", "Private"])

osf_token = None
if project_type == "Private":
    # Token input
    st.subheader("🔑 OSF Token")
    token_source = st.radio("Choose token source:", ["Paste token manually", "Use .env file"])

    if token_source == "Paste token manually":
        osf_token = st.text_input("Enter your OSF API token:", type="password")
    else:
        osf_token = os.getenv("TEST_PAT")

st.write(exporter.MockAPIResponse.MARKDOWN_FILES)