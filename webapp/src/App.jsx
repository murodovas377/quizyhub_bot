import React, { useEffect, useState } from 'react';
import './App.css';
import Dashboard from './pages/Dashboard';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    initTelegramWebApp();
  }, []);

  const initTelegramWebApp = async () => {
    try {
      const tg = window.Telegram?.WebApp;
      
      if (!tg) {
        setError('Telegram WebApp not available');
        setLoading(false);
        return;
      }

      // Инициализируем WebApp
      tg.ready();
      tg.expand();

      // Получаем initData
      const initData = tg.initData;
      
      if (!initData) {
        setError('No init data from Telegram');
        setLoading(false);
        return;
      }

      // Отправляем на сервер для верификации
      const response = await fetch(`${API_URL}/user`, {
        method: 'GET',
        headers: {
          'x-telegram-init-data': initData,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setError(null);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to fetch user');
      }
    } catch (err) {
      console.error('Error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="app">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div className="spinner"></div>
          <p>Загрузка...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app">
        <div style={{ textAlign: 'center', padding: '40px', color: 'red' }}>
          <h2>❌ Ошибка</h2>
          <p>{error}</p>
          <p style={{ fontSize: '12px', marginTop: '20px', color: '#999' }}>
            Убедись что открываешь из Telegram бота!
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="app">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Нет данных пользователя</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Dashboard user={user} language={user.language || 'ru'} />
    </div>
  );
}

export default App;