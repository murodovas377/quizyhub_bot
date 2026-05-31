// server.js - Express сервер для Telegram Mini App
// Установи: npm install express cors dotenv axios pg

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { Pool } from 'pg';
import axios from 'axios';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

// PostgreSQL подключение (Railway)
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

const BOT_TOKEN = process.env.BOT_TOKEN;
const TELEGRAM_API = 'https://api.telegram.org';

// ═══════════════════════════════════════════════════════════════════════
// MIDDLEWARE - Проверка Telegram Init Data
// ═══════════════════════════════════════════════════════════════════════

async function verifyTelegramWebApp(req, res, next) {
  try {
    const initData = req.headers['x-telegram-init-data'];
    
    if (!initData) {
      return res.status(401).json({ error: 'No init data' });
    }

    // Простая проверка (в продакшене делай полную валидацию)
    const params = new URLSearchParams(initData);
    const user = JSON.parse(params.get('user'));
    
    req.userId = user.id;
    req.user = user;
    next();
  } catch (e) {
    res.status(401).json({ error: 'Invalid init data' });
  }
}

// ═══════════════════════════════════════════════════════════════════════
// API: Получить информацию о пользователе
// ═══════════════════════════════════════════════════════════════════════

app.get('/api/user', verifyTelegramWebApp, async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM users WHERE user_id = $1',
      [req.userId]
    );
    
    const user = result.rows[0] || {};
    
    // Получи информацию о премиуме
    const premiumResult = await pool.query(
      'SELECT expire_time FROM premium WHERE user_id = $1',
      [req.userId]
    );
    
    const premiumPlusResult = await pool.query(
      'SELECT expire_time FROM premium_plus WHERE user_id = $1',
      [req.userId]
    );

    res.json({
      user_id: req.userId,
      name: user.name || req.user.first_name,
      username: user.username || req.user.username,
      language: user.language || 'ru',
      is_premium: premiumResult.rows.length > 0,
      is_premium_plus: premiumPlusResult.rows.length > 0,
      premium_expires: premiumResult.rows[0]?.expire_time || null,
      premium_plus_expires: premiumPlusResult.rows[0]?.expire_time || null
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Загрузить все тесты пользователя
// ═══════════════════════════════════════════════════════════════════════

app.get('/api/tests', verifyTelegramWebApp, async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM user_tests WHERE user_id = $1 ORDER BY created_at DESC',
      [req.userId]
    );
    
    res.json(result.rows);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Получить тест по ID
// ═══════════════════════════════════════════════════════════════════════

app.get('/api/tests/:testId', verifyTelegramWebApp, async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM tests WHERE test_id = $1',
      [req.params.testId]
    );
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Test not found' });
    }

    res.json(result.rows[0]);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Создать новый тест
// ═══════════════════════════════════════════════════════════════════════

app.post('/api/tests', verifyTelegramWebApp, async (req, res) => {
  try {
    const { name, questions, split, time, answer_mode } = req.body;

    // Проверка лимитов
    const countResult = await pool.query(
      'SELECT COUNT(*) FROM user_tests WHERE user_id = $1',
      [req.userId]
    );

    const testCount = parseInt(countResult.rows[0].count);
    
    // Проверка: есть ли премиум
    const premiumResult = await pool.query(
      'SELECT expire_time FROM premium WHERE user_id = $1 AND expire_time > NOW()',
      [req.userId]
    );

    if (testCount >= 2 && premiumResult.rows.length === 0) {
      return res.status(403).json({ 
        error: 'Limit reached',
        message: 'Нужен Premium для создания больше 2 тестов'
      });
    }

    const testId = `test_${Date.now()}_${req.userId}`;
    
    const result = await pool.query(
      `INSERT INTO tests (test_id, name, questions, split, time, answer_mode) 
       VALUES ($1, $2, $3, $4, $5, $6) 
       RETURNING *`,
      [testId, name, JSON.stringify(questions), split, time, answer_mode]
    );

    // Добавить тест пользователю
    await pool.query(
      `INSERT INTO user_tests (user_id, test_id) VALUES ($1, $2)`,
      [req.userId, testId]
    );

    res.json({ test_id: testId, ...result.rows[0] });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Обновить тест
// ═══════════════════════════════════════════════════════════════════════

app.put('/api/tests/:testId', verifyTelegramWebApp, async (req, res) => {
  try {
    const { name, time, order } = req.body;
    const { testId } = req.params;

    const result = await pool.query(
      `UPDATE tests 
       SET name = COALESCE($1, name), 
           time = COALESCE($2, time),
           order_type = COALESCE($3, order_type),
           updated_at = NOW()
       WHERE test_id = $4
       RETURNING *`,
      [name, time, order, testId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Test not found' });
    }

    res.json(result.rows[0]);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Удалить тест
// ═══════════════════════════════════════════════════════════════════════

app.delete('/api/tests/:testId', verifyTelegramWebApp, async (req, res) => {
  try {
    const { testId } = req.params;

    // Удалить из user_tests
    await pool.query(
      'DELETE FROM user_tests WHERE test_id = $1',
      [testId]
    );

    // Удалить сам тест
    await pool.query(
      'DELETE FROM tests WHERE test_id = $1',
      [testId]
    );

    res.json({ success: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Получить результаты теста
// ═══════════════════════════════════════════════════════════════════════

app.get('/api/tests/:testId/results', verifyTelegramWebApp, async (req, res) => {
  try {
    const { testId } = req.params;
    
    const result = await pool.query(
      `SELECT * FROM test_results 
       WHERE test_id = $1 
       ORDER BY score DESC, time_spent ASC 
       LIMIT 10`,
      [testId]
    );

    res.json(result.rows);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Сохранить результат теста
// ═══════════════════════════════════════════════════════════════════════

app.post('/api/tests/:testId/results', verifyTelegramWebApp, async (req, res) => {
  try {
    const { testId } = req.params;
    const { group_key, score, total, time_spent } = req.body;

    const result = await pool.query(
      `INSERT INTO test_results (test_id, user_id, group_key, score, total, time_spent)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [testId, req.userId, group_key, score, total, time_spent]
    );

    res.json(result.rows[0]);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API: Загрузить готовые тесты (только для Premium+)
// ═══════════════════════════════════════════════════════════════════════

app.get('/api/ready-tests', verifyTelegramWebApp, async (req, res) => {
  try {
    // Проверка премиум+
    const premiumPlusResult = await pool.query(
      'SELECT expire_time FROM premium_plus WHERE user_id = $1 AND expire_time > NOW()',
      [req.userId]
    );

    if (premiumPlusResult.rows.length === 0) {
      return res.status(403).json({ error: 'Premium+ required' });
    }

    const result = await pool.query(
      'SELECT * FROM ready_tests ORDER BY created_at DESC'
    );

    res.json(result.rows);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════
// ЗАПУСК СЕРВЕРА
// ═══════════════════════════════════════════════════════════════════════

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Web App Server запущен на порту ${PORT}`);
});

export default app;
