// pages/Dashboard.jsx - Главная панель с списком тестов

import React, { useEffect, useState } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

function Dashboard({ user, language, t, onCreateNew, onEdit, onViewResults }) {
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async () => {
    try {
      setLoading(true);
      const initData = window.Telegram?.WebApp?.initData;
      const response = await fetch(`${API_URL}/tests`, {
        headers: {
          'x-telegram-init-data': initData
        }
      });

      if (response.ok) {
        const data = await response.json();
        setTests(data);
      } else {
        setError('Не удалось загрузить тесты');
      }
    } catch (err) {
      console.error('Error fetching tests:', err);
      setError('Ошибка подключения');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (testId) => {
    if (!confirm(t('deleteTest') + '?')) return;

    try {
      const initData = window.Telegram?.WebApp?.initData;
      const response = await fetch(`${API_URL}/tests/${testId}`, {
        method: 'DELETE',
        headers: {
          'x-telegram-init-data': initData
        }
      });

      if (response.ok) {
        setTests(tests.filter(t => t.test_id !== testId));
        // Показать уведомление
        if (window.Telegram?.WebApp?.showPopup) {
          window.Telegram.WebApp.showPopup({
            title: 'Успешно',
            message: 'Тест удален'
          });
        }
      }
    } catch (err) {
      console.error('Error deleting test:', err);
    }
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <div className="spinner"></div>
          <p>{t('loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {error && (
        <div className="alert alert-error">
          ⚠️ {error}
        </div>
      )}

      {tests.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <h3>{t('noTests')}</h3>
          <p>Создай свой первый тест, чтобы начать!</p>
          <button className="btn btn-primary" onClick={onCreateNew}>
            ✍️ {t('createNew')}
          </button>
        </div>
      ) : (
        <>
          <div style={{ marginBottom: '16px' }}>
            <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>
              📂 {t('dashboard')} ({tests.length})
            </h2>
          </div>

          {tests.map((test) => (
            <div key={test.test_id} className="test-card">
              <div className="test-card-content">
                <div className="test-card-name">
                  {test.name}
                </div>
                <div className="test-card-meta">
                  <span>❓ {test.question_count || 0} вопросов</span>
                  <span>⏱️ {test.time || 60} сек</span>
                  <span>📊 {test.group_count || 0} групп</span>
                </div>
              </div>

              <div className="test-card-actions">
                <button
                  title={t('viewResults')}
                  onClick={() => onViewResults(test)}
                >
                  📊
                </button>
                <button
                  title={t('editTest')}
                  onClick={() => onEdit(test)}
                >
                  ✏️
                </button>
                <button
                  title={t('deleteTest')}
                  onClick={() => handleDelete(test.test_id)}
                  style={{ color: '#df5152' }}
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </>
      )}

      {/* Floating Action Button */}
      <button
        className="btn btn-primary"
        onClick={onCreateNew}
        style={{
          position: 'fixed',
          bottom: '100px',
          right: '16px',
          borderRadius: '50%',
          width: '56px',
          height: '56px',
          fontSize: '24px',
          boxShadow: '0 4px 12px rgba(0, 136, 204, 0.4)'
        }}
      >
        ➕
      </button>
    </div>
  );
}

export default Dashboard;
