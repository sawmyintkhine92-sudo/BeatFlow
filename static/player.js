window.addEventListener("DOMContentLoaded", function () {

    const userId = window.USER_ID || "guest";

    let player = document.getElementById("player");

    if (!player) {
        console.log("Audio element missing");
        return;
    }

    let items = document.querySelectorAll(".song-item");
    let playlist = [];

    // LocalStorage ထဲက Playlist ကို စစ်ဆေးခြင်း
    const savedPlaylist = localStorage.getItem("globalPlaylist_" + userId);
    if (savedPlaylist) {
        playlist = JSON.parse(savedPlaylist);
    } else if (items.length > 0) {
        playlist = Array.from(items).map(i => ({
            src: i.dataset.src,
            title: i.dataset.title,
            thumb: i.dataset.thumb
        }));
    }

    let currentIndex = 0;
    let isRepeat = false;
    let isShuffle = false;

    // သီချင်း item များကို နှိပ်လျှင် ဖွင့်ရန်
    items.forEach((item, index) => {
        item.addEventListener("click", function () {
            if (items.length === playlist.length) {
                playSong(index);
            } else {
                const targetSrc = item.dataset.src;
                const foundIndex = playlist.findIndex(s => s.src === targetSrc);
                if (foundIndex !== -1) {
                    playSong(foundIndex);
                } else {
                    playlist = Array.from(items).map(i => ({
                        src: i.dataset.src,
                        title: i.dataset.title,
                        thumb: i.dataset.thumb
                    }));
                    localStorage.setItem("globalPlaylist_" + userId, JSON.stringify(playlist));
                    playSong(index);
                }
            }
        });
    });

    // ▶️ PLAY SONG
    function playSong(i) {
        if (!playlist.length) return;

        currentIndex = i;

        if (currentIndex >= playlist.length) currentIndex = 0;
        if (currentIndex < 0) currentIndex = playlist.length - 1;

        player.src = playlist[currentIndex].src;
        player.load();
        player.play().catch(err => console.log("Playback error:", err));

        localStorage.setItem("nowTitle_" + userId, playlist[currentIndex].title);
        localStorage.setItem("nowThumb_" + userId, playlist[currentIndex].thumb);
        localStorage.setItem("nowSrc_" + userId, playlist[currentIndex].src);

        let nowText = document.getElementById("nowText");
        let nowThumb = document.getElementById("nowThumb");

        if (nowText) nowText.innerText = playlist[currentIndex].title;

        if (nowThumb) {
            if (playlist[currentIndex].thumb) {
                nowThumb.src = playlist[currentIndex].thumb;
                nowThumb.style.display = "block";
            } else {
                nowThumb.style.display = "none";
            }
        }
    }

    // ▶️ TOGGLE PLAY
    function togglePlay() {
        if (!playlist.length) return;

        if (!player.src || player.src === window.location.href) {
            playSong(currentIndex);
            return;
        }

        if (player.paused) {
            player.play().catch(err => console.log(err));
        } else {
            player.pause();
        }
    }

    // ⏭️ NEXT
    function nextSong() {
        if (!playlist.length) return;

        if (isShuffle) {
            currentIndex = Math.floor(Math.random() * playlist.length);
        } else {
            currentIndex = (currentIndex + 1) % playlist.length;
        }

        playSong(currentIndex);
    }

    // ⏮️ PREV
    function prevSong() {
        if (!playlist.length) return;

        currentIndex--;
        if (currentIndex < 0) currentIndex = playlist.length - 1;

        playSong(currentIndex);
    }

    // 🔁 REPEAT
    function toggleRepeat() {
        isRepeat = !isRepeat;
        isShuffle = false;
        
        let repeatBtn = document.getElementById("repeatBtn");
        if (repeatBtn) {
            repeatBtn.classList.toggle("active-btn", isRepeat);
        }
        let shuffleBtn = document.getElementById("shuffleBtn");
        if (shuffleBtn) shuffleBtn.classList.remove("active-btn");
    }

    // 🔀 SHUFFLE
    function toggleShuffle() {
        isShuffle = !isShuffle;
        isRepeat = false;

        let shuffleBtn = document.getElementById("shuffleBtn");
        if (shuffleBtn) {
            shuffleBtn.classList.toggle("active-btn", isShuffle);
        }
        let repeatBtn = document.getElementById("repeatBtn");
        if (repeatBtn) repeatBtn.classList.remove("active-btn");
    }

    // 🔥 AUTO NEXT
    player.addEventListener("ended", function () {
        if (isRepeat) {
            player.currentTime = 0;
            player.play().catch(err => console.log(err));
        } else {
            nextSong();
        }
    });

    // 🔊 VOLUME
    let volume = document.getElementById("volume");
    if (volume) {
        volume.value = player.volume;
        volume.addEventListener("input", function () {
            player.volume = this.value;
        });
    }

    // 📊 SEEK
    let seek = document.getElementById("seek");

    if (seek) {
        player.addEventListener("timeupdate", function () {
            if (!player.duration) return;

            seek.value = (player.currentTime / player.duration) * 100;

            const cm = Math.floor(player.currentTime / 60);
            const cs = Math.floor(player.currentTime % 60);

            const dm = Math.floor(player.duration / 60);
            const ds = Math.floor(player.duration % 60);

            const ct = document.getElementById("currentTime");
            const dt = document.getElementById("duration");

            // (Syntax Error ပြင်ဆင်ပြီးသား နေရာဖြစ်ပါတယ်)
            if (ct) ct.textContent = cm + ":" + String(cs).padStart(2, "0");
            if (dt) dt.textContent = dm + ":" + String(ds).padStart(2, "0");
        });

        seek.addEventListener("input", function () {
            if (player.duration)
                player.currentTime = (this.value / 100) * player.duration;
        });
    }

    // 💾 RESTORE LAST SONG
    const savedSrc = localStorage.getItem("nowSrc_" + userId);
    const savedTitle = localStorage.getItem("nowTitle_" + userId);
    const savedThumb = localStorage.getItem("nowThumb_" + userId);

    if (savedSrc && playlist.length) {
        const index = playlist.findIndex(s => s.src === savedSrc);

        if (index !== -1) {
            currentIndex = index;
            player.src = savedSrc;

            let nowText = document.getElementById("nowText");
            let nowThumb = document.getElementById("nowThumb");

            if (nowText) nowText.innerText = savedTitle;
            if (nowThumb && savedThumb) {
                nowThumb.src = savedThumb;
                nowThumb.style.display = "block";
            }
        }
    }

    // 🌍 GLOBAL EXPORT
    window.playSong = playSong;
    window.togglePlay = togglePlay;
    window.nextSong = nextSong;
    window.prevSong = prevSong;
    window.toggleRepeat = toggleRepeat;
    window.toggleShuffle = toggleShuffle;

});