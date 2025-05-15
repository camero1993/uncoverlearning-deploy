import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import Chat from '../Chat';
import { uploadDocument } from '../../services/api';

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
  const [fileTitle, setFileTitle] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Prevent background scroll when overlay is open
  useEffect(() => {
    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = originalStyle; };
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      const url = URL.createObjectURL(file);
      setPdfUrl(url);
      setUploadStatus('Uploading...');
      
      try {
        console.log('Uploading document:', file.name);
        const result = await uploadDocument(file, file.name);
        console.log('Upload result:', result);
        
        setFileTitle(file.name);
        setUploadStatus('Document uploaded and processing started!');
      } catch (err: any) {
        console.error('Upload error:', err);
        // Enhanced error reporting
        let errorMessage = 'Failed to upload document.';
        
        if (err.response) {
          console.error('Server response:', err.response.data);
          // Add server error details if available
          if (err.response.data && err.response.data.detail) {
            errorMessage = `Server Error: ${err.response.data.detail}`;
          } else {
            errorMessage = `Server Error (${err.response.status}): Failed to process document`;
          }
        }
        
        setUploadStatus(errorMessage);
      }
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
              <UploadButton htmlFor="pdf-upload">Upload your document
                <HiddenInput
                  id="pdf-upload"
                  type="file"
                  accept="application/pdf"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                />
              </UploadButton>
              {uploadStatus && <div style={{ marginTop: '1rem', color: '#5c6a5a' }}>{uploadStatus}</div>}
            </>
          ) : (
            <>
              <PdfIframe src={pdfUrl} title="PDF Viewer" />
              {uploadStatus && <div style={{ position: 'absolute', bottom: 16, left: 16, color: '#5c6a5a', background: '#fff', padding: '0.5rem 1rem', borderRadius: 6 }}>{uploadStatus}</div>}
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