import os
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mls_cyber_secret_key_99'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mls_vault.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['FINAL_FOLDER'] = 'mls_final'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    credits = db.Column(db.Integer, default=100)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    return float(subprocess.check_output(cmd, shell=True))

# --- Core Video Engine (NO ZOOM VERSION) ---
def edit_video(video_path, audio_path, bg_music_path=None):
    output_filename = f"final_{os.path.basename(video_path)}"
    output_path = os.path.join(app.config['FINAL_FOLDER'], output_filename)
    
    if not os.path.exists(app.config['FINAL_FOLDER']):
        os.makedirs(app.config['FINAL_FOLDER'])

    # 1. Silence Remove
    processed_audio = "temp_voice_clean.mp3"
    subprocess.run(['ffmpeg', '-y', '-i', audio_path, '-af', 'silenceremove=stop_periods=-1:stop_duration=0.1:stop_threshold=-30dB', processed_audio])

    # 2. Sync Calculation
    v_dur = get_duration(video_path)
    a_dur = get_duration(processed_audio)
    speed = a_dur / v_dur

    # 3. NO ZOOM Filter: Sirf size fix karega, zoom nahi karega
    # pad=1080:1920:(ow-iw)/2:(oh-ih)/2 se video center mein rahegi bina zoom hue
    no_zoom_filter = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

    if bg_music_path:
        filter_complex = (
            f"[0:v]{no_zoom_filter},setpts={speed}*PTS[v]; "
            f"[1:a]volume=1.8[voice]; "
            f"[2:a]volume=0.08,aloop=loop=-1:size=2e9[bg]; "
            f"[voice][bg]amix=inputs=2:duration=first[a]"
        )
        cmd = ['ffmpeg', '-y', '-i', video_path, '-i', processed_audio, '-i', bg_music_path, '-filter_complex', filter_complex, '-map', '[v]', '-map', '[a]']
    else:
        filter_complex = f"[0:v]{no_zoom_filter},setpts={speed}*PTS[v]"
        cmd = ['ffmpeg', '-y', '-i', video_path, '-i', processed_audio, '-filter_complex', filter_complex, '-map', '[v]', '-map', '1:a']

    cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-c:a', 'aac', '-shortest', output_path])
    
    subprocess.run(cmd)
    if os.path.exists(processed_audio): os.remove(processed_audio)
    return output_filename

# --- Routes ---
@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        return "Invalid Login", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        new_user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/edit', methods=['POST'])
@login_required
def edit():
    if current_user.credits < 25: return jsonify({'success': False, 'error': 'Low Credits!'})
    v_file, a_file = request.files['video'], request.files['audio']
    bg_file = request.files.get('bg_music')
    v_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(v_file.filename))
    a_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(a_file.filename))
    v_file.save(v_path); a_file.save(a_path)
    bg_path = None
    if bg_file:
        bg_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(bg_file.filename))
        bg_file.save(bg_path)
    try:
        output_file = edit_video(v_path, a_path, bg_path)
        current_user.credits -= 25
        db.session.commit()
        return jsonify({'success': True, 'download_url': url_for('download_file', filename=output_file)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['FINAL_FOLDER'], filename, as_attachment=True)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    for folder in [app.config['UPLOAD_FOLDER'], app.config['FINAL_FOLDER']]:
        if not os.path.exists(folder): os.makedirs(folder)
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=5500)
