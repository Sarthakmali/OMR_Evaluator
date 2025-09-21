# OMR Scoring Application

A web-based Optical Mark Recognition (OMR) scoring system that allows users to upload answer keys, process OMR sheets, and generate detailed score reports.

## 🌟 Features

- **Answer Key Management**: Create and manage multiple answer key sets (Set A, B, C, etc.)
- **CSV Data Storage**: Create and select CSV files for organized data storage
- **OMR Processing**: Upload and automatically score OMR sheets
- **Results Dashboard**: View comprehensive student results with statistics
- **Cloud Ready**: Deploy to any cloud platform with Docker support

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd omr_core
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   # Terminal 1 - Backend
   uvicorn main:app --reload --port 8000
   
   # Terminal 2 - Frontend
   streamlit run app.py --server.port 8501
   ```

4. **Access the application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or with Docker directly
docker build -t omr-app .
docker run -p 8000:8000 -p 8501:8501 omr-app
```

## 🌐 Cloud Deployment

This application is ready for deployment on free cloud platforms:

- **Railway**: [Deploy with Railway](https://railway.app)
- **Render**: [Deploy with Render](https://render.com)
- **Heroku**: [Deploy with Heroku](https://heroku.com)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## 📖 How to Use

1. **Add Answer Key Sets**
   - Click "Add New Set" to create answer keys
   - Enter set name (A, B, C, etc.)
   - Paste answer key data in the specified format

2. **Select Data Storage**
   - Choose an existing CSV file or create a new one
   - CSV files store all student results with proper headers

3. **Upload and Score OMR Sheets**
   - Enter student details (name, roll number)
   - Select the appropriate answer key set
   - Upload OMR sheet image
   - View instant scoring results

4. **View Results**
   - Access the Results Dashboard
   - View individual scores and statistics
   - Export data from selected CSV files

## 🛠️ Technical Details

- **Backend**: FastAPI (Python)
- **Frontend**: Streamlit (Python)
- **OMR Processing**: OpenCV + NumPy
- **Data Storage**: CSV files
- **Deployment**: Docker containers

## 📁 Project Structure

```
omr_core/
├── app.py                 # Streamlit frontend
├── main.py               # FastAPI backend
├── omr_scoring.py        # OMR processing logic
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Local development
└── DEPLOYMENT.md        # Deployment guide
```

## 🔧 Configuration

The application uses environment variables for configuration:

- `UPLOAD_DIR`: Directory for uploaded files
- `ANSWERKEY_DIR`: Directory for answer keys
- `API_BASE_URL`: Backend API URL

## 📊 CSV Output Format

The application generates CSV files with the following columns:

- Student Name
- Roll Number
- Python, EDA, SQL, Power BI, Statistics (subject scores)
- Marks Obtained
- Total Marks
- Percentage
- Set Name

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is open source. Feel free to use, modify, and distribute.

## 🆘 Support

For issues and questions:
1. Check the [DEPLOYMENT.md](DEPLOYMENT.md) guide
2. Review the application logs
3. Create an issue in the repository
