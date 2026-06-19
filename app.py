import streamlit as st
import pandas as pd
import time
import io
from datetime import datetime
from tracking_service import detect_carrier, fetch_tracking_data

# --- 1. Web Dashboard Configuration ---
st.set_page_config(page_title="Bulk B/L Tracker", page_icon="🚢", layout="centered")

st.title("🚢 Bulk B/L Tracking Tool (v1.3)")
st.subheader("💡 Track up to 100 B/L numbers in one upload.") 
st.caption("No more checking one by one. Upload once. Download once.")
st.markdown("---")

# --- 2. Step 1: Download Template ---
st.subheader("Step 1: Download Template")

sample_data = {"B_L_NUMBER": ["HMCUIND123456", "MAEU777888999", "ONEY555444333", "HMCUIND123456", "XYZ123456789"]}
sample_df = pd.DataFrame(sample_data)

towrite = io.BytesIO()
with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
    sample_df.to_excel(writer, index=False)
towrite.seek(0)

st.download_button(
    label="📥 Download Excel Template (.xlsx)",
    data=towrite,
    file_name="BL_Tracking_Template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.markdown("---")

# --- 3. Step 2: Upload Excel File ---
st.subheader("Step 2: Upload Your Excel File")
uploaded_file = st.file_uploader("Drag and drop your Excel file here.", type=["xlsx"])

# --- 4. Step 3: Process and UI ---
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    if "B_L_NUMBER" in df.columns:
        df['B_L_NUMBER'] = df['B_L_NUMBER'].astype(str).str.strip()
        raw_total = len(df)
        
        unique_df = df.drop_duplicates(subset=['B_L_NUMBER']).copy()
        unique_total = len(unique_df)
        duplicated_cnt = raw_total - unique_total
        
        st.info(f"📋 **{raw_total} B/L Loaded.** (중복 제거 완료: {raw_total} → {unique_total} 건 / {duplicated_cnt}건 절약)")
        
        estimated_seconds = round(unique_total * 0.3, 1)
        st.write(f"⏱️ 예상 소요 시간: `{estimated_seconds} 초` (중복 제거로 `{round(duplicated_cnt * 0.3, 1)}초` 단축)")
        
        if st.button("▶️ Start Bulk Tracking"):
            start_time = time.time()
            my_bar = st.progress(0, text="선사 API 서버 연결 중...")
            
            tracked_results = {}
            failed_bls = []
            completed_cnt, delayed_cnt, failed_cnt = 0, 0, 0
            
            for index, bl in enumerate(unique_df['B_L_NUMBER']):
                carrier = detect_carrier(bl)
                res = fetch_tracking_data(bl, carrier)
                
                if carrier == "UNKNOWN":
                    failed_cnt += 1
                    failed_bls.append(bl)
                elif res["status"] == "Delay":
                    delayed_cnt += 1
                else:
                    completed_cnt += 1
                    
                tracked_results[bl] = {
                    "CARRIER": carrier,
                    "STATUS": res["status"],
                    "ETA": res["eta"],
                    "POL": res["pol"],
                    "POD": res["pod"],
                    "VESSEL": res["vessel"],
                    "LAST_UPDATED": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                percent_complete = int(((index + 1) / unique_total) * 100)
                my_bar.progress(percent_complete, text=f"조회 중: {bl} ({index+1}/{unique_total})")
                
            my_bar.empty()
            st.balloons()
            
            elapsed_time = round(time.time() - start_time, 1)
            
            st.markdown("### 📊 Tracking Summary")
            st.markdown(f"✅ **조회 완료 시각:** `{datetime.now().strftime('%H:%M:%S')}` | 🕒 **실제 소요 시간:** `{elapsed_time} 초`")
            
            df['CARRIER'] = df['B_L_NUMBER'].map(lambda x: tracked_results[x]['CARRIER'])
            df['STATUS'] = df['B_L_NUMBER'].map(lambda x: tracked_results[x]['STATUS'])
            df['ETA'] = df['B_L_NUMBER'].map(lambda x: tracked_results[x]['ETA'])
            df['POL'] = df['B_L_NUMBER'].map(lambda x: tracked_results[x]['POL'])
            df['POD'] = df['B_L_NUMBER'].map(lambda x: tracked_results[x]['POD'])
            df['VESSEL'] = df['B_L_NUMBER'].map(lambda x: tracked_results[x]['VESSEL'])
            df['LAST_UPDATED'] = df['B_L_NUMBER'].map(lambda x: tracked_results[x]['LAST_UPDATED'])
            
            final_total = len(df)
            final_success = len(df[df['STATUS'].isin(['On Board', 'On Schedule'])])
            final_delay = len(df[df['STATUS'] == 'Delay'])
            final_failed = len(df[df['STATUS'] == 'Failed'])
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("총 B/L 건수", f"{final_total}")
            col2.metric("✔ 조회 성공", f"{final_success}")
            col3.metric("⚠️ 지연 품목", f"{final_delay}")
            col4.metric("❌ 조회 실패", f"{final_failed}")
            
            if failed_bls:
                st.warning(f"⚠️ 조회 실패 B/L 리스트 ({len(failed_bls)}건): {', '.join(failed_bls)}")
            
            st.markdown("### 📋 Tracking Results Preview")
            st.dataframe(df, use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            
            st.markdown("---")
            st.subheader("Step 3: Download Final Report")
            st.download_button(
                label="🟢 Download Tracking Result (.xlsx)",
                data=output,
                file_name="BL_Tracking_Result_Final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("❌ 엑셀 양식이 올바르지 않습니다. 'B_L_NUMBER' 컬럼을 확인해 주세요.")