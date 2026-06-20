import streamlit as st
import pandas as pd
import io
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# API 키 세팅
if "TRACKINGMORE_API_KEY" in st.secrets:
    os.environ["TRACKINGMORE_API_KEY"] = st.secrets["TRACKINGMORE_API_KEY"]

from tracking_service import track_bulk_bl

st.set_page_config(page_title="Bulk B/L Tracker", layout="wide")

st.title("🚢 Bulk B/L Tracking Tool (Debug Mode)")
st.markdown("API 응답 구조 확인을 위한 디버그 모드입니다.")

st.subheader("1. Download Template")
sample_df = pd.DataFrame({"B_L_NUMBER": ["ONEYSUBG12277500", "HMCU1234567"]})
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    sample_df.to_excel(writer, index=False, sheet_name='Sheet1')

st.download_button(
    label="📥 Download Excel Template",
    data=buffer.getvalue(),
    file_name="bulk_bl_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.write("---")

st.subheader("2. Upload Your B/L List")
uploaded_file = st.file_uploader("Excel file", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name='Sheet1')
        if "B_L_NUMBER" in df.columns:
            bl_list = df["B_L_NUMBER"].dropna().astype(str).str.strip().tolist()
            unique_bl_list = list(dict.fromkeys(bl_list))
            
            if st.button("▶️ Start Bulk Tracking", type="primary"):
                progress_text = st.empty()
                progress_bar = st.progress(0.0)
                
                def update_progress(current, total):
                    progress_bar.progress(current / total)
                    progress_text.text(f"Processing: {current} / {total}")
                
                with st.spinner("Connecting to API..."):
                    tracking_results = track_bulk_bl(unique_bl_list, progress_callback=update_progress)
                    result_df = pd.DataFrame(tracking_results)
                    
                    st.subheader("📋 Tracking Results Preview")
                    st.dataframe(result_df, width=1200)
                    
                    # 🔍 디버그용 코드: Raw JSON 확인
                    if not result_df.empty:
                        with st.expander("🔍 API가 실제로 보내준 데이터 (Raw JSON)"):
                            st.code(result_df.iloc[0]["Remarks"], language="json")
                            
                    out_buffer = io.BytesIO()
                    with pd.ExcelWriter(out_buffer, engine='openpyxl') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Result')
                    
                    st.download_button("📥 Download Result", data=out_buffer.getvalue(), file_name="result.xlsx")
        else:
            st.error("Column 'B_L_NUMBER' not found.")
    except Exception as e:
        st.error(f"Error: {str(e)}")