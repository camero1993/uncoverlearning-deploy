import React, { useState } from 'react';
import styled from 'styled-components';
import FlashcardContainer from './components/FlashcardContainer';
// import Chat from './components/Chat'; // Removed unused import
import ExpandedLogoCard from './components/ExpandedLogoCard';
import { FlashcardData } from './types';

// Import images
import logo from './assets/logo.png';
import magnusImage from './assets/team/magnus.jpg';
import henryImage from './assets/team/henry.jpg';
import tajImage from './assets/team/taj.jpg';

const AppContainer = styled.div`
  min-height: 100vh;
  background: #ffffff;
  overflow: hidden;
`;

const App: React.FC = () => {
  const [isChatExpanded, setIsChatExpanded] = useState(false);

  const handleExpandLogoCard = () => {
    setIsChatExpanded(true);
  };

  const handleCollapseLogoCard = () => {
    setIsChatExpanded(false);
  };

  const cards: FlashcardData[] = [
    {
      id: 'logo',
      isLogoCard: true,
      frontContent: (
        <>
          <img src={logo} alt="Uncover Learning" style={{ width: '200px', marginBottom: '2rem' }} />
          <h1 style={{ fontFamily: 'Fraunces, serif', fontSize: '2.5rem', color: '#5c6a5a', marginBottom: '1rem' }}>
            uncover learning
          </h1>
        </>
      ),
      backContent: null // No longer used, handled by ExpandedLogoCard
    },
    {
      id: 'problem',
      frontContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            the problem
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            College textbooks are expensive, hard to understand, and often go unused.
          </p>
          <div style={{ display: 'flex', gap: '2rem', marginTop: '2rem' }}>
            <div style={{ textAlign: 'center' }}>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '3rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>$400</h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1rem', color: '#000' }}>Average textbook cost</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '3rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>65%</h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1rem', color: '#000' }}>Students who skip buying</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '3rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>40%</h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1rem', color: '#000' }}>Textbooks never opened</p>
            </div>
          </div>
        </>
      ),
      backContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            the impact
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            This creates a significant barrier to learning and success for students.
          </p>
          <ul style={{ 
            fontFamily: 'Montserrat, sans-serif', 
            fontSize: '1.25rem', 
            color: '#000',
            listStyle: 'none',
            padding: 0,
            marginTop: '2rem'
          }}>
            <li style={{ marginBottom: '1rem' }}>• Students struggle to understand complex concepts</li>
            <li style={{ marginBottom: '1rem' }}>• Grades suffer due to lack of resources</li>
            <li style={{ marginBottom: '1rem' }}>• Financial burden affects mental health</li>
            <li style={{ marginBottom: '1rem' }}>• Learning becomes a source of stress</li>
          </ul>
        </>
      )
    },
    {
      id: 'solution',
      frontContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            the solution
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            We're building an AI-powered platform that makes textbooks more accessible and engaging.
          </p>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '1.5rem',
            marginTop: '2rem',
            maxWidth: '600px'
          }}>
            <div>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Chat with Your Textbook
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.25rem', color: '#000' }}>
                Ask questions and get instant, accurate answers from your textbook content.
              </p>
            </div>
            <div>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Personalized Learning
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.25rem', color: '#000' }}>
                Get explanations tailored to your learning style and pace.
              </p>
            </div>
            <div>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Affordable Access
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.25rem', color: '#000' }}>
                Pay a fraction of the cost of traditional textbooks.
              </p>
            </div>
          </div>
        </>
      ),
      backContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            how it works
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            Our platform uses advanced AI to make learning more interactive and effective.
          </p>
          <ol style={{ 
            fontFamily: 'Montserrat, sans-serif', 
            fontSize: '1.25rem', 
            color: '#000',
            paddingLeft: '1.5rem',
            marginTop: '2rem'
          }}>
            <li style={{ marginBottom: '1rem' }}>Upload your textbook or select from our library</li>
            <li style={{ marginBottom: '1rem' }}>Chat with the AI to understand concepts</li>
            <li style={{ marginBottom: '1rem' }}>Get personalized explanations and examples</li>
            <li style={{ marginBottom: '1rem' }}>Track your progress and understanding</li>
          </ol>
        </>
      )
    },
    {
      id: 'mission',
      frontContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            our mission
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            To make quality education accessible to everyone through technology.
          </p>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '1.5rem',
            marginTop: '2rem',
            maxWidth: '600px'
          }}>
            <div>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Democratize Learning
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.25rem', color: '#000' }}>
                Break down barriers to education through affordable technology.
              </p>
            </div>
            <div>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Enhance Understanding
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.25rem', color: '#000' }}>
                Make complex concepts accessible through AI-powered explanations.
              </p>
            </div>
            <div>
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Support Success
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.25rem', color: '#000' }}>
                Help students achieve their academic goals through better learning tools.
              </p>
            </div>
          </div>
        </>
      ),
      backContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            our values
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            We believe in creating a more equitable and effective learning environment.
          </p>
          <ul style={{ 
            fontFamily: 'Montserrat, sans-serif', 
            fontSize: '1.25rem', 
            color: '#000',
            listStyle: 'none',
            padding: 0,
            marginTop: '2rem'
          }}>
            <li style={{ marginBottom: '1rem' }}>• Accessibility for all students</li>
            <li style={{ marginBottom: '1rem' }}>• Quality education at affordable prices</li>
            <li style={{ marginBottom: '1rem' }}>• Innovation in learning technology</li>
            <li style={{ marginBottom: '1rem' }}>• Student success and well-being</li>
          </ul>
        </>
      )
    },
    {
      id: 'team',
      frontContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            our team
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            Meet the founders behind Uncover Learning.
          </p>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(3, 1fr)', 
            gap: '2rem',
            marginTop: '2rem',
            maxWidth: '1000px'
          }}>
            <div style={{ textAlign: 'center' }}>
              <img 
                src={tajImage}
                alt="Taj O'Malley" 
                style={{ 
                  width: '200px', 
                  height: '200px', 
                  borderRadius: '50%',
                  marginBottom: '1rem',
                  objectFit: 'cover'
                }} 
              />
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Taj O'Malley
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1rem', color: '#000' }}>
                Principal Co-Founder
              </p>
              <a 
                href="https://www.linkedin.com/in/taj-o-malley-94776a239/" 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ 
                  fontFamily: 'Montserrat, sans-serif',
                  fontSize: '1rem',
                  color: '#5c6a5a',
                  textDecoration: 'none',
                  display: 'inline-block',
                  marginTop: '0.5rem'
                }}
              >
                LinkedIn
              </a>
            </div>
            <div style={{ textAlign: 'center' }}>
              <img 
                src={henryImage}
                alt="Henry Dicks" 
                style={{ 
                  width: '200px', 
                  height: '200px', 
                  borderRadius: '50%',
                  marginBottom: '1rem',
                  objectFit: 'cover'
                }} 
              />
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Henry Dicks
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1rem', color: '#000' }}>
                Operational Co-Founder
              </p>
              <a 
                href="https://www.linkedin.com/in/henry-dicks/" 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ 
                  fontFamily: 'Montserrat, sans-serif',
                  fontSize: '1rem',
                  color: '#5c6a5a',
                  textDecoration: 'none',
                  display: 'inline-block',
                  marginTop: '0.5rem'
                }}
              >
                LinkedIn
              </a>
            </div>
            <div style={{ textAlign: 'center' }}>
              <img 
                src={magnusImage}
                alt="Magnus Graham" 
                style={{ 
                  width: '200px', 
                  height: '200px', 
                  borderRadius: '50%',
                  marginBottom: '1rem',
                  objectFit: 'cover'
                }} 
              />
              <h4 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.5rem', color: '#5c6a5a', marginBottom: '0.5rem' }}>
                Magnus Graham
              </h4>
              <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1rem', color: '#000' }}>
                Technical Co-Founder
        </p>
        <a
                href="https://www.linkedin.com/in/magnus-graham/" 
          target="_blank"
          rel="noopener noreferrer"
                style={{ 
                  fontFamily: 'Montserrat, sans-serif',
                  fontSize: '1rem',
                  color: '#5c6a5a',
                  textDecoration: 'none',
                  display: 'inline-block',
                  marginTop: '0.5rem'
                }}
              >
                LinkedIn
              </a>
            </div>
          </div>
        </>
      ),
      backContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            our story
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            We started Uncover Learning to solve the problems we faced as students.
          </p>
          <div style={{ 
            fontFamily: 'Montserrat, sans-serif', 
            fontSize: '1.25rem', 
            color: '#000',
            marginTop: '2rem',
            maxWidth: '600px'
          }}>
            <p style={{ marginBottom: '1rem' }}>
              As former students, we experienced firsthand the challenges of expensive textbooks and complex learning materials. We saw how these barriers affected not just our own education, but that of our peers as well.
            </p>
            <p style={{ marginBottom: '1rem' }}>
              With backgrounds in technology and education, we set out to create a solution that would make learning more accessible, engaging, and effective for everyone.
            </p>
            <p>
              Today, we're building the future of education technology, one that puts students first and makes quality learning accessible to all.
            </p>
          </div>
        </>
      )
    },
    {
      id: 'contact',
      frontContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            get in touch
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            Join us in revolutionizing education.
          </p>
          <form style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '1rem',
            marginTop: '2rem',
            maxWidth: '400px'
          }}>
            <input 
              type="email" 
              placeholder="Enter your email" 
              style={{ 
                fontFamily: 'Montserrat, sans-serif',
                fontSize: '1rem',
                padding: '0.75rem',
                border: '1px solid #5c6a5a',
                borderRadius: '6px',
                outline: 'none'
              }}
            />
            <button 
              type="submit"
              style={{ 
                fontFamily: 'Montserrat, sans-serif',
                fontSize: '1rem',
                padding: '0.75rem',
                backgroundColor: '#5c6a5a',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
            >
              Subscribe
            </button>
          </form>
        </>
      ),
      backContent: (
        <>
          <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '2rem', color: '#5c6a5a', marginBottom: '1.5rem' }}>
            stay updated
          </h3>
          <p style={{ fontFamily: 'Montserrat, sans-serif', fontSize: '1.5rem', color: '#000', marginBottom: '1.5rem' }}>
            Be the first to know about our launch and updates.
          </p>
          <div style={{ 
            fontFamily: 'Montserrat, sans-serif', 
            fontSize: '1.25rem', 
            color: '#000',
            marginTop: '2rem',
            maxWidth: '600px'
          }}>
            <p style={{ marginBottom: '1rem' }}>
              We're working hard to bring Uncover Learning to students everywhere. Subscribe to our newsletter to:
            </p>
            <ul style={{ 
              listStyle: 'none',
              padding: 0,
              marginBottom: '2rem'
            }}>
              <li style={{ marginBottom: '0.5rem' }}>• Get early access to our platform</li>
              <li style={{ marginBottom: '0.5rem' }}>• Receive exclusive launch offers</li>
              <li style={{ marginBottom: '0.5rem' }}>• Stay updated on our progress</li>
              <li style={{ marginBottom: '0.5rem' }}>• Join our community of learners</li>
            </ul>
            <p>
              Together, we can make education more accessible and effective for everyone.
            </p>
    </div>
        </>
      )
    }
  ];

  return (
    <AppContainer>
      {isChatExpanded ? (
        <ExpandedLogoCard 
          onCollapse={handleCollapseLogoCard} 
          logo={logo} 
          brandText="uncover learning" 
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
