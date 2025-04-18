document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.flashcard');
  cards.forEach(card => {
    const frontBtn = card.querySelector('.front-btn');
    const backBtn  = card.querySelector('.back-btn');

    if (card.classList.contains('back-card')) {
      card.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
      return;
    }

    frontBtn && frontBtn.addEventListener('click', e => {
      e.stopPropagation();
      card.classList.add('zoomed');
    });

    backBtn && backBtn.addEventListener('click', e => {
      e.stopPropagation();
      card.classList.remove('zoomed');
    });
  });
});
