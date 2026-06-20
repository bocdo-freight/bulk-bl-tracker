import streamlit as st
import pandas as pd
import io
from tracking_service import track_bulk_bl

# 웹 페이지 제목 및 레이아웃 설정 (영문 완료)
st.set_page_config(page_title="Bulk B/L Tracker", layout="wide")

st.title("🚢 Bulk B/L Tracking Tool (v1.4)")
st.markdown("Track up to 100 B/L numbers in one upload.")

# 1. 샘플 템플릿 다운로드 기능
st.subheader("1. Download Template")
sample_df = pd.DataFrame({"B_L_NUMBER": ["ONEYSUBG12277500", "HMCU1234567", "MAEU7654321"]})

# 엑셀 다운로드를 위한 버퍼 메모리 작업
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

# 2. 엑셀 업로드 기능
st.subheader("2. Upload Your B/L List")
uploaded_file = st.file_uploader("Drag and drop your Excel file here.", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 업로드된 엑셀 읽기
        df = pd.read_excel(uploaded_file, sheet_name='Sheet1')
        
        if "B_L_NUMBER" in df.columns:
            # 공백 제거 및 결측치 제거
            bl_list = df["B_L_NUMBER"].dropna().astype(str).str.strip().tolist()
            raw_count = len(bl_list)
            
            # 중복 제거 및 글로벌 영문 메시지 처리
            unique_bl_list = list(dict.fromkeys(bl_list))
            unique_count = len(unique_bl_list)
            saved_count = raw_count - unique_count
            
            # 형님이 짚어주신 초록색 알림창을 100% 영문으로 변환 완료!
            st.success(
                f"📋 {raw_count} B/L numbers loaded successfully! "
                f"(Deduplicated: {raw_count} → {unique_count} | {saved_count} duplicated entries removed to save your API costs)"
            )
            
            # 3. 트래킹 시작 버튼
            if st.button("▶️ Start Bulk Tracking", type="primary"):
                with st.spinner("Tracking in progress... Please wait."):
                    # 가짜 데이터 서비스 호출
                    tracking_results = track_bulk_bl(unique_bl_list)
                    result_df = pd.DataFrame(tracking_results)
                    
                    # 컬럼 순서 완벽 정렬
                    columns_order = ["B/L Number", "Carrier", "Status", "POL", "ETD", "POD", "ETA"]
                    result_df = result_df[columns_order]
                    
                    # 결과 화면 렌더링
                    st.subheader("📋 Tracking Results Preview")
                    st.dataframe(result_df, width=1200)
                    
                    # 결과 엑셀 파일 생성
                    out_buffer = io.BytesIO()
                    with pd.ExcelWriter(out_buffer, engine='openpyxl') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Tracking_Result')
                        
                    # 다운로드 버튼 제공 (영문)
                    st.download_button(
                        label="📥 Download Tracking Result (.xlsx)",
                        data=out_buffer.getvalue(),
                        file_name="tracking_result.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            # 에러 메시지 영문 변환
            st.error("❌ Column 'B_L_NUMBER' not found. Please verify the template format.")
    except Exception as e:
        # 시스템 예외 에러 메시지 영문 변환
        st.error(f"❌ Error occurred: {str(e)}. Please check your Excel structure and sheet name (must be 'Sheet1').")