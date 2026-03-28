import streamlit as st
import requests

# Constants
API_URL = "http://localhost:8000/generate_assertions"

st.set_page_config(
    page_title="VeriGen SVA Generator",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("VeriGen: SVA Generator")
st.markdown("A simple interface to generate **SystemVerilog Assertions (SVA)** from RTL snippets.")

# Input Section
st.subheader("RTL Input")
rtl_input = st.text_area(
    "Paste your SystemVerilog RTL code here:",
    height=250,
    placeholder="always_ff @(posedge clk or negedge rst_n) begin\n    if (!rst_n) ...\nend"
)

# Optional Inputs expander
with st.expander("Advanced Options", expanded=False):
    clock_hint = st.text_input("Clock Signal (Optional)", placeholder="e.g. posedge clk")
    sync_filter = st.selectbox("Preferred Example Type", options=["Auto", "True", "False"], index=0)

# Generate Button
if st.button("Generate Assertions", type="primary"):
    if not rtl_input.strip():
        st.error("Please enter some RTL code before generating.")
    else:
        with st.spinner("Analyzing RTL and thinking... (this may take a few seconds)"):
            # Prepare request payload
            payload = {
                "rtl_code": rtl_input,
                "clock_hint": clock_hint if clock_hint else None,
                "synchronous_filter": sync_filter if sync_filter != "Auto" else None
            }

            try:
                # Call the local verigen backend API
                response = requests.post(API_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    assertions = data.get("assertions", "")
                    explanation = data.get("explanation", "")

                    st.success("Assertions generated successfully!")
                    
                    st.subheader("Generated SVA")
                    if assertions:
                        # Assuming the backend provides raw SV text (usually starting with `systemverilog)
                        st.markdown(assertions)
                    else:
                        st.warning("No assertions were returned by the API.")
                        
                    st.subheader("Explanation & CoT Reasoning")
                    if explanation:
                        st.markdown(explanation)
                    else:
                        st.info("No explanation was returned.")
                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to the VeriGen API. Is the backend server running? (python api.py)")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
