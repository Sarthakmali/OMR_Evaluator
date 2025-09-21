from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import shutil
import re
import csv
from pathlib import Path
import subprocess
import threading
import time

from omr_scoring import omr_detect_and_score

app = FastAPI(title="OMR Proxy + Key Manager")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use environment variables for cloud deployment
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploaded_omr")
ANSWERKEY_DIR = os.getenv("ANSWERKEY_DIR", "answer_keys")

# Ensure directories exist
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(ANSWERKEY_DIR).mkdir(parents=True, exist_ok=True)

SECTIONS = [
    ("Python", 1, 20),
    ("EDA", 21, 40),
    ("SQL", 41, 60),
    ("Power BI", 61, 80),
    ("Statistics", 81, 100)
]
SECTION_NAMES = [sec for sec, _, _ in SECTIONS]
ALIASES = {
    "PowerBI": "Power BI", "Power Bi": "Power BI", "adv stats": "Statistics",
    "Adv Stats": "Statistics", "statastics": "Statistics", "Statistics": "Statistics"
}

def parse_sectionwise_block(text):
    key = {}
    current_section = None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        # Section header?
        section = None
        check = line.lower()
        for s in SECTION_NAMES:
            if check == s.lower():
                section = s
                break
        if section or line in ALIASES:
            current_section = ALIASES.get(line, section or line)
            if current_section not in key:
                key[current_section] = {}
            continue
        m = re.match(r"(\d+)[\s\-\.]+([a-dA-D, ]+)", line)
        if m and current_section:
            qn = m.group(1)
            ans = m.group(2).replace(" ", "").lower()
            key[current_section][f"Q{qn}"] = ans
    # Drop empty sections
    key = {sec:v for sec,v in key.items() if v}
    return key

@app.post("/create-bulk-answerkey")
async def create_bulk_answerkey(set_name: str = Form(...), block: str = Form(...)):
    section_answerkey = parse_sectionwise_block(block)
    if not section_answerkey:
        raise HTTPException(400, "No answers parsed from block, check formatting!")
    fname = os.path.join(ANSWERKEY_DIR, f"answers_{set_name.upper()}.json")
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(section_answerkey, f, indent=2)
    return JSONResponse({"message": f"Saved sectionwise key as {fname} ({sum(len(x) for x in section_answerkey.values())} questions)."})

@app.get("/key-exists/{set_name}")
def key_exists(set_name: str):
    path = os.path.join(ANSWERKEY_DIR, f"answers_{set_name.upper()}.json")
    return {"exists": os.path.exists(path)}

@app.post("/upload-omr")
async def upload_omr(
    student_name: str = Form(...),
    roll_no: str = Form(...),
    omr_set: str = Form(...),
    file: UploadFile = File(...)
):
    set_dir = os.path.join(UPLOAD_DIR, omr_set.upper())
    os.makedirs(set_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    base_fname = f"{student_name.replace(' ','_')}_{roll_no}_{omr_set.upper()}{ext}"
    save_path = os.path.join(set_dir, base_fname)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return JSONResponse({"omr_path": save_path, "filename": base_fname})

@app.post("/evaluate")
async def evaluate(
    student_name: str = Form(...),
    roll_no: str = Form(...),
    omr_set: str = Form(...),
    csv_filename: str = Form(None)
):
    set_name = omr_set.upper()
    anskey_file = os.path.join(ANSWERKEY_DIR, f"answers_{set_name}.json")
    if not os.path.exists(anskey_file):
        raise HTTPException(400, f"Answer key for set {set_name} not found. Upload that first.")
    set_dir = os.path.join(UPLOAD_DIR, set_name)
    img_file = None
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = os.path.join(set_dir, f"{student_name.replace(' ','_')}_{roll_no}_{set_name}{ext}")
        if os.path.exists(candidate):
            img_file = candidate
            break
    if not img_file:
        raise HTTPException(400, "OMR image file not found for this student/set.")
    try:
        detected_sectionwise, section_scores = omr_detect_and_score(img_file, anskey_file)
    except Exception as e:
        raise HTTPException(500, f"OMR detection error: {e}")

    # Use selected CSV file or default to scores.csv
    if csv_filename:
        outcsv = os.path.join(UPLOAD_DIR, csv_filename)
    else:
        outcsv = os.path.join(UPLOAD_DIR, "scores.csv")
    
    # Calculate percentage (assuming total possible marks is 100)
    total_possible = 100
    percentage = round((section_scores["Total"] / total_possible) * 100, 2) if total_possible > 0 else 0
    
    # Prepare row data with all required columns
    row = [
        student_name,  # Student Name
        roll_no,       # Roll Number
        section_scores.get("Python", 0),      # Python
        section_scores.get("EDA", 0),         # EDA
        section_scores.get("SQL", 0),         # SQL
        section_scores.get("Power BI", 0),    # Power BI
        section_scores.get("Statistics", 0),  # Statistics
        section_scores["Total"],              # Marks Obtained
        total_possible,                       # Total Marks
        percentage,                           # Percentage
        set_name                              # Set Name
    ]
    
    # Check if file exists and has headers
    is_new = not os.path.exists(outcsv)
    if is_new:
        # Create new file with headers
        headers = ["Student Name", "Roll Number", "Python", "EDA", "SQL", "Power BI", "Statistics", 
                  "Marks Obtained", "Total Marks", "Percentage", "Set Name"]
        with open(outcsv, "w", newline="", encoding="utf-8") as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow(headers)
            writer.writerow(row)
    else:
        # Append to existing file
        with open(outcsv, "a", newline="", encoding="utf-8") as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow(row)

    return {
        "name": student_name,
        "roll_no": roll_no,
        "set": set_name,
        "score": section_scores["Total"],
        "section_scores": section_scores,
        "percentage": percentage,
        "csv_file": csv_filename or "scores.csv"
    }

@app.get("/all-scores")
def all_scores():
    csv_file = os.path.join(UPLOAD_DIR, "scores.csv")
    if not os.path.exists(csv_file):
        return []
    with open(csv_file, newline="") as f:
        reader = list(csv.reader(f))
    if not reader:
        return []
    keys = reader[0]
    results = [dict(zip(keys, row)) for row in reader[1:]]
    return results

@app.get("/answer-key-sets")
def get_answer_key_sets():
    """Get list of all existing answer key sets"""
    sets = []
    if os.path.exists(ANSWERKEY_DIR):
        for filename in os.listdir(ANSWERKEY_DIR):
            if filename.startswith("answers_") and filename.endswith(".json"):
                set_name = filename.replace("answers_", "").replace(".json", "")
                sets.append(set_name)
    return {"sets": sorted(sets)}

@app.get("/csv-files")
def get_csv_files():
    """Get list of all existing CSV files"""
    csv_files = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if filename.endswith(".csv"):
                csv_files.append(filename)
    return {"files": sorted(csv_files)}

@app.post("/create-csv")
async def create_csv_file(filename: str = Form(...)):
    """Create a new CSV file with headers"""
    if not filename.endswith(".csv"):
        filename += ".csv"
    
    csv_path = os.path.join(UPLOAD_DIR, filename)
    
    # Check if file already exists
    if os.path.exists(csv_path):
        raise HTTPException(400, f"CSV file '{filename}' already exists!")
    
    # Create CSV with headers
    headers = ["Student Name", "Roll Number", "Python", "EDA", "SQL", "Power BI", "Statistics", 
              "Marks Obtained", "Total Marks", "Percentage", "Set Name"]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
    
    return {"message": f"CSV file '{filename}' created successfully!", "filename": filename}

@app.get("/current-csv")
def get_current_csv():
    """Get the currently selected CSV file"""
    # This will be managed by the frontend session state
    return {"current_csv": None}

@app.get("/health")
def health_check():
    """Health check endpoint for deployment"""
    return {"status": "healthy", "message": "OMR API is running"}

@app.get("/", response_class=HTMLResponse)
def root():
    """Root endpoint - serve main HTML page"""
    with open("index.html", "r") as f:
        return f.read()

@app.get("/streamlit", response_class=HTMLResponse)
def streamlit_app():
    """Streamlit app endpoint - serve a simplified OMR interface"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OMR Scoring Application</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 30px; 
                text-align: center; 
            }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .header p { font-size: 1.2em; opacity: 0.9; }
            .content { padding: 30px; }
            .section { 
                margin-bottom: 40px; 
                padding: 25px; 
                border: 2px solid #f0f0f0; 
                border-radius: 10px; 
                background: #fafafa;
            }
            .section h2 { 
                color: #667eea; 
                margin-bottom: 20px; 
                font-size: 1.8em;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }
            .form-group { margin-bottom: 20px; }
            .form-group label { 
                display: block; 
                margin-bottom: 8px; 
                font-weight: 600; 
                color: #333; 
            }
            .form-group input, .form-group textarea, .form-group select { 
                width: 100%; 
                padding: 12px; 
                border: 2px solid #ddd; 
                border-radius: 8px; 
                font-size: 16px;
                transition: border-color 0.3s;
            }
            .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 8px; 
                font-size: 16px; 
                cursor: pointer; 
                transition: transform 0.2s;
                margin: 10px 5px;
            }
            .btn:hover { transform: translateY(-2px); }
            .btn-secondary { background: #6c757d; }
            .alert { 
                padding: 15px; 
                margin: 15px 0; 
                border-radius: 8px; 
                font-weight: 500;
            }
            .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { 
                background: white; 
                padding: 20px; 
                border-radius: 10px; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                border: 1px solid #e0e0e0;
            }
            .status { 
                display: inline-block; 
                padding: 5px 15px; 
                border-radius: 20px; 
                font-size: 14px; 
                font-weight: 600;
            }
            .status-success { background: #d4edda; color: #155724; }
            .status-warning { background: #fff3cd; color: #856404; }
            .back-btn { 
                display: inline-block; 
                background: #6c757d; 
                color: white; 
                padding: 10px 20px; 
                text-decoration: none; 
                border-radius: 5px; 
                margin-bottom: 20px;
            }
            .back-btn:hover { background: #5a6268; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 OMR Scoring Application</h1>
                <p>Automated Optical Mark Recognition & Scoring System</p>
            </div>
            
            <div class="content">
                <a href="/" class="back-btn">← Back to Home</a>
                
                <div class="alert alert-success">
                    <strong>✅ Application Status:</strong> The OMR scoring system is fully operational! 
                    All features are available through the interface below and the backend API.
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>📚 Answer Key Sets</h3>
                        <p>Create and manage multiple answer key sets for different exams.</p>
                        <div class="form-group">
                            <label>Set Name:</label>
                            <input type="text" placeholder="Enter set name (A, B, C, etc.)" maxlength="1">
                        </div>
                        <div class="form-group">
                            <label>Answer Key Data:</label>
                            <textarea rows="4" placeholder="Paste your answer key data here..."></textarea>
                        </div>
                        <button class="btn">Save Answer Key</button>
                    </div>
                    
                    <div class="card">
                        <h3>💾 CSV Data Storage</h3>
                        <p>Organize your results with custom CSV files.</p>
                        <div class="form-group">
                            <label>CSV File Name:</label>
                            <input type="text" placeholder="Enter CSV file name">
                        </div>
                        <button class="btn">Create New CSV</button>
                        <button class="btn btn-secondary">Select Existing CSV</button>
                    </div>
                    
                    <div class="card">
                        <h3>📝 OMR Processing</h3>
                        <p>Upload OMR sheets for automated scoring.</p>
                        <div class="form-group">
                            <label>Student Name:</label>
                            <input type="text" placeholder="Enter student name">
                        </div>
                        <div class="form-group">
                            <label>Roll Number:</label>
                            <input type="text" placeholder="Enter roll number">
                        </div>
                        <div class="form-group">
                            <label>Answer Key Set:</label>
                            <select>
                                <option>Select answer key set</option>
                                <option>Set A</option>
                                <option>Set B</option>
                                <option>Set C</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>OMR Sheet Image:</label>
                            <input type="file" accept="image/*">
                        </div>
                        <button class="btn">Upload & Score OMR</button>
                    </div>
                    
                    <div class="card">
                        <h3>📈 Results Dashboard</h3>
                        <p>View and analyze student results.</p>
                        <div class="status status-success">System Ready</div>
                        <p style="margin-top: 15px;">No results yet. Upload OMR sheets to see data here.</p>
                        <button class="btn btn-secondary">View All Results</button>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🔧 API Endpoints</h2>
                    <p>Access the backend API directly:</p>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        <li><strong>Health Check:</strong> <a href="/health" target="_blank">/health</a></li>
                        <li><strong>API Documentation:</strong> <a href="/docs" target="_blank">/docs</a></li>
                        <li><strong>Answer Key Sets:</strong> <a href="/answer-key-sets" target="_blank">/answer-key-sets</a></li>
                        <li><strong>CSV Files:</strong> <a href="/csv-files" target="_blank">/csv-files</a></li>
                    </ul>
                </div>
            </div>
        </div>
        
        <script>
            // Add real functionality
            document.addEventListener('DOMContentLoaded', function() {
                loadAnswerKeySets();
                loadCSVFiles();
                loadResults();
                
                // Add event listeners
                document.querySelectorAll('.btn').forEach(btn => {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const action = this.textContent.trim();
                        
                        if (action === 'Save Answer Key') {
                            saveAnswerKey();
                        } else if (action === 'Create New CSV') {
                            createCSV();
                        } else if (action === 'Select Existing CSV') {
                            selectCSV();
                        } else if (action === 'Upload & Score OMR') {
                            uploadOMR();
                        } else if (action === 'View All Results') {
                            viewResults();
                        }
                    });
                });
            });
            
            async function loadAnswerKeySets() {
                try {
                    const response = await fetch('/answer-key-sets');
                    const data = await response.json();
                    updateAnswerKeyDisplay(data.sets || []);
                } catch (error) {
                    console.log('Error loading answer key sets:', error);
                }
            }
            
            async function loadCSVFiles() {
                try {
                    const response = await fetch('/csv-files');
                    const data = await response.json();
                    updateCSVDisplay(data.files || []);
                } catch (error) {
                    console.log('Error loading CSV files:', error);
                }
            }
            
            async function loadResults() {
                try {
                    const response = await fetch('/all-scores');
                    const data = await response.json();
                    updateResultsDisplay(data);
                } catch (error) {
                    console.log('Error loading results:', error);
                }
            }
            
            function updateAnswerKeyDisplay(sets) {
                const display = document.querySelector('.answer-key-display') || createDisplay('answer-key-display', 'Answer Key Sets');
                display.innerHTML = sets.length > 0 ? 
                    'Available Sets: ' + sets.join(', ') : 
                    'No answer key sets created yet.';
            }
            
            function updateCSVDisplay(files) {
                const display = document.querySelector('.csv-display') || createDisplay('csv-display', 'CSV Files');
                display.innerHTML = files.length > 0 ? 
                    'Available Files: ' + files.join(', ') : 
                    'No CSV files created yet.';
            }
            
            function updateResultsDisplay(results) {
                const display = document.querySelector('.results-display') || createDisplay('results-display', 'Results');
                if (results && results.length > 0) {
                    let html = '<table style="width:100%; border-collapse: collapse;"><tr><th>Name</th><th>Roll</th><th>Score</th><th>Set</th></tr>';
                    results.forEach(result => {
                        html += `<tr><td>${result.Name || result.name || 'N/A'}</td><td>${result.Roll || result.roll || 'N/A'}</td><td>${result.Total || result.total || 'N/A'}</td><td>${result.Set || result.set || 'N/A'}</td></tr>`;
                    });
                    html += '</table>';
                    display.innerHTML = html;
                } else {
                    display.innerHTML = 'No results available yet. Upload OMR sheets to see results here.';
                }
            }
            
            function createDisplay(className, title) {
                const section = document.querySelector('.section');
                const display = document.createElement('div');
                display.className = className;
                display.style.cssText = 'margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;';
                section.appendChild(display);
                return display;
            }
            
            async function saveAnswerKey() {
                const setName = document.querySelector('input[placeholder*="set name"]').value;
                const answerData = document.querySelector('textarea[placeholder*="answer key data"]').value;
                
                if (!setName || !answerData) {
                    alert('Please enter both set name and answer key data!');
                    return;
                }
                
                try {
                    const formData = new FormData();
                    formData.append('set_name', setName);
                    formData.append('block', answerData);
                    
                    const response = await fetch('/create-bulk-answerkey', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        alert('✅ ' + result.message);
                        document.querySelector('input[placeholder*="set name"]').value = '';
                        document.querySelector('textarea[placeholder*="answer key data"]').value = '';
                        loadAnswerKeySets();
                    } else {
                        const error = await response.text();
                        alert('❌ Error: ' + error);
                    }
                } catch (error) {
                    alert('❌ Error saving answer key: ' + error.message);
                }
            }
            
            async function createCSV() {
                const csvName = document.querySelector('input[placeholder*="CSV file name"]').value;
                
                if (!csvName) {
                    alert('Please enter a CSV file name!');
                    return;
                }
                
                try {
                    const formData = new FormData();
                    formData.append('filename', csvName);
                    
                    const response = await fetch('/create-csv', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        alert('✅ ' + result.message);
                        document.querySelector('input[placeholder*="CSV file name"]').value = '';
                        loadCSVFiles();
                    } else {
                        const error = await response.text();
                        alert('❌ Error: ' + error);
                    }
                } catch (error) {
                    alert('❌ Error creating CSV: ' + error.message);
                }
            }
            
            function selectCSV() {
                alert('CSV Selection: This would show a dropdown of available CSV files for selection.');
            }
            
            async function uploadOMR() {
                const studentName = document.querySelector('input[placeholder*="student name"]').value;
                const rollNo = document.querySelector('input[placeholder*="roll number"]').value;
                const omrSet = document.querySelector('select').value;
                const fileInput = document.querySelector('input[type="file"]');
                
                if (!studentName || !rollNo || !omrSet || !fileInput.files[0]) {
                    alert('Please fill all fields and select an image file!');
                    return;
                }
                
                try {
                    // Upload OMR
                    const formData = new FormData();
                    formData.append('file', fileInput.files[0]);
                    formData.append('student_name', studentName);
                    formData.append('roll_no', rollNo);
                    formData.append('omr_set', omrSet);
                    
                    const uploadResponse = await fetch('/upload-omr', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (uploadResponse.ok) {
                        // Evaluate OMR
                        const evalData = new FormData();
                        evalData.append('student_name', studentName);
                        evalData.append('roll_no', rollNo);
                        evalData.append('omr_set', omrSet);
                        
                        const evalResponse = await fetch('/evaluate', {
                            method: 'POST',
                            body: evalData
                        });
                        
                        if (evalResponse.ok) {
                            const result = await evalResponse.json();
                            alert(`✅ OMR Processed Successfully!\\nScore: ${result.score}/100\\nPercentage: ${result.percentage}%\\nSet: ${result.set}`);
                            
                            // Clear form
                            document.querySelector('input[placeholder*="student name"]').value = '';
                            document.querySelector('input[placeholder*="roll number"]').value = '';
                            document.querySelector('select').value = '';
                            fileInput.value = '';
                            
                            loadResults();
                        } else {
                            const error = await evalResponse.text();
                            alert('❌ Error evaluating OMR: ' + error);
                        }
                    } else {
                        const error = await uploadResponse.text();
                        alert('❌ Error uploading OMR: ' + error);
                    }
                } catch (error) {
                    alert('❌ Error processing OMR: ' + error.message);
                }
            }
            
            function viewResults() {
                loadResults();
                alert('Results refreshed! Check the Results Dashboard section below.');
            }
        </script>
    </body>
    </html>
    """