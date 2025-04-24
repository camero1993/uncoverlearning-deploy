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
              // IMPORTANT: Replace 'path/to/your/document.pdf' with the actual URL
              // where your backend serves the PDF file.
              // If using FastAPI StaticFiles mounted at /static, it would be like '/static/your_document_name.pdf'
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
      // Don't return here anymore, we need to attach listeners
      // for upload and chat *inside* the logo card back
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
    // NOTE: The flashcard loop structure was slightly adjusted to
    // NOT return early for the logo card, as upload/chat listeners
    // are within it. Moved other card logic into an else block.


  //
  // Chatbot prompt handler (remains largely the same)
  //
  const sendBtn = document.querySelector('#logo-card .send-btn');
  const chatInput = document.querySelector('#logo-card .chat-input');
  const chatWin = document.querySelector('#logo-card .chat-window');

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

      // IMPORTANT: If your RAG is specific to a document,
      // you need a way to get the currently selected document title here.
      // This is a placeholder - replace with actual logic to get the title.
      // If your RAG is over ALL documents, you might omit file_title
      // and update the Python search logic accordingly.
      // You might get the title of the LAST uploaded document, for example.
      // For now, using null as the frontend doesn't provide it, but backend hardcodes.
      const currentFileTitle = null; // <--- Keep this null as backend hardcodes for now


      // 1) Render user bubble
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      userBubble.textContent = query;
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
            // We are NOT sending file_title from the frontend in this hardcoded scenario
            // ...(currentFileTitle && { file_title: currentFileTitle }) // Commented out as backend hardcodes
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
        aiBubble.textContent = data.answer ?? 'No answer could be retrieved.';
        chatWin.appendChild(aiBubble);
        chatWin.scrollTop = chatWin.scrollHeight;

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
  // PDF Upload Handler (NEW SECTION) - Commented out HTML in index.html
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

  //         // --- Optional: Store the uploaded file title ---
  //         // If you want the chatbot to query the *last* uploaded document,
  //         // you would store its title here in a variable accessible by the chatbot handler.
  //         // Example:
  //         // window.lastUploadedFileTitle = formData.get('original_name');
  //         // You would then use window.lastUploadedFileTitle in the chatbot fetch call.
  //         // -----------------------------------------------

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
