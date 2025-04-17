document.addEventListener('DOMContentLoaded', () => {
  const hero       = document.getElementById('hero');
  const heroBtn    = document.getElementById('hero-btn');
  const gridWrap   = document.getElementById('grid-wrapper');
  const cards      = document.querySelectorAll('.flashcard');

  // Hero flip → reveal grid
  heroBtn.addEventListener('click', () => {
    hero.classList.add('flipped');
    setTimeout(() => {
      gridWrap.classList.add('visible');
    }, 800);
  });

  // Flashcard click logic
  cards.forEach(card => {
    const frontBtn = card.querySelector('.front-btn');
    const backBtn  = card.querySelector('.back-btn');

    // Center card returns to hero
    if (card.classList.contains('back-card')) {
      card.addEventListener('click', () => {
        gridWrap.classList.remove('visible');
        hero.classList.remove('flipped');
      });
      return;
    }

    // Front → Back flip
    frontBtn && frontBtn.addEventListener('click', e => {
      e.stopPropagation();
      card.classList.add('flipped');
    });

    // Back → Front flip
    backBtn && backBtn.addEventListener('click', e => {
      e.stopPropagation();
      card.classList.remove('flipped');
    });
  });
});
