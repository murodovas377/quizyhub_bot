// pages/TestResults.jsx - Результаты и лидерборд

import React, { useEffect, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

function TestResults({ test, user, language, t, onBack }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchResults();
  }, [test?.test_id]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const initData = window.Telegram?.WebApp?.initData;

      const response = await fetch(
        `${API_URL}/tests/${test.test_id}/results`,
        {
          headers: {
            'x-telegram-init-data': initData
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setResults(data);
      } else {
        setError('Не удалось загрузить результаты');
      }
    } catch (err) {
      console.error('Error fetching results:', err);
      setError('Ошибка подключения');
    } finally {
      setLoading(false);
    }
  };

  const getMedal = (position) => {
    const medals = ['🥇', '🥈', '🥉'];
    return medals[position] || `${position + 1}.`;
  };

  if (loading) {
    return (
      <div>
        <button
          className="btn btn-secondary"
          onClick={onBack}
          style={{ marginBottom: '16px' }}
        >
          🔙 {t('backButton')}
        </button>
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <div className="spinner"></div>
          <p>{t('loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button
        className="btn btn-secondary"
        onClick={onBack}
        style={{ marginBottom: '16px' }}
      >
        🔙 {t('backButton')}
      </button>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '16px' }}>
          ⚠️ {error}
        </div>
      )}

      <div className="form-container">
        <h2 style={{ marginBottom: '12px' }}>🏆 Результаты теста</h2>
        <p style={{ fontSize: '14px', color: '#666', marginBottom: '16px' }}>
          {test?.name}
        </p>

        {results.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
            <p>📊 Результатов нет</p>
          </div>
        ) : (
          <div>
            {results.map((result, index) => (
              <div
                key={result.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '12px 0',
                  borderBottom: '1px solid #eee',
                  fontSize: '14px'
                }}
              >
                <span style={{ fontSize: '18px', width: '30px' }}>
                  {getMedal(index)}
                </span>
                <div style={{ flex: 1 }}>
                  <p style={{ marginBottom: '2px', fontWeight: 600 }}>
                    @{result.username || 'Неизвестный'}
                  </p>
                  <p style={{ fontSize: '12px', color: '#666' }}>
                    ✅ {result.score}/{result.total} • ⏱ {result.time_spent}s
                  </p>
                </div>
                <div
                  style={{
                    fontSize: '16px',
                    fontWeight: 600,
                    color: '#0088cc'
                  }}
                >
                  {Math.round((result.score / result.total) * 100)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Кнопка для поделиться */}
      <button
        className="btn btn-primary"
        onClick={() => {
          const tg = window.Telegram?.WebApp;
          if (tg?.close) {
            tg.close();
          }
        }}
        style={{ marginTop: '16px' }}
      >
        📤 Поделиться тестом
      </button>
    </div>
  );
}

export default TestResults;
