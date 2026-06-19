import streamlit as tf
import pandas as pd
import io
from tracking_service import track_bulk_bl

# 웹 페이지 제목 설정
tf.set_page_config(page_title="Bulk B/L Tracker", layout="wide")

tf.title("🚢 Bulk B/L Tracking Tool (v1.4)")
tf.markdown("Track up to 100 B/L numbers in one upload.")

# 1. 샘플 템플릿 다운로드 기능
tf.subheader("1. Download Template")
sample_df = pd.DataFrame({"B_L_NUMBER": ["ONEYSUBG12277500", "HMCU1234567", "MAEU7654321"]})

# 엑셀 다운로드를 위한 버퍼 메모리 작업
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    sample_df.to_excel(writer, index=False, sheet_name='Sheet1')
    
tf.download_button(
    label="📥 Download Excel Template (.xlsx)",
    data=buffer.getvalue(),
    file_name="bulk_bl_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

tf.write("---")

# 2. 엑셀 업로드 기능
tf.subheader("2. Upload Your B/L List")
uploaded_file = tf.file_uploader("Drag and drop your Excel file here.", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 업로드된 엑셀 읽기
        df = pd.read_excel(uploaded_file, sheet_name='Sheet1')
        
        if "B_L_NUMBER" in df.columns:
            # 공백 제거 및 결측치 제거
            bl_list = df["B_L_NUMBER"].dropna().astype(str).str.strip().tolist()
            raw_count = len(bl_list)
            
            # 중복 제거 UI 반영
            unique_bl_list = list(dict.fromkeys(bl_list))
            unique_count = len(unique_bl_list)
            saved_count = raw_count - unique_count
            
            tf.success(f"📋 {raw_count} B/L Loaded. (중복 제거 완료: {raw_count} → {unique_count} 건 / {saved_count}건 절약)")
            
            # 3. 트래킹 시작 버튼
            if tf.button("▶️ Start Bulk Tracking", type="primary"):
                with tf.spinner("Tracking in progress... Please wait."):
                    # 가짜 데이터 서비스 호출
                    tracking_results = track_bulk_bl(unique_bl_list)
                    result_df = pd.DataFrame(tracking_results)
                    
                    # 형님이 요청하신 ETD 포함 컬럼 순서 완벽 정렬!
                    columns_order = ["B/L Number", "Carrier", "Status", "POL", "ETD", "POD", "ETA"]
                    result_df = result_df[columns_order]
                    
                    # 화면에 프리뷰 표 띄우기
                    tf.subheader("📋 Tracking Results Preview")
                    tf.dataframe(result_df, width=1200) # stretch 스타일 반영
                    
                    # 결과 엑셀 파일 생성
                    out_buffer = io.BytesIO()
                    with pd.ExcelWriter(out_buffer, engine='openpyxl') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Tracking_Result')
                        
                    # 다운로드 버튼 제공
                    tf.download_button(
                        label="📥 Download Tracking Result (.xlsx)",
                        data=out_buffer.getvalue(),
                        file_name="tracking_result.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            tf.error("❌ 'B_L_NUMBER' 컬럼을 찾을 수 없습니다. 템플릿 양식을 확인해 주세요.")
    except Exception as e:
        tf.error(f"❌ 에러 발생: {str(e)}. 엑셀 파일 구조나 시트 이름(Sheet1)을 확인해 주세요.")