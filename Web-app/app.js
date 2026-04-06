// ============================================================
// CONFIGURATION
// Point this to your backend URL.
// Local dev:  http://localhost:8000
// Production: https://your-app.railway.app
// ============================================================
const BACKEND_URL = 'https://jarvis-career-agent-production.up.railway.app';


// ============================================================
// STATE
// ============================================================
let authToken    = localStorage.getItem('jarvis_token') || null;
let currentUser  = null;
let lastResult   = null;
let isRecording  = false;
let recognition  = null;
let isMuted      = false;


// ============================================================
// ON PAGE LOAD
// ============================================================
window.addEventListener('load', function() {
  // Restore API key if saved
  const savedKey = localStorage.getItem('groq_api_key');
  if (savedKey) document.getElementById('apiKeyInput').value = savedKey;

  if (authToken) {
    // Already logged in — verify token and go straight to app
    fetchCurrentUser();
  } else {
    showAuthScreen();
  }
});


// ============================================================
// AUTH SCREEN
// ============================================================

function showAuthScreen() {
  document.getElementById('authScreen').style.display = 'flex';
  document.getElementById('mainApp').style.display    = 'none';
}

function showMainApp() {
  document.getElementById('authScreen').style.display = 'none';
  document.getElementById('mainApp').style.display    = 'block';
  document.getElementById('userNameLabel').textContent = `Hi, ${currentUser.name.split(' ')[0]} 👋`;

  setTimeout(function() {
    jarvisSpeak(
      `Welcome back ${currentUser.name.split(' ')[0]}. ` +
      'Paste your resume and job description, then say analyze or click the button.'
    );
  }, 600);
}

function switchTab(tab) {
  document.getElementById('loginForm').style.display    = tab === 'login' ? 'block' : 'none';
  document.getElementById('registerForm').style.display = tab === 'register' ? 'block' : 'none';
  document.getElementById('loginTab').classList.toggle('active', tab === 'login');
  document.getElementById('registerTab').classList.toggle('active', tab === 'register');
  document.getElementById('loginError').textContent    = '';
  document.getElementById('registerError').textContent = '';
}

async function handleRegister() {
  const name     = document.getElementById('regName').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value.trim();
  const errEl    = document.getElementById('registerError');

  if (!name || !email || !password) {
    errEl.textContent = 'Please fill in all fields.'; return;
  }
  if (password.length < 6) {
    errEl.textContent = 'Password must be at least 6 characters.'; return;
  }

  try {
    const res  = await fetch(`${BACKEND_URL}/auth/register`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name, email, password })
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || 'Registration failed.'; return; }

    errEl.style.color    = '#22cc77';
    errEl.textContent    = 'Account created! Please login.';
    setTimeout(() => switchTab('login'), 1500);

  } catch (e) {
    errEl.textContent = 'Could not connect to server. Is the backend running?';
  }
}

async function handleLogin() {
  const email    = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value.trim();
  const errEl    = document.getElementById('loginError');

  if (!email || !password) { errEl.textContent = 'Please enter email and password.'; return; }

  try {
    // FastAPI login expects form data, not JSON
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const res  = await fetch(`${BACKEND_URL}/auth/login`, {
      method: 'POST', body: formData
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || 'Login failed.'; return; }

    authToken = data.access_token;
    localStorage.setItem('jarvis_token', authToken);
    await fetchCurrentUser();

  } catch (e) {
    errEl.textContent = 'Could not connect to server. Is the backend running?';
  }
}

async function fetchCurrentUser() {
  try {
    const res  = await fetch(`${BACKEND_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (!res.ok) { handleLogout(); return; }
    currentUser = await res.json();
    showMainApp();
  } catch (e) {
    handleLogout();
  }
}

function handleLogout() {
  authToken   = null;
  currentUser = null;
  localStorage.removeItem('jarvis_token');
  showAuthScreen();
}


// ============================================================
// HISTORY PANEL
// ============================================================

async function toggleHistory() {
  const panel = document.getElementById('historyPanel');
  if (panel.style.display === 'none') {
    panel.style.display = 'block';
    await loadHistory();
  } else {
    panel.style.display = 'none';
  }
}

async function loadHistory() {
  const listEl = document.getElementById('historyList');
  listEl.innerHTML = '<p style="color:#888;font-size:13px">Loading...</p>';

  try {
    const res  = await fetch(`${BACKEND_URL}/history`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    const data = await res.json();

    if (!data.length) {
      listEl.innerHTML = '<p style="color:#888;font-size:13px">No analyses yet. Run your first one!</p>';
      return;
    }

    listEl.innerHTML = data.map(function(item) {
      const date  = new Date(item.created_at).toLocaleDateString('en-IN');
      const grade = item.ats_grade;
      const gradeColor = grade === 'A' ? '#22cc77' : grade === 'B' ? '#3399ff' :
                         grade === 'C' ? '#ffaa00' : grade === 'D' ? '#ff6600' : '#cc3333';
      return `
        <div class="history-item" onclick="loadAnalysis(${item.id})">
          <div class="hi-left">
            <p class="hi-role">${item.role}</p>
            <p class="hi-date">${date}</p>
          </div>
          <div class="hi-right">
            <span class="hi-score">${item.ats_score}</span>
            <span class="hi-grade" style="color:${gradeColor}">${grade}</span>
          </div>
        </div>`;
    }).join('');

  } catch (e) {
    listEl.innerHTML = '<p style="color:#cc4444;font-size:13px">Could not load history.</p>';
  }
}

async function loadAnalysis(id) {
  try {
    const res    = await fetch(`${BACKEND_URL}/analysis/${id}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    const result = await res.json();
    lastResult   = result;
    toggleHistory();
    renderResults(result);
    renderAtsScore(result);
    document.getElementById('resultActions').style.display = 'flex';
    jarvisSpeak(`Loaded your previous analysis for ${result.role}. ATS score was ${result.ats_score} out of 100.`);
  } catch (e) {
    console.error('Could not load analysis:', e);
  }
}


// ============================================================
// PDF UPLOAD
// ============================================================

document.getElementById('pdfInput').addEventListener('change', function() {
  const file = this.files[0];
  if (!file) return;
  document.getElementById('fileName').textContent = '✓ ' + file.name + ' loaded';
  document.getElementById('fileName').style.display = 'block';
  document.getElementById('uploadBox').classList.add('has-file');
  jarvisSpeak('Resume PDF loaded. Now paste the job description and say analyze.');
});


// ============================================================
// SPINNER
// ============================================================

const spinnerMessages = [
  'Computing ATS score with TF-IDF...',
  'Extracting keywords from job description...',
  'Measuring cosine similarity...',
  'Running AI gap analysis...',
  'Building your project roadmap...',
  'Saving to your account...'
];

let spinnerInterval = null;

function showSpinner() {
  document.getElementById('resultsArea').style.display    = 'none';
  document.getElementById('loadingSpinner').style.display = 'block';
  document.getElementById('resultActions').style.display  = 'none';
  document.getElementById('atsCard').style.display        = 'none';
  let i = 0;
  document.getElementById('spinnerText').textContent = spinnerMessages[0];
  spinnerInterval = setInterval(function() {
    i = (i + 1) % spinnerMessages.length;
    document.getElementById('spinnerText').textContent = spinnerMessages[i];
  }, 2000);
}

function hideSpinner() {
  clearInterval(spinnerInterval);
  document.getElementById('loadingSpinner').style.display = 'none';
  document.getElementById('resultsArea').style.display   = 'block';
}


// ============================================================
// MAIN ANALYSIS — calls your FastAPI backend
// ============================================================

async function runAnalysis() {
  const jd         = document.getElementById('jdInput').value.trim();
  const resumeText = document.getElementById('resumeText').value.trim();
  const apiKey     = document.getElementById('apiKeyInput').value.trim();

  if (!jd)     { jarvisSpeak('Please paste a job description first.'); return; }
  if (!apiKey) { jarvisSpeak('Please enter your Groq API key at the top.'); return; }

  // Save API key for convenience
  localStorage.setItem('groq_api_key', apiKey);

  document.getElementById('analyzeBtn').textContent = 'Analyzing...';
  document.getElementById('analyzeBtn').disabled    = true;
  setStatus('analyzing', true);
  showSpinner();

  try {
    const res  = await fetch(`${BACKEND_URL}/analyze`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({
        resume_text:     resumeText,
        job_description: jd,
        groq_api_key:    apiKey
      })
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || 'Analysis failed.');
      jarvisSpeak('There was an error during analysis. Please try again.');
      return;
    }

    lastResult = data;
    hideSpinner();
    renderResults(data);
    renderAtsScore(data);
    document.getElementById('resultActions').style.display = 'flex';
    setStatus('complete', true);

    // JARVIS speaks the summary
    jarvisSpeak(
      `Analysis complete for ${data.role}. ` +
      `Your ATS score is ${data.ats_score} out of 100, grade ${data.ats_grade}. ` +
      `I found ${data.gaps.length} skill gaps and ${data.new_projects.length} projects to build. ` +
      `This analysis has been saved to your account.`
    );

  } catch (e) {
    showError('Could not connect to backend. Make sure the server is running.');
    jarvisSpeak('Could not connect to the backend server.');
  }

  document.getElementById('analyzeBtn').textContent = 'Analyze My Resume →';
  document.getElementById('analyzeBtn').disabled    = false;
}


// ============================================================
// RENDER ATS SCORE CARD
// ============================================================

function renderAtsScore(result) {
  const card  = document.getElementById('atsCard');
  const score = result.ats_score || 0;
  const grade = result.ats_grade || 'F';

  document.getElementById('atsScore').textContent = score;
  document.getElementById('atsGrade').textContent = grade;

  // Color the grade
  const gradeEl    = document.getElementById('atsGrade');
  const gradeColor = grade === 'A' ? '#22cc77' : grade === 'B' ? '#3399ff' :
                     grade === 'C' ? '#ffaa00' : grade === 'D' ? '#ff6600' : '#cc3333';
  gradeEl.style.color = gradeColor;

  // Matched keywords
  const matchedEl = document.getElementById('matchedKeywords');
  matchedEl.innerHTML = (result.matched_keywords || []).map(function(kw) {
    return `<span class="kw-tag matched">${kw}</span>`;
  }).join('');

  // Missing keywords
  const missingEl = document.getElementById('missingKeywords');
  missingEl.innerHTML = (result.missing_keywords || []).map(function(kw) {
    return `<span class="kw-tag missing">${kw}</span>`;
  }).join('');

  card.style.display = 'flex';
}


// ============================================================
// RENDER RESULTS
// ============================================================

function renderResults(result) {
  var html = '';

  html += '<h2>Skill Gaps for "' + (result.role || 'this role') + '"</h2>';
  (result.gaps || []).forEach(function(gap) {
    html += '<div class="gap-card"><strong>' + gap.skill + '</strong><p>' + gap.reason + '</p></div>';
  });

  html += '<h2>Projects to Build</h2>';
  (result.new_projects || []).forEach(function(p, i) {
    html += buildProjectCard(p, 'new_' + i, 'NEW', 'badge-new');
  });

  if (result.upgrade_projects && result.upgrade_projects.length > 0) {
    html += '<h2>Projects to Upgrade</h2>';
    result.upgrade_projects.forEach(function(p, i) {
      html += buildProjectCard(p, 'upg_' + i, 'UPGRADE', 'badge-upgrade');
    });
  }

  document.getElementById('resultsArea').innerHTML = html;
}

function buildProjectCard(project, id, badgeLabel, badgeClass) {
  var html = '<div class="project-card">';
  html += '<div class="project-header" onclick="toggleCard(\'' + id + '\')">';
  html += '<span class="project-title">' + project.title + '</span>';
  html += '<span class="project-right"><span class="badge ' + badgeClass + '">' + badgeLabel + '</span>';
  html += '<span class="arrow" id="arrow_' + id + '">▼</span></span></div>';
  html += '<div class="project-body" id="body_' + id + '">';
  html += '<p class="project-why">' + project.why + '</p>';
  if (project.tech && project.tech.length > 0) {
    html += '<div class="tech-tags">';
    project.tech.forEach(function(t) { html += '<span>' + t + '</span>'; });
    html += '</div>';
  }
  if (project.steps && project.steps.length > 0) {
    html += '<ol>';
    project.steps.forEach(function(s) { html += '<li>' + s + '</li>'; });
    html += '</ol>';
  }
  html += '</div></div>';
  return html;
}

function toggleCard(id) {
  document.getElementById('body_' + id).classList.toggle('open');
  document.getElementById('arrow_' + id).classList.toggle('open');
}


// ============================================================
// VOICE — JARVIS SPEAKS
// ============================================================

function jarvisSpeak(text, onDone) {
  if (isMuted) { if (onDone) onDone(); return; }
  window.speechSynthesis.cancel();

  var bubble = document.getElementById('jarvisBubble');
  bubble.style.display = 'block';
  document.getElementById('jarvisSpeechText').textContent = text;
  setOrbState('speaking');
  setJarvisState('Speaking...');

  var utterance  = new SpeechSynthesisUtterance(text);
  utterance.rate  = 0.95;
  utterance.pitch = 0.9;

  var voices    = window.speechSynthesis.getVoices();
  var preferred = voices.find(function(v) {
    return v.name.includes('Google UK') || v.name.includes('Daniel') || v.name.includes('David');
  });
  if (preferred) utterance.voice = preferred;

  utterance.onend = function() {
    setOrbState('idle'); setJarvisState('JARVIS ready');
    if (onDone) onDone();
  };
  window.speechSynthesis.speak(utterance);
}

function toggleMute() {
  isMuted = !isMuted;
  document.getElementById('muteBtn').textContent = isMuted ? '🔇' : '🔊';
  if (isMuted) window.speechSynthesis.cancel();
}

function setOrbState(state) {
  var orb = document.getElementById('jarvisOrb');
  orb.classList.remove('speaking', 'listening');
  if (state !== 'idle') orb.classList.add(state);
}

function setJarvisState(text) {
  document.getElementById('jarvisState').textContent = text;
}


// ============================================================
// VOICE INPUT
// ============================================================

function toggleVoice() {
  if (isRecording) { recognition.stop(); return; }
  if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
    alert('Voice input only works in Google Chrome.'); return;
  }
  window.speechSynthesis.cancel();

  var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition                 = new SpeechRec();
  recognition.lang            = 'en-US';
  recognition.continuous      = false;
  recognition.interimResults  = true;

  recognition.onresult = function(event) {
    var final = '';
    for (var i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) final += event.results[i][0].transcript;
    }
    document.getElementById('voiceTranscript').textContent = final;
    if (final) handleVoiceCommand(final.toLowerCase().trim());
  };

  recognition.onstart = function() {
    isRecording = true;
    document.getElementById('micBtn').textContent = '⏹ Stop';
    document.getElementById('micBtn').classList.add('active');
    setOrbState('listening'); setJarvisState('Listening...');
  };

  recognition.onend = function() {
    isRecording = false;
    document.getElementById('micBtn').textContent = '🎙 Hold to Speak';
    document.getElementById('micBtn').classList.remove('active');
    setOrbState('idle'); setJarvisState('JARVIS ready');
    setTimeout(function() {
      document.getElementById('voiceTranscript').textContent = '';
    }, 3000);
  };

  recognition.start();
}

function handleVoiceCommand(cmd) {
  if (cmd.includes('analyze') || cmd.includes('start'))
    jarvisSpeak('Starting analysis.', runAnalysis);
  else if (cmd.includes('ats') || cmd.includes('score'))
    jarvisSpeak(lastResult ? `Your ATS score is ${lastResult.ats_score} out of 100, grade ${lastResult.ats_grade}.` : 'No analysis yet.');
  else if (cmd.includes('gap') || cmd.includes('skill'))
    jarvisSpeak(lastResult ? 'Your skill gaps are: ' + lastResult.gaps.map(function(g){return g.skill;}).join(', ') + '.' : 'No analysis yet.');
  else if (cmd.includes('first') || cmd.includes('project'))  speakProject(0);
  else if (cmd.includes('second'))   speakProject(1);
  else if (cmd.includes('third'))    speakProject(2);
  else if (cmd.includes('download') || cmd.includes('pdf'))   { jarvisSpeak('Downloading report.'); downloadPDF(); }
  else if (cmd.includes('history') || cmd.includes('show'))   { jarvisSpeak('Opening your history.'); toggleHistory(); }
  else if (cmd.includes('clear'))    jarvisSpeak('Clearing.', clearAll);
  else if (cmd.includes('help'))     jarvisSpeak('Say: analyze, ATS score, read first project, download report, show history, or clear.');
  else if (cmd.includes('hello') || cmd.includes('hi'))       jarvisSpeak('Hello! Say analyze to get started.');
  else { document.getElementById('jdInput').value += ' ' + cmd; jarvisSpeak('Added to job description.'); }
}

function speakProject(idx) {
  var projects = (lastResult || {}).new_projects || [];
  if (projects[idx]) {
    var p = projects[idx];
    jarvisSpeak(`Project ${idx+1}: ${p.title}. ${p.why}. Tech: ${p.tech.join(', ')}.`);
    var body = document.getElementById('body_new_' + idx);
    if (body && !body.classList.contains('open')) {
      body.classList.add('open');
      document.getElementById('arrow_new_' + idx).classList.add('open');
    }
  } else { jarvisSpeak('No project found at that position.'); }
}


// ============================================================
// COPY + DOWNLOAD PDF
// ============================================================

function copyResults() {
  if (!lastResult) return;
  var r    = lastResult;
  var text = `JARVIS CAREER ANALYSIS\n${'='.repeat(40)}\n`;
  text    += `Role: ${r.role}\nATS Score: ${r.ats_score}/100  Grade: ${r.ats_grade}\n\n`;
  text    += `MATCHED KEYWORDS: ${(r.matched_keywords||[]).join(', ')}\n`;
  text    += `MISSING KEYWORDS: ${(r.missing_keywords||[]).join(', ')}\n\n`;
  text    += `SKILL GAPS\n${'-'.repeat(30)}\n`;
  r.gaps.forEach(function(g,i){text+=`${i+1}. ${g.skill}\n   ${g.reason}\n\n`;});
  text    += `PROJECTS TO BUILD\n${'-'.repeat(30)}\n`;
  r.new_projects.forEach(function(p,i){
    text+=`${i+1}. ${p.title}\n   ${p.why}\n   Tech: ${p.tech.join(', ')}\n`;
    p.steps.forEach(function(s,j){text+=`   ${j+1}. ${s}\n`;});
    text+='\n';
  });
  navigator.clipboard.writeText(text).then(function(){
    var btn = document.getElementById('copyBtn');
    btn.textContent = '✓ Copied!';
    setTimeout(function(){btn.textContent='📋 Copy';},2500);
  });
}

function downloadPDF() {
  if (!lastResult) return;
  var jsPDF = window.jspdf.jsPDF;
  var doc   = new jsPDF();
  var pw    = doc.internal.pageSize.getWidth();
  var mg    = 20;
  var cw    = pw - mg*2;
  var y     = 20;

  function t(text, fs, bold, c) {
    doc.setFontSize(fs); doc.setFont('helvetica', bold?'bold':'normal');
    doc.setTextColor(c[0],c[1],c[2]);
    doc.splitTextToSize(text,cw).forEach(function(l){
      if(y>270){doc.addPage();y=20;}
      doc.text(l,mg,y); y+=fs*0.5;
    }); y+=2;
  }

  doc.setFillColor(17,17,17); doc.rect(0,0,pw,28,'F');
  doc.setFontSize(16);doc.setFont('helvetica','bold');doc.setTextColor(255,255,255);
  doc.text('JARVIS — Career Agent',mg,17);
  doc.setFontSize(9);doc.setFont('helvetica','normal');doc.setTextColor(180,180,180);
  doc.text('Resume Analysis Report',mg,24);

  y=38;
  t(`Target Role: ${lastResult.role}`,14,true,[30,30,30]);
  t(`ATS Score: ${lastResult.ats_score}/100  |  Grade: ${lastResult.ats_grade}`,12,true,[17,85,170]);
  t(`Matched Keywords: ${(lastResult.matched_keywords||[]).join(', ')}`,9,false,[40,120,40]);
  t(`Missing Keywords: ${(lastResult.missing_keywords||[]).join(', ')}`,9,false,[180,60,0]);
  y+=4;

  t('SKILL GAPS',10,true,[120,120,120]);
  lastResult.gaps.forEach(function(g,i){
    t(`${i+1}. ${g.skill}`,11,true,[180,60,0]);
    t(`   ${g.reason}`,10,false,[100,60,40]); y+=2;
  });

  t('PROJECTS TO BUILD',10,true,[120,120,120]);
  lastResult.new_projects.forEach(function(p,i){
    y+=2; t(`${i+1}. ${p.title}`,11,true,[17,85,170]);
    t(`   ${p.why}`,10,false,[80,80,80]);
    t(`   Tech: ${p.tech.join(', ')}`,9,false,[120,120,120]);
    p.steps.forEach(function(s,j){t(`   ${j+1}. ${s}`,9,false,[60,60,60]);});
    y+=3;
  });

  var pc = doc.internal.getNumberOfPages();
  for(var i=1;i<=pc;i++){
    doc.setPage(i);doc.setFontSize(8);doc.setTextColor(180,180,180);
    doc.text(`Generated by JARVIS Career Agent · Page ${i} of ${pc}`,mg,290);
  }
  doc.save(`JARVIS_${(lastResult.role||'Report').replace(/\s+/g,'_')}.pdf`);
}


// ============================================================
// HELPERS
// ============================================================

function setStatus(text, active) {
  var pill = document.getElementById('statusPill');
  pill.textContent = text;
  if (active) pill.classList.add('active');
  else pill.classList.remove('active');
}

function showError(msg) {
  hideSpinner();
  document.getElementById('resultsArea').innerHTML =
    `<div style="background:#fff5f5;border:1px solid #ffcccc;border-radius:8px;padding:16px;font-size:13px;color:#cc0000;line-height:1.7">⚠️ ${msg}</div>`;
  setStatus('error', false);
}

function clearAll() {
  lastResult = null;
  document.getElementById('jdInput').value    = '';
  document.getElementById('resumeText').value = '';
  document.getElementById('pdfInput').value   = '';
  document.getElementById('fileName').style.display       = 'none';
  document.getElementById('uploadBox').classList.remove('has-file');
  document.getElementById('resultActions').style.display  = 'none';
  document.getElementById('atsCard').style.display        = 'none';
  document.getElementById('loadingSpinner').style.display = 'none';
  document.getElementById('resultsArea').style.display    = 'block';
  document.getElementById('jarvisBubble').style.display   = 'none';
  document.getElementById('resultsArea').innerHTML =
    '<div class="idle-message"><p>Paste your resume and job description,<br>then click <strong>Analyze My Resume</strong>.</p></div>';
  setStatus('standby', false);
  setOrbState('idle'); setJarvisState('JARVIS ready');
}
