(function() {
  const config = window.RAGChatConfig || {
    apiUrl: 'http://localhost:8000/api/v1',
    botName: '📚 Book Assistant',
    placeholder: 'Ask anything...'
  };

  let selectedText = '';
  let chatOpen = false;

  function createWidget() {
    // Chat button
    const btn = document.createElement('button');
    btn.id = 'rag-chat-btn';
    btn.innerHTML = '💬';
    btn.setAttribute('aria-label', 'Open chat');
    btn.onclick = toggleChat;
    document.body.appendChild(btn);

    // Chat panel
    const panel = document.createElement('div');
    panel.id = 'rag-chat-panel';
    panel.style.display = 'none';
    panel.innerHTML = `
      <div id="rag-chat-header">
        <h3>${config.botName}</h3>
        <button id="rag-chat-close" aria-label="Close chat">×</button>
      </div>
      <div id="rag-chat-messages">
        <div class="rag-message bot">
          <div class="rag-message-content">
            👋 Hi! I'm your book assistant. Ask me anything about the textbook!
          </div>
        </div>
      </div>
      <div id="rag-chat-input-container">
        <input type="text" id="rag-chat-input" placeholder="${config.placeholder}" autocomplete="off" />
        <button id="rag-chat-send" aria-label="Send">➤</button>
      </div>
    `;
    document.body.appendChild(panel);

    // Selection toolbar
    const toolbar = document.createElement('div');
    toolbar.id = 'rag-selection-toolbar';
    toolbar.innerHTML = '✨ Ask about this';
    toolbar.onclick = askAboutSelection;
    document.body.appendChild(toolbar);

    // Event listeners
    document.getElementById('rag-chat-close').onclick = toggleChat;
    document.getElementById('rag-chat-send').onclick = sendMessage;
    document.getElementById('rag-chat-input').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });
    document.addEventListener('mouseup', handleSelection);

    // CTA button click
    document.querySelector('.cta-box .btn')?.addEventListener('click', (e) => {
      e.preventDefault();
      toggleChat();
    });
  }

  function toggleChat() {
    chatOpen = !chatOpen;
    const panel = document.getElementById('rag-chat-panel');
    panel.style.display = chatOpen ? 'flex' : 'none';
    if (chatOpen) {
      setTimeout(() => document.getElementById('rag-chat-input').focus(), 100);
    }
  }

  function handleSelection() {
    const selection = window.getSelection();
    selectedText = selection.toString().trim();
    const toolbar = document.getElementById('rag-selection-toolbar');
    
    if (selectedText.length > 5 && selectedText.length < 500) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      toolbar.style.display = 'block';
      toolbar.style.bottom = (window.innerHeight - rect.top + 10) + 'px';
      toolbar.style.right = '24px';
    } else {
      toolbar.style.display = 'none';
    }
  }

  function askAboutSelection() {
    if (!selectedText) return;
    if (!chatOpen) toggleChat();
    document.getElementById('rag-chat-input').value = selectedText;
    sendMessage();
    document.getElementById('rag-selection-toolbar').style.display = 'none';
    window.getSelection().removeAllRanges();
  }

  function addMessage(content, isUser = false, sources = null) {
    const messages = document.getElementById('rag-chat-messages');
    const msg = document.createElement('div');
    msg.className = 'rag-message ' + (isUser ? 'user' : 'bot');
    
    let html = `<div class="rag-message-content">${escapeHtml(content)}</div>`;
    
    if (sources && sources.length > 0) {
      html += '<div class="rag-sources">';
      sources.forEach((s, i) => {
        const chapter = s.chapter_name || 'Unknown Chapter';
        html += `<div>📖 ${escapeHtml(chapter)}</div>`;
      });
      html += '</div>';
    }
    
    msg.innerHTML = html;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  function addTypingIndicator() {
    const messages = document.getElementById('rag-chat-messages');
    const typing = document.createElement('div');
    typing.className = 'rag-message bot';
    typing.id = 'rag-typing';
    typing.innerHTML = '<div class="rag-typing"><span></span><span></span><span></span></div>';
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTypingIndicator() {
    const typing = document.getElementById('rag-typing');
    if (typing) typing.remove();
  }

  async function sendMessage() {
    const input = document.getElementById('rag-chat-input');
    const question = input.value.trim();
    if (!question) return;

    const sendBtn = document.getElementById('rag-chat-send');
    sendBtn.disabled = true;

    addMessage(question, true);
    input.value = '';
    addTypingIndicator();

    try {
      const response = await fetch(`${config.apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, selected_text: null })
      });

      const data = await response.json();
      removeTypingIndicator();

      if (data.status === 'ok' && data.data) {
        addMessage(data.data.answer, false, data.data.sources);
      } else {
        addMessage('Sorry, something went wrong. Please try again.', false);
      }
    } catch (error) {
      removeTypingIndicator();
      addMessage('Connection error. Please check if the server is running.', false);
    }

    sendBtn.disabled = false;
    input.focus();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
  }

  // Initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWidget);
  } else {
    createWidget();
  }
})();
