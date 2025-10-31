package com.safina.game;

import android.graphics.Canvas;
import android.graphics.Paint;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class EnvironmentObjects {
    private List<EnvironmentObject> objects;
    private Random random;
    private Paint envPaint;
    
    public EnvironmentObjects() {
        objects = new ArrayList<>();
        random = new Random();
        envPaint = new Paint();
        envPaint.setColor(0xFF888888); // خاکستری برای محیط
        
        generateEnvironment();
    }
    
    private void generateEnvironment() {
        // تولید آبجکت‌های محیطی تصادفی
        for (int i = 0; i < 50; i++) {
            float x = random.nextInt(2000) - 500;
            float y = random.nextInt(2000) - 500;
            int type = random.nextInt(3);
            objects.add(new EnvironmentObject(x, y, type));
        }
    }
    
    public void render(Canvas canvas) {
        for (EnvironmentObject obj : objects) {
            obj.render(canvas, envPaint);
        }
    }
    
    private static class EnvironmentObject {
        private float x, y;
        private int type; // 0: سنگ, 1: درخت, 2: ساختمان
        
        public EnvironmentObject(float x, float y, int type) {
            this.x = x;
            this.y = y;
            this.type = type;
        }
        
        public void render(Canvas canvas, Paint paint) {
            switch (type) {
                case 0: // سنگ
                    paint.setColor(0xFF666666);
                    canvas.drawCircle(x, y, 15, paint);
                    break;
                case 1: // درخت
                    paint.setColor(0xFF00AA00);
                    canvas.drawCircle(x, y, 20, paint);
                    break;
                case 2: // ساختمان
                    paint.setColor(0xFFAA0000);
                    canvas.drawRect(x - 25, y - 25, x + 25, y + 25, paint);
                    break;
            }
        }
    }
}
