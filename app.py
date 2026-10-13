import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import yt_dlp
ADMIN_CODE = "BF-ADMIN-2026"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'profile_pics')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'music'), exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- Database Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    profile_image = db.Column(db.String(200), default='default.png')
    is_admin = db.Column(db.Boolean, default=False)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    downloads = db.relationship('DownloadedSong', backref='user', lazy=True, cascade="all, delete-orphan")
    favorites = db.relationship('FavoriteSong', backref='user', lazy=True, cascade="all, delete-orphan")
    playlists = db.relationship('Playlist', backref='user', lazy=True, cascade="all, delete-orphan")
    search_histories = db.relationship('SearchHistory', backref='user', lazy=True, cascade="all, delete-orphan")

class DownloadedSong(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    song_title = db.Column(db.String(200), nullable=False)
    youtube_id = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    thumbnail_path = db.Column(db.String(200))

class FavoriteSong(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    song_title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    thumbnail_path = db.Column(db.String(200))

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    songs = db.relationship('PlaylistSong', backref='playlist', lazy=True, cascade="all, delete-orphan")

class PlaylistSong(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    song_title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(200), nullable=False)
    song_title = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
@login_required
def index():
    user_songs = DownloadedSong.query.filter_by(user_id=current_user.id).all()
    user_favs = FavoriteSong.query.filter_by(user_id=current_user.id).all()
    user_playlists = Playlist.query.filter_by(user_id=current_user.id).all()

    favorite_paths = {
    fav.file_path
    for fav in user_favs
}
    
    return render_template('index.html', username=current_user.username, downloaded_songs=user_songs, favorites=user_favs, playlists=user_playlists,favorite_paths=favorite_paths)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user_exists = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if user_exists:
            flash('Username or Email already exists!', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        admin_code = request.form.get('admin_code')
        is_admin = False

        if admin_code == ADMIN_CODE:
            is_admin = True

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            is_admin=is_admin
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                if current_user.profile_image != 'default.png':
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_image = filename
                db.session.commit()
                flash('Profile picture updated successfully!', 'success')
                return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

@app.route('/delete_profile_pic')
@login_required
def delete_profile_pic():
    if current_user.profile_image != 'default.png':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_image)
        if os.path.exists(file_path):
            os.remove(file_path)
        current_user.profile_image = 'default.png'
        db.session.commit()
        flash('Profile picture removed successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)

@app.route('/change_name', methods=['POST'])
@login_required
def change_name():
    new_name = request.form.get('username')

    if new_name:
        current_user.username = new_name
        db.session.commit()
    return redirect(url_for('settings'))

@app.route('/change_email', methods=['POST'])
@login_required
def change_email():
    new_email = request.form.get('email')

    if new_email:
        current_user.email = new_email
        db.session.commit()

    return redirect(url_for('settings'))  

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    old = request.form.get('old_password')
    new = request.form.get('new_password')

    if check_password_hash(current_user.password, old):
        current_user.password = generate_password_hash(new)
        db.session.commit()

    return redirect(url_for('settings'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('index'))
    total_users = User.query.count()
    total_downloads = DownloadedSong.query.count()
    all_users = User.query.all()
    return render_template('admin.html', total_users=total_users, total_downloads=total_downloads, all_users=all_users)

def get_youtube_audio_stream(video_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractor_args':{
            'youtube':{
                'player_client': ['ios', 'web']
            }
        },
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return info['url']
    except Exception as e:
        print(f"Error fetching stream for {video_id}: {e}")
        return None

@app.route('/admin/user/<int:user_id>')
@login_required
def user_detail(user_id):

    if not current_user.is_admin:
        flash("Access denied!", "error")
        return redirect(url_for("index"))

    user = User.query.get_or_404(user_id)

    download_count = DownloadedSong.query.filter_by(user_id=user.id).count()
    favorite_count = FavoriteSong.query.filter_by(user_id=user.id).count()

    return render_template(
        "user_detail.html",
        user=user,
        download_count=download_count,
        favorite_count=favorite_count
    )

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):

    # ❗ only admin can delete
    if not current_user.is_admin:
        return redirect(url_for("index"))

    user = db.session.get(User, user_id)

    if not user:
        return redirect(url_for("admin_dashboard"))

    # ❌ protect admin account
    if user.is_admin:
        flash("You cannot delete admin account!", "error")
        return redirect(url_for("admin_dashboard"))

    # ❌ protect self delete
    if user.id == current_user.id:
        flash("You cannot delete yourself!", "error")
        return redirect(url_for("admin_dashboard"))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_song():
    search_results = []
    query = ""
    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            new_history = SearchHistory(user_id=current_user.id, query=query, song_title="Searching....") 
            db.session.add(new_history)
            db.session.commit()
            
            user_histories = db.session.query(SearchHistory).filter_by(user_id=current_user.id).order_by(SearchHistory.timestamp.desc()).all()
            if len(user_histories) > 20:
                for old_h in user_histories[20:]:
                    db.session.delete(old_h)
                db.session.commit()

            ydl_opts = {'quiet': True, 'skip_download': True, 'extract_flat': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    result = ydl.extract_info(f"ytsearch5:{query}", download=False)
                    if 'entries' in result:
                        for entry in result['entries']:
                            video_id = entry.get('id')
                            audio_stream_url = get_youtube_audio_stream(video_id)
                            search_results.append({
                                'title': entry.get('title'), 
                                'id': video_id,
                                'audio_url': audio_stream_url})
                except Exception as e:
                    print(f"Search error: {e}")
                    flash('Search failed.', 'error')
                    
    user_playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return render_template('search.html', results=search_results, query=query, playlists=user_playlists)

@app.route('/download/<video_id>')
@login_required
def download_song(video_id):

    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    music_folder = os.path.join('static', 'music')
    output_template = os.path.join(music_folder, f"{video_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web']
            }
        },
        'outtmpl': output_template,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            song_title = info.get('title', 'Unknown Title')
            actual_ext = info.get('ext', 'webm')

        file_path = f"music/{video_id}.{actual_ext}"

        # ⭐ THUMBNAIL ADD HERE
        thumb_path = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

        if not DownloadedSong.query.filter_by(
            user_id=current_user.id,
            youtube_id=video_id
        ).first():

            new_download = DownloadedSong(
                user_id=current_user.id,
                song_title=song_title,
                youtube_id=video_id,
                file_path=file_path,
                thumbnail_path=thumb_path   # ⭐ ADD THIS
            )

            db.session.add(new_download)

            new_history = SearchHistory(
                user_id=current_user.id,
                query=song_title,
                song_title=song_title
            )
            db.session.add(new_history)

            db.session.commit()

            flash(f'Downloaded "{song_title}"!', 'success')

    except Exception as e:
        print(e)
        flash('Download failed.', 'error')

    next_page = request.args.get('next')
    return redirect(next_page or request.referrer or url_for('search_song'))

@app.route('/delete_song/<int:song_id>')
@login_required
def delete_song(song_id):

    song = DownloadedSong.query.get_or_404(song_id)

    if song.user_id != current_user.id:
        flash("Permission denied.")
        return redirect(url_for("playlist"))

    # Favorite ထဲကလည်းဖျက်
    fav = FavoriteSong.query.filter_by(
        user_id=current_user.id,
        file_path=song.file_path
    ).first()

    if fav:
        db.session.delete(fav)

    # Database ထဲက DownloadedSong ကိုဖျက်
    db.session.delete(song)
    db.session.commit()

    # File ကိုနောက်မှဖျက်
    file_path = os.path.join("static", song.file_path)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except PermissionError:
        flash("Song removed, but audio file is still playing. Close the player and delete again.")

    flash("Song deleted successfully.")
    return redirect(url_for("playlist"))

@app.route('/add_favorite/<int:download_id>', methods=['POST'])
@login_required
def add_favorite(download_id):
    song = DownloadedSong.query.get_or_404(download_id)
    existing = FavoriteSong.query.filter_by(user_id=current_user.id, file_path=song.file_path).first()
    if existing:
        return jsonify({"success": False, "message": "Already in favorites"})
    
    thumb = getattr(song, 'thumbnail_path', None) or getattr(song, 'thumb_path', None)
    fav = FavoriteSong(
        user_id=current_user.id,
        song_title=song.song_title,
        file_path=song.file_path,
        thumbnail_path=thumb
    )
    db.session.add(fav)
    db.session.commit()
    return jsonify({"success": True, "message": "Added to favorites"})

@app.route('/toggle_favorite/<int:download_id>', methods=['POST'])
@login_required
def toggle_favorite(download_id):
    song = DownloadedSong.query.get_or_404(download_id)
    
    fav = FavoriteSong.query.filter_by(
        user_id=current_user.id,
        file_path=song.file_path
    ).first()
    
    if fav:
        # 🌟 ရှိပြီးသားမို့လို့ Database ထဲက ဖျက်ပြီး အဖြူပြန်ပြောင်းခိုင်းမယ်
        db.session.delete(fav)
        db.session.commit()
        return jsonify({"favorite": False, "message": "Removed from favorites"})
    else:
        # 🌟 မရှိသေးရင် Database ထဲအသစ်ထည့်ပြီး အနီပြောင်းခိုင်းမယ်
        thumb = getattr(song, 'thumbnail_path', None) or getattr(song, 'thumb_path', None)
        new_fav = FavoriteSong(
            user_id=current_user.id,
            song_title=song.song_title,
            file_path=song.file_path,
            thumbnail_path=thumb
        )
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({"favorite": True, "message": "Added to favorites"})


@app.route('/add_favorite_playlist/<int:song_id>', methods=['GET', 'POST'])
@login_required
def add_favorite_playlist(song_id):
    song = PlaylistSong.query.get_or_404(song_id)
    
    existing = FavoriteSong.query.filter_by(user_id=current_user.id, file_path=song.file_path).first()
    if existing:
        return jsonify({"success": False, "message": "Already in favorites"})
    
    thumb = getattr(song, 'thumb_path', None) or getattr(song, 'thumbnail_path', None)
    fav = FavoriteSong(
        user_id=current_user.id,
        song_title=song.song_title,
        file_path=song.file_path,
        thumbnail_path=thumb
    )
    db.session.add(fav)
    db.session.commit()
    return jsonify({"success": True, "message": "Added to favorites"})

@app.route('/delete_favorite/<int:fav_id>')
@login_required
def delete_favorite(fav_id):
    fav = db.session.get(FavoriteSong, fav_id)
    if fav and fav.user_id == current_user.id:
        db.session.delete(fav)
        db.session.commit()
    return jsonify({"success": True})

@app.route('/delete_playlist/<int:playlist_id>', methods=['POST', 'GET'])
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id == current_user.id:
        db.session.delete(playlist)
        db.session.commit()
        flash('Playlist deleted successfully!', 'success')
    else:
        flash('Permission denied.', 'error')
    return redirect(url_for('playlist'))

@app.route('/add_to_playlist_direct', methods=['POST'])
@login_required
def add_to_playlist_direct():
    video_id = request.form.get('video_id')
    song_title = request.form.get('song_title')
    playlist_id = request.form.get('playlist_id')
    pl = db.session.get(Playlist, playlist_id)
    if video_id and song_title and pl and pl.user_id == current_user.id:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        music_folder = os.path.join('static', 'music')
        output_template = os.path.join(music_folder, f"{video_id}.%(ext)s")
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': output_template, 'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                actual_ext = info.get('ext', 'webm')
            file_path = f"music/{video_id}.{actual_ext}"
            if not DownloadedSong.query.filter_by(user_id=current_user.id, youtube_id=video_id).first():
                new_download = DownloadedSong(user_id=current_user.id, song_title=song_title, youtube_id=video_id, file_path=file_path)
                db.session.add(new_download)
            new_ps = PlaylistSong(playlist_id=pl.id, song_title=song_title, file_path=file_path)
            db.session.add(new_ps)
            db.session.commit()
            flash(f'Added "{song_title}" to playlist offline!', 'success')
        except Exception:
            flash('Failed to download and add to playlist.', 'error')
    return redirect(url_for('index'))

@app.route('/remove_from_playlist/<int:ps_id>')
@login_required
def remove_from_playlist(ps_id):
    ps = db.session.get(PlaylistSong, ps_id)
    if ps and ps.playlist.user_id == current_user.id:
        db.session.delete(ps)
        db.session.commit()
    return redirect(url_for('playlist'))

@app.route('/favorites')
@login_required
def view_favorites():
    all_favs = FavoriteSong.query.filter_by(user_id=current_user.id).order_by(FavoriteSong.id.desc()).all()
    return render_template('favorites.html', favorites=all_favs)

@app.route('/playlist')
@login_required
def playlist():
    songs = DownloadedSong.query.filter_by(user_id=current_user.id)\
        .order_by(DownloadedSong.id.desc()).all()

    favorites_paths = {
    fav.file_path
    for fav in FavoriteSong.query.filter_by(
        user_id=current_user.id
    ).all()
}
    return render_template("playlists.html",songs=songs,favorite_paths=favorites_paths)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

