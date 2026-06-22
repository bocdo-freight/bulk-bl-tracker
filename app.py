import io
import os
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Bulk B/L Tracker",
    page_icon="🚢",
    layout="wide",
)

try:
    api_token = str(st.secrets["SHIPSGO_API_TOKEN"]).strip()
except Exception:
    api_token = ""

if api_token:
    os.environ["SHIPSGO_API_TOKEN"] = api_token

from config import (
    MAX_BLS_PER_UPLOAD,
    detect_carrier_scac,
    normalize_number,
)

import provider as provider_module

if hasattr(provider_module, "OceanTrackingProvider"):
    TrackingProvider = provider_module.OceanTrackingProvider
elif hasattr(provider_module, "ShipsGoProvider"):
    TrackingProvider = provider_module.ShipsGoProvider
else:
    raise ImportError(
        "No supported tracking provider class was found in provider.py."
    )

if hasattr(provider_module, "TrackingAPIError"):
    TrackingError = provider_module.TrackingAPIError
elif hasattr(provider_module, "ShipsGoAPIError"):
    TrackingError = provider_module.ShipsGoAPIError
else:
    TrackingError = RuntimeError

SCHEDULE_COLUMNS = [
    "B/L Number",
    "Status",
    "Carrier",
    "POL Country Code",
    "POL",
    "ETD",
    "POD Country Code",
    "POD",
    "ETA",
    "Initial ETA",
    "ETA Change (Days)",
    "Last Checked",
]

DETAIL_COLUMNS = [
    "B/L Number",
    "Container Number(s)",
    "Container Count",
    "Vessel",
    "Voyage",
    "Latest Event",
    "Latest Place",
    "Latest Event Time",
    "Transshipment Count",
    "Remarks",
]

EXPORT_COLUMNS = [
    "B/L Number",
    "Status",
    "Carrier",
    "SCAC",
    "Container Number(s)",
    "Container Count",
    "POL Country Code",
    "POL",
    "ETD",
    "POD Country Code",
    "POD",
    "ETA",
    "Initial ETA",
    "ETA Change (Days)",
    "Vessel",
    "Voyage",
    "Latest Event",
    "Latest Place",
    "Latest Event Time",
    "Transshipment Count",
    "Last Checked",
    "Remarks",
]

def public_error_message(value: object) -> str:
    text = str(value)
    replacements = {
        "ShipsGo API": "Tracking service",
        "ShipsGo": "Tracking service",
        "SHIPSGO_API_TOKEN": "API token",
    }

    for old_text, new_text in replacements.items():
        text = text.replace(old_text, new_text)

    return text

def create_template() -> bytes:
    dataframe = pd.DataFrame(
        {
            "B_L_NUMBER": [
                "ENTER_BL_NUMBER_HERE",
            ]
        }
    )
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(
            writer,
            index=False,
            sheet_name="B_L_List",
        )

    return output.getvalue()

def create_result_excel(dataframe: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(
            writer,
            index=False,
            sheet_name="Tracking_Result",
        )

        worksheet = writer.sheets["Tracking_Result"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for cells in worksheet.columns:
            column_letter = cells[0].column_letter
            max_length = 0

            for cell in cells:
                value = "" if cell.value is None else str(cell.value)
                max_length = max(max_length, len(value))

            worksheet.column_dimensions[column_letter].width = min(
                max(max_length + 2, 12),
                35,
            )

    return output.getvalue()

def find_column(
    dataframe: pd.DataFrame,
    candidate_names: set[str],
):
    normalized_columns = {
        str(column).strip().upper().replace(" ", "_"): column
        for column in dataframe.columns
    }
    for candidate in candidate_names:
        if candidate in normalized_columns:
            return normalized_columns[candidate]

    return None

def read_entries(uploaded_file):
    dataframe = pd.read_excel(uploaded_file, sheet_name=0)
    bl_column = find_column(
        dataframe,
        {
            "B_L_NUMBER",
            "BL_NUMBER",
            "B/L_NUMBER",
            "BOOKING_NUMBER",
        },
    )

    if bl_column is None:
        raise ValueError(
            "The B_L_NUMBER column was not found. "
            "Please use the provided template."
        )

    carrier_column = find_column(
        dataframe,
        {
            "CARRIER_SCAC",
            "SCAC",
            "CARRIER",
            "CARRIER_CODE",
        },
    )

    unique_entries = {}
    raw_count = 0

    for _, row in dataframe.iterrows():
        bl_number = normalize_number(row.get(bl_column))

        if not bl_number:
            continue

        raw_count += 1
        carrier_code = ""

        if carrier_column:
            carrier_code = normalize_number(row.get(carrier_column))

        carrier_code = (
            carrier_code
            or detect_carrier_scac(bl_number)
        )

        if bl_number not in unique_entries:
            unique_entries[bl_number] = {
                "bl_number": bl_number,
                "carrier_scac": carrier_code,
            }
        elif (
            not unique_entries[bl_number]["carrier_scac"]
            and carrier_code
        ):
            unique_entries[bl_number]["carrier_scac"] = carrier_code

    return list(unique_entries.values()), raw_count

def clear_previous_results() -> None:
    for key in (
        "analysis_df",
        "result_df",
        "analysis_editor",
    ):
        st.session_state.pop(key, None)

def ensure_columns(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    result = dataframe.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = "N/A"

    return result[columns]

def normalize_analysis(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    result = result.rename(
        columns={
            "Carrier SCAC": "Carrier Code",
            "Registration Status": "Availability",
        }
    )

    if "B/L Number" not in result.columns:
        result["B/L Number"] = ""

    if "Carrier Code" not in result.columns:
        result["Carrier Code"] = ""

    if "Availability" not in result.columns:
        result["Availability"] = "NEW"

    result["Availability"] = (
        result["Availability"]
        .astype(str)
        .str.upper()
        .replace(
            {
                "EXISTING": "AVAILABLE",
            }
        )
    )

    return result[
        [
            "B/L Number",
            "Carrier Code",
            "Availability",
        ]
    ]

def format_status(value: object) -> str:
    status = str(value).strip().upper()
    labels = {
        "SAILING": "🚢 In Transit",
        "ARRIVED": "✅ Arrived",
        "DELIVERED": "✅ Delivered",
        "INPROGRESS": "⏳ Processing",
        "PROCESSING": "⏳ Processing",
        "CREATED": "⏳ Processing",
        "BOOKED": "📋 Booked",
        "NOT REGISTERED": "➕ Not Registered",
        "CARRIER REQUIRED": "⚠️ Carrier Required",
        "ERROR": "❌ Error",
    }

    return labels.get(status, status.title())

def prepare_schedule_dataframe(
    result_df: pd.DataFrame,
) -> pd.DataFrame:
    schedule_df = ensure_columns(
        result_df,
        SCHEDULE_COLUMNS,
    )
    schedule_df = schedule_df.copy()
    schedule_df["Status"] = schedule_df["Status"].map(format_status)

    return schedule_df

def prepare_detail_dataframe(
    result_df: pd.DataFrame,
) -> pd.DataFrame:
    return ensure_columns(
        result_df,
        DETAIL_COLUMNS,
    )

def prepare_export_dataframe(
    result_df: pd.DataFrame,
) -> pd.DataFrame:
    export_df = ensure_columns(
        result_df,
        EXPORT_COLUMNS,
    )
    export_df = export_df.copy()
    export_df["Status"] = export_df["Status"].map(format_status)

    return export_df

st.title("🚢 Bulk B/L Tracking Tool")
st.caption(
    "Upload an Excel file to retrieve "
    "the latest ocean shipment status."
)

if not api_token:
    st.error(
        "The tracking service is not configured. "
        "Please contact the administrator."
    )
    st.stop()

st.info(
    "Upload a list of B/L numbers to check "
    "availability and retrieve the latest "
    "shipment information."
)

st.subheader("1. Download Template")
st.download_button(
    label="📥 Download Excel Template",
    data=create_template(),
    file_name="bulk_bl_tracking_template.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
)
st.divider()

st.subheader("2. Upload B/L List")
uploaded_file = st.file_uploader(
    "Upload Excel file",
    type=["xlsx"],
)

if uploaded_file is not None:
    try:
        entries, raw_count = read_entries(uploaded_file)
        unique_count = len(entries)

        if unique_count == 0:
            st.error("No valid B/L numbers were found.")
            st.stop()

        if unique_count > MAX_BLS_PER_UPLOAD:
            st.error(
                f"A maximum of {MAX_BLS_PER_UPLOAD} "
                "B/L numbers can be processed at one time."
            )
            st.stop()

        input_signature = tuple(
            (
                entry["bl_number"],
                entry["carrier_scac"],
            )
            for entry in entries
        )

        if (
            st.session_state.get("input_signature")
            != input_signature
        ):
            st.session_state["input_signature"] = input_signature
            clear_previous_results()

        duplicate_count = raw_count - unique_count

        st.success(
            f"Uploaded: {raw_count} | "
            f"Unique: {unique_count} | "
            f"Duplicates removed: {duplicate_count}"
        )

        if st.button(
            "🔎 Check B/L Availability",
            type="primary",
        ):
            try:
                provider = TrackingProvider()

                with st.spinner(
                    "Checking shipment records..."
                ):
                    analysis_rows = provider.analyze(entries)

                st.session_state["analysis_df"] = normalize_analysis(
                    pd.DataFrame(analysis_rows)
                )

                st.session_state.pop("result_df", None)

            except TrackingError as exc:
                st.error(public_error_message(exc))

        if "analysis_df" in st.session_state:
            st.subheader("3. Review")

            analysis_df = normalize_analysis(
                st.session_state["analysis_df"]
            )

            available_count = int(
                (
                    analysis_df["Availability"]
                    == "AVAILABLE"
                ).sum()
            )

            new_count = int(
                (
                    analysis_df["Availability"]
                    == "NEW"
                ).sum()
            )

            col1, col2, col3 = st.columns(3)

            col1.metric("Total", len(analysis_df))
            col2.metric("Available", available_count)
            col3.metric("New Registration", new_count)

            edited_analysis = st.data_editor(
                analysis_df,
                hide_index=True,
                use_container_width=True,
                disabled=[
                    "B/L Number",
                    "Availability",
                ],
                column_config={
                    "Carrier Code": st.column_config.TextColumn(
                        "Carrier Code",
                        help=(
                            "Carrier code required "
                            "for a new registration."
                        ),
                        max_chars=10,
                    ),
                    "Availability": st.column_config.TextColumn(
                        "Availability"
                    ),
                },
                key="analysis_editor",
            )

            missing_carrier_count = int(
                (
                    (
                        edited_analysis["Availability"]
                        == "NEW"
                    )
                    &
                    (
                        edited_analysis["Carrier Code"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        == ""
                    )
                ).sum()
            )

            register_missing = False
            registration_confirmed = False

            if new_count > 0:
                st.warning(
                    f"{new_count} B/L number(s) "
                    "require new registration."
                )

                register_missing = st.checkbox(
                    "Register missing B/L numbers"
                )

                if register_missing:
                    registration_confirmed = st.checkbox(
                        "I confirm that the new "
                        "registrations may proceed."
                    )

                    if missing_carrier_count > 0:
                        st.error(
                            f"{missing_carrier_count} new "
                            "B/L number(s) require a "
                            "carrier code."
                        )
            else:
                st.success(
                    "All B/L numbers are ready "
                    "for tracking."
                )

            start_disabled = bool(
                register_missing
                and (
                    not registration_confirmed
                    or missing_carrier_count > 0
                )
            )

            if st.button(
                "▶️ Start Tracking",
                type="primary",
                disabled=start_disabled,
            ):
                tracking_entries = []

                for _, row in edited_analysis.iterrows():
                    tracking_entries.append(
                        {
                            "bl_number": normalize_number(
                                row["B/L Number"]
                            ),
                            "carrier_scac": normalize_number(
                                row["Carrier Code"]
                            ),
                        }
                    )

                progress_text = st.empty()
                progress_bar = st.progress(0.0)

                def update_progress(
                    current: int,
                    total: int,
                    bl_number: str,
                ) -> None:
                    progress_text.text(
                        f"Processing {current}/{total} — "
                        f"{bl_number}"
                    )
                    progress_bar.progress(current / total)

                try:
                    provider = TrackingProvider()

                    with st.spinner(
                        "Retrieving tracking data..."
                    ):
                        tracking_result = provider.track(
                            tracking_entries,
                            register_missing,
                            update_progress,
                        )

                    if isinstance(tracking_result, tuple):
                        rows = tracking_result[0]
                    else:
                        rows = tracking_result

                    st.session_state["result_df"] = pd.DataFrame(
                        rows
                    )

                except TrackingError as exc:
                    st.error(public_error_message(exc))

                finally:
                    progress_text.empty()
                    progress_bar.empty()

        if "result_df" in st.session_state:
            result_df = st.session_state["result_df"].copy()

            st.divider()
            st.subheader("📊 Tracking Results")

            failed_statuses = [
                "ERROR",
                "NOT REGISTERED",
                "CARRIER REQUIRED",
            ]

            retrieved_count = int(
                (
                    ~result_df["Status"].isin(
                        failed_statuses
                    )
                ).sum()
            )

            eta_series = result_df.get(
                "ETA Change (Days)",
                pd.Series(
                    index=result_df.index,
                    dtype="float64",
                ),
            )

            eta_change_values = pd.to_numeric(
                eta_series,
                errors="coerce",
            )

            delayed_count = int(
                (
                    eta_change_values > 0
                ).sum()
            )

            arrived_count = int(
                (
                    result_df["Status"]
                    .astype(str)
                    .str.upper()
                    .isin(
                        [
                            "ARRIVED",
                            "DELIVERED",
                        ]
                    )
                ).sum()
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Total", len(result_df))
            col2.metric("Retrieved", retrieved_count)
            col3.metric("Delayed", delayed_count)
            col4.metric("Arrived", arrived_count)

            st.markdown("#### Main Schedule")

            st.dataframe(
                prepare_schedule_dataframe(result_df),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "POL Country Code": st.column_config.TextColumn(
                        "POL Country",
                        width="small",
                    ),
                    "POD Country Code": st.column_config.TextColumn(
                        "POD Country",
                        width="small",
                    ),
                },
            )

            st.markdown(
                "#### Container & Vessel Details"
            )

            st.dataframe(
                prepare_detail_dataframe(result_df),
                hide_index=True,
                use_container_width=True,
            )

            export_df = prepare_export_dataframe(result_df)

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            st.download_button(
                label="📥 Download Tracking Result",
                data=create_result_excel(export_df),
                file_name=(
                    "bulk_bl_tracking_result_"
                    f"{timestamp}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            )

    except ValueError as exc:
        st.error(public_error_message(exc))

    except Exception as exc:
        st.error(public_error_message(exc))