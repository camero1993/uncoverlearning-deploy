import React, { useState, useEffect, useRef, useCallback } from 'react';
import styled from 'styled-components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { queryDocument, getChatHistory, clearChatHistory, Message } from '../../services/api';

interface ChatProps {
  onClose: () => void;
  isOpen: boolean;
  fileTitle?: string | null;
}

const Container = styled.div<{ $isOpen: boolean }>`
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  opacity: ${props => props.$isOpen ? 1 : 0};
  visibility: ${props => props.$isOpen ? 'visible' : 'hidden'};
  transition: opacity 0.3s ease, visibility 0.3s ease;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid #eee;
`;

const Title = styled.h3`
  margin: 0;
  font-size: 1.25rem;
  color: #5c6a5a;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  color: #5c6a5a;
  cursor: pointer;
  font-size: 1.5rem;
  padding: 0.5rem;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.7;
  }
`;

const MessagesContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const MessageBubble = styled.div<{ $isUser: boolean }>`
  max-width: 80%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: ${props => props.$isUser ? '#5c6a5a' : '#f5f5f5'};
  color: ${props => props.$isUser ? '#ffffff' : '#000000'};
  align-self: ${props => props.$isUser ? 'flex-end' : 'flex-start'};
  font-size: 0.875rem;
  line-height: 1.5;
`;

const InputContainer = styled.form`
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #eee;
`;

const Input = styled.input`
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.875rem;
  transition: border-color 0.2s;

  &:focus {
    outline: none;
    border-color: #5c6a5a;
  }
`;

const SendButton = styled.button`
  padding: 0.75rem 1.5rem;
  background: #5c6a5a;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background: #4a5649;
  }

  &:disabled {
    background: #ccc;
    cursor: not-allowed;
  }
`;

const ClearButton = styled.button`
  padding: 0.5rem 1rem;
  background: none;
  border: 1px solid #5c6a5a;
  color: #5c6a5a;
  border-radius: 6px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #5c6a5a;
    color: #fff;
  }
`;

const LoadingIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #f5f5f5;
  border-radius: 12px;
  align-self: flex-start;
  font-size: 0.875rem;
  color: #666;

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

const Chat: React.FC<ChatProps> = ({ isOpen, onClose, fileTitle }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadChatHistory = useCallback(async () => {
    try {
      console.log('loadChatHistory: Attempting to load chat history');
      const history = await getChatHistory();
      console.log('loadChatHistory: Successfully loaded history', history);
      
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
    } catch (error: any) {
      console.error('Failed to load chat history. Details:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Error response data:', error.response.data);
        console.error('Error response status:', error.response.status);
        console.error('Error response headers:', error.response.headers);
      } else if (error.request) {
        // The request was made but no response was received
        console.error('Error request:', error.request);
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Error message:', error.message);
      }
      
      // Handle error gracefully by showing a welcome message instead
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
    if (isOpen) {
      loadChatHistory();
    }
  }, [isOpen, loadChatHistory]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      console.log('Querying document with:', input.trim(), 'File title:', fileTitle);
      const response = await queryDocument(input.trim(), fileTitle || undefined);
      console.log('Query response:', response);
      setMessages(prev => [...prev, response]);
    } catch (error: any) {
      console.error('Failed to send message:', error);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = async () => {
    try {
      await clearChatHistory();
      let welcomeMessage = 'Chat history cleared. How can I help you now?';
      if (fileTitle) {
        welcomeMessage = `Chat history cleared. I'm ready to answer new questions about "${fileTitle}".`;
      }
      setMessages([{
        role: 'assistant',
        content: welcomeMessage
      }]);
    } catch (error) {
      console.error('Failed to clear chat history:', error);
    }
  };

  return (
    <Container $isOpen={isOpen} data-testid="chat-container">
      <Header>
        <Title>{fileTitle ? `Chat: ${fileTitle}` : 'Chat with Document'}</Title>
        <CloseButton onClick={onClose}>&times;</CloseButton>
      </Header>
      <MessagesContainer>
        {messages.map((msg, index) => (
          <MessageBubble key={index} $isUser={msg.role === 'user'}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </MessageBubble>
        ))}
        {isLoading && <LoadingIndicator>Thinking...</LoadingIndicator>}
        <div ref={messagesEndRef} />
      </MessagesContainer>
      <InputContainer onSubmit={handleSubmit}>
        <Input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={isLoading}
        />
        <SendButton type="submit" disabled={isLoading || !input.trim()}>
          Send
        </SendButton>
        <ClearButton type="button" onClick={handleClearChat} disabled={isLoading}>
          Clear Chat
        </ClearButton>
      </InputContainer>
    </Container>
  );
};

export default Chat; 