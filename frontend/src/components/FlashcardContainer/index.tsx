import React from 'react';
import styled from 'styled-components';
import Flashcard from '../Flashcard';
import { FlashcardData } from '../../types';

const Container = styled.div`
  display: flex;
  align-items: center;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  height: 100vh;
  padding: 0 12vw;
  background: #ffffff;
  scrollbar-width: none;
  -ms-overflow-style: none;

  &::-webkit-scrollbar {
    display: none;
  }

  > * {
    scroll-snap-align: center;
  }
`;

interface FlashcardContainerProps {
  cards: FlashcardData[];
  onExpandLogoCard: () => void;
  onCollapseLogoCard: () => void;
}

const FlashcardContainer: React.FC<FlashcardContainerProps> = ({
  cards,
  onExpandLogoCard,
  onCollapseLogoCard
}) => {
  return (
    <Container>
      {cards.map((card, index) => (
        <Flashcard
          key={index}
          {...card}
          onExpand={card.isLogoCard ? onExpandLogoCard : undefined}
          onCollapse={card.isLogoCard ? onCollapseLogoCard : undefined}
        />
      ))}
    </Container>
  );
};

export default FlashcardContainer; 