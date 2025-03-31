from flask import Flask, render_template, url_for, request, redirect, session, flash
import sqlite3
import os
import random
from datetime import datetime
import torch
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this for production
app.config['UPLOAD_FOLDER'] = 'static/audio'  # Keep this for static folder structure
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allow XttsConfig for loading (to prevent WeightsUnpickler error)
torch.serialization.add_safe_globals([XttsConfig])

# Initialize Coqui TTS
try:
    # Get device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Load the model with safe configuration
    tts_coqui = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device == "cuda"))
    print("Coqui TTS initialized successfully")
except Exception as e:
    print(f"Could not initialize Coqui TTS: {e}")
    tts_coqui = None

@app.route('/')
def home():
    return render_template('home.html')

@app.route("/signup")
def signup():
    name = request.args.get('username', '')
    number = request.args.get('number', '')
    email = request.args.get('email', '')
    password = request.args.get('psw', '')

    con = sqlite3.connect('signup.db')
    cur = con.cursor()
    cur.execute("insert into `detail` (`name`,`number`,`email`, `password`) VALUES (?, ?, ?, ?)", (name, number, email, password))
    con.commit()
    con.close()

    return render_template("signup-in.html")

@app.route("/signin")
def signin():
    mail1 = request.args.get('name', '')
    password1 = request.args.get('psw', '')
    con = sqlite3.connect('signup.db')
    cur = con.cursor()
    cur.execute("select `name`, `password` from detail where `name` = ? AND `password` = ?", (mail1, password1,))
    data = cur.fetchone()
    print(data)

    if data == None:
        return render_template("signup-in.html")    
    elif mail1 == 'admin' and password1 == 'admin':
        return render_template("index.html")
    elif mail1 == str(data[0]) and password1 == str(data[1]):
        return render_template("index.html")
    else:
        return render_template("signup-in.html")

@app.route('/predict', methods=['POST'])
def predict():
    try:
        text = request.form.get('message', '').strip()
        emotion = request.form.get('emotion', 'neutral')  # Get selected emotion

        if not text:
            flash("Please enter text to convert", "warning")
            return redirect(url_for('index'))

        # Map emotions to reference speaker folders (audio files for each emotion)
        emotion_speakers = {
            "happy": "audio_files/happiness",  # Folder for happy emotion audio files
            "sad": "audio_files/sadness",      # Folder for sad emotion audio files
            "angry": "audio_files/anger",     # Folder for angry emotion audio files
            "fear": "audio_files/fear",       # Folder for fear emotion audio files
            "disgust": "audio_files/disgust", # Folder for disgust emotion audio files
            "neutral": "audio_files/neutral"  # Folder for neutral emotion audio files
        }

        # Use absolute paths for the folders
        base_dir = os.path.abspath(os.path.dirname(__file__))  # Current directory
        emotion_speakers_full_path = {emotion: os.path.join(base_dir, folder) for emotion, folder in emotion_speakers.items()}

        # Fetch a random file from the respective emotion folder
        speaker_folder = emotion_speakers_full_path.get(emotion, emotion_speakers_full_path['neutral'])
        speaker_file = random.choice(os.listdir(speaker_folder))
        speaker_wav = os.path.join(speaker_folder, speaker_file)

        # Generate unique filename for output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_file = f"speech_{timestamp}.wav"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_file)  # Save audio to the desired folder

        # Generate speech using Coqui TTS
        if tts_coqui:
            try:
                tts_coqui.tts_to_file(
                    text=text,
                    speaker_wav=speaker_wav,
                    language="en",
                    file_path=file_path
                )
                print(f"Saved Coqui TTS audio to: {file_path}")
            except Exception as coqui_error:
                print(f"Coqui TTS failed: {coqui_error}")
                raise Exception("TTS generation failed")

        if not os.path.exists(file_path):
            raise Exception("Audio file was not created")

        return render_template('index.html', audio_file=audio_file, original_text=text)

    except Exception as e:
        print(f"Error in speech generation: {str(e)}")
        flash(f"Error generating speech: {str(e)}", "danger")
        return redirect(url_for('index'))


@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/signout')
def signout():
    return render_template('signup-in.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
