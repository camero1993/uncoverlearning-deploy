import React, { useState } from 'react';
import styled from 'styled-components';
import FlashcardContainer from './components/FlashcardContainer/';
// import Chat from './components/Chat'; // Removed unused import
import NotebookChat from './components/NotebookChat/';
import { FlashcardData } from './types';

// Import images
import logo from './assets/logo.png';

const AppContainer = styled.div`
  min-height: 100vh;
  background: #ffffff;
  overflow: hidden;
`;

// Mode Selection Styled Components
const ModeSelectionContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
`;

const ModeTitle = styled.h2`
  font-family: 'Fraunces', serif;
  font-size: 2.5rem;
  color: #5c6a5a;
  margin-bottom: 2rem;
`;

const ModeButtonsContainer = styled.div`
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
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

const App: React.FC = () => {
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [selectedMode, setSelectedMode] = useState<'student' | 'professor' | null>(null);

  const handleExpandLogoCard = () => {
    if (selectedMode) {
      setIsChatExpanded(true);
    }
  };

  const handleCollapseLogoCard = () => {
    setIsChatExpanded(false);
    setSelectedMode(null);
  };

  const handleModeSelect = (mode: 'student' | 'professor') => {
    setSelectedMode(mode);
    setIsChatExpanded(true);
  };

  const cards: FlashcardData[] = [
    {
      id: 'logo',
      isLogoCard: true,
      frontContent: (
        <>
          <img 
            src={logo} 
            alt="Uncover Learning" 
            style={{ 
              width: 'min(60vw, 400px)', 
              maxWidth: '80%',
              height: 'auto',
              marginBottom: '2rem' 
            }} 
          />
        </>
      ),
      backContent: (
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
      )
    }
  ];

  return (
    <AppContainer>
      {isChatExpanded ? (
        <NotebookChat 
          onClose={handleCollapseLogoCard} 
          isOpen={isChatExpanded}
          initialMode={selectedMode} 
        />
      ) : (
        <FlashcardContainer 
          cards={cards}
          onExpandLogoCard={handleExpandLogoCard}
          onCollapseLogoCard={handleCollapseLogoCard}
        />
      )}
    </AppContainer>
  );
};

export default App;
