import streamlit as st
import pandas as pd
import io
import os
import logging

# 챗GPT 피드백 버그 5위 해결: 프로그램의 최상단 루트(app.py)에서 로그 마스터 설정 수행
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 챗GPT 피드백 버그 2위 완벽 해결: 
# config가 읽히기 전에 시스템 환경변수에 최우선 주입하여 동기화 꼬임을 원천 차단합니다.
if "TRACKINGMORE_API_KEY" in st.secrets:
    os.environ["TRACKINGMORE_API_KEY"] = st.secrets["TRACKINGMORE_API_KEY"]

from tracking_service import track_bulk_bl

st.set_page_config(page_title="Bulk B/L Tracker", layout="wide")

st.title("🚢 Bulk B/L Tracking Tool (v1.8 - Enterprise Final)")
st.markdown("Track up to 100 B/L numbers in one upload.")

st.subheader("1. Download Template")
sample_df = pd.DataFrame({"B_L_NUMBER": ["ONEYSUBG12277500", "HMCU1234567", "MAEU7654321", "INVALID123"]})

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    sample_df.to_excel(writer, index=False, sheet_name='Sheet1')
    
st.download_button(
    label="📥 Download Excel Template (.xlsx)",
    data=buffer.getvalue(),
    file_name="bulk_bl_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.write("---")

st.subheader("2. Upload Your B/L List")
uploaded_file = st.file_uploader("Drag and drop your Excel file here.", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name='Sheet1')
        
        if "B_L_NUMBER" in df.columns:
            bl_list = df["B_L_NUMBER"].dropna().astype(str).str.strip().tolist()
            raw_count = len(bl_list)
            
            unique_bl_list = list(dict.fromkeys(bl_list))
            unique_count = len(unique_bl_list)
            saved_count = raw_count - unique_count
            
            st.success(
                f"📊 **Smart Cost Saver Analysis**\n\n"
                f"* **Total Uploaded:** {raw_count} B/Ls\n"
                f"* **Duplicates Removed:** {saved_count} items\n"
                f"* **Actual API Calls to Bill:** {unique_count} calls (You saved {saved_count} unnecessary API fees!)"
            )
            
            if st.button("▶️ Start Bulk Tracking", type="primary"):
                progress_text = st.empty()
                progress_bar = st.progress(0.0)
                
                def update_progress(current, total):
                    percent = current / total
                    progress_text.text(f"⏳ Processing: {current} / {total} B/Ls ({int(percent*100)}%)")
                    progress_bar.progress(percent)
                
                with st.spinner("Connecting to global carrier network..."):
                    tracking_results = track_bulk_bl(unique_bl_list, progress_callback=update_progress)
                    result_df = pd.DataFrame(tracking_results)
                    
                    columns_order = ["B/L Number", "Carrier", "Status", "POL", "ETD", "POD", "ETA", "Remarks"]
                    result_df = result_df[columns_order]
                    
                    progress_text.empty()
                    progress_bar.empty()
                    
                    st.subheader("📋 Tracking Results Preview")
                    st.dataframe(result_df, width=1200)
                    
                    out_buffer = io.BytesIO()
                    with pd.ExcelWriter(out_buffer, engine='openpyxl') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Tracking_Result')
                        
                    st.download_button(
                        label="📥 Download Tracking Result (.xlsx)",
                        data=out_buffer.getvalue(),
                        file_name="tracking_result.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.error("❌ Column 'B_L_NUMBER' not found. Please verify the template format.")
    except Exception as e:
        st.error(f"❌ Error occurred: {str(e)}. Please check your Excel structure and sheet name.")