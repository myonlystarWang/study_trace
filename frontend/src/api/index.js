import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
});

// 家长门禁请求头拦截器
api.interceptors.request.use((config) => {
  const pin = sessionStorage.getItem('parent_pin');
  if (pin) {
    config.headers['X-Parent-PIN'] = pin;
  }
  return config;
});

export const homeworkApi = {
  getList: (dateStr) => api.get('/homework', { params: { date: dateStr } }),
  getCalendar: (monthStr) => api.get('/homework/calendar', { params: { month: monthStr } }),
  create: (data) => api.post('/homework', data),
  update: (id, data) => api.put(`/homework/${id}`, data),
  delete: (id) => api.delete(`/homework/${id}`),
  toMistake: (id) => api.post(`/homework/${id}/to-mistake`)
};

export const mistakeApi = {
  getList: (params) => api.get('/mistakes', { params }),
  getReviewQueue: (subjectId) => api.get('/mistakes', { params: { ebbinghaus_today: true, ...(subjectId ? { subject_id: subjectId } : {}) } }),
  getDetail: (id) => api.get(`/mistakes/${id}`),
  create: (data) => api.post('/mistakes', data),
  update: (id, data) => api.put(`/mistakes/${id}`, data),
  delete: (id) => api.delete(`/mistakes/${id}`),
  review: (id, result) => api.post(`/mistakes/${id}/review`, { mistake_id: id, result }),
  submitReview: (id, result) => api.post(`/mistakes/${id}/review`, { mistake_id: id, result }),
  uploadImage: (formData) => api.post('/mistakes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
};

export const settingsApi = {
  getSubjects: () => api.get('/settings/subjects'),
  createSubject: (data) => api.post('/settings/subjects', data),
  updateSubject: (id, data) => api.put(`/settings/subjects/${id}`, data),
  deleteSubject: (id) => api.delete(`/settings/subjects/${id}`),
  verifyPin: (pin) => api.post('/settings/verify-pin', { pin }),
  changePin: (oldPin, newPin) => api.put('/settings/pin', { old_pin: oldPin, new_pin: newPin })
};

export const backupApi = {
  exportUrl: '/api/backup/export',
  importBackup: (formData) => api.post('/backup/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
};

export const ocrApi = {
  createTask: (formData) =>
    api.post('/ocr/tasks', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  getTask: (taskId) => api.get(`/ocr/tasks/${taskId}`),
  getEngines: () => api.get('/ocr/engines')
};

export const notificationApi = {
  getConfig: () => api.get('/notifications/config'),
  updateConfig: (data) => api.put('/notifications/config', data),
  testChannel: (channel, target) => api.post(`/notifications/test/${channel}`, { target }),
  sendSummaryNow: (channels) => api.post('/notifications/send-summary-now', { channels })
};

export const paperApi = {
  getCandidates: (params) => api.get('/paper/candidates', { params }),
  compose: (data) => api.post('/paper/compose', data),
  getPaper: (id) => api.get(`/paper/${id}`),
  markPrinted: (id) => api.post(`/paper/${id}/mark_printed`),
  batchReview: (id, reviews) => api.post(`/paper/${id}/batch_review`, { reviews }),
  getHistory: (params) => api.get('/paper/history', { params })
};

export const examApi = {
  getList: (examType) => api.get('/exams', { params: examType ? { exam_type: examType } : {} }),
  getDetail: (id) => api.get(`/exams/${id}`),
  create: (data) => api.post('/exams', data),
  update: (id, data) => api.put(`/exams/${id}`, data),
  delete: (id) => api.delete(`/exams/${id}`),
  getTrends: (subjectId) => api.get('/exams/charts/trends', { params: subjectId ? { subject_id: subjectId } : {} }),
  getRadar: (examId) => api.get('/exams/charts/radar', { params: examId ? { exam_id: examId } : {} }),
  getWeaknesses: () => api.get('/exams/diagnostics/weaknesses'),
  getMonthlyAnalytics: (year, month) => api.get('/exams/analytics/monthly', { params: { year, month } })
};


export default api;

