document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.flashcard');

  cards.forEach(card => {
    const frontBtn = card.querySelector('.front-btn');
    const backBtn  = card.querySelector('.back-btn');

    // Center card scrolls to intro
    if (card.classList.contains('back-card')) {
      card.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      return;
    }

    // Front button → zoom (no flip)
    if (frontBtn) {
      frontBtn.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.add('zoomed');
      });
    }

    // Back arrow → exit zoom
    if (backBtn) {
      backBtn.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.remove('zoomed');
      });
    }
  });
});
