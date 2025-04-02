document.addEventListener("DOMContentLoaded", function() {
  // Elements
  const revealButton = document.getElementById("reveal-button");
  const introSection = document.getElementById("intro");
  const cardGrid = document.getElementById("card-grid");
  const modal = document.getElementById("card-modal");
  const modalBody = document.getElementById("modal-body");
  const closeModal = document.getElementById("close-modal");

  // Show grid when intro is revealed
  revealButton.addEventListener("click", function() {
    introSection.classList.add("hidden");
    cardGrid.classList.remove("hidden");
  });

  // Detailed content for each flashcard
  const cardContent = {
    problem: `
      <h2>College textbooks are over-priced and ineffective</h2>
      <p><strong>$1,212</strong> average cost of books and supplies for college students, 2023 (NCES)</p>
      <p><strong>56%</strong> of local students reported not using purchased textbooks</p>
      <p><strong>65%</strong> of students nationwide avoided purchasing a required book because of high prices during the 2020 school year (U.S PIRG)</p>
      <h3>Problem Persistence</h3>
      <p>The textbook market failures continue to hold students back because textbook publishers service professors, not students. Professors are ultimately the market decision makers, as they select the materials that students are required to pay for to "succeed" in their classes. They often make these selections without price, or quality in mind. This leads to expensive textbooks that fail to adequately support student studying. The state of this industry is especially tragic in our current age of information, where it has never been easier or cheaper to learn practically. Why can't our education system make the same adjustment?</p>
    `,
    mission: `
      <h2>To Make Growth-Generating, Personalized Learning Accessible to All</h2>
      <h3>Mission Based Initiatives:</h3>
      <ul>
        <li>Incentivizing college professors to use free and open learning materials as course books provided by Uncover Learning through learning-optimizing generative models</li>
        <li>Empowering educators and academics to create more open-source learning materials, which can be uploaded to and leveraged by Uncover Learning's models for immediate student use</li>
        <li>Bridging gaps between generations of college students by incentivizing the sharing of student-created study guides and notes through the Uncover Learning application</li>
        <li>Leveraging uploaded materials over time to build the most affordable and effective online learning platform in the world, offering low cost education globally</li>
      </ul>
    `,
    solution: `
      <h2>Uncover Learning is building a solution to our first mission-based initiative:</h2>
      <p>A course-based education application that enhances learning by closing the knowledge and accessibility gaps between professors and students.</p>
      <h3>How?</h3>
      <p>We will collect open-source and accessible learning materials and textbooks, then design AI-powered courseware around them to provide college sections with the same professor-servicing convenience as today's expensive textbooks. Except our courseware will equally serve students, with fully personalized studying tools, including language model-powered tutoring chatbots based solely on textbook information, fine-tuned to enhance learning, not cheating.</p>
    `,
    team: `
      <h2>Meet the Team</h2>
      <div class="team-members">
        <div class="team-member">
          <img src="assets/taj.jpg" alt="Taj O'Malley" />
          <p><strong>Taj O'Malley</strong><br>Principal Co-Founder<br>
          <a href="https://www.linkedin.com/in/taj-o-malley-94776a239/" target="_blank">
            <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linkedin.svg" alt="LinkedIn" class="social-icon" />
          </a></p>
        </div>
        <div class="team-member">
          <img src="assets/henry.jpg" alt="Henry Dicks" />
          <p><strong>Henry Dicks</strong><br>Operational Co-Founder<br>
          <a href="https://www.linkedin.com/in/henry-dicks/" target="_blank">
            <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linkedin.svg" alt="LinkedIn" class="social-icon" />
          </a></p>
        </div>
        <div class="team-member">
          <img src="assets/magnus.jpg" alt="Magnus Graham" />
          <p><strong>Magnus Graham</strong><br>Technical Co-Founder<br>
          <a href="https://www.linkedin.com/in/magnus-graham/" target="_blank">
            <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linkedin.svg" alt="LinkedIn" class="social-icon" />
          </a></p>
        </div>
      </div>
    `,
    coming: `
      <h2>Coming Soon</h2>
      <p>We are currently building our first model prototype, which will test the chatbot tutor function based on uploaded learning materials.</p>
      <p>Once deployed, we plan on testing its functionality in classrooms at the University of Portland, while continuing to build additional features.</p>
    `,
    contact: `
      <h2>Stay updated - Join Our Movement Towards Accessible Education for All</h2>
      <form action="https://YOUR_MAILCHIMP_URL" method="post" target="_blank">
        <input type="email" name="EMAIL" placeholder="Enter your email" required />
        <button type="submit">Join</button>
      </form>
      <p>Questions or Connections? Email us at: <a href="mailto:Uncoverlearning@outlook.com">Uncoverlearning@outlook.com</a></p>
    `
  };

  // Add click event listeners to mini-cards to open the modal with content
  document.querySelectorAll(".mini-card").forEach(card => {
    card.addEventListener("click", function() {
      const cardId = this.getAttribute("data-card");
      modalBody.innerHTML = cardContent[cardId];
      modal.classList.remove("hidden");
    });
  });

  // Close modal when the close button is clicked
  closeModal.addEventListener("click", function() {
    console.log("Close button clicked"); // Debug log
    modal.classList.add("hidden");
  });

  // Close modal when clicking outside the modal-content
  modal.addEventListener("click", function(e) {
    if (e.target === modal) {
      modal.classList.add("hidden");
    }
  });
});
