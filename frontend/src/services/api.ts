import axios from 'axios';

// For troubleshooting - hardcode the Render URL instead of using environment variables
// This will help determine if the environment variable is the issue
// const HARDCODED_API_URL = 'https://uncoverlearning-deploy.onrender.com';
// const API_BASE_URL = HARDCODED_API_URL; // Temporarily override environment variables

// Use environment variable for API base URL, with a fallback for local development
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001';

console.log('API Configuration:');
console.log('- process.env.REACT_APP_API_BASE_URL:', process.env.REACT_APP_API_BASE_URL);
// console.log('- Using hardcoded API URL for troubleshooting:', API_BASE_URL);
console.log('- Effective API_BASE_URL being used:', API_BASE_URL);

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

// Simple direct upload (for files under 10MB)
const uploadSingleFile = async (
  file: File, 
  filename: string, 
  onProgress?: ProgressCallback
): Promise<any> => {
  // Create form data
  const formData = new FormData();
  formData.append('file', file);
  formData.append('original_name', filename);

  console.log(`uploadSingleFile: POSTing to ${API_BASE_URL}/api/documents/upload_document/`);
  console.log(`File details: Name=${filename}, Size=${(file.size / 1024 / 1024).toFixed(2)}MB, Type=${file.type}`);
  
  onProgress?.({
    loaded: 0,
    total: file.size,
    percentage: 0,
    stage: 'uploading',
    message: 'Starting upload...'
  });
  
  try {
    const response = await api.post('/api/documents/upload_document/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds timeout for uploads
      onUploadProgress: (progressEvent) => {
        const loaded = progressEvent.loaded;
        const total = progressEvent.total || file.size;
        const percentage = Math.round((loaded * 100) / total);
        
        console.log(`Upload progress: ${percentage}%`);
        
        onProgress?.({
          loaded,
          total,
          percentage,
          stage: 'uploading',
          message: `Uploading: ${percentage}%`
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
      console.log('File too large for direct upload, will try chunked upload');
      throw new Error('CHUNKED_UPLOAD_REQUIRED');
    }
    
    console.error('Upload error details:', {
      name: error.name,
      message: error.message,
      code: error.code,
      response: error.response ? {
        status: error.response.status,
        data: error.response.data
      } : 'No response'
    });
    
    throw error;
  }
};

// Configuration for chunked uploads
const CHUNK_SIZE = 1024 * 1024; // 1MB chunks
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 2000; // 2 seconds

// Helper function to add delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Function to upload a single chunk with retry logic
const uploadChunkWithRetry = async (
  uploadId: string,
  chunkIndex: number,
  totalChunks: number,
  chunkData: string,
  retryCount = 0
): Promise<any> => {
  try {
    return await api.post('/api/documents/upload_chunk/', {
      upload_id: uploadId,
      chunk_index: chunkIndex,
      total_chunks: totalChunks,
      chunk_data: chunkData
    });
  } catch (error: any) {
    // If we haven't exceeded max retries, try again
    if (retryCount < MAX_RETRY_ATTEMPTS) {
      console.log(`Chunk ${chunkIndex + 1}/${totalChunks} upload failed, retrying (${retryCount + 1}/${MAX_RETRY_ATTEMPTS})...`);
      await delay(RETRY_DELAY);
      return uploadChunkWithRetry(uploadId, chunkIndex, totalChunks, chunkData, retryCount + 1);
    }
    
    // Otherwise, throw the error
    console.error(`Failed to upload chunk ${chunkIndex + 1} after ${MAX_RETRY_ATTEMPTS} attempts`);
    throw error;
  }
};

// Function to calculate timeout based on file size (1 minute base + 1 minute per 10MB)
const calculateTimeout = (fileSize: number): number => {
  const baseSizeInMB = fileSize / (1024 * 1024);
  const baseTimeout = 60000; // 1 minute base
  const additionalTimeout = Math.ceil(baseSizeInMB / 10) * 60000; // 1 minute per 10MB
  return baseTimeout + additionalTimeout;
};

// Chunked upload for larger files
const uploadChunkedFile = async (
  file: File, 
  filename: string, 
  onProgress?: ProgressCallback
): Promise<any> => {
  // Calculate chunks
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
      mime_type: file.type
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
      
      // Show preparing stage for large files with many chunks
      if (chunkIndex === 0) {
        onProgress?.({
          loaded: 0,
          total: file.size,
          percentage: 0,
          stage: 'uploading',
          message: `Starting to upload ${totalChunks} chunks...`
        });
      }
      
      // Read chunk as ArrayBuffer and convert to Base64
      const arrayBuffer = await chunk.arrayBuffer();
      const base64Chunk = arrayBufferToBase64(arrayBuffer);
      
      // Upload chunk with retry logic
      console.log(`Uploading chunk ${chunkIndex + 1}/${totalChunks}`);
      try {
        await uploadChunkWithRetry(
          uploadId,
          chunkIndex,
          totalChunks,
          base64Chunk
        );
        
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
      } catch (error) {
        console.error(`Error uploading chunk ${chunkIndex + 1}/${totalChunks}:`, error);
        throw new Error(`Failed to upload chunk ${chunkIndex + 1}/${totalChunks}`);
      }
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
    }, {
      timeout: calculateTimeout(file.size) // Dynamic timeout based on file size
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
    throw error;
  }
};

// Helper function to convert ArrayBuffer to Base64
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const binary = new Uint8Array(buffer);
  let binaryString = '';
  for (let i = 0; i < binary.byteLength; i++) {
    binaryString += String.fromCharCode(binary[i]);
  }
  return btoa(binaryString);
}

// Main upload function that chooses the appropriate method based on file size
export const uploadDocument = async (
  file: File, 
  filename: string, 
  onProgress?: ProgressCallback
): Promise<any> => {
  const MAX_DIRECT_UPLOAD_SIZE = 10 * 1024 * 1024; // 10MB

  // ADDED: Detailed logging for diagnostics
  console.log('[uploadDocument] File details:', {
    name: file.name,
    size: file.size,
    type: file.type,
    maxDirect: MAX_DIRECT_UPLOAD_SIZE,
    decision_shouldBeChunked: file.size > MAX_DIRECT_UPLOAD_SIZE
  });
  
  try {
    if (file.size > MAX_DIRECT_UPLOAD_SIZE) {
      console.log(`[uploadDocument] File size (${file.size} bytes) > MAX_DIRECT_UPLOAD_SIZE (${MAX_DIRECT_UPLOAD_SIZE} bytes). Using chunked upload.`);
      return await uploadChunkedFile(file, filename, onProgress);
    }
    console.log(`[uploadDocument] File size (${file.size} bytes) <= MAX_DIRECT_UPLOAD_SIZE (${MAX_DIRECT_UPLOAD_SIZE} bytes). Using direct upload.`);
    return await uploadSingleFile(file, filename, onProgress);
  } catch (error: any) {
    if (error.message === 'CHUNKED_UPLOAD_REQUIRED') {
      console.log('[uploadDocument] Switching to chunked upload after CHUNKED_UPLOAD_REQUIRED error.');
      return await uploadChunkedFile(file, filename, onProgress);
    }
    console.error('[uploadDocument] Error:', error);
    throw error;
  }
};

export const queryDocument = async (
  query: string, 
  file_title?: string | null,
  mode?: 'student' | 'professor' | null
): Promise<Message> => {
  console.log(`queryDocument: POSTing to ${API_BASE_URL}/api/queries/query_document/ with`, { query, file_title, mode });
  
  const response = await api.post('/api/queries/query_document/', { 
    query,
    file_title: file_title || null,
    mode: mode || 'student'
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
