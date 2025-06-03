import React, { useState } from 'react';
import styled from 'styled-components';
import { uploadDocument, UploadProgressInfo } from '../../services/api';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
  max-width: 400px;
`;

const Input = styled.input`
  display: none;
`;

const Label = styled.label`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  border: 2px dashed #5c6a5a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  text-align: center;

  &:hover {
    background: rgba(92, 106, 90, 0.05);
  }
`;

const Button = styled.button`
  padding: 0.75rem 2rem;
  background: #5c6a5a;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
  width: 100%;

  &:hover {
    background: #4a5649;
  }

  &:disabled {
    background: #ccc;
    cursor: not-allowed;
  }
`;

const Message = styled.div<{ type: 'success' | 'error' | 'info' | 'warning' }>`
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  background: ${props => 
    props.type === 'success' ? '#e6f4ea' : 
    props.type === 'info' ? '#e8f0fe' : 
    props.type === 'warning' ? '#fef7e0' :
    '#fce8e6'};
  color: ${props => 
    props.type === 'success' ? '#1e4620' : 
    props.type === 'info' ? '#1a73e8' : 
    props.type === 'warning' ? '#b06000' :
    '#c5221f'};
  font-size: 0.875rem;
  text-align: center;
  width: 100%;
`;

const FileName = styled.span`
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.5rem;
`;

const ProgressContainer = styled.div`
  width: 100%;
  margin-top: 1rem;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ percentage: number }>`
  height: 100%;
  width: ${props => props.percentage}%;
  background-color: #5c6a5a;
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  font-size: 0.75rem;
  color: #666;
  text-align: center;
  margin-top: 0.5rem;
`;

const StageIndicator = styled.div`
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-top: 0.5rem;
`;

const Stage = styled.div<{ active: boolean, completed: boolean }>`
  font-size: 0.75rem;
  color: ${props => 
    props.completed ? '#1e4620' : 
    props.active ? '#1a73e8' : 
    '#666'};
  font-weight: ${props => (props.active || props.completed) ? 'bold' : 'normal'};
`;

const RetryButton = styled.button`
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  background: transparent;
  color: #1a73e8;
  border: 1px solid #1a73e8;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(26, 115, 232, 0.1);
  }
`;

const DocumentUpload: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' | 'warning' } | null>(null);
  const [progress, setProgress] = useState<UploadProgressInfo | null>(null);
  const [uploadFailed, setUploadFailed] = useState(false);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      setMessage(null);
      setProgress(null);
      setUploadFailed(false);
      
      // Show file size information
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
      const isLargeFile = file.size > 10 * 1024 * 1024;
      
      if (isLargeFile) {
        setMessage({ 
          text: `Selected file is ${fileSizeMB}MB. It will be uploaded in chunks. This may take several minutes depending on your connection speed.`, 
          type: 'warning' 
        });
      } else {
        setMessage({ 
          text: `Selected file is ${fileSizeMB}MB.`, 
          type: 'info' 
        });
      }
    } else {
      setMessage({ text: 'Please select a PDF file', type: 'error' });
    }
  };

  const handleProgressUpdate = (progressInfo: UploadProgressInfo) => {
    setProgress(progressInfo);
    
    if (progressInfo.stage === 'processing') {
      setMessage({ 
        text: 'Processing document... This may take a minute for large files.', 
        type: 'info' 
      });
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadFailed(false);
    setMessage({ text: 'Starting upload...', type: 'info' });
    setProgress({
      loaded: 0,
      total: selectedFile.size,
      percentage: 0,
      stage: 'preparing',
      message: 'Preparing upload...'
    });

    try {
      await uploadDocument(selectedFile, selectedFile.name, handleProgressUpdate);
      setMessage({ text: 'Document uploaded successfully!', type: 'success' });
      setSelectedFile(null);
      // Reset the file input
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    } catch (error: any) {
      console.error('Upload error:', error);
      setUploadFailed(true);
      
      // Provide more specific error messages based on the error
      if (error.message && error.message.includes('chunk')) {
        setMessage({ 
          text: `Chunk upload failed. Please check your connection and try again.`, 
          type: 'error' 
        });
      } else if (error.response?.status === 413) {
        setMessage({ 
          text: 'File too large for direct upload. The system will try to upload in chunks.',
          type: 'warning' 
        });
      } else {
        setMessage({ 
          text: `Failed to upload document: ${error.message || 'Unknown error'}`, 
          type: 'error' 
        });
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await handleUpload();
  };
  
  const handleRetry = async () => {
    await handleUpload();
  };
  
  const getStageStatus = (stageName: string) => {
    if (!progress) return { active: false, completed: false };
    
    const stages = ['preparing', 'uploading', 'processing', 'complete'];
    const currentStageIndex = stages.indexOf(progress.stage);
    const stageIndex = stages.indexOf(stageName);
    
    return {
      active: stageIndex === currentStageIndex,
      completed: stageIndex < currentStageIndex
    };
  };

  return (
    <Container>
      <Form onSubmit={handleSubmit}>
        <Input
          type="file"
          id="document-upload"
          accept=".pdf"
          onChange={handleFileSelect}
        />
        <Label htmlFor="document-upload">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#5c6a5a" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>Click to upload or drag and drop</span>
          <span style={{ fontSize: '0.75rem', color: '#666' }}>PDF files only (any size)</span>
          {selectedFile && <FileName>{selectedFile.name}</FileName>}
        </Label>
        <Button type="submit" disabled={!selectedFile || isUploading}>
          {isUploading ? 'Uploading...' : 'Upload Document'}
        </Button>
        
        {progress && (
          <ProgressContainer>
            <ProgressBar>
              <ProgressFill percentage={progress.percentage} />
            </ProgressBar>
            <ProgressText>
              {progress.message} ({Math.round(progress.loaded / 1024 / 1024 * 100) / 100}MB / {Math.round(progress.total / 1024 / 1024 * 100) / 100}MB)
            </ProgressText>
            <StageIndicator>
              <Stage {...getStageStatus('preparing')}>Preparing</Stage>
              <Stage {...getStageStatus('uploading')}>Uploading</Stage>
              <Stage {...getStageStatus('processing')}>Processing</Stage>
              <Stage {...getStageStatus('complete')}>Complete</Stage>
            </StageIndicator>
          </ProgressContainer>
        )}
        
        {uploadFailed && (
          <RetryButton type="button" onClick={handleRetry}>
            Retry Upload
          </RetryButton>
        )}
      </Form>
      {message && (
        <Message type={message.type}>
          {message.text}
        </Message>
      )}
    </Container>
  );
};

export default DocumentUpload; 