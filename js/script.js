document.addEventListener('DOMContentLoaded', () => {
  const hero = document.getElementById('hero');
  const heroBtn = document.getElementById('hero-btn');
  const grid = document.getElementById('grid');
  const cards = document.querySelectorAll('.flashcard');

  // Hero flip → show grid
  heroBtn.addEventListener('click', () => {
    hero.classList.add('flipped');
    setTimeout(() => {
      hero.classList.add('hidden');
      grid.classList.remove('hidden');
    }, 800);
  });

  // Card click behaviors
  cards.forEach(card => {
    const inner = card.querySelector('.card-inner');
    const frontBtn = card.querySelector('.front-btn');
    const backBtn = card.querySelector('.back-btn');

    // Zoom in on front-face click area (excluding center card)
    if (!card.classList.contains('back-card')) {
      card.addEventListener('click', e => {
        if (e.target === frontBtn) return;
        // zoom: make this card full screen
        cards.forEach(c => c.classList.add('hidden'));
        card.classList.remove('hidden');
        card.classList.add('zoomed');
      });
    }

    // Front→Back flip
    if (frontBtn) {
      frontBtn.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.add('flipped');
      });
    }

    // Back→Front flip
    if (backBtn) {
      backBtn.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.remove('flipped');
      });
    }

    // Center card returns to hero
    if (card.classList.contains('back-card')) {
      card.addEventListener('click', () => {
        grid.classList.add('hidden');
        hero.classList.remove('hidden');
        setTimeout(() => hero.classList.remove('flipped'), 50);
      });
    }
  });
});
