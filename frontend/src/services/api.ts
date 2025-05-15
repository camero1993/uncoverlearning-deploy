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
  // Add a reasonable timeout for all requests
  timeout: 30000, // 30 seconds default timeout
});

// Add response interceptor for better error logging
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', {
      message: error.message,
      endpoint: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data
    });
    return Promise.reject(error);
  }
);

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const uploadDocument = async (file: File, filename: string): Promise<any> => {
  // Create form data
  const formData = new FormData();
  formData.append('file', file);
  formData.append('original_name', filename);

  console.log(`uploadDocument: POSTing to ${API_BASE_URL}/api/documents/upload_document/`);
  console.log(`File details: Name=${filename}, Size=${(file.size / 1024 / 1024).toFixed(2)}MB, Type=${file.type}`);
  
  try {
    // Set timeout for large files to prevent hanging requests
    // Increase timeout for large files (30 seconds)
    const response = await api.post('/api/documents/upload_document/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds timeout for uploads
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || file.size));
        console.log(`Upload progress: ${percentCompleted}%`);
      }
    });
    
    console.log('Upload successful, response:', response.data);
    return response.data;
  } catch (error: any) {
    // Detailed error categorization and logging
    if (error.code === 'ECONNABORTED') {
      console.error('Upload timeout: Request took too long to complete');
    }
    
    console.error('Upload error details:', {
      name: error.name,
      message: error.message,
      code: error.code,
      stack: error.stack,
      response: error.response ? {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        headers: error.response.headers
      } : 'No response',
      request: error.request ? 'Request was made but no response received' : 'No request was made',
      config: error.config ? {
        url: error.config.url,
        method: error.config.method,
        timeout: error.config.timeout,
        headers: error.config.headers
      } : 'No config'
    });
    
    // Rethrow with enhanced message for timeout case
    if (error.code === 'ECONNABORTED') {
      throw new Error('Upload timed out. The file may be too large or the server is too busy.');
    }
    
    throw error;
  }
};

export const queryDocument = async (query: string, file_title?: string): Promise<Message> => {
  console.log(`queryDocument: POSTing to ${API_BASE_URL}/api/queries/query_document/ with`, { query, file_title });
  
  const response = await api.post('/api/queries/query_document/', { 
    query,
    file_title: file_title || null
  });
  
  return {
    role: 'assistant',
    content: response.data.answer
  };
};

export const getChatHistory = async (): Promise<Message[]> => {
  // Explicitly log the full URL to verify what's being used
  const fullUrl = `${API_BASE_URL}/api/queries/chat-history`;
  console.log('getChatHistory: Requesting from', fullUrl);
  
  try {
    // Use axios instance with the correct path
    const response = await api.get('/api/queries/chat-history');
    console.log('Chat history response:', response.status, response.data);
    return response.data;
  } catch (error: any) {
    console.error('Chat history fetch failed:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data
    });
    // Return empty array on error to prevent UI crashes
    return [];
  }
};

export const clearChatHistory = async (): Promise<void> => {
  console.log(`clearChatHistory: DELETEing to ${API_BASE_URL}/api/queries/chat-history`);
  await api.delete('/api/queries/chat-history');
};

export default api; 