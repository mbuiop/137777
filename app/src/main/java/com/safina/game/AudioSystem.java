package com.safina.game;

import android.content.Context;
import android.media.MediaPlayer;
import java.util.HashMap;

public class AudioSystem {
    private Context context;
    private MediaPlayer backgroundMusic;
    private HashMap<String, Integer> soundMap;
    private boolean audioEnabled = true;
    
    public AudioSystem(Context context) {
        this.context = context;
        soundMap = new HashMap<>();
        initializeSoundMap();
    }
    
    private void initializeSoundMap() {
        // mapping صداها - می‌توانید فایل‌های صوتی خود را اضافه کنید
        soundMap.put("explosion", 0);
        soundMap.put("laser", 0);
        soundMap.put("powerup", 0);
    }
    
    public void initialize() {
        // مقداردهی اولیه سیستم صدا
        if (audioEnabled) {
            startBackgroundMusic();
        }
    }
    
    private void startBackgroundMusic() {
        // شروع موسیقی پس‌زمینه
        // در اینجا می‌توانید فایل موسیقی خود را load کنید
    }
    
    public void playSound(String soundName) {
        if (!audioEnabled) return;
        
        // پخش صدای مورد نظر
        // نیاز به فایل‌های صوتی در پوشه res/raw دارد
    }
    
    public void resume() {
        if (audioEnabled && backgroundMusic != null) {
            backgroundMusic.start();
        }
    }
    
    public void pause() {
        if (backgroundMusic != null && backgroundMusic.isPlaying()) {
            backgroundMusic.pause();
        }
    }
    
    public void destroy() {
        if (backgroundMusic != null) {
            backgroundMusic.release();
            backgroundMusic = null;
        }
    }
    
    public void setAudioEnabled(boolean enabled) {
        this.audioEnabled = enabled;
        if (!enabled) {
            pause();
        } else {
            resume();
        }
    }
}
