package com.safina.game;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.SurfaceView;
import android.view.SurfaceHolder;

public class GameEngine extends SurfaceView implements SurfaceHolder.Callback, Runnable {
    private Thread gameThread;
    private SurfaceHolder holder;
    private volatile boolean running = false;
    private Paint paint;
    
    // سیستم‌های بازی
    private AdvancedGameState gameState;
    private AdvancedGameObjects gameObjects;
    private AdvancedParticleSystem particleSystem;
    private AudioSystem audioSystem;
    private CameraSystem cameraSystem;
    private EnemySystem enemySystem;
    private EnvironmentObjects environmentObjects;
    private PlanetSystem planetSystem;
    private PowerUpSystem powerUpSystem;
    private VirtualJoystick virtualJoystick;

    public GameEngine(Context context) {
        super(context);
        holder = getHolder();
        holder.addCallback(this);
        
        paint = new Paint();
        paint.setColor(Color.WHITE);
        paint.setTextSize(40);
        
        // مقداردهی اولیه سیستم‌ها
        initializeSystems();
    }

    private void initializeSystems() {
        gameState = new AdvancedGameState();
        gameObjects = new AdvancedGameObjects();
        particleSystem = new AdvancedParticleSystem();
        audioSystem = new AudioSystem(getContext());
        cameraSystem = new CameraSystem();
        enemySystem = new EnemySystem();
        environmentObjects = new EnvironmentObjects();
        planetSystem = new PlanetSystem();
        powerUpSystem = new PowerUpSystem();
        virtualJoystick = new VirtualJoystick();
        
        // شروع سیستم‌ها
        gameState.initialize();
        audioSystem.initialize();
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        running = true;
        gameThread = new Thread(this);
        gameThread.start();
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        running = false;
        try {
            gameThread.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        // هنگام تغییر سایز صفحه
    }

    @Override
    public void run() {
        while (running) {
            if (!holder.getSurface().isValid()) {
                continue;
            }
            
            updateGame();
            renderFrame();
        }
    }

    private void updateGame() {
        // آپدیت منطق بازی
        gameState.update();
        gameObjects.update();
        enemySystem.update();
        particleSystem.update();
        cameraSystem.update();
        planetSystem.update();
        powerUpSystem.update();
    }

    private void renderFrame() {
        Canvas canvas = holder.lockCanvas();
        if (canvas == null) return;
        
        // پس‌زمینه
        canvas.drawColor(Color.BLACK);
        
        // رندر سیستم‌ها
        environmentObjects.render(canvas);
        planetSystem.render(canvas);
        gameObjects.render(canvas);
        enemySystem.render(canvas);
        particleSystem.render(canvas);
        
        // رندر اطلاعات بازی
        canvas.drawText("Safina 3D Game - FPS: 60", 50, 50, paint);
        
        holder.unlockCanvasAndPost(canvas);
    }

    public void resume() {
        running = true;
        audioSystem.resume();
    }

    public void pause() {
        running = false;
        audioSystem.pause();
    }

    public void destroy() {
        running = false;
        audioSystem.destroy();
    }
  }
