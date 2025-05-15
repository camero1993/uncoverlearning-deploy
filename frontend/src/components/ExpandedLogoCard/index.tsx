import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import Chat from '../Chat';
import { uploadDocument, UploadProgressInfo } from '../../services/api';

interface ExpandedLogoCardProps {
  onCollapse: () => void;
  logo: string;
  brandText: string;
}

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 2000;
  background: rgba(255,255,255,0.98);
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.3s;
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  padding: 1.5rem 2rem 1rem 2rem;
  border-bottom: 1px solid #eee;
`;

const BackButton = styled.button`
  background: none;
  border: none;
  color: #5c6a5a;
  font-size: 2rem;
  cursor: pointer;
  margin-right: 2rem;
  transition: opacity 0.2s;
  &:hover { opacity: 0.7; }
`;

const Logo = styled.img`
  width: 120px;
  height: auto;
  margin-right: 1.5rem;
`;

const Brand = styled.h1`
  font-family: 'Fraunces', serif;
  font-size: 2rem;
  color: #5c6a5a;
  font-weight: 600;
  margin: 0;
`;

const Main = styled.div`
  flex: 1;
  display: flex;
  height: calc(100vh - 80px);
`;

const PdfPanel = styled.div`
  flex: 0 0 60%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f8f8;
  border-right: 1px solid #eee;
  position: relative;
`;

const UploadButton = styled.label`
  display: inline-block;
  padding: 1.25rem 2.5rem;
  background: #5c6a5a;
  color: #fff;
  border-radius: 8px;
  font-size: 1.25rem;
  font-family: 'Montserrat', sans-serif;
  cursor: pointer;
  transition: background 0.2s;
  &:hover { background: #4a5649; }
  &:disabled, &[disabled] {
    background: #a0a0a0;
    cursor: not-allowed;
  }
`;

const ErrorContainer = styled.div`
  margin-top: 1rem;
  color: #d32f2f;
  font-family: 'Montserrat', sans-serif;
  max-width: 400px;
  text-align: center;
`;

const StatusContainer = styled.div`
  margin-top: 1rem;
  color: #5c6a5a;
  font-family: 'Montserrat', sans-serif;
  max-width: 400px;
  text-align: center;
`;

const ProgressContainer = styled.div`
  width: 300px;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin: 1rem 0;
`;

const ProgressBar = styled.div<{ width: number }>`
  height: 100%;
  background: #5c6a5a;
  width: ${props => props.width}%;
  transition: width 0.3s ease;
`;

const PdfIframe = styled.iframe`
  width: 100%;
  height: 90vh;
  border: none;
  background: #fff;
`;

const ChatPanel = styled.div`
  flex: 0 0 40%;
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
`;

const HiddenInput = styled.input`
  display: none;
`;

const ExpandedLogoCard: React.FC<ExpandedLogoCardProps> = ({ onCollapse, logo, brandText }) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [fileTitle, setFileTitle] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<UploadProgressInfo | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Prevent background scroll when overlay is open
  useEffect(() => {
    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = originalStyle; };
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    // Reset states
    setUploadError(null);
    setUploadStatus(null);
    setProgress(null);
    
    const file = e.target.files?.[0];
    
    // Validate file is present
    if (!file) {
      setUploadError('No file selected.');
      return;
    }
    
    // Validate file type
    if (file.type !== 'application/pdf') {
      setUploadError('Only PDF files are allowed.');
      return;
    }
    
    // Create object URL for preview
    const url = URL.createObjectURL(file);
    setPdfUrl(url);
    setUploadStatus('Preparing upload...');
    setIsUploading(true);
    
    try {
      console.log('Uploading document:', file.name, 'Size:', (file.size / 1024 / 1024).toFixed(2) + 'MB');
      
      // Upload with progress tracking
      const result = await uploadDocument(
        file, 
        file.name,
        (progressInfo) => {
          setProgress(progressInfo);
          
          // Update status based on the stage
          switch (progressInfo.stage) {
            case 'preparing':
              setUploadStatus(`Preparing upload: ${progressInfo.message}`);
              break;
            case 'uploading':
              setUploadStatus(`Uploading: ${progressInfo.percentage}%`);
              break;
            case 'processing':
              setUploadStatus('Processing document...');
              break;
            case 'complete':
              setUploadStatus('Document uploaded successfully! You can now ask questions about it.');
              break;
          }
        }
      );
      
      console.log('Upload result:', result);
      
      setFileTitle(file.name);
      setIsUploading(false);
      setUploadStatus('Document uploaded and processed! You can now ask questions about it.');
    } catch (err: any) {
      console.error('Upload error:', err);
      setIsUploading(false);
      
      // Enhanced error reporting with detailed categorization
      let errorMessage = 'Failed to upload document: Unknown error.';
      
      if (err.response) {
        // Server responded with error
        console.error('Server response:', err.response.data);
        
        if (err.response.status === 413) {
          errorMessage = `File is too large for the server to process. Please try a smaller file.`;
        } else if (err.response.status === 401 || err.response.status === 403) {
          errorMessage = 'Not authorized to upload files.';
        } else if (err.response.status >= 500) {
          if (err.response.data && err.response.data.detail) {
            errorMessage = `Server Error: ${err.response.data.detail}`;
          } else {
            errorMessage = `Server Error (${err.response.status}): The server encountered an error processing your document.`;
          }
        }
      } else if (err.request) {
        // Request made but no response received
        errorMessage = 'No response from server. Please check your internet connection.';
      } else if (err.message) {
        // Other error
        errorMessage = `${err.message}`;
      }
      
      setUploadError(errorMessage);
      setUploadStatus(null);
    }
  };

  return (
    <Overlay role="dialog" aria-modal="true" aria-label="Uncover Learning PDF and Chat">
      <Header>
        <BackButton aria-label="Back" onClick={onCollapse} tabIndex={0}>&larr;</BackButton>
        <Logo src={logo} alt="Uncover Learning Logo" />
        <Brand>{brandText}</Brand>
      </Header>
      <Main>
        <PdfPanel>
          {!pdfUrl ? (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <UploadButton 
                  htmlFor="pdf-upload" 
                  style={{ 
                    opacity: isUploading ? 0.6 : 1, 
                    pointerEvents: isUploading ? 'none' : 'auto' 
                  }}
                >
                  {isUploading ? 'Uploading...' : 'Upload your document'}
                  <HiddenInput
                    id="pdf-upload"
                    type="file"
                    accept="application/pdf"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    disabled={isUploading}
                  />
                </UploadButton>
                
                {progress && (
                  <div style={{ marginTop: '1rem', width: '300px' }}>
                    <ProgressContainer>
                      <ProgressBar width={progress.percentage} />
                    </ProgressContainer>
                    <div style={{ fontSize: '0.8rem', textAlign: 'center' }}>
                      {progress.message}
                    </div>
                  </div>
                )}
                
                {uploadError && <ErrorContainer>{uploadError}</ErrorContainer>}
                {uploadStatus && !progress && <StatusContainer>{uploadStatus}</StatusContainer>}
                
                <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#777' }}>
                  Files larger than 10MB will be uploaded in chunks
                </div>
              </div>
            </>
          ) : (
            <>
              <PdfIframe src={pdfUrl} title="PDF Viewer" />
              
              {progress && (
                <div style={{ position: 'absolute', bottom: 16, right: 16, background: '#fff', padding: '0.5rem 1rem', borderRadius: 6, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
                  <ProgressContainer style={{ width: '200px' }}>
                    <ProgressBar width={progress.percentage} />
                  </ProgressContainer>
                  <div style={{ fontSize: '0.8rem', textAlign: 'center' }}>
                    {progress.message}
                  </div>
                </div>
              )}
              
              {uploadError && <div style={{ position: 'absolute', bottom: 16, left: 16, color: '#d32f2f', background: '#fff', padding: '0.5rem 1rem', borderRadius: 6 }}>{uploadError}</div>}
              {uploadStatus && !progress && <div style={{ position: 'absolute', bottom: 16, left: 16, color: '#5c6a5a', background: '#fff', padding: '0.5rem 1rem', borderRadius: 6 }}>{uploadStatus}</div>}
            </>
          )}
        </PdfPanel>
        <ChatPanel>
          <Chat isOpen={true} onClose={onCollapse} fileTitle={fileTitle} />
        </ChatPanel>
      </Main>
    </Overlay>
  );
};

export default ExpandedLogoCard; 