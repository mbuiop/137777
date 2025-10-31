package com.safina.game;

import android.graphics.Canvas;
import android.graphics.Paint;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class AdvancedParticleSystem {
    private List<Particle> particles;
    private Random random;
    private Paint particlePaint;
    
    public AdvancedParticleSystem() {
        particles = new ArrayList<>();
        random = new Random();
        particlePaint = new Paint();
        particlePaint.setColor(0xFFFFFF00); // زرد
    }
    
    public void update() {
        // آپدیت تمام ذرات
        for (Particle particle : particles) {
            particle.update();
        }
        
        // حذف ذرات تمام شده
        particles.removeIf(particle -> !particle.isAlive());
        
        // ایجاد ذرات جدید تصادفی
        if (random.nextInt(100) < 20) { // 20% chance
            createParticle(random.nextInt(1000), random.nextInt(1000));
        }
    }
    
    public void render(Canvas canvas) {
        for (Particle particle : particles) {
            particle.render(canvas, particlePaint);
        }
    }
    
    public void createParticle(float x, float y) {
        particles.add(new Particle(x, y));
    }
    
    public void createExplosion(float x, float y, int count) {
        for (int i = 0; i < count; i++) {
            createParticle(x, y);
        }
    }
    
    private static class Particle {
        private float x, y;
        private float velocityX, velocityY;
        private int life;
        private boolean alive = true;
        
        public Particle(float startX, float startY) {
            this.x = startX;
            this.y = startY;
            this.velocityX = (float) (Math.random() * 10 - 5);
            this.velocityY = (float) (Math.random() * 10 - 5);
            this.life = 60; // 60 فریم
        }
        
        public void update() {
            x += velocityX;
            y += velocityY;
            life--;
            
            if (life <= 0) {
                alive = false;
            }
        }
        
        public void render(Canvas canvas, Paint paint) {
            canvas.drawCircle(x, y, 5, paint);
        }
        
        public boolean isAlive() { return alive; }
    }
}
