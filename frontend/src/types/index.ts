import { ReactNode } from 'react';

export interface FlashcardData {
  id: string;
  frontContent: ReactNode;
  backContent: ReactNode;
  isLogoCard?: boolean;
} 