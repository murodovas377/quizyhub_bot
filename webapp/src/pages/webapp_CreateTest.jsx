// pages/CreateTest.jsx - Форма создания нового теста

import React, { useState } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

function CreateTest({ user, language, t, onBack, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    answer_mode: 'hash',
    time: 60,
    split: 30,
    questions: []
  });

  const [step, setStep] = useState('name');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'time' || name === 'split' ? parseInt(value) : value
    }));
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const parseQuestions = async () => {
    if (!file) {
      setError('Выбери файл');
      return;
    }

    try {
      setLoading(true);
      const text = await file.text();

      // Простой парсер вопросов
      const questions = [];
      const blocks = text.split(/\n\s*\+{3,}\s*\n/);

      for (const block of blocks) {
        const parts = block.split(/\n\s*={3,}\s*\n/);
        if (parts.length < 2) continue;

        const question = parts[0].trim();
        const answers = [];
        let correctIndex = null;

        for (let i = 1; i < parts.length; i++) {
          let answer = parts[i].trim();
          
          if (formData.answer_mode === 'hash' && answer.startsWith('#')) {
            answer = answer.substring(1).trim();
            correctIndex = answers.length;
          }

          answers.push(answer);
        }

        if (formData.answer_mode === 'first') {
          correctIndex = 0;
        }

        if (correctIndex !== null && answers.length >= 2) {
          questions.push({
            question,
            answers,
            correct: correctIndex
          });
        }
      }

      if (questions.length === 0) {
        setError('Не удалось распознать вопросы');
        setLoading(false);
        return;
      }

      setFormData(prev => ({
        ...prev,
        questions
      }));

      setStep('time');
    } catch (err) {
      setError('Ошибка при чтении файла');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError('Введи название теста');
      return;
    }

    if (formData.questions.length === 0) {
      setError('Загрузи файл с вопросами');
      return;
    }

    try {
      setLoading(true);
      const initData = window.Telegram?.WebApp?.initData;

      const response = await fetch(`${API_URL}/tests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-telegram-init-data': initData
        },
        body: JSON.stringify({
          name: formData.name,
          questions: formData.questions,
          answer_mode: formData.answer_mode,
          time: formData.time,
          split: formData.split
        })
      });

      if (response.ok) {
        // Уведомление от Telegram
        if (window.Telegram?.WebApp?.showPopup) {
          window.Telegram.WebApp.showPopup({
            title: '✅ Успешно',
            message: 'Тест создан!'
          });
        }
        onSuccess();
      } else {
        const data = await response.json();
        setError(data.message || 'Ошибка при создании');
      }
    } catch (err) {
      console.error('Error creating test:', err);
      setError('Ошибка подключения');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <button
          className="btn btn-secondary"
          onClick={onBack}
          style={{ marginBottom: '16px' }}
        >
          🔙 {t('backButton')}
        </button>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '16px' }}>
          ⚠️ {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="form-container">
        {/* ШАГ 1: Название */}
        {step === 'name' && (
          <>
            <h2 style={{ marginBottom: '16px' }}>Шаг 1: Название теста</h2>
            <div className="form-group">
              <label>{t('testName')}</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Введи название"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label>Режим ответов</label>
              <select
                name="answer_mode"
                value={formData.answer_mode}
                onChange={handleChange}
              >
                <option value="hash">1️⃣ # правильный</option>
                <option value="first">2️⃣ Первый правильный</option>
              </select>
            </div>

            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setStep('file')}
              disabled={!formData.name.trim()}
            >
              Далее →
            </button>
          </>
        )}

        {/* ШАГ 2: Загрузка файла */}
        {step === 'file' && (
          <>
            <h2 style={{ marginBottom: '16px' }}>Шаг 2: Загрузи файл</h2>
            <p style={{ fontSize: '12px', color: '#666', marginBottom: '12px' }}>
              Поддерживаются .txt и .docx файлы
            </p>

            <div className="form-group">
              <input
                type="file"
                accept=".txt,.docx"
                onChange={handleFileChange}
              />
            </div>

            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep('name')}
              >
                ← Назад
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={parseQuestions}
                disabled={!file || loading}
              >
                {loading ? '⏳ Загрузка...' : 'Распознать вопросы'}
              </button>
            </div>
          </>
        )}

        {/* ШАГ 3: Время и разбиение */}
        {step === 'time' && (
          <>
            <h2 style={{ marginBottom: '16px' }}>Шаг 3: Настройки</h2>

            <div className="alert alert-success">
              ✅ Распознано {formData.questions.length} вопросов
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
              <label>Вопросов на группу</label>
              <input
                type="number"
                name="split"
                value={formData.split}
                onChange={handleChange}
                min="5"
                max="100"
              />
            </div>

            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep('file')}
              >
                ← Назад
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? '⏳ Создание...' : '✅ Создать тест'}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}

export default CreateTest;
