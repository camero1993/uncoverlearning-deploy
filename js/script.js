document.addEventListener('DOMContentLoaded', () => {
  const hero       = document.getElementById('hero');
  const heroBtn    = document.getElementById('hero-btn');
  const gridWrap   = document.getElementById('grid-wrapper');
  const cards      = document.querySelectorAll('.flashcard');

  // Hero flip → reveal grid view
  heroBtn.addEventListener('click', () => {
    hero.classList.add('flipped');
    setTimeout(() => {
      gridWrap.classList.add('visible');
    }, 800);
  });

  cards.forEach(card => {
    const frontBtn = card.querySelector('.front-btn');
    const backBtn  = card.querySelector('.back-btn');

    // Logo center card returns home
    if (card.classList.contains('back-card')) {
      card.addEventListener('click', () => {
        gridWrap.classList.remove('visible');
        hero.classList.remove('flipped');
      });
      return;
    }

    // Front button → directly zoom in (skip extra flip)
    frontBtn && frontBtn.addEventListener('click', e => {
      e.stopPropagation();
      card.classList.add('zoomed');
    });

    // Back arrow → exit zoom, return to grid
    backBtn && backBtn.addEventListener('click', e => {
      e.stopPropagation();
      card.classList.remove('zoomed');
    });
  });
});
