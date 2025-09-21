# OMR Scoring App - Cloud Deployment Guide

This guide will help you deploy the OMR Scoring application to free cloud hosting platforms.

## 🚀 Quick Deploy Options

### Option 1: Railway (Recommended - Easiest)

1. **Fork this repository** to your GitHub account
2. Go to [Railway.app](https://railway.app)
3. Sign up with GitHub
4. Click "New Project" → "Deploy from GitHub repo"
5. Select your forked repository
6. Railway will automatically detect the Dockerfile and deploy
7. Your app will be available at: `https://your-app-name.railway.app`

### Option 2: Render

1. **Fork this repository** to your GitHub account
2. Go to [Render.com](https://render.com)
3. Sign up with GitHub
4. Click "New" → "Web Service"
5. Connect your GitHub repository
6. Select "Docker" as the environment
7. Render will use the provided `render.yaml` configuration
8. Your app will be available at: `https://your-app-name.onrender.com`

### Option 3: Heroku (Alternative)

1. **Fork this repository** to your GitHub account
2. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
3. Create a new Heroku app:
   ```bash
   heroku create your-omr-app-name
   ```
4. Deploy:
   ```bash
   git push heroku main
   ```
5. Your app will be available at: `https://your-omr-app-name.herokuapp.com`

## 🔧 Local Testing with Docker

Before deploying, you can test locally:

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run with Docker
docker build -t omr-app .
docker run -p 8000:8000 -p 8501:8501 omr-app
```

Access the app at:
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000

## 📁 File Structure

```
omr_core/
├── app.py                 # Streamlit frontend
├── main.py               # FastAPI backend
├── omr_scoring.py        # OMR processing logic
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Local development
├── railway.json         # Railway deployment config
├── render.yaml          # Render deployment config
└── DEPLOYMENT.md        # This guide
```

## 🌐 Environment Variables

The app uses these environment variables (automatically set in cloud deployments):

- `UPLOAD_DIR`: Directory for uploaded files (default: "uploaded_omr")
- `ANSWERKEY_DIR`: Directory for answer keys (default: "answer_keys")
- `API_BASE_URL`: Backend API URL (auto-configured in cloud)

## 📊 Features

- ✅ **Answer Key Management**: Create and manage multiple answer key sets
- ✅ **CSV Data Storage**: Create and select CSV files for data storage
- ✅ **OMR Processing**: Upload and score OMR sheets automatically
- ✅ **Results Dashboard**: View and analyze student results
- ✅ **Cloud Ready**: Works on any cloud platform with Docker support

## 🔒 Security Notes

- The app is configured for public access (CORS enabled)
- File uploads are limited to image formats
- No authentication is implemented (add if needed for production)

## 🆘 Troubleshooting

### Common Issues:

1. **Port conflicts**: Make sure ports 8000 and 8501 are available
2. **Memory issues**: Free tiers have limited memory, try smaller images
3. **File persistence**: Files are stored in container (temporary in free tiers)

### Getting Help:

- Check the application logs in your hosting platform
- Ensure all dependencies are installed correctly
- Verify the Dockerfile builds successfully locally

## 🎯 Production Considerations

For production use, consider:

1. **Database**: Replace file storage with a database
2. **Authentication**: Add user login/registration
3. **File Storage**: Use cloud storage (AWS S3, etc.)
4. **Monitoring**: Add logging and monitoring
5. **Scaling**: Use multiple instances behind a load balancer

## 📝 License

This project is open source. Feel free to modify and distribute.
