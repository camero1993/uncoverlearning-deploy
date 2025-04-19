document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.flashcard');

  cards.forEach(card => {
    const cta      = card.querySelector('.cta-text');
    const frontBtn = card.querySelector('.front-btn');
    const trigger  = card.id === 'logo-card' ? cta : (cta || frontBtn);
    const backBtn  = card.querySelector('.back-btn');

    // Logo card: expand/collapse (no flip)
    if (card.id === 'logo-card') {
      if (trigger) {
        trigger.addEventListener('click', e => {
          e.stopPropagation();
          card.classList.add('expanded');
        });
      }
      if (backBtn) {
        backBtn.addEventListener('click', e => {
          e.stopPropagation();
          card.classList.remove('expanded');
          card.scrollIntoView({ behavior: 'smooth', inline: 'center' });
        });
      }
      return;
    }

    // Other cards: standard flip front/back
    if (trigger) {
      trigger.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.toggle('flipped');
      });
    }
    if (backBtn) {
      backBtn.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.remove('flipped');
      });
    }
  });

  //
  // Chatbot prompt handler
  //
  const sendBtn   = document.querySelector('#logo-card .send-btn');
  const chatInput = document.querySelector('#logo-card .chat-input');
  const chatWin   = document.querySelector('#logo-card .chat-window');

  if (sendBtn && chatInput && chatWin) {
    sendBtn.addEventListener('click', async () => {
      const query = chatInput.value.trim();
      if (!query) return;

      // 1) Render user bubble
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      userBubble.textContent = query;
      chatWin.appendChild(userBubble);
      chatWin.scrollTop = chatWin.scrollHeight;
      chatInput.value = '';

      // 2) Send to backend
      try {
        const res = await fetch('/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            query, 
            // if you need a file title, add it here, e.g.:
            // file_title: 'my_textbook.pdf' 
          }),
        });
        const data = await res.json();

        // 3) Render AI bubble
        const aiBubble = document.createElement('div');
        aiBubble.className = 'chat-bubble ai';
        aiBubble.textContent = data.answer ?? 'No answer.';
        chatWin.appendChild(aiBubble);
        chatWin.scrollTop = chatWin.scrollHeight;
      } catch (err) {
        console.error('API error:', err);
        const errBubble = document.createElement('div');
        errBubble.className = 'chat-bubble ai';
        errBubble.textContent = 'Error fetching answer.';
        chatWin.appendChild(errBubble);
        chatWin.scrollTop = chatWin.scrollHeight;
      }
    });
  }
});
