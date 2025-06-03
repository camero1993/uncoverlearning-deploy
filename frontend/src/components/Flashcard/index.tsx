import React, { useState } from 'react';
import styled from 'styled-components';

interface FlashcardProps {
  id: string;
  frontContent: React.ReactNode;
  backContent: React.ReactNode;
  isLogoCard?: boolean;
  onExpand?: () => void;
  onCollapse?: () => void;
}

const Card = styled.div<{ $isFlipped: boolean; $isExpanded: boolean; $isLogoCard: boolean }>`
  flex: 0 0 70vw;
  height: 80vh;
  margin: 0 3vw;
  scroll-snap-align: center;
  perspective: 1000px;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  ${props => props.$isLogoCard && props.$isExpanded && `
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    margin: 0;
    flex: none;
    scroll-snap-align: none;
    z-index: 1000;
    overflow: hidden;
  `}
`;

const CardInner = styled.div<{ $isFlipped: boolean; $isLogoCard: boolean }>`
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  transform: ${props => props.$isFlipped ? 'rotateX(180deg)' : 'rotateX(0)'};
  cursor: ${props => props.$isLogoCard ? 'pointer' : 'default'};

  ${props => props.$isLogoCard && props.$isFlipped && `
    transition: none;
  `}
`;

const CardFace = styled.div<{ $isBack?: boolean }>`
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  padding: 2rem;
  transform: ${props => props.$isBack ? 'rotateX(180deg)' : 'rotateX(0)'};
  overflow: hidden;

  ${props => !props.$isBack && `
    text-align: center;
  `}
`;

const ContentWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  max-width: 800px;
  margin: 0 auto;
`;

const MissionText = styled.h1`
  font-family: 'Fraunces', serif;
  font-weight: 600;
  color: #5c6a5a;
  text-transform: lowercase;
  font-size: 2.5rem;
  margin-bottom: 1.5rem;
  line-height: 1.2;
  max-width: 600px;
`;

const CTAText = styled.p`
  font-family: 'Montserrat', sans-serif;
  font-weight: 400;
  font-size: 1.25rem;
  color: #000;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease;
  margin-top: 1rem;

  &:hover {
    transform: translateY(-4px);
    opacity: 0.8;
  }
`;

const Button = styled.button`
  font-family: 'Montserrat', sans-serif;
  font-weight: 400;
  background: #5c6a5a;
  color: #fff;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  margin-top: 2rem;
  font-size: 1rem;

  &:hover {
    background-color: #4a5649;
  }
`;

const BackButton = styled(Button)`
  position: absolute;
  top: 1rem;
  left: 1rem;
  padding: 0.5rem 1rem;
  font-size: 1.5rem;
  background: none;
  color: #5c6a5a;
  margin: 0;
  
  &:hover {
    background: rgba(92, 106, 90, 0.1);
  }
`;

const Flashcard: React.FC<FlashcardProps> = ({
  id,
  frontContent,
  backContent,
  isLogoCard = false,
  onExpand,
  onCollapse
}) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleFlip = (e: React.MouseEvent) => {
    if (!isLogoCard) {
      e.stopPropagation();
      setIsFlipped(!isFlipped);
    }
  };

  const handleExpand = (e: React.MouseEvent) => {
    if (isLogoCard) {
      e.stopPropagation();
      setIsExpanded(true);
      setIsFlipped(true);
      onExpand?.();
    }
  };

  const handleCollapse = (e: React.MouseEvent) => {
    if (isLogoCard) {
      e.stopPropagation();
      setIsExpanded(false);
      setIsFlipped(false);
      onCollapse?.();
    }
  };

  return (
    <Card 
      $isFlipped={isFlipped} 
      $isExpanded={isExpanded}
      $isLogoCard={isLogoCard}
    >
      <CardInner 
        $isFlipped={isFlipped}
        $isLogoCard={isLogoCard}
        onClick={isLogoCard ? handleExpand : handleFlip}
      >
        <CardFace>
          <ContentWrapper>
            {frontContent}
            {id === 'problem' && !isLogoCard && (
              <Button onClick={handleFlip}>
                see how
              </Button>
            )}
            {isLogoCard && (
              <>
                <MissionText>engineer equitable education everywhere</MissionText>
                <CTAText onClick={handleExpand}>
                  click to uncover our textbook tutor prototype
                </CTAText>
              </>
            )}
          </ContentWrapper>
        </CardFace>
        <CardFace $isBack>
          <BackButton onClick={isLogoCard ? handleCollapse : handleFlip}>
            &larr;
          </BackButton>
          <ContentWrapper>
            {backContent}
          </ContentWrapper>
        </CardFace>
      </CardInner>
    </Card>
  );
};

export default Flashcard; 