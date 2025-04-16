document.addEventListener("DOMContentLoaded", function() {
  // Elements
  const revealBtn = document.getElementById("reveal-btn");
  const heroSection = document.getElementById("hero");
  const gridSection = document.getElementById("grid");
  const cards = document.querySelectorAll(".flashcard");

  // Show grid view when hero CTA is clicked
  revealBtn.addEventListener("click", function() {
    heroSection.classList.add("hidden");
    gridSection.classList.remove("hidden");
  });

  // Add click handlers for flashcards
  cards.forEach(card => {
    card.addEventListener("click", function() {
      // If this is the middle (back) card, return to hero view
      if (card.classList.contains("back-card")) {
        gridSection.classList.add("hidden");
        heroSection.classList.remove("hidden");
        // Reset any flipped state on all cards
        cards.forEach(c => c.classList.remove("flipped"));
      } else {
        // Toggle flip animation to show content
        card.classList.toggle("flipped");
      }
    });
  });
});
