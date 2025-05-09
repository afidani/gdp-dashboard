import streamlit as st
import pandas as pd
import io
from datetime import datetime
from fpdf import FPDF

# --- Settings ---
st.set_page_config(page_title="QA Productivity Dashboard", layout="wide")
st.title("📊 QA Productivity Dashboard")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload your QA activity file (Excel or CSV)", type=["xlsx", "xls", "csv"])

if uploaded_file:
    # Read file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Ensure standard columns
    expected_cols = ["QA Name", "Date", "Activity Type", "Cases"]  # Adjust as needed
    if not all(col in df.columns for col in expected_cols):
        st.error(f"Missing columns. Expected: {expected_cols}")
    else:
        df["Date"] = pd.to_datetime(df["Date"])
        df["Productive"] = df["Activity Type"].str.contains("Sample", case=False, na=False)
        
        # --- Filters ---
        date_min = df["Date"].min()
        date_max = df["Date"].max()
        date_range = st.date_input("Filter by date range", [date_min, date_max])

        if len(date_range) == 2:
            df = df[(df["Date"] >= pd.to_datetime(date_range[0])) & (df["Date"] <= pd.to_datetime(date_range[1]))]

        st.subheader("📌 Productivity Summary")

        # --- Summary per QA ---
        summary = df[df["Productive"]].groupby(["QA Name", "Date"]).agg({"Cases": "sum"}).reset_index()
        pivot = summary.pivot(index="QA Name", columns="Date", values="Cases").fillna(0).astype(int)
        st.dataframe(pivot.style.format("{:.0f}"), use_container_width=True)

        # --- Alerts ---
        st.subheader("🚨 Daily Performance Alerts")

        def generate_alerts(row):
            if row["Cases"] >= 20:
                return "🟢 Meets target"
            elif 15 <= row["Cases"] < 20:
                return "🟡 Slightly below target"
            else:
                return "🔴 Below target"

        alert_df = summary.copy()
        alert_df["Status"] = alert_df.apply(generate_alerts, axis=1)
        alert_df["Recommendation"] = alert_df["Status"].map({
            "🟢 Meets target": "👍 Good performance. Stay consistent.",
            "🟡 Slightly below target": "⚠️ Slightly under target. Monitor workload or distractions.",
            "🔴 Below target": "❌ Underperforming. Review task distribution or support needs."
        })

        st.dataframe(alert_df, use_container_width=True)

        # --- Export Section ---
        st.markdown("### 📤 Export Alerts")

        col1, col2 = st.columns(2)

        with col1:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                alert_df.to_excel(writer, sheet_name="QA Alerts", index=False)
            st.download_button(
                label="Download as Excel",
                data=excel_buffer,
                file_name="qa_alerts_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col2:
            class PDF(FPDF):
                def header(self):
                    self.set_font("Arial", "B", 12)
                    self.cell(200, 10, "QA Alerts Report", ln=True, align="C")

                def table(self, data):
                    self.set_font("Arial", "", 10)
                    col_widths = [40, 30, 30, 30, 60]
                    headers = list(data.columns)
                    for i, header in enumerate(headers):
                        self.cell(col_widths[i], 10, header, border=1)
                    self.ln()
                    for _, row in data.iterrows():
                        for i, item in enumerate(row):
                            self.cell(col_widths[i], 10, str(item), border=1)
                        self.ln()

            pdf = PDF()
            pdf.add_page()
            pdf.table(alert_df[["QA Name", "Date", "Cases", "Status", "Recommendation"]])
            pdf_buffer = io.BytesIO(pdf.output(dest="S").encode("latin-1"))

            st.download_button(
                label="Download as PDF",
                data=pdf_buffer,
                file_name="qa_alerts_report.pdf",
                mime="application/pdf"
            )

else:
    st.info("Upload a file to begin.")
