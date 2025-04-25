document.addEventListener('DOMContentLoaded', () => {
  const RENDER_BACKEND_BASE_URL = 'https://uncoverlearning-deploy.onrender.com';
  // Existing Flashcard Logic
  const cards = document.querySelectorAll('.flashcard');

  cards.forEach(card => {
    const cta = card.querySelector('.cta-text');
    const frontBtn = card.querySelector('.front-btn');
    // Determine trigger based on card ID, prioritizing cta if it exists
    const trigger = card.id === 'logo-card' ? cta : (cta || frontBtn);
    const backBtn = card.querySelector('.back-btn');

    // Logo card: expand/collapse (no flip)
    if (card.id === 'logo-card') {
      // Get the iframe element for PDF display
      const pdfViewer = card.querySelector('#pdf-viewer'); // Ensure your HTML has <iframe id="pdf-viewer">

      if (trigger) {
        trigger.addEventListener('click', e => {
          e.stopPropagation();
          card.classList.add('expanded');

          // --- Set the PDF source when the chat interface is shown ---
          if (pdfViewer) {
              // IMPORTANT: Replace '/static/your_document_name.pdf' with the actual URL
              // where your backend serves the PDF file.
              // This assumes your backend serves static files from /static.
              pdfViewer.src = `${RENDER_BACKEND_BASE_URL}/static/Psychiatric-Mental_Health_Nursing-WEB.pdf`; // <<< CHANGE THIS PATH >>>
              console.log("PDF viewer source set to:", pdfViewer.src); // Log for debugging
          }
          // -----------------------------------------------------------
        });
      }
      if (backBtn) {
        backBtn.addEventListener('click', e => {
          e.stopPropagation();
          card.classList.remove('expanded');
          // Optional: scroll back into view after collapsing
          card.scrollIntoView({ behavior: 'smooth', inline: 'center' });

          // --- Clear the PDF source when closing ---
          if (pdfViewer) {
              pdfViewer.src = ''; // Clear the iframe source
              console.log("PDF viewer source cleared."); // Log for debugging
          }
          // -----------------------------------------
        });
      }
    } else {
       // Other cards: standard flip front/back
       if (trigger) {
         trigger.addEventListener('click', e => {
           e.stopPropagation();
           card.classList.toggle('flipped');
         });
       }
       if (backBtn) {
         backBtn.addEventListener('click', e => {
           e.stopPropagation();
           card.classList.remove('flipped');
         });
       }
    }
  });


  //
  // Chatbot prompt handler and Search (Search logic is not yet fully implemented)
  //
  const sendBtn = document.querySelector('#logo-card .send-btn');
  const chatInput = document.querySelector('#logo-card .chat-input');
  const chatWin = document.querySelector('#logo-card .chat-window');
  // Search input and message storage elements are not yet fully implemented
  // const chatSearchInput = document.querySelector('#logo-card .chat-search-input');
  // const chatMessages = [];


  // --- REMOVED: Character typing animation function ---
  // function typeText(element, text, delay = 20) { ... }
  // ----------------------------------------------------


  // --- NEW: Function to fade in blocks of text ---
  function fadeInBlocks(containerElement, htmlContent, blockDelay = 100, fadeDuration = 500) {
      // Create a temporary div to parse the HTML content
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = htmlContent;

      // Get the child nodes (paragraphs, lists, etc.) from the parsed HTML
      const blocks = Array.from(tempDiv.childNodes).filter(node => node.nodeType === Node.ELEMENT_NODE);

      // Clear the container element before adding new content
      containerElement.innerHTML = '';

      // Append each block to the container and set initial styles for fade-in
      blocks.forEach(block => {
          // Clone the node to avoid issues with moving elements
          const clonedBlock = block.cloneNode(true);
          // Apply initial styles for fade-in
          clonedBlock.style.opacity = '0';
          clonedBlock.style.transition = `opacity ${fadeDuration}ms ease-in-out`;
          // Append the block to the chat bubble element
          containerElement.appendChild(clonedBlock);
      });

      // Sequentially fade in each block
      blocks.forEach((_, index) => {
          setTimeout(() => {
              // Get the actual element in the DOM (which is the clone)
              const elementToFadeIn = containerElement.children[index];
              if (elementToFadeIn) {
                 elementToFadeIn.style.opacity = '1';
                 // Scroll to the bottom as blocks fade in
                 chatWin.scrollTop = chatWin.scrollHeight;
              }
          }, blockDelay * (index + 1)); // Delay each block's fade by blockDelay * its index
      });
  }
  // -----------------------------------------------


  if (sendBtn && chatInput && chatWin) {
    // Allow sending with Enter key
    chatInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent default form submission
            sendBtn.click(); // Simulate button click
        }
    });

    sendBtn.addEventListener('click', async () => {
      const query = chatInput.value.trim();
      if (!query) return;

      // 1) Render user bubble
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      userBubble.textContent = query; // User input is just text
      chatWin.appendChild(userBubble);
      chatWin.scrollTop = chatWin.scrollHeight;
      chatInput.value = ''; // Clear input after sending

      // 2) Send to backend (to the /query_document endpoint)
      try {
        const res = await fetch(`${RENDER_BACKEND_BASE_URL}/query_document/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: query,
            // file_title is hardcoded in the backend for now
          }),
        });

        if (!res.ok) {
             const errorData = await res.json(); // Try to read error details from response
             throw new Error(`HTTP error! status: ${res.status}, detail: ${JSON.stringify(errorData.detail || errorData || res.statusText)}`); // Stringify detail for better logging
        }

        const data = await res.json();

        // 3) Render AI bubble
        const aiBubble = document.createElement('div');
        aiBubble.className = 'chat-bubble ai';
        // Append the bubble element immediately
        chatWin.appendChild(aiBubble);
        chatWin.scrollTop = chatWin.scrollHeight;


        // --- MODIFIED: Convert AI response (assumed Markdown) to HTML and start fade-in animation ---
        const aiResponseText = data.answer ?? 'No answer could be retrieved.';
        // Use marked.js to convert Markdown to HTML
        const aiResponseHTML = marked.parse(aiResponseText);

        // Start the fade-in animation for the AI bubble's content
        // Fade in each block with 100ms delay between blocks, and each fade takes 500ms
        fadeInBlocks(aiBubble, aiResponseHTML, 100, 500); // Call the new function
        // -----------------------------------------------------------------------------------------

      } catch (err) {
        console.error('API error:', err);
        const errBubble = document.createElement('div');
        errBubble.className = 'chat-bubble ai error';
        errBubble.textContent = `Error fetching answer: ${err.message || err}`;
        chatWin.appendChild(errBubble);
        chatWin.scrollTop = chatWin.scrollHeight;
      }
    });
  }


  //
  // PDF Upload Handler (Commented out HTML in index.html)
  //
  // const uploadForm = document.getElementById('uploadForm');
  // const uploadStatus = document.getElementById('uploadStatus');

  // if (uploadForm && uploadStatus) {
  //   uploadForm.addEventListener('submit', async (event) => {
  //     event.preventDefault(); // Prevent the default form submission (page reload)

  //     const formData = new FormData(uploadForm); // Get the form data, including the file and name inputs

  //     uploadStatus.textContent = 'Uploading and processing...';
  //     uploadStatus.style.color = 'blue'; // Indicate ongoing process

  //     try {
  //       const response = await fetch(`${RENDER_BACKEND_BASE_URL}/upload_document/`, {
  //         method: 'POST',
  //         body: formData, // Send the FormData object
  //         // Do NOT set Content-Type header for FormData, the browser handles it
  //       });

  //       const result = await response.json(); // Expect JSON response from FastAPI

  //       if (response.ok) { // Check for success (HTTP status 200-299)
  //         uploadStatus.textContent = 'Success: ' + (result.message || 'Document processed.');
  //         uploadStatus.style.color = 'green'; // Indicate success
  //         // Optionally clear the form or update UI upon success
  //         uploadForm.reset();

  //       } else { // Handle errors (HTTP status 4xx or 5xx)
  //         uploadStatus.textContent = 'Error: ' + (result.detail || result.message || response.statusText || 'Upload failed.');
  //         uploadStatus.style.color = 'red'; // Indicate error
  //       }

  //     } catch (error) {
  //       console.error('Upload fetch error:', error);
  //       uploadStatus.textContent = 'Upload failed: ' + (error.message || 'Network error.');
  //       uploadStatus.style.color = 'red'; // Indicate error
  //     }
  //   });
  // }
});
