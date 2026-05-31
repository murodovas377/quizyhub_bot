// App.jsx - Главный компонент React Web App для Telegram Mini App

import React, { useEffect, useState } from 'react';
import './App.css';
import Dashboard from './pages/Dashboard';
import CreateTest from './pages/CreateTest';
import EditTest from './pages/EditTest';
import TestResults from './pages/TestResults';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

function App() {
  const [user, setUser] = useState(null);
  const [language, setLanguage] = useState('ru');
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [selectedTest, setSelectedTest] = useState(null);
  const [loading, setLoading] = useState(true);

  // Инициализация Telegram WebApp
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      
      // Получить язык
      const lang = tg.initDataUnsafe?.user?.language_code || 'ru';
      if (lang.startsWith('en')) {
        setLanguage('en');
      } else if (lang.startsWith('uz')) {
        setLanguage('uz');
      } else {
        setLanguage('ru');
      }

      // Получить информацию о пользователе
      fetchUser();
    }
  }, []);

  // Загрузить информацию о пользователе
  const fetchUser = async () => {
    try {
      const initData = window.Telegram?.WebApp?.initData;
      const response = await fetch(`${API_URL}/user`, {
        headers: {
          'x-telegram-init-data': initData
        }
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setLanguage(userData.language || language);
      }
    } catch (error) {
      console.error('Error fetching user:', error);
    } finally {
      setLoading(false);
    }
  };

  const translations = {
    ru: {
      dashboard: 'Мои тесты',
      createNew: 'Создать новый',
      readyTests: 'Готовые тесты',
      editTest: 'Редактировать',
      deleteTest: 'Удалить',
      viewResults: 'Результаты',
      startTest: 'Начать тест',
      backButton: 'Назад',
      loading: 'Загрузка...',
      noTests: 'У вас ещё нет тестов',
      testName: 'Название теста',
      testTime: 'Время на вопрос (сек)',
      questions: 'Вопросы',
      save: 'Сохранить',
      cancel: 'Отмена',
      premiumRequired: 'Нужен Premium',
      logOut: 'Выход'
    },
    en: {
      dashboard: 'My Tests',
      createNew: 'Create New',
      readyTests: 'Ready Tests',
      editTest: 'Edit',
      deleteTest: 'Delete',
      viewResults: 'Results',
      startTest: 'Start Test',
      backButton: 'Back',
      loading: 'Loading...',
      noTests: 'You have no tests yet',
      testName: 'Test Name',
      testTime: 'Time per question (sec)',
      questions: 'Questions',
      save: 'Save',
      cancel: 'Cancel',
      premiumRequired: 'Premium Required',
      logOut: 'Log Out'
    },
    uz: {
      dashboard: 'Mening testlar',
      createNew: 'Yangi yaratish',
      readyTests: 'Tayyor testlar',
      editTest: 'Tahrirlash',
      deleteTest: 'Oʻchirish',
      viewResults: 'Natijalar',
      startTest: 'Testni boshlash',
      backButton: 'Orqaga',
      loading: 'Yuklanmoqda...',
      noTests: 'Hali testlar yoq',
      testName: 'Test nomi',
      testTime: 'Savol uchun vaqt (sek)',
      questions: 'Savollar',
      save: 'Saqlash',
      cancel: 'Bekor qilish',
      premiumRequired: 'Premium kerak',
      logOut: 'Chiqish'
    }
  };

  const t = (key) => translations[language]?.[key] || translations['ru'][key];

  if (loading) {
    return (
      <div className="app">
        <div className="loader">
          <div className="spinner"></div>
          <p>{t('loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      {/* HEADER */}
      <header className="header">
        <div className="header-content">
          <h1>📚 QuizHub</h1>
          <div className="header-actions">
            <button 
              className="lang-btn"
              onClick={() => setLanguage(language === 'ru' ? 'en' : language === 'en' ? 'uz' : 'ru')}
            >
              {language === 'ru' ? '🇷🇺' : language === 'en' ? '🇬🇧' : '🇺🇿'}
            </button>
            <button className="logout-btn" onClick={() => {
              window.Telegram?.WebApp?.close();
            }}>
              {t('logOut')}
            </button>
          </div>
        </div>
      </header>

      {/* ОСНОВНОЙ КОНТЕНТ */}
      <main className="main-content">
        {currentPage === 'dashboard' && (
          <Dashboard 
            user={user}
            language={language}
            translations={translations[language]}
            t={t}
            onCreateNew={() => setCurrentPage('create')}
            onEdit={(test) => {
              setSelectedTest(test);
              setCurrentPage('edit');
            }}
            onViewResults={(test) => {
              setSelectedTest(test);
              setCurrentPage('results');
            }}
          />
        )}

        {currentPage === 'create' && (
          <CreateTest 
            user={user}
            language={language}
            t={t}
            onBack={() => setCurrentPage('dashboard')}
            onSuccess={() => setCurrentPage('dashboard')}
          />
        )}

        {currentPage === 'edit' && (
          <EditTest 
            test={selectedTest}
            user={user}
            language={language}
            t={t}
            onBack={() => setCurrentPage('dashboard')}
            onSuccess={() => setCurrentPage('dashboard')}
          />
        )}

        {currentPage === 'results' && (
          <TestResults 
            test={selectedTest}
            user={user}
            language={language}
            t={t}
            onBack={() => setCurrentPage('dashboard')}
          />
        )}
      </main>

      {/* НАВИГАЦИЯ */}
      <nav className="bottom-nav">
        <button 
          className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentPage('dashboard')}
        >
          <span className="icon">📂</span>
          <span className="label">{t('dashboard')}</span>
        </button>
        <button 
          className={`nav-btn ${currentPage === 'create' ? 'active' : ''}`}
          onClick={() => setCurrentPage('create')}
        >
          <span className="icon">✍️</span>
          <span className="label">{t('createNew')}</span>
        </button>
        <button 
          className="nav-btn"
          onClick={() => {
            if (!user?.is_premium_plus) {
              alert(t('premiumRequired'));
              return;
            }
            // Логика для готовых тестов
          }}
        >
          <span className="icon">⭐</span>
          <span className="label">{t('readyTests')}</span>
        </button>
      </nav>
    </div>
  );
}

export default App;
