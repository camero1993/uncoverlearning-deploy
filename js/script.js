document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.flashcard');

  cards.forEach(card => {
    const cta = card.querySelector('.cta-text');
    const btn = card.querySelector('.front-btn');
    const trigger = cta || btn;
    const back = card.querySelector('.back-btn');

    if (trigger) {
      trigger.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.toggle('flipped');
      });
    }

    if (back) {
      back.addEventListener('click', e => {
        e.stopPropagation();
        card.classList.remove('flipped');
      });
    }
  });

  // Add API query handler for asking questions
  const form = document.getElementById("ask-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const query = document.getElementById("query").value;
      const fileTitle = document.getElementById("fileTitle").value;

      try {
        const res = await fetch("http://localhost:8000/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, file_title: fileTitle }),
        });

        const data = await res.json();
        document.getElementById("response").innerText = data.answer;
      } catch (error) {
        document.getElementById("response").innerText = "❌ Error fetching answer.";
        console.error("API error:", error);
      }
    });
  }
});
