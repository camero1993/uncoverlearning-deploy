document.addEventListener("DOMContentLoaded", function() {
  const flipBtn = document.getElementById("flip-btn");
  const hero = document.getElementById("hero");
  const grid = document.getElementById("grid");
  const flashcards = document.querySelectorAll(".flashcard");

  // When the flip button is clicked on the hero card, flip the hero to reveal grid
  flipBtn.addEventListener("click", function() {
    hero.classList.add("flipped");
    // Wait for the flip animation (0.8s) then hide hero and show grid
    setTimeout(() => {
      hero.classList.add("hidden");
      grid.classList.remove("hidden");
    }, 800);
  });

  // Add click behavior to each flashcard in the grid
  flashcards.forEach(card => {
    card.addEventListener("click", function() {
      // If the clicked card is the center (back) card, return to hero view
      if (card.classList.contains("back-card")) {
        grid.classList.add("hidden");
        hero.classList.remove("hidden");
        // Reverse the flip animation (remove flipped after a short delay)
        setTimeout(() => {
          hero.classList.remove("flipped");
        }, 50);
      } else {
        // Otherwise, toggle the flip on the card
        card.classList.toggle("flipped");
      }
    });
  });
});
