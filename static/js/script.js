const SecurePixel = (() => {
  const $ = (selector) => document.querySelector(selector);

  function setNotice(element, message, type = 'error') {
    element.textContent = message;
    element.className = `notice visible ${type}`;
  }

  function bindUpload(inputId, dropId, previewId, wrapId, fileNameId) {
    const input = $(`#${inputId}`);
    const drop = $(`#${dropId}`);
    const preview = $(`#${previewId}`);
    const wrap = $(`#${wrapId}`);
    const name = $(`#${fileNameId}`);
    const show = (file) => {
      if (!file) return;
      if (!file.type.startsWith('image/')) return;
      const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files;
      preview.src = URL.createObjectURL(file); name.textContent = file.name; wrap.classList.add('visible'); drop.classList.add('has-file');
    };
    input.addEventListener('change', () => show(input.files[0]));
    ['dragenter', 'dragover'].forEach((event) => drop.addEventListener(event, (e) => { e.preventDefault(); drop.classList.add('dragging'); }));
    ['dragleave', 'drop'].forEach((event) => drop.addEventListener(event, (e) => { e.preventDefault(); drop.classList.remove('dragging'); }));
    drop.addEventListener('drop', (e) => show(e.dataTransfer.files[0]));
  }

  function bindPasswords() {
    document.querySelectorAll('.visibility-toggle').forEach((button) => button.addEventListener('click', () => {
      const input = $(`#${button.dataset.target}`); input.type = input.type === 'password' ? 'text' : 'password'; button.classList.toggle('revealed');
    }));
  }

  function passwordStrength(value) {
    let score = 0;
    if (value.length >= 12) score++; if (value.length >= 16) score++; if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++; if (/\d/.test(value)) score++; if (/[^A-Za-z0-9]/.test(value)) score++;
    return Math.min(score, 4);
  }

  function bindStrength() {
    const input = $('#encrypt-password'); const fill = $('#strength-fill'); const label = $('#strength-label');
    input.addEventListener('input', () => { const score = passwordStrength(input.value); fill.style.width = `${score * 25}%`; fill.dataset.score = score; label.textContent = !input.value ? 'Waiting for a password' : ['Too short', 'Getting there', 'Good foundation', 'Strong password', 'Excellent password'][score]; });
  }

  function setBusy(form, busy) { form.classList.toggle('is-busy', busy); form.querySelector('button[type="submit"]').disabled = busy; }

  async function submitForm(form, endpoint, notice, success) {
    setNotice(notice, ''); setBusy(form, true);
    try {
      const response = await fetch(endpoint, { method: 'POST', body: new FormData(form) });
      if (response.ok) return success(response);
      const data = await response.json().catch(() => ({})); throw new Error(data.error || 'Unable to process this request.');
    } catch (error) { setNotice(notice, error.message); } finally { setBusy(form, false); }
  }

  function initEncrypt() {
    const form = $('#encrypt-form'); bindUpload('encrypt-image', 'encrypt-drop', 'encrypt-preview', 'encrypt-preview-wrap', 'encrypt-file-name'); bindPasswords(); bindStrength();
    $('#message').addEventListener('input', (event) => { $('#message-count').textContent = `${(new Blob([event.target.value]).size / 1024).toFixed(1)} / 256 KB`; });
    form.addEventListener('submit', (event) => { event.preventDefault(); if (!$('#encrypt-image').files[0]) return setNotice($('#encrypt-notice'), 'Choose a cover image first.'); if (!$('#message').value.trim()) return setNotice($('#encrypt-notice'), 'Enter a secret message.'); submitForm(form, '/api/encrypt', $('#encrypt-notice'), async (response) => { const blob = await response.blob(); $('#download-link').href = URL.createObjectURL(blob); $('#encrypt-success').classList.add('visible'); $('#encrypt-success').scrollIntoView({ behavior: 'smooth', block: 'center' }); }); });
  }

  function initDecrypt() {
    const form = $('#decrypt-form'); bindUpload('decrypt-image', 'decrypt-drop', 'decrypt-preview', 'decrypt-preview-wrap', 'decrypt-file-name'); bindPasswords();
    form.addEventListener('submit', (event) => { event.preventDefault(); if (!$('#decrypt-image').files[0]) return setNotice($('#decrypt-notice'), 'Choose an encrypted image first.'); submitForm(form, '/api/decrypt', $('#decrypt-notice'), async (response) => { const data = await response.json(); $('#secret-output').textContent = data.message; $('#decrypt-result').classList.add('visible'); $('#decrypt-result').scrollIntoView({ behavior: 'smooth', block: 'center' }); }); });
  }
  return { initEncrypt, initDecrypt };
})();
