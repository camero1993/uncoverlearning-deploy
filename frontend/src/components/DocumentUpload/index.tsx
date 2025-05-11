import React, { useState } from 'react';
import styled from 'styled-components';
import { uploadDocument } from '../../services/api';

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

const Message = styled.div<{ type: 'success' | 'error' }>`
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  background: ${props => props.type === 'success' ? '#e6f4ea' : '#fce8e6'};
  color: ${props => props.type === 'success' ? '#1e4620' : '#c5221f'};
  font-size: 0.875rem;
  text-align: center;
`;

const FileName = styled.span`
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.5rem;
`;

const DocumentUpload: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      setMessage(null);
    } else {
      setMessage({ text: 'Please select a PDF file', type: 'error' });
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setMessage(null);

    try {
      await uploadDocument(selectedFile, selectedFile.name);
      setMessage({ text: 'Document uploaded successfully!', type: 'success' });
      setSelectedFile(null);
      // Reset the file input
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    } catch (error) {
      setMessage({ text: 'Failed to upload document. Please try again.', type: 'error' });
    } finally {
      setIsUploading(false);
    }
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
          <span style={{ fontSize: '0.75rem', color: '#666' }}>PDF files only</span>
          {selectedFile && <FileName>{selectedFile.name}</FileName>}
        </Label>
        <Button type="submit" disabled={!selectedFile || isUploading}>
          {isUploading ? 'Uploading...' : 'Upload Document'}
        </Button>
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