package com.safina.game;

public class AdvancedGameState {
    private int score = 0;
    private int level = 1;
    private int lives = 3;
    private boolean gameRunning = true;
    
    public void initialize() {
        score = 0;
        level = 1;
        lives = 3;
        gameRunning = true;
    }
    
    public void update() {
        // آپدیت وضعیت بازی
        if (gameRunning) {
            score += 10; // افزایش امتیاز
        }
    }
    
    public void increaseScore(int points) {
        score += points;
    }
    
    public void decreaseLives() {
        lives--;
        if (lives <= 0) {
            gameRunning = false;
        }
    }
    
    public void levelUp() {
        level++;
        // افزایش سختی بازی
    }
    
    // Getter methods
    public int getScore() { return score; }
    public int getLevel() { return level; }
    public int getLives() { return lives; }
    public boolean isGameRunning() { return gameRunning; }
}
