// pages/EditTest.jsx - Редактирование теста

import React, { useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

function EditTest({ test, user, language, t, onBack, onSuccess }) {
  const [formData, setFormData] = useState({
    name: test?.name || '',
    time: test?.time || 60,
    order: test?.order || 'normal'
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'time' ? parseInt(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      setLoading(true);
      const initData = window.Telegram?.WebApp?.initData;

      const response = await fetch(`${API_URL}/tests/${test.test_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'x-telegram-init-data': initData
        },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        if (window.Telegram?.WebApp?.showPopup) {
          window.Telegram.WebApp.showPopup({
            title: '✅ Успешно',
            message: 'Тест обновлен!'
          });
        }
        onSuccess();
      } else {
        setError('Ошибка при обновлении');
      }
    } catch (err) {
      console.error('Error updating test:', err);
      setError('Ошибка подключения');
    } finally {
      setLoading(false);
    }
  };

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

      <form onSubmit={handleSubmit} className="form-container">
        <h2 style={{ marginBottom: '16px' }}>✏️ Редактирование теста</h2>

        <div className="form-group">
          <label>{t('testName')}</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label>{t('testTime')}</label>
          <input
            type="number"
            name="time"
            value={formData.time}
            onChange={handleChange}
            min="10"
            max="300"
          />
        </div>

        <div className="form-group">
          <label>Порядок вопросов</label>
          <select
            name="order"
            value={formData.order}
            onChange={handleChange}
          >
            <option value="normal">📋 По порядку</option>
            <option value="shuffle">🔀 Перемешать всё</option>
            <option value="questions">❓ Только вопросы</option>
            <option value="answers">✅ Только ответы</option>
          </select>
        </div>

        <div className="form-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onBack}
          >
            {t('cancel')}
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? '⏳ Сохранение...' : '💾 ' + t('save')}
          </button>
        </div>
      </form>
    </div>
  );
}

export default EditTest;
