package com.safina.game;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.view.MotionEvent;

public class VirtualJoystick {
    private float centerX, centerY;
    private float handleX, handleY;
    private float radius;
    private boolean isPressed = false;
    private Paint basePaint, handlePaint;
    
    // جهت‌های جوئستیک
    private float joystickX = 0;
    private float joystickY = 0;
    
    public VirtualJoystick() {
        // موقعیت پیش‌فرض جوئستیک
        centerX = 200;
        centerY = 1200;
        handleX = centerX;
        handleY = centerY;
        radius = 80;
        
        // رنگ‌ها
        basePaint = new Paint();
        basePaint.setColor(0x80FFFFFF); // نیمه شفاف سفید
        basePaint.setAlpha(128);
        
        handlePaint = new Paint();
        handlePaint.setColor(0xFFCCCCCC);
    }
    
    public boolean onTouchEvent(MotionEvent event) {
        float touchX = event.getX();
        float touchY = event.getY();
        
        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                // بررسی اگر لمس در محدوده جوئستیک باشد
                if (isInJoystickArea(touchX, touchY)) {
                    isPressed = true;
                    updateHandlePosition(touchX, touchY);
                    return true;
                }
                break;
                
            case MotionEvent.ACTION_MOVE:
                if (isPressed) {
                    updateHandlePosition(touchX, touchY);
                    return true;
                }
                break;
                
            case MotionEvent.ACTION_UP:
                isPressed = false;
                resetHandle();
                return true;
        }
        
        return false;
    }
    
    private boolean isInJoystickArea(float x, float y) {
        float distance = (float) Math.sqrt(
            Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2)
        );
        return distance <= radius;
    }
    
    private void updateHandlePosition(float touchX, float touchY) {
        // محاسبه فاصله از مرکز
        float dx = touchX - centerX;
        float dy = touchY - centerY;
        float distance = (float) Math.sqrt(dx * dx + dy * dy);
        
        // محدود کردن به شعاع جوئستیک
        if (distance > radius) {
            dx = dx * radius / distance;
            dy = dy * radius / distance;
            distance = radius;
        }
        
        handleX = centerX + dx;
        handleY = centerY + dy;
        
        // نرمالایز کردن جهت (-1 تا 1)
        joystickX = dx / radius;
        joystickY = dy / radius;
    }
    
    private void resetHandle() {
        handleX = centerX;
        handleY = centerY;
        joystickX = 0;
        joystickY = 0;
    }
    
    public void render(Canvas canvas) {
        // رندر پایه جوئستیک
        canvas.drawCircle(centerX, centerY, radius, basePaint);
        
        // رندر هندل
        canvas.drawCircle(handleX, handleY, radius / 2, handlePaint);
    }
    
    // گرفتن جهت جوئستیک
    public float getJoystickX() { return joystickX; }
    public float getJoystickY() { return joystickY; }
    public boolean isPressed() { return isPressed; }
}
