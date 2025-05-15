import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://uncoverlearning-deploy.onrender.com';

// Debug the API_BASE_URL
console.log('API_BASE_URL is set to:', API_BASE_URL);

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

export const uploadDocument = async (file: File, filename: string): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('original_name', filename);

  const response = await api.post('/api/documents/upload_document/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const queryDocument = async (query: string, file_title?: string): Promise<Message> => {
  const response = await api.post('/api/queries/query_document/', { 
    query,
    file_title: file_title || null
  });
  
  // Extract the answer from the response and format it as a Message
  return {
    role: 'assistant',
    content: response.data.answer
  };
};

export const getChatHistory = async (): Promise<Message[]> => {
  try {
    console.log('Fetching chat history from:', `${API_BASE_URL}/api/queries/chat-history`);
    const response = await api.get('/api/queries/chat-history');
    return response.data;
  } catch (error) {
    console.error('Error in getChatHistory:', error);
    // Return empty array instead of throwing to avoid breaking UI
    return [];
  }
};

export const clearChatHistory = async (): Promise<void> => {
  try {
    await api.delete('/api/queries/chat-history');
  } catch (error) {
    console.error('Error in clearChatHistory:', error);
    // Swallow the error to avoid breaking UI
  }
};

export default api; 