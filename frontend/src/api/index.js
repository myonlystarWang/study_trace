import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
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
  getDetail: (id) => api.get(`/mistakes/${id}`),
  create: (data) => api.post('/mistakes', data),
  update: (id, data) => api.put(`/mistakes/${id}`, data),
  delete: (id) => api.delete(`/mistakes/${id}`),
  review: (id, result) => api.post(`/mistakes/${id}/review`, { mistake_id: id, result }),
  uploadImage: (formData) => api.post('/mistakes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
};

export const settingsApi = {
  getSubjects: () => api.get('/settings/subjects'),
  createSubject: (data) => api.post('/settings/subjects', data),
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

export default api;
