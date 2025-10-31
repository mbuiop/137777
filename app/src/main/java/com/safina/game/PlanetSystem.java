package com.safina.game;

import android.graphics.Canvas;
import android.graphics.Paint;
import java.util.ArrayList;
import java.util.List;

public class PlanetSystem {
    private List<Planet> planets;
    private Paint planetPaint;
    
    public PlanetSystem() {
        planets = new ArrayList<>();
        planetPaint = new Paint();
        
        // ایجاد سیارات نمونه
        createSamplePlanets();
    }
    
    private void createSamplePlanets() {
        planets.add(new Planet(200, 200, 50, 0xFFFF8800, "Sun"));    // خورشید
        planets.add(new Planet(400, 200, 20, 0xFF8888FF, "Planet A")); // سیاره آبی
        planets.add(new Planet(600, 400, 30, 0xFF00FF00, "Planet B")); // سیاره سبز
    }
    
    public void update() {
        // آپدیت موقعیت سیارات (حرکت مداری)
        for (Planet planet : planets) {
            planet.update();
        }
    }
    
    public void render(Canvas canvas) {
        for (Planet planet : planets) {
            planet.render(canvas, planetPaint);
        }
    }
    
    private static class Planet {
        private float x, y;
        private float radius;
        private int color;
        private String name;
        private float angle = 0;
        
        public Planet(float x, float y, float radius, int color, String name) {
            this.x = x;
            this.y = y;
            this.radius = radius;
            this.color = color;
            this.name = name;
        }
        
        public void update() {
            // حرکت مداری ساده
            angle += 0.01f;
            if (name.equals("Planet A")) {
                x = 400 + (float) Math.cos(angle) * 150;
                y = 200 + (float) Math.sin(angle) * 150;
            } else if (name.equals("Planet B")) {
                x = 600 + (float) Math.cos(angle * 0.7) * 200;
                y = 400 + (float) Math.sin(angle * 0.7) * 200;
            }
        }
        
        public void render(Canvas canvas, Paint paint) {
            paint.setColor(color);
            canvas.drawCircle(x, y, radius, paint);
        }
    }
}
