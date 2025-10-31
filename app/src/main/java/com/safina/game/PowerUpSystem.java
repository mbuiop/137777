package com.safina.game;

import android.graphics.Canvas;
import android.graphics.Paint;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class PowerUpSystem {
    private List<PowerUp> powerUps;
    private Random random;
    private Paint powerUpPaint;
    private int spawnCounter = 0;
    
    public PowerUpSystem() {
        powerUps = new ArrayList<>();
        random = new Random();
        powerUpPaint = new Paint();
    }
    
    public void update() {
        // آپدیت تمام قدرت‌ها
        for (PowerUp powerUp : powerUps) {
            powerUp.update();
        }
        
        // حذف قدرت‌های جمع‌شده
        powerUps.removeIf(powerUp -> !powerUp.isActive());
        
        // تولید قدرت‌های جدید
        spawnCounter++;
        if (spawnCounter >= 300) { // هر 5 ثانیه
            spawnPowerUp();
            spawnCounter = 0;
        }
    }
    
    public void render(Canvas canvas) {
        for (PowerUp powerUp : powerUps) {
            powerUp.render(canvas, powerUpPaint);
        }
    }
    
    private void spawnPowerUp() {
        float x = random.nextInt(1000);
        float y = random.nextInt(1000);
        int type = random.nextInt(3);
        powerUps.add(new PowerUp(x, y, type));
    }
    
    private static class PowerUp {
        private float x, y;
        private boolean active = true;
        private int type; // 0: سرعت, 1: قدرت, 2: سلامتی
        private float blinkTimer = 0;
        
        public PowerUp(float x, float y, int type) {
            this.x = x;
            this.y = y;
            this.type = type;
        }
        
        public void update() {
            // انیمیشن چشمک زن
            blinkTimer += 0.1f;
        }
        
        public void render(Canvas canvas, Paint paint) {
            // رنگ‌های مختلف برای انواع مختلف قدرت
            switch (type) {
                case 0: paint.setColor(0xFFFFFF00); break; // زرد - سرعت
                case 1: paint.setColor(0xFFFF00FF); break; // بنفش - قدرت
                case 2: paint.setColor(0xFF00FFFF); break; // فیروزه‌ای - سلامتی
            }
            
            // اثر چشمک زن
            if ((int)(blinkTimer * 10) % 2 == 0) {
                canvas.drawCircle(x, y, 15, paint);
            }
        }
        
        public void collect() {
            active = false;
        }
        
        public boolean isActive() { return active; }
        public int getType() { return type; }
        public float getX() { return x; }
        public float getY() { return y; }
    }
}
