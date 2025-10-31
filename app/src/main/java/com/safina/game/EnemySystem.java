package com.safina.game;

import android.graphics.Canvas;
import android.graphics.Paint;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class EnemySystem {
    private List<Enemy> enemies;
    private Random random;
    private Paint enemyPaint;
    private int spawnTimer = 0;
    
    public EnemySystem() {
        enemies = new ArrayList<>();
        random = new Random();
        enemyPaint = new Paint();
        enemyPaint.setColor(0xFFFF0000); // قرمز برای دشمنان
    }
    
    public void update() {
        // آپدیت تمام دشمنان
        for (Enemy enemy : enemies) {
            enemy.update();
        }
        
        // حذف دشمنان شکست خورده
        enemies.removeIf(enemy -> !enemy.isActive());
        
        // تولید دشمنان جدید
        spawnTimer++;
        if (spawnTimer >= 120) { // هر 2 ثانیه
            spawnEnemy();
            spawnTimer = 0;
        }
    }
    
    public void render(Canvas canvas) {
        for (Enemy enemy : enemies) {
            enemy.render(canvas, enemyPaint);
        }
    }
    
    private void spawnEnemy() {
        float x = random.nextInt(1000);
        float y = random.nextInt(1000);
        enemies.add(new Enemy(x, y));
    }
    
    public void clearAllEnemies() {
        enemies.clear();
    }
    
    private static class Enemy {
        private float x, y;
        private boolean active = true;
        private int health = 100;
        
        public Enemy(float startX, float startY) {
            this.x = startX;
            this.y = startY;
        }
        
        public void update() {
            // حرکت دشمن - منطق AI ساده
            x += Math.random() * 4 - 2;
            y += Math.random() * 4 - 2;
        }
        
        public void render(Canvas canvas, Paint paint) {
            canvas.drawCircle(x, y, 25, paint); // دشمن بزرگتر
        }
        
        public void takeDamage(int damage) {
            health -= damage;
            if (health <= 0) {
                active = false;
            }
        }
        
        public boolean isActive() { return active; }
        public float getX() { return x; }
        public float getY() { return y; }
    }
}
