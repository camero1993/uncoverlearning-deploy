import React, { useState, useEffect, useRef, useCallback } from 'react';
import styled from 'styled-components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { queryDocument, getChatHistory, uploadDocument, Message } from '../../services/api';
import logo from '../../assets/logo.png';

interface NotebookChatProps {
  onClose: () => void;
  isOpen: boolean;
  fileTitle?: string | null;
  initialMode?: 'student' | 'professor' | null;
}

// Floating Window System
const FloatingWindow = styled.div<{ $x: number; $y: number; $width: number; $height: number }>`
  position: absolute;
  left: ${props => props.$x}px;
  top: ${props => props.$y}px;
  width: ${props => props.$width}px;
  height: ${props => props.$height}px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 300px;
  min-height: 200px;
  max-width: 800px;
  max-height: 600px;
`;

const WindowHeader = styled.div`
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: move;
  user-select: none;
`;

const WindowTitle = styled.h3`
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
`;

const WindowCloseButton = styled.button`
  width: 20px;
  height: 20px;
  border: none;
  background: none;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &:hover {
    background: #f3f4f6;
    color: #6b7280;
  }
`;

const WindowBody = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

// Tab Dock
const TabDock = styled.div`
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 48px;
  background: #ffffff;
  border-top: 1px solid #e5e7eb;
  display: flex;
  z-index: 50;
`;

const Tab = styled.button<{ $isActive: boolean }>`
  flex: 1;
  height: 100%;
  border: none;
  background: ${props => props.$isActive ? '#f3f4f6' : '#ffffff'};
  color: #374151;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-right: 1px solid #e5e7eb;
  
  &:hover {
    background: #f9fafb;
  }
  
  &:last-child {
    border-right: none;
  }
`;

// Mode Selection Styled Components
const ModeOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 2000;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s;

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
`;

const ModeSelectionContainer = styled.div`
  text-align: center;
`;

const ModeTitle = styled.h2`
  font-family: 'Fraunces', serif;
  font-size: 2.5rem;
  color: #5c6a5a;
  margin-bottom: 2rem;
  font-weight: 400;
`;

const ModeButtonsContainer = styled.div`
  display: flex;
  gap: 2rem;
`;

const ModeButton = styled.button`
  padding: 1rem 2rem;
  background: #5c6a5a;
  color: white;
  border: none;
  border-radius: 8px;
  font-family: 'Montserrat', sans-serif;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #4a5649;
    transform: translateY(-2px);
  }
`;

// Main Layout Styled Components
const NotebookContainer = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 2000;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
`;

const Header = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
  min-height: 64px;
`;

const HeaderLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
`;

const BackButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: none;
  border: none;
  border-radius: 8px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: #f3f4f6;
    color: #374151;
  }
`;

const Logo = styled.img`
  height: 32px;
  width: auto;
`;

const CourseTitle = styled.h1`
  font-size: 20px;
  font-weight: 500;
  color: #374151;
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
`;

const HeaderRight = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
`;

const SignInText = styled.span`
  font-size: 14px;
  color: #6b7280;
  font-weight: 400;
`;

const ProfileIcon = styled.div`
  width: 32px;
  height: 32px;
  background: #3b82f6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: 500;
`;

const MainContent = styled.div`
  flex: 1;
  position: relative;
  height: calc(100vh - 64px);
`;

// Sources Panel (Full Screen)
const SourcesPanel = styled.div`
  width: 100%;
  height: calc(100% - 48px);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  position: relative;
`;

const EmptyState = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 24px;
  color: #6b7280;
`;

const EmptyIcon = styled.div`
  width: 64px;
  height: 64px;
  background: #f3f4f6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
`;

const EmptyTitle = styled.p`
  font-size: 14px;
  color: #374151;
  margin: 0 0 8px 0;
  font-weight: 500;
`;

const EmptyDescription = styled.p`
  font-size: 12px;
  color: #9ca3af;
  margin: 0 0 24px 0;
  line-height: 1.5;
  max-width: 240px;
`;

const UploadButton = styled.label`
  display: inline-block;
  padding: 12px 24px;
  background: #5c6a5a;
  color: #ffffff;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background: #4a5649;
  }
`;

const HiddenInput = styled.input`
  display: none;
`;

const UploadArea = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
`;

const StatusContainer = styled.div`
  margin-top: 12px;
  text-align: center;
  font-size: 12px;
  color: #5c6a5a;
  max-width: 280px;
`;

const ErrorContainer = styled.div`
  margin-top: 12px;
  text-align: center;
  font-size: 12px;
  color: #dc2626;
  max-width: 280px;
`;

const FileSizeNote = styled.div`
  margin-top: 8px;
  font-size: 11px;
  color: #9ca3af;
`;

const PdfViewer = styled.iframe<{ $isDragging: boolean }>`
  width: 100%;
  height: 100%;
  border: none;
  background: #ffffff;
  pointer-events: ${props => props.$isDragging ? 'none' : 'auto'};
`;

// Drag overlay to prevent iframe interference
const DragOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 999;
  background: transparent;
  cursor: move;
`;

// Custom resize handle
const ResizeHandle = styled.div`
  position: absolute;
  bottom: 0;
  right: 0;
  width: 16px;
  height: 16px;
  background: linear-gradient(-45deg, transparent 30%, #d1d5db 30%, #d1d5db 70%, transparent 70%);
  cursor: nw-resize;
  border-bottom-right-radius: 8px;
  
  &:hover {
    background: linear-gradient(-45deg, transparent 30%, #9ca3af 30%, #9ca3af 70%, transparent 70%);
  }
`;

const PdfContainer = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  position: relative;
`;

const FileInfo = styled.div`
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  font-size: 12px;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const FileName = styled.span`
  font-weight: 500;
  color: #374151;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const RemoveButton = styled.button`
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: color 0.2s;

  &:hover {
    color: #6b7280;
  }
`;

const NoteEditor = styled.div`
  margin-top: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
`;

const NoteTextArea = styled.textarea`
  width: 100%;
  min-height: 150px;
  padding: 16px;
  border: none;
  outline: none;
  resize: vertical;
  font-size: 14px;
  line-height: 1.5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  
  &::placeholder {
    color: #9ca3af;
  }
`;



const ChatMessages = styled.div`
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 280px;
`;

const MessageContainer = styled.div<{ $isUser: boolean }>`
  display: flex;
  justify-content: ${props => props.$isUser ? 'flex-end' : 'flex-start'};
`;

const MessageBubble = styled.div<{ $isUser: boolean }>`
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  background: ${props => props.$isUser ? '#5c6a5a' : '#f3f4f6'};
  color: ${props => props.$isUser ? '#ffffff' : '#374151'};
  font-size: 14px;
  line-height: 1.5;
`;

const LoadingIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f3f4f6;
  border-radius: 12px;
  font-size: 14px;
  color: #6b7280;

  &::after {
    content: '';
    width: 12px;
    height: 12px;
    border: 2px solid #5c6a5a;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

const ChatInputContainer = styled.div`
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
`;

const InputForm = styled.form`
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
`;

const ChatInput = styled.input`
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;

  &:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  &:disabled {
    background: #f9fafb;
    color: #9ca3af;
  }
`;

const SendButton = styled.button`
  padding: 12px;
  background: #3b82f6;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #d1d5db;
    cursor: not-allowed;
  }
`;

const SourceCount = styled.div`
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
`;

// Notes styling for floating window
const NotesContent = styled.div`
  flex: 1;
  padding: 16px 20px;
`;

const AddNoteButton = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 16px;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;

  &:hover {
    border-color: #9ca3af;
    color: #374151;
  }
`;



// Constants for file upload
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB in bytes
const MAX_FILE_SIZE_MB = MAX_FILE_SIZE / (1024 * 1024);

const NotebookChat: React.FC<NotebookChatProps> = ({ onClose, isOpen, fileTitle: initialFileTitle, initialMode = null }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<'student' | 'professor' | null>(initialMode);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [fileTitle, setFileTitle] = useState<string | null>(initialFileTitle || null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isAddingNote, setIsAddingNote] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  
  // Window state - both start closed
  const [windows, setWindows] = useState({
    chat: { 
      isOpen: false, 
      position: { x: 50, y: 50 },
      size: { width: 400, height: 500 }
    },
    notes: { 
      isOpen: false, 
      position: { x: 500, y: 50 },
      size: { width: 400, height: 500 }
    }
  });
  const [dragState, setDragState] = useState<{
    isDragging: boolean;
    window: 'chat' | 'notes' | null;
    offset: { x: number; y: number };
  }>({ isDragging: false, window: null, offset: { x: 0, y: 0 } });
  const [resizeState, setResizeState] = useState<{
    isResizing: boolean;
    window: 'chat' | 'notes' | null;
    startPos: { x: number; y: number };
    startSize: { width: number; height: number };
  }>({ isResizing: false, window: null, startPos: { x: 0, y: 0 }, startSize: { width: 0, height: 0 } });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadChatHistory = useCallback(async () => {
    try {
      const history = await getChatHistory();
      
      if (history.length === 0) {
        let welcomeMessage = 'Welcome! How can I help you with your document today?';
        if (fileTitle) {
          welcomeMessage = `Welcome! I'm ready to answer questions about "${fileTitle}".`;
        }
        setMessages([{ 
          role: 'assistant', 
          content: welcomeMessage
        }]);
      } else {
        setMessages(history);
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
      let welcomeMessage = 'Welcome! How can I help you with your document today?';
      if (fileTitle) {
        welcomeMessage = `Welcome! I'm ready to answer questions about "${fileTitle}".`;
      }
      setMessages([{ 
        role: 'assistant', 
        content: welcomeMessage
      }]);
    }
  }, [fileTitle]);

  useEffect(() => {
    if (isOpen && mode) {
      loadChatHistory();
    }
  }, [isOpen, mode, loadChatHistory]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    try {
      setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
      const response = await queryDocument(userMessage, fileTitle, mode);
      setMessages(prev => [...prev, response]);
    } catch (error) {
      console.error('Error querying document:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleModeSelect = (selectedMode: 'student' | 'professor') => {
    setMode(selectedMode);
  };

  const getModePrefix = () => {
    if (mode === 'student') return 'Studying: ';
    if (mode === 'professor') return 'Planning: ';
    return '';
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    // Reset states
    setUploadError(null);
    setUploadStatus(null);
    
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
    
    // Validate file size (limit to 50MB for this component's initial check)
    if (file.size > MAX_FILE_SIZE) {
      setUploadError(`File is too large. Maximum size is ${MAX_FILE_SIZE_MB}MB. Your file is ${(file.size / (1024 * 1024)).toFixed(2)}MB.`);
      return;
    }
    
    // Create object URL for preview
    const url = URL.createObjectURL(file);
    setPdfUrl(url);
    setUploadStatus('Uploading document... This may take a moment.');
    setIsUploading(true);
    
    try {
      console.log('Uploading document:', file.name, 'Size:', (file.size / 1024 / 1024).toFixed(2) + 'MB');
      const result = await uploadDocument(file, file.name);
      console.log('Upload result:', result);
      
      setFileTitle(file.name);
      setUploadStatus('Document uploaded and processing started! You can now ask questions about it.');
      setIsUploading(false);
    } catch (err: any) {
      console.error('Upload error:', err);
      setIsUploading(false);
      
      let errorMessage = 'Failed to upload document: Unknown error.';
      
      if (err.response) {
        console.error('Server response:', err.response.data);
        if (err.response.status === 413) {
          errorMessage = `File is too large for the server to process directly. Chunked upload might be attempted or a smaller file (under 10MB for direct, or check chunking limits).`;
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
        errorMessage = 'No response from server. Please check your internet connection.';
      } else if (err.message && err.message.startsWith('Failed to upload chunk')) {
        errorMessage = err.message;
      } else if (err.message) {
        errorMessage = `${err.message}`;
      }
      
      setUploadError(errorMessage);
      setUploadStatus(null);
    }
  };

  const handleRemoveFile = () => {
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
    }
    setPdfUrl(null);
    setFileTitle(null);
    setUploadStatus(null);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAddNote = () => {
    setIsAddingNote(!isAddingNote);
  };

  // Window management
  const openWindow = (windowType: 'chat' | 'notes') => {
    setWindows(prev => ({
      ...prev,
      [windowType]: { ...prev[windowType], isOpen: true }
    }));
  };

  const closeWindow = (windowType: 'chat' | 'notes') => {
    setWindows(prev => ({
      ...prev,
      [windowType]: { ...prev[windowType], isOpen: false }
    }));
  };

  const handleMouseDown = (e: React.MouseEvent, windowType: 'chat' | 'notes') => {
    const rect = (e.currentTarget.parentElement as HTMLElement).getBoundingClientRect();
    setIsDragging(true);
    setDragState({
      isDragging: true,
      window: windowType,
      offset: {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      }
    });
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (dragState.isDragging && dragState.window) {
      setWindows(prev => ({
        ...prev,
        [dragState.window!]: {
          ...prev[dragState.window!],
          position: {
            x: Math.max(0, e.clientX - dragState.offset.x),
            y: Math.max(0, e.clientY - dragState.offset.y)
          }
        }
      }));
    }
  }, [dragState]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragState({ isDragging: false, window: null, offset: { x: 0, y: 0 } });
    setResizeState({ isResizing: false, window: null, startPos: { x: 0, y: 0 }, startSize: { width: 0, height: 0 } });
  }, []);

  // Resize handlers
  const handleResizeStart = (e: React.MouseEvent, windowType: 'chat' | 'notes') => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true); // Prevent PDF interference during resize
    setResizeState({
      isResizing: true,
      window: windowType,
      startPos: { x: e.clientX, y: e.clientY },
      startSize: { 
        width: windows[windowType].size.width, 
        height: windows[windowType].size.height 
      }
    });
  };

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (resizeState.isResizing && resizeState.window) {
      const deltaX = e.clientX - resizeState.startPos.x;
      const deltaY = e.clientY - resizeState.startPos.y;
      
      const newWidth = Math.max(300, Math.min(800, resizeState.startSize.width + deltaX));
      const newHeight = Math.max(200, Math.min(600, resizeState.startSize.height + deltaY));
      
      setWindows(prev => ({
        ...prev,
        [resizeState.window!]: {
          ...prev[resizeState.window!],
          size: { width: newWidth, height: newHeight }
        }
      }));
    }
  }, [resizeState]);

  const handleResizeEnd = useCallback(() => {
    setIsDragging(false);
    setResizeState({ isResizing: false, window: null, startPos: { x: 0, y: 0 }, startSize: { width: 0, height: 0 } });
  }, []);

  useEffect(() => {
    if (dragState.isDragging || resizeState.isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mousemove', handleResizeMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.addEventListener('mouseup', handleResizeEnd);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mousemove', handleResizeMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.removeEventListener('mouseup', handleResizeEnd);
      };
    }
  }, [dragState.isDragging, resizeState.isResizing, handleMouseMove, handleResizeMove, handleMouseUp, handleResizeEnd]);

  if (!isOpen) return null;

  // Mode selection screen
  if (!mode) {
    return (
      <ModeOverlay>
        <ModeSelectionContainer>
          <ModeTitle>I am a...</ModeTitle>
          <ModeButtonsContainer>
            <ModeButton onClick={() => handleModeSelect('student')}>
              Student
            </ModeButton>
            <ModeButton onClick={() => handleModeSelect('professor')}>
              Professor
            </ModeButton>
          </ModeButtonsContainer>
        </ModeSelectionContainer>
      </ModeOverlay>
    );
  }

  // Main NotebookLM layout
  return (
    <NotebookContainer>
      <Header>
        <HeaderLeft>
          <BackButton onClick={onClose} title="Back to flashcard deck">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </BackButton>
          <Logo src={logo} alt="Uncover Learning" />
          <CourseTitle>
            {getModePrefix()}Course X [Lesson 1]
          </CourseTitle>
        </HeaderLeft>
        <HeaderRight>
          <SignInText>Sign-in</SignInText>
          <ProfileIcon>U</ProfileIcon>
        </HeaderRight>
      </Header>

      <MainContent>
        {/* Full-Screen Sources Panel */}
        <SourcesPanel>
          {!pdfUrl ? (
            <EmptyState>
              <EmptyIcon>
                <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </EmptyIcon>
              <EmptyTitle>Saved sources will appear here</EmptyTitle>
              <EmptyDescription>
                Click Add source above to add PDFs, websites, text, videos, or audio files. Or import a file directly from Google Drive.
              </EmptyDescription>
              <UploadArea>
                <UploadButton htmlFor="pdf-upload" style={{ opacity: isUploading ? 0.7 : 1, pointerEvents: isUploading ? 'none' : 'auto' }}>
                  {isUploading ? 'Uploading...' : 'Upload a source'}
                  <HiddenInput
                    id="pdf-upload"
                    type="file"
                    accept="application/pdf"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    disabled={isUploading}
                  />
                </UploadButton>
                {uploadError && <ErrorContainer>{uploadError}</ErrorContainer>}
                {uploadStatus && <StatusContainer>{uploadStatus}</StatusContainer>}
                <FileSizeNote>Maximum file size: {MAX_FILE_SIZE_MB}MB</FileSizeNote>
              </UploadArea>
            </EmptyState>
          ) : (
            <PdfContainer>
              <FileInfo>
                <FileName>{fileTitle}</FileName>
                <RemoveButton onClick={handleRemoveFile} title="Remove file">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </RemoveButton>
              </FileInfo>
              <PdfViewer src={pdfUrl} title="PDF Viewer" $isDragging={isDragging} />
              {uploadError && (
                <div style={{ 
                  position: 'absolute', 
                  bottom: '16px', 
                  left: '16px', 
                  color: '#dc2626', 
                  background: '#ffffff', 
                  padding: '8px 12px', 
                  borderRadius: '6px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                  fontSize: '12px'
                }}>
                  {uploadError}
                </div>
              )}
              {uploadStatus && (
                <div style={{ 
                  position: 'absolute', 
                  bottom: '16px', 
                  left: '16px', 
                  color: '#5c6a5a', 
                  background: '#ffffff', 
                  padding: '8px 12px', 
                  borderRadius: '6px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                  fontSize: '12px'
                }}>
                  {uploadStatus}
                </div>
              )}
            </PdfContainer>
          )}
        </SourcesPanel>

        {/* Tab Dock */}
        <TabDock>
          <Tab 
            $isActive={windows.chat.isOpen}
            onClick={() => openWindow('chat')}
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Chat
          </Tab>
          <Tab 
            $isActive={windows.notes.isOpen}
            onClick={() => openWindow('notes')}
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Notes
          </Tab>
        </TabDock>

        {/* Floating Chat Window */}
        {windows.chat.isOpen && (
          <FloatingWindow 
            $x={windows.chat.position.x} 
            $y={windows.chat.position.y}
            $width={windows.chat.size.width}
            $height={windows.chat.size.height}
          >
            <WindowHeader onMouseDown={(e) => handleMouseDown(e, 'chat')}>
              <WindowTitle>Chat</WindowTitle>
              <WindowCloseButton 
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => {
                  e.stopPropagation();
                  closeWindow('chat');
                }}
              >
                <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </WindowCloseButton>
            </WindowHeader>
            
            <WindowBody>
              <ChatMessages>
                {messages.map((msg, index) => (
                  <MessageContainer key={index} $isUser={msg.role === 'user'}>
                    <MessageBubble $isUser={msg.role === 'user'}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </MessageBubble>
                  </MessageContainer>
                ))}
                {isLoading && (
                  <MessageContainer $isUser={false}>
                    <LoadingIndicator>Thinking...</LoadingIndicator>
                  </MessageContainer>
                )}
                <div ref={messagesEndRef} />
              </ChatMessages>

              <ChatInputContainer>
                <InputForm onSubmit={handleSubmit}>
                  <ChatInput
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={fileTitle ? "Ask a question about your document..." : "Upload a source to get started"}
                    disabled={isLoading}
                  />
                  <SendButton type="submit" disabled={isLoading || !input.trim()}>
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </SendButton>
                </InputForm>
                <SourceCount>{fileTitle ? '1 source' : '0 sources'}</SourceCount>
              </ChatInputContainer>
            </WindowBody>
            <ResizeHandle onMouseDown={(e) => handleResizeStart(e, 'chat')} />
          </FloatingWindow>
        )}

        {/* Floating Notes Window */}
        {windows.notes.isOpen && (
          <FloatingWindow 
            $x={windows.notes.position.x} 
            $y={windows.notes.position.y}
            $width={windows.notes.size.width}
            $height={windows.notes.size.height}
          >
            <WindowHeader onMouseDown={(e) => handleMouseDown(e, 'notes')}>
              <WindowTitle>Notes</WindowTitle>
              <WindowCloseButton 
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => {
                  e.stopPropagation();
                  closeWindow('notes');
                }}
              >
                <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </WindowCloseButton>
            </WindowHeader>
            
            <WindowBody>
              <NotesContent>
                <AddNoteButton onClick={handleAddNote}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  {isAddingNote ? 'Cancel' : 'Add note'}
                </AddNoteButton>

                {isAddingNote && (
                  <NoteEditor>
                    <NoteTextArea
                      placeholder="Start typing your note..."
                      autoFocus
                    />
                  </NoteEditor>
                )}
              </NotesContent>
            </WindowBody>
            <ResizeHandle onMouseDown={(e) => handleResizeStart(e, 'notes')} />
          </FloatingWindow>
        )}

        {/* Drag Overlay - prevents iframe interference during drag */}
        {isDragging && <DragOverlay />}
      </MainContent>
    </NotebookContainer>
  );
};

export default NotebookChat; 