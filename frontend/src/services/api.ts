import axios from 'axios';

// For troubleshooting - hardcode the Render URL instead of using environment variables
// This will help determine if the environment variable is the issue
const HARDCODED_API_URL = 'https://uncoverlearning-deploy.onrender.com';
const API_BASE_URL = HARDCODED_API_URL; // Temporarily override environment variables

console.log('API Configuration:');
console.log('- process.env.REACT_APP_API_BASE_URL:', process.env.REACT_APP_API_BASE_URL);
console.log('- Using hardcoded API URL for troubleshooting:', API_BASE_URL);

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

  console.log(`uploadDocument: POSTing to ${API_BASE_URL}/api/documents/upload_document/`);
  const response = await api.post('/api/documents/upload_document/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const queryDocument = async (query: string): Promise<Message> => {
  console.log(`queryDocument: POSTing to ${API_BASE_URL}/api/queries/query_document/`);
  const response = await api.post('/api/queries/query_document/', { query });
  return response.data;
};

export const getChatHistory = async (): Promise<Message[]> => {
  // Explicitly log the full URL to verify what's being used
  const fullUrl = `${API_BASE_URL}/api/queries/chat-history`;
  console.log('getChatHistory: Requesting from', fullUrl);
  
  try {
    // Make a direct fetch call for diagnostic purposes
    const directFetch = await fetch(fullUrl);
    console.log('Direct fetch result:', directFetch.status);
  } catch (error) {
    console.error('Direct fetch failed:', error);
  }
  
  // Now use axios as before
  const response = await api.get('/api/queries/chat-history');
  return response.data;
};

export const clearChatHistory = async (): Promise<void> => {
  console.log(`clearChatHistory: DELETEing to ${API_BASE_URL}/api/queries/chat-history`);
  await api.delete('/api/queries/chat-history');
};

export default api; 