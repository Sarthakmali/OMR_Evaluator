import streamlit as st
import requests
import pandas as pd
import time
import os
import re

# Dynamic API base URL for cloud deployment
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="OMR Scorer Bulk", layout="centered")
st.title("Bulk Answer Key Paste + Evaluation UI")

# Function to get existing answer key sets
@st.cache_data(ttl=5)  # Cache for 5 seconds to allow dynamic updates
def get_answer_key_sets():
    try:
        response = requests.get(f"{API_BASE}/answer-key-sets")
        if response.ok:
            return response.json().get("sets", [])
        return []
    except:
        return []

# Function to get existing CSV files
@st.cache_data(ttl=5)  # Cache for 5 seconds to allow dynamic updates
def get_csv_files():
    try:
        response = requests.get(f"{API_BASE}/csv-files")
        if response.ok:
            return response.json().get("files", [])
        return []
    except:
        return []

# Display existing answer key sets at the top
col_header, col_refresh = st.columns([4, 1])
with col_header:
    st.header("📚 Answer Key Sets")
with col_refresh:
    if st.button("🔄 Refresh", key="refresh_sets"):
        get_answer_key_sets.clear()
        st.rerun()

existing_sets = get_answer_key_sets()

if existing_sets:
    st.subheader("Existing Answer Key Sets:")
    cols = st.columns(min(len(existing_sets) + 1, 6))  # Max 6 columns including "Add New"
    
    for i, set_name in enumerate(existing_sets):
        with cols[i]:
            st.info(f"Set {set_name}")
    
    # Add "Add New" option
    if len(existing_sets) < 5:  # Limit to 5 sets max
        with cols[len(existing_sets)]:
            if st.button("➕ Add New Set", key="add_new_set"):
                st.session_state.show_add_form = True
else:
    st.info("No answer key sets found. Add your first set below!")
    st.session_state.show_add_form = True

# CSV File Management Section
st.markdown("---")
st.header("📊 Data Storage Management")

# Initialize session state for CSV file selection
if 'selected_csv_file' not in st.session_state:
    st.session_state.selected_csv_file = None
if 'show_create_csv' not in st.session_state:
    st.session_state.show_create_csv = False

# Get existing CSV files
existing_csv_files = get_csv_files()

# CSV file selection interface
col_csv_header, col_csv_refresh = st.columns([4, 1])
with col_csv_header:
    st.subheader("Select CSV File for Data Storage")
with col_csv_refresh:
    if st.button("🔄 Refresh", key="refresh_csv"):
        get_csv_files.clear()
        st.rerun()

# Show current selection
if st.session_state.selected_csv_file:
    st.success(f"📁 Currently selected: **{st.session_state.selected_csv_file}**")
else:
    st.warning("⚠️ No CSV file selected. Please select or create one below.")

# CSV file options
if existing_csv_files:
    st.write("**Available CSV Files:**")
    csv_cols = st.columns(min(len(existing_csv_files), 4))
    
    for i, csv_file in enumerate(existing_csv_files):
        with csv_cols[i % 4]:
            if st.button(f"📄 {csv_file}", key=f"select_csv_{i}"):
                st.session_state.selected_csv_file = csv_file
                st.rerun()

# Create new CSV file section
st.write("**Create New CSV File:**")
col_create, col_cancel = st.columns([2, 1])

with col_create:
    if st.button("➕ Create New CSV File", key="create_csv_btn"):
        st.session_state.show_create_csv = True

with col_cancel:
    if st.button("❌ Cancel", key="cancel_csv_btn"):
        st.session_state.show_create_csv = False
        st.rerun()

# Show create CSV form
if st.session_state.show_create_csv:
    st.markdown("---")
    st.subheader("Create New CSV File")
    
    new_csv_name = st.text_input("Enter CSV file name (without .csv extension)", key="new_csv_name")
    
    col_save, col_cancel_create = st.columns([1, 1])
    
    with col_save:
        if st.button("💾 Create & Use", key="save_csv_btn"):
            if new_csv_name.strip():
                try:
                    response = requests.post(
                        f"{API_BASE}/create-csv",
                        data={"filename": new_csv_name.strip()}
                    )
                    if response.ok:
                        created_file = response.json()["filename"]
                        st.session_state.selected_csv_file = created_file
                        st.session_state.show_create_csv = False
                        get_csv_files.clear()  # Clear cache to refresh list
                        st.success(f"✅ CSV file '{created_file}' created and selected!")
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {response.text}")
                except Exception as e:
                    st.error(f"❌ Error creating CSV: {str(e)}")
            else:
                st.error("Please enter a valid CSV file name.")
    
    with col_cancel_create:
        if st.button("❌ Cancel", key="cancel_create_csv"):
            st.session_state.show_create_csv = False
            st.rerun()

# Show add form if requested or no sets exist
if st.session_state.get("show_add_form", False):
    st.markdown("---")
    st.header("Step 1: Paste Answer Key For a Set")
    set_name = st.text_input("Set Name (A/B/...) for This Key", max_chars=1)
    answer_key_block = st.text_area(
        "Paste Answer Key Block (e.g. '1 - a', '16 - a,b,c,d'). No special format needed.",
        height=300
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save/Replace Answer Key"):
            if not set_name or not answer_key_block.strip():
                st.error("Provide set and paste block.")
            else:
                res = requests.post(
                    f"{API_BASE}/create-bulk-answerkey",
                    data={"set_name": set_name.upper(), "block": answer_key_block}
                )
                if res.ok:
                    st.success(res.json()["message"])
                    # Clear cache to refresh the sets list
                    get_answer_key_sets.clear()
                    # Hide the form after successful save
                    st.session_state.show_add_form = False
                    st.rerun()
                else:
                    st.error(res.text)
    
    with col2:
        if st.button("Cancel", key="cancel_add"):
            st.session_state.show_add_form = False
            st.rerun()

st.markdown("---")

st.header("Step 2: Upload OMR Sheet and Score")
student_name = st.text_input("Student Name")
roll_no = st.text_input("Roll No")

# Show available sets in dropdown
if existing_sets:
    sel_set = st.selectbox("Select OMR Set", existing_sets, key="omr_set_select")
    key_exists = True  # All sets in dropdown exist
else:
    st.warning("No answer key sets available. Please add an answer key set first.")
    sel_set = None
    key_exists = False

omr_file = st.file_uploader("Upload OMR Sheet", type=["jpg", "jpeg", "png"])

if st.button("Save OMR & Score"):
    if not (student_name and roll_no and sel_set and omr_file):
        st.error("Fill all fields and upload.")
    elif not key_exists:
        st.error(f"No answer key for set {sel_set.upper()}. Paste key first.")
    elif not st.session_state.selected_csv_file:
        st.error("⚠️ Please select a CSV file for data storage above.")
    else:
        # normalize set (remove leading "Set " if present) to match backend filenames
        norm_set = re.sub(r'^(set\s*)', '', sel_set.strip(), flags=re.I).upper()
        # determine mime type from uploaded file or fallback by extension
        mimetype = getattr(omr_file, "type", None) or ("image/" + os.path.splitext(omr_file.name)[1].lstrip('.').lower())
        files = {"file": (omr_file.name, omr_file.read(), mimetype)}
        data = {"student_name": student_name, "roll_no": roll_no, "omr_set": norm_set}
        r = requests.post(API_BASE + "/upload-omr", files=files, data=data)
        if not r.ok:
            st.error("Failed to save OMR: " + r.text)
        else:
            # Prepare evaluation data with selected CSV file
            evaldata = {
                "student_name": student_name,
                "roll_no": roll_no,
                "omr_set": norm_set,
                "csv_filename": st.session_state.selected_csv_file
            }
            evalres = requests.post(API_BASE + "/evaluate", data=evaldata)
            if evalres.ok:
                data = evalres.json()
                score = data.get("score", "N/A")
                percentage = data.get("percentage", "N/A")
                section_scores = data.get("section_scores", {})
                csv_file = data.get("csv_file", "scores.csv")
                
                st.success(f"✅ OMR scored successfully!")
                st.info(f"📊 **Total Score:** {score}/100 | **Percentage:** {percentage}% | **Set:** {sel_set.upper()}")
                st.info(f"💾 **Data saved to:** {csv_file}")
                
                if section_scores:
                    st.subheader("📈 Section-wise Scores")
                    # Create a nice table for section scores
                    section_data = {
                        "Subject": list(section_scores.keys()),
                        "Marks": list(section_scores.values())
                    }
                    st.table(section_data)
            else:
                st.error("Scoring error: " + evalres.text)

st.markdown("---")
st.header("📋 Results Dashboard")

# Show results from selected CSV file
if st.session_state.selected_csv_file:
    st.subheader(f"Results from: {st.session_state.selected_csv_file}")
    try:
        # Read the selected CSV file
        csv_path = f"uploaded_omr/{st.session_state.selected_csv_file}"
        if os.path.exists(csv_path):
            table = pd.read_csv(csv_path)
            if not table.empty:
                st.dataframe(table, use_container_width=True)
                
                # Show summary statistics
                if len(table) > 0:
                    st.subheader("📊 Summary Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Students", len(table))
                    with col2:
                        avg_score = table['Marks Obtained'].mean()
                        st.metric("Average Score", f"{avg_score:.1f}")
                    with col3:
                        max_score = table['Marks Obtained'].max()
                        st.metric("Highest Score", f"{max_score}")
                    with col4:
                        min_score = table['Marks Obtained'].min()
                        st.metric("Lowest Score", f"{min_score}")
            else:
                st.info("No data found in the selected CSV file.")
        else:
            st.warning(f"CSV file '{st.session_state.selected_csv_file}' not found.")
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
else:
    st.info("Please select a CSV file above to view results.")
