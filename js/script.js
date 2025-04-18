document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.flashcard');

  cards.forEach(card => {
    // Front trigger: either CTA text (logo) or front-btn
    const cta = card.querySelector('.cta-text');
    const btn = card.querySelector('.front-btn');
    const trigger = cta || btn;
    const back = card.querySelector('.back-btn');

    // Flip forward
    if (trigger) {
      trigger.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.toggle('flipped');
      });
    }

    // Flip back
    if (back) {
      back.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.remove('flipped');
      });
    }
  });
});
