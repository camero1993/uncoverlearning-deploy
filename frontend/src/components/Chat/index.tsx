import React, { useState, useEffect, useRef, useCallback } from 'react';
import styled from 'styled-components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { queryDocument, getChatHistory, clearChatHistory, Message } from '../../services/api';

interface ChatProps {
  onClose: () => void;
  isOpen: boolean;
  fileTitle?: string | null;
  mode?: 'student' | 'professor' | null;
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
  position: relative;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid #eee;
  position: sticky;
  top: 0;
  background: #ffffff;
  border-radius: 12px 12px 0 0;
  z-index: 10;
`;

const HeaderContent = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 1rem;
`;

const Title = styled.h3`
  margin: 0;
  font-size: 1.25rem;
  color: #5c6a5a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
`;

const ButtonsContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
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
  margin-bottom: 80px; /* Add space for the fixed input container */
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
  background: #ffffff;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  border-radius: 0 0 12px 12px;
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

const Chat: React.FC<ChatProps> = ({ onClose, isOpen, fileTitle, mode = 'student' }) => {
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

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    try {
      // Add user message immediately
      setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

      // Get response from backend
      const response = await queryDocument(userMessage, fileTitle, mode);
      
      // Add assistant response
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

  const renderMessage = (message: Message, index: number) => {
    return (
      <MessageBubble key={index} $isUser={message.role === 'user'}>
        <ReactMarkdown 
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{
            p: ({node, ...props}) => <p style={{margin: 0}} {...props} />
          }}
        >
          {message.content}
        </ReactMarkdown>
      </MessageBubble>
    );
  };

  return (
    <Container $isOpen={isOpen}>
      <Header>
        <HeaderContent>
          <Title>{fileTitle || 'Chat'}</Title>
          <ButtonsContainer>
            <ClearButton onClick={handleClearChat}>Clear Chat</ClearButton>
            <CloseButton onClick={onClose}>×</CloseButton>
          </ButtonsContainer>
        </HeaderContent>
      </Header>
      <MessagesContainer ref={messagesEndRef}>
        {messages.map((message, index) => renderMessage(message, index))}
        {isLoading && <LoadingIndicator>Thinking...</LoadingIndicator>}
      </MessagesContainer>
      <InputContainer onSubmit={handleSubmit}>
        <Input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
        />
        <SendButton type="submit" disabled={!input.trim() || isLoading}>
          Send
        </SendButton>
      </InputContainer>
    </Container>
  );
};

export default Chat; 