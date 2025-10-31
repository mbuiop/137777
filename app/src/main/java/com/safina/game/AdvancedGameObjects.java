package com.safina.game;

import android.graphics.Canvas;
import android.graphics.Paint;
import java.util.ArrayList;
import java.util.List;

public class AdvancedGameObjects {
    private List<GameObject> gameObjects;
    private Paint objectPaint;
    
    public AdvancedGameObjects() {
        gameObjects = new ArrayList<>();
        objectPaint = new Paint();
        objectPaint.setColor(0xFF00FF00); // سبز
    }
    
    public void update() {
        // آپدیت تمام آبجکت‌های بازی
        for (GameObject obj : gameObjects) {
            obj.update();
        }
        
        // حذف آبجکت‌های غیرفعال
        gameObjects.removeIf(obj -> !obj.isActive());
    }
    
    public void render(Canvas canvas) {
        // رندر تمام آبجکت‌های بازی
        for (GameObject obj : gameObjects) {
            obj.render(canvas, objectPaint);
        }
    }
    
    public void addObject(GameObject obj) {
        gameObjects.add(obj);
    }
    
    public void clearAll() {
        gameObjects.clear();
    }
    
    // کلاس داخلی برای آبجکت‌های بازی
    public static class GameObject {
        protected float x, y;
        protected boolean active = true;
        
        public void update() {
            // منطق آپدیت آبجکت
        }
        
        public void render(Canvas canvas, Paint paint) {
            // رندر آبجکت - می‌تواند override شود
            canvas.drawCircle(x, y, 20, paint);
        }
        
        public boolean isActive() { return active; }
        public void setActive(boolean active) { this.active = active; }
    }
}
