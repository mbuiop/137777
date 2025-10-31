package com.safina.game;

public class CameraSystem {
    private float cameraX = 0;
    private float cameraY = 0;
    private float targetX = 0;
    private float targetY = 0;
    private float zoom = 1.0f;
    
    public void update() {
        // حرکت نرم دوربین به سمت هدف
        cameraX += (targetX - cameraX) * 0.1f;
        cameraY += (targetY - cameraY) * 0.1f;
    }
    
    public void setTarget(float x, float y) {
        this.targetX = x;
        this.targetY = y;
    }
    
    public void setZoom(float zoomLevel) {
        this.zoom = Math.max(0.5f, Math.min(2.0f, zoomLevel));
    }
    
    public float getCameraX() { return cameraX; }
    public float getCameraY() { return cameraY; }
    public float getZoom() { return zoom; }
    
    public void shake(float intensity) {
        // اثر لرزش دوربین
        cameraX += (Math.random() - 0.5) * intensity;
        cameraY += (Math.random() - 0.5) * intensity;
    }
}
