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

export interface UploadProgressInfo {
  loaded: number;
  total: number;
  percentage: number;
  stage: 'preparing' | 'uploading' | 'processing' | 'complete';
  message: string;
}

type ProgressCallback = (progress: UploadProgressInfo) => void;

/**
 * Upload a file using the chunked upload API for large files
 */
const uploadChunkedFile = async (
  file: File, 
  filename: string, 
  onProgress?: ProgressCallback
): Promise<any> => {
  // Configuration
  const CHUNK_SIZE = 1 * 1024 * 1024; // 1MB chunks
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  
  console.log(`Starting chunked upload for ${filename}`);
  console.log(`File details: Size=${(file.size / 1024 / 1024).toFixed(2)}MB, Chunks=${totalChunks}`);
  
  onProgress?.({
    loaded: 0,
    total: file.size,
    percentage: 0,
    stage: 'preparing',
    message: 'Preparing file for chunked upload...'
  });
  
  try {
    // Step 1: Initialize chunked upload
    console.log('Initializing chunked upload');
    const initResponse = await api.post('/api/documents/initiate_chunked_upload/', {
      file_name: filename,
      total_chunks: totalChunks,
      total_size: file.size,
      mime_type: 'application/pdf'
    });
    
    const uploadId = initResponse.data.upload_id;
    console.log(`Chunked upload initialized with ID: ${uploadId}`);
    
    // Step 2: Upload chunks
    let uploadedBytes = 0;
    let uploadedChunks = 0;
    
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);
      
      // Read chunk as ArrayBuffer and convert to Base64
      const arrayBuffer = await chunk.arrayBuffer();
      const binary = new Uint8Array(arrayBuffer);
      let binaryString = '';
      for (let i = 0; i < binary.byteLength; i++) {
        binaryString += String.fromCharCode(binary[i]);
      }
      const base64Chunk = btoa(binaryString);
      
      // Upload chunk
      console.log(`Uploading chunk ${chunkIndex + 1}/${totalChunks}`);
      const chunkResponse = await api.post('/api/documents/upload_chunk/', {
        upload_id: uploadId,
        chunk_index: chunkIndex,
        total_chunks: totalChunks,
        chunk_data: base64Chunk
      });
      
      // Update progress
      uploadedBytes += chunk.size;
      uploadedChunks++;
      const percentage = Math.round((uploadedBytes * 100) / file.size);
      
      console.log(`Chunk ${chunkIndex + 1}/${totalChunks} uploaded. Total progress: ${percentage}%`);
      
      onProgress?.({
        loaded: uploadedBytes,
        total: file.size,
        percentage,
        stage: 'uploading',
        message: `Uploading chunk ${uploadedChunks}/${totalChunks}: ${percentage}%`
      });
    }
    
    // Step 3: Finalize upload
    console.log('Finalizing chunked upload');
    
    onProgress?.({
      loaded: file.size,
      total: file.size,
      percentage: 100,
      stage: 'processing',
      message: 'Processing document...'
    });
    
    const finalizeResponse = await api.post('/api/documents/finalize_chunked_upload/', {
      upload_id: uploadId,
      original_name: filename
    });
    
    console.log('Chunked upload finalized, response:', finalizeResponse.data);
    
    onProgress?.({
      loaded: file.size,
      total: file.size,
      percentage: 100,
      stage: 'complete',
      message: 'Upload complete'
    });
    
    return finalizeResponse.data;
  } catch (error: any) {
    console.error('Chunked upload error:', error);
    
    // Detailed error logging
    console.error('Chunked upload error details:', {
      name: error.name,
      message: error.message,
      response: error.response ? {
        status: error.response.status,
        data: error.response.data
      } : 'No response'
    });
    
    throw error;
  }
};

export const uploadDocument = async (file: File, filename: string, onProgress?: ProgressCallback): Promise<any> => {
  // Create form data
  const formData = new FormData();
  formData.append('file', file);
  formData.append('original_name', filename);

  // For files larger than 10MB, use chunked upload
  if (file.size > 10 * 1024 * 1024) {
    console.log(`File is larger than 10MB (${(file.size / 1024 / 1024).toFixed(2)}MB), using chunked upload`);
    return uploadChunkedFile(file, filename, onProgress);
  }

  console.log(`Regular upload: POSTing to ${API_BASE_URL}/api/documents/upload_document/`);
  console.log(`File details: Name=${filename}, Size=${(file.size / 1024 / 1024).toFixed(2)}MB, Type=${file.type}`);
  
  onProgress?.({
    loaded: 0,
    total: file.size,
    percentage: 0,
    stage: 'uploading',
    message: 'Starting upload...'
  });
  
  try {
    // Set timeout for large files to prevent hanging requests
    const response = await api.post('/api/documents/upload_document/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds timeout for uploads
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || file.size));
        console.log(`Upload progress: ${percentCompleted}%`);
        
        onProgress?.({
          loaded: progressEvent.loaded,
          total: progressEvent.total || file.size,
          percentage: percentCompleted,
          stage: 'uploading',
          message: `Uploading: ${percentCompleted}%`
        });
      }
    });
    
    console.log('Upload successful, response:', response.data);
    
    onProgress?.({
      loaded: file.size,
      total: file.size,
      percentage: 100,
      stage: 'complete',
      message: 'Upload complete'
    });
    
    return response.data;
  } catch (error: any) {
    // Check for 413 error with suggestion for chunked upload
    if (error.response?.status === 413 && error.response?.data?.suggestion) {
      console.log('File too large for direct upload, switching to chunked upload');
      return uploadChunkedFile(file, filename, onProgress);
    }
    
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