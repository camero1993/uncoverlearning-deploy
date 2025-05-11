import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const uploadDocument = async (file: File, filename: string): Promise<void> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('filename', filename);

  await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const queryDocument = async (query: string): Promise<Message> => {
  const response = await api.post('/query', { query });
  return response.data;
};

export const getChatHistory = async (): Promise<Message[]> => {
  const response = await api.get('/chat-history');
  return response.data;
};

export const clearChatHistory = async (): Promise<void> => {
  await api.delete('/chat-history');
};

export default api; 