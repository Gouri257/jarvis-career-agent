// ============================================================
// PART 1: SETUP
// ============================================================

let pdfBase64   = null;   // stores uploaded PDF
let isRecording = false;  // is mic currently on?
let recognition = null;   // speech recognition object
let lastResult  = null;   // stores last analysis so Copy/PDF work
let isMuted     = false;  // is JARVIS voice muted?

// YOUR GROQ API KEY — get free at console.groq.com
const API_KEY = localStorage.getItem('groq_api_key') || '';


// ============================================================
// PART 2: JARVIS SPEAKS — Text to Speech
// This is what makes JARVIS talk back to you
// ============================================================

function jarvisSpeak(text, onDone) {
  // If muted, skip speaking but still run the callback
  if (isMuted) {
    setOrbState('idle');
    if (onDone) onDone();
    return;
  }

  // Cancel anything JARVIS is currently saying
  window.speechSynthesis.cancel();

  // Show what JARVIS is saying as text too
  const bubble     = document.getElementById('jarvisBubble');
  const bubbleText = document.getElementById('jarvisSpeechText');
  bubble.style.display   = 'block';
  bubbleText.textContent = text;

  // Set orb to speaking state
  setOrbState('speaking');
  setJarvisState('Speaking...');

  // Create the speech utterance
  const utterance    = new SpeechSynthesisUtterance(text);
  utterance.rate     = 0.95;  // slightly slower — clearer
  utterance.pitch    = 0.9;   // slightly deeper — more JARVIS-like
  utterance.volume   = 1;

  // Try to pick a good English voice
  const voices    = window.speechSynthesis.getVoices();
  const preferred = voices.find(function(v) {
    return v.name.includes('Google UK') ||
           v.name.includes('Daniel') ||
           v.name.includes('Microsoft David') ||
           (v.lang === 'en-GB' && v.localService);
  });
  if (preferred) utterance.voice = preferred;

  utterance.onend = function() {
    setOrbState('idle');
    setJarvisState('JARVIS ready');
    if (onDone) onDone();
  };

  utterance.onerror = function() {
    setOrbState('idle');
    setJarvisState('JARVIS ready');
    if (onDone) onDone();
  };

  window.speechSynthesis.speak(utterance);
}

// Toggle mute on/off
function toggleMute() {
  isMuted = !isMuted;
  const btn = document.getElementById('muteBtn');
  if (isMuted) {
    btn.textContent = '🔇';
    btn.classList.add('muted');
    window.speechSynthesis.cancel();
    setOrbState('idle');
    setJarvisState('JARVIS muted');
  } else {
    btn.textContent = '🔊';
    btn.classList.remove('muted');
    setJarvisState('JARVIS ready');
  }
}


// ============================================================
// PART 3: ORB STATE HELPER
// Controls what the JARVIS orb animation looks like
// ============================================================

function setOrbState(state) {
  const orb = document.getElementById('jarvisOrb');
  orb.classList.remove('speaking', 'listening');
  if (state === 'speaking')  orb.classList.add('speaking');
  if (state === 'listening') orb.classList.add('listening');
}

function setJarvisState(text) {
  document.getElementById('jarvisState').textContent = text;
}


// ============================================================
// PART 4: VOICE INPUT — User speaks to JARVIS
// ============================================================

function toggleVoice() {
  if (isRecording) {
    recognition.stop();
    return;
  }

  if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
    alert('Voice input only works in Google Chrome. Please use Chrome.');
    return;
  }

  // Stop JARVIS if it is currently speaking
  window.speechSynthesis.cancel();

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.lang             = 'en-US';
  recognition.continuous       = false;
  recognition.interimResults   = true;

  // Show words in real time as user speaks
  recognition.onresult = function(event) {
    let interimText = '';
    let finalText   = '';

    for (var i = event.resultIndex; i < event.results.length; i++) {
      var transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalText += transcript;
      } else {
        interimText += transcript;
      }
    }

    document.getElementById('voiceTranscript').textContent = finalText || interimText;

    if (finalText) {
      handleVoiceCommand(finalText.toLowerCase().trim());
    }
  };

  recognition.onstart = function() {
    isRecording = true;
    document.getElementById('micBtn').textContent = '⏹ Stop';
    document.getElementById('micBtn').classList.add('active');
    setOrbState('listening');
    setJarvisState('Listening...');
  };

  recognition.onend = function() {
    isRecording = false;
    document.getElementById('micBtn').textContent = '🎙 Hold to Speak';
    document.getElementById('micBtn').classList.remove('active');
    setOrbState('idle');
    setJarvisState('JARVIS ready');
    setTimeout(function() {
      document.getElementById('voiceTranscript').textContent = '';
    }, 3000);
  };

  recognition.onerror = function(event) {
    console.log('Voice error:', event.error);
    recognition.stop();
  };

  recognition.start();
}


// ============================================================
// PART 5: VOICE COMMAND HANDLER
// Decides what to do based on what the user said
// ============================================================

function handleVoiceCommand(command) {
  console.log('Voice command received:', command);

  // ANALYZE
  if (command.includes('analyze') || command.includes('start') || command.includes('go')) {
    jarvisSpeak('Starting analysis now. Please wait.', function() {
      runAnalysis();
    });
  }

  // SKILL GAPS
  else if (command.includes('gap') || command.includes('missing') || command.includes('skill')) {
    if (lastResult && lastResult.gaps) {
      var gapNames = lastResult.gaps.map(function(g) { return g.skill; }).join(', ');
      jarvisSpeak('Your skill gaps are: ' + gapNames + '. Would you like details on any of these?');
    } else {
      jarvisSpeak('I have not run an analysis yet. Please paste a job description and say analyze.');
    }
  }

  // READ A PROJECT
  else if (command.includes('project') || command.includes('first') || command.includes('second') || command.includes('third')) {
    if (lastResult && lastResult.new_projects && lastResult.new_projects.length > 0) {
      var projectIndex = 0;
      if (command.includes('second')) projectIndex = 1;
      if (command.includes('third'))  projectIndex = 2;
      var p = lastResult.new_projects[projectIndex];
      if (p) {
        var stepsText = p.steps.slice(0, 3).join('. ');
        jarvisSpeak(
          'Project ' + (projectIndex + 1) + ': ' + p.title + '. ' +
          p.why + '. ' +
          'Tech stack: ' + p.tech.join(', ') + '. ' +
          'First steps: ' + stepsText
        );
        // Open that card on the page
        var cardId = 'new_' + projectIndex;
        var body   = document.getElementById('body_' + cardId);
        var arrow  = document.getElementById('arrow_' + cardId);
        if (body && !body.classList.contains('open')) {
          body.classList.add('open');
          if (arrow) arrow.classList.add('open');
        }
      }
    } else {
      jarvisSpeak('No projects found yet. Please run an analysis first.');
    }
  }

  // DOWNLOAD PDF
  else if (command.includes('download') || command.includes('save') || command.includes('report') || command.includes('pdf')) {
    if (lastResult) {
      jarvisSpeak('Downloading your report now.');
      downloadPDF();
    } else {
      jarvisSpeak('There is no report yet. Please run an analysis first.');
    }
  }

  // COPY
  else if (command.includes('copy')) {
    if (lastResult) {
      jarvisSpeak('Copying your results to clipboard.');
      copyResults();
    } else {
      jarvisSpeak('Nothing to copy yet. Please run an analysis first.');
    }
  }

  // CLEAR
  else if (command.includes('clear') || command.includes('reset') || command.includes('start over')) {
    jarvisSpeak('Clearing everything. Ready for a new analysis.', function() {
      clearAll();
    });
  }

  // HELLO
  else if (command.includes('hello') || command.includes('hi') || command.includes('hey')) {
    jarvisSpeak('Hello! I am JARVIS, your career assistant. Upload your resume, paste a job description, and say analyze to get started.');
  }

  // HELP
  else if (command.includes('help') || command.includes('what can you do') || command.includes('commands')) {
    jarvisSpeak(
      'Here is what I can do. ' +
      'Say analyze to start the analysis. ' +
      'Say what are my skill gaps to hear your gaps. ' +
      'Say read the first project to hear project details. ' +
      'Say download report to save a PDF. ' +
      'Say clear to reset everything.'
    );
  }

  // HOW MANY
  else if (command.includes('how many')) {
    if (lastResult) {
      var n = (lastResult.new_projects || []).length + (lastResult.upgrade_projects || []).length;
      jarvisSpeak('I found ' + n + ' projects for you.');
    } else {
      jarvisSpeak('No results yet. Please run an analysis first.');
    }
  }

  // ANYTHING ELSE — treat as job description input
  else {
    var jdBox = document.getElementById('jdInput');
    if (jdBox.value.trim() === '') {
      jdBox.value = command;
      jarvisSpeak('Got it. I added that to the job description box. Say analyze when you are ready, or add more details.');
    } else {
      jdBox.value += ' ' + command;
      jarvisSpeak('Added to your job description. Say analyze when ready.');
    }
  }
}


// ============================================================
// PART 6: PDF UPLOAD
// ============================================================

document.getElementById('pdfInput').addEventListener('change', function() {
  var file = this.files[0];
  if (!file) return;

  document.getElementById('fileName').textContent = '✓ ' + file.name + ' loaded';
  document.getElementById('fileName').style.display = 'block';
  document.getElementById('uploadBox').classList.add('has-file');

  var reader = new FileReader();
  reader.onload = function(e) {
    pdfBase64 = e.target.result.split(',')[1];
    jarvisSpeak('Resume PDF loaded. Now paste the job description and say analyze, or click the Analyze button.');
  };
  reader.readAsDataURL(file);
});


// ============================================================
// PART 7: LOADING SPINNER
// ============================================================

var spinnerMessages = [
  'Reading your resume...',
  'Analyzing the job description...',
  'Finding skill gaps...',
  'Generating project ideas...',
  'Building your roadmap...'
];

var spinnerInterval = null;

function showSpinner() {
  document.getElementById('resultsArea').style.display   = 'none';
  document.getElementById('loadingSpinner').style.display = 'block';
  document.getElementById('resultActions').style.display  = 'none';

  var msgIndex = 0;
  document.getElementById('spinnerText').textContent = spinnerMessages[0];
  spinnerInterval = setInterval(function() {
    msgIndex = (msgIndex + 1) % spinnerMessages.length;
    document.getElementById('spinnerText').textContent = spinnerMessages[msgIndex];
  }, 2000);
}

function hideSpinner() {
  clearInterval(spinnerInterval);
  document.getElementById('loadingSpinner').style.display = 'none';
  document.getElementById('resultsArea').style.display   = 'block';
}


// ============================================================
// PART 8: MAIN ANALYSIS — calls Groq AI
// ============================================================

async function runAnalysis() {
  var jd         = document.getElementById('jdInput').value.trim();
  var resumeText = document.getElementById('resumeText').value.trim();

  if (!jd) {
    jarvisSpeak('Please paste a job description first. I need to know what role you are applying for.');
    return;
  }

  document.getElementById('analyzeBtn').textContent = 'Analyzing...';
  document.getElementById('analyzeBtn').disabled    = true;
  setStatus('analyzing', true);
  showSpinner();

  var resumeSection = '';
  if (resumeText) {
    resumeSection = '\nHere is the candidate\'s resume:\n---\n' + resumeText + '\n---\nAnalyze this resume carefully and give personalised, specific gaps and project ideas.';
  } else if (pdfBase64) {
    resumeSection = '\nThe user uploaded a PDF resume but it cannot be read in this version. Generate suggestions from the job description alone. Set upgrade_projects to an empty array.';
  } else {
    resumeSection = '\nNo resume provided. Generate suggestions from the job description alone. Set upgrade_projects to an empty array.';
  }

  var fullPrompt = 'You are JARVIS, an expert career coach AI.\n' +
    'Analyze the candidate profile against the job description.\n' +
    'Return ONLY a valid JSON object. No markdown. No explanation. Just raw JSON.\n\n' +
    'Structure:\n' +
    '{\n' +
    '  "role": "exact job title from the JD",\n' +
    '  "gaps": [\n' +
    '    {"skill": "skill name", "reason": "why this matters for this specific role"}\n' +
    '  ],\n' +
    '  "new_projects": [\n' +
    '    {\n' +
    '      "title": "specific project name",\n' +
    '      "why": "one sentence why this impresses for this exact role",\n' +
    '      "tech": ["tech1", "tech2", "tech3"],\n' +
    '      "steps": ["step 1", "step 2", "step 3", "step 4"]\n' +
    '    }\n' +
    '  ],\n' +
    '  "upgrade_projects": [\n' +
    '    {\n' +
    '      "title": "existing project + what to add",\n' +
    '      "why": "why this upgrade matters",\n' +
    '      "tech": ["tech1"],\n' +
    '      "steps": ["step 1", "step 2", "step 3"]\n' +
    '    }\n' +
    '  ]\n' +
    '}\n\n' +
    'Rules:\n' +
    '- 3 to 4 skill gaps\n' +
    '- 2 to 3 new projects\n' +
    '- 1 to 2 upgrade projects (or empty array)\n' +
    '- Be specific to this JD — no generic advice\n' +
    '- Steps must be concrete and actionable\n\n' +
    'Job Description:\n' + jd + '\n' + resumeSection;

  try {
    var response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': 'Bearer ' + API_KEY
      },
      body: JSON.stringify({
        model: 'llama-3.3-70b-versatile',
        messages: [
          { role: 'system', content: fullPrompt },
          { role: 'user',   content: 'Analyze and return the JSON now.' }
        ],
        max_tokens:  1500,
        temperature: 0.7
      })
    });

    var data = await response.json();
    console.log('Groq response:', data);

    if (data.error) {
      showError('API Error: ' + data.error.message);
      jarvisSpeak('There was an error: ' + data.error.message);
      return;
    }

    if (!data.choices || data.choices.length === 0) {
      showError('Empty response from Groq. Please try again.');
      jarvisSpeak('I received an empty response. Please try again.');
      return;
    }

    var rawText = data.choices[0].message.content;
    var clean   = rawText.replace(/```json|```/g, '').trim();

    var result;
    try {
      result = JSON.parse(clean);
    } catch (e) {
      showError('Could not parse response as JSON.');
      jarvisSpeak('I had trouble reading the response. Please try again.');
      resetButton();
      return;
    }

    lastResult = result;
    hideSpinner();
    renderResults(result);
    document.getElementById('resultActions').style.display = 'flex';
    setStatus('complete', true);

    // JARVIS speaks a summary
    var gapCount     = (result.gaps || []).length;
    var projectCount = (result.new_projects || []).length;
    var firstName    = result.new_projects && result.new_projects[0] ? result.new_projects[0].title : 'some great projects';

    jarvisSpeak(
      'Analysis complete for ' + result.role + '. ' +
      'I found ' + gapCount + ' skill gaps and ' + projectCount + ' projects for you to build. ' +
      'The first project is ' + firstName + '. ' +
      'Click any project card to see the step by step guide, or say read the first project.'
    );

  } catch (error) {
    showError('Network error: ' + error.message);
    jarvisSpeak('I could not connect to the server. Please check your internet and try again.');
  }

  resetButton();
}


// ============================================================
// PART 9: RENDER RESULTS
// ============================================================

function renderResults(result) {
  var html = '';

  html += '<h2>Skill Gaps for "' + (result.role || 'this role') + '"</h2>';
  if (result.gaps && result.gaps.length > 0) {
    result.gaps.forEach(function(gap) {
      html += '<div class="gap-card"><strong>' + gap.skill + '</strong><p>' + gap.reason + '</p></div>';
    });
  }

  html += '<h2>Projects to Build</h2>';
  if (result.new_projects && result.new_projects.length > 0) {
    result.new_projects.forEach(function(p, i) {
      html += buildProjectCard(p, 'new_' + i, 'NEW', 'badge-new');
    });
  }

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
// PART 10: COPY RESULTS
// ============================================================

function copyResults() {
  if (!lastResult) return;

  var text = 'JARVIS CAREER ANALYSIS\n' + '='.repeat(40) + '\nRole: ' + lastResult.role + '\n\n';
  text += 'SKILL GAPS\n' + '-'.repeat(30) + '\n';
  lastResult.gaps.forEach(function(gap, i) {
    text += (i + 1) + '. ' + gap.skill + '\n   ' + gap.reason + '\n\n';
  });
  text += 'PROJECTS TO BUILD\n' + '-'.repeat(30) + '\n';
  lastResult.new_projects.forEach(function(p, i) {
    text += (i + 1) + '. ' + p.title + '\n   Why: ' + p.why + '\n   Tech: ' + p.tech.join(', ') + '\n   Steps:\n';
    p.steps.forEach(function(s, j) { text += '     ' + (j + 1) + '. ' + s + '\n'; });
    text += '\n';
  });
  if (lastResult.upgrade_projects && lastResult.upgrade_projects.length > 0) {
    text += 'PROJECTS TO UPGRADE\n' + '-'.repeat(30) + '\n';
    lastResult.upgrade_projects.forEach(function(p, i) {
      text += (i + 1) + '. ' + p.title + '\n   Why: ' + p.why + '\n   Tech: ' + p.tech.join(', ') + '\n   Steps:\n';
      p.steps.forEach(function(s, j) { text += '     ' + (j + 1) + '. ' + s + '\n'; });
      text += '\n';
    });
  }

  navigator.clipboard.writeText(text).then(function() {
    var btn = document.getElementById('copyBtn');
    btn.textContent = '✓ Copied!';
    btn.classList.add('copied');
    setTimeout(function() { btn.textContent = '📋 Copy Results'; btn.classList.remove('copied'); }, 2500);
  }).catch(function() { alert('Could not copy. Please select the text manually.'); });
}


// ============================================================
// PART 11: DOWNLOAD PDF
// ============================================================

function downloadPDF() {
  if (!lastResult) return;
  var jsPDF      = window.jspdf.jsPDF;
  var doc        = new jsPDF();
  var pageWidth  = doc.internal.pageSize.getWidth();
  var margin     = 20;
  var cw         = pageWidth - margin * 2;
  var y          = 20;

  function addText(text, fs, bold, c) {
    doc.setFontSize(fs);
    doc.setFont('helvetica', bold ? 'bold' : 'normal');
    doc.setTextColor(c[0], c[1], c[2]);
    var lines = doc.splitTextToSize(text, cw);
    lines.forEach(function(line) {
      if (y > 270) { doc.addPage(); y = 20; }
      doc.text(line, margin, y);
      y += fs * 0.5;
    });
    y += 2;
  }

  function addLine() { doc.setDrawColor(220,220,220); doc.line(margin, y, pageWidth-margin, y); y += 6; }

  function addHeading(text) {
    y += 4;
    doc.setFillColor(245,245,245);
    doc.rect(margin, y-5, cw, 10, 'F');
    addText(text.toUpperCase(), 9, true, [120,120,120]);
    y += 2;
  }

  doc.setFillColor(17,17,17); doc.rect(0,0,pageWidth,28,'F');
  doc.setFontSize(16); doc.setFont('helvetica','bold'); doc.setTextColor(255,255,255);
  doc.text('JARVIS — Career Agent', margin, 17);
  doc.setFontSize(9); doc.setFont('helvetica','normal'); doc.setTextColor(180,180,180);
  doc.text('Resume Analysis Report', margin, 24);
  var ds = new Date().toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'});
  doc.text(ds, pageWidth - margin - doc.getTextWidth(ds), 24);

  y = 40;
  addText('Target Role: ' + lastResult.role, 14, true, [30,30,30]);
  addLine();
  addHeading('Skill Gaps');
  lastResult.gaps.forEach(function(gap,i) {
    addText((i+1)+'.  '+gap.skill, 11, true, [180,60,0]);
    addText('     '+gap.reason, 10, false, [100,60,40]);
    y += 2;
  });
  addHeading('Projects to Build');
  lastResult.new_projects.forEach(function(p,i) {
    y += 2;
    addText((i+1)+'.  '+p.title, 11, true, [17,85,170]);
    addText('     '+p.why, 10, false, [80,80,80]);
    addText('     Tech: '+p.tech.join(', '), 9, false, [120,120,120]);
    addText('     Steps:', 9, true, [80,80,80]);
    p.steps.forEach(function(s,j) { addText('       '+(j+1)+'. '+s, 9, false, [60,60,60]); });
    y += 3;
  });
  if (lastResult.upgrade_projects && lastResult.upgrade_projects.length > 0) {
    addHeading('Projects to Upgrade');
    lastResult.upgrade_projects.forEach(function(p,i) {
      y += 2;
      addText((i+1)+'.  '+p.title, 11, true, [170,100,0]);
      addText('     '+p.why, 10, false, [80,80,80]);
      addText('     Tech: '+p.tech.join(', '), 9, false, [120,120,120]);
      addText('     Steps:', 9, true, [80,80,80]);
      p.steps.forEach(function(s,j) { addText('       '+(j+1)+'. '+s, 9, false, [60,60,60]); });
      y += 3;
    });
  }
  var pc = doc.internal.getNumberOfPages();
  for (var i = 1; i <= pc; i++) {
    doc.setPage(i); doc.setFontSize(8); doc.setTextColor(180,180,180);
    doc.text('Generated by JARVIS Career Agent · Page '+i+' of '+pc, margin, 290);
  }
  doc.save('JARVIS_Analysis_' + (lastResult.role || 'Report').replace(/\s+/g, '_') + '.pdf');
}


// ============================================================
// PART 12: HELPERS
// ============================================================

function setStatus(text, active) {
  var pill = document.getElementById('statusPill');
  pill.textContent = text;
  if (active) pill.classList.add('active');
  else        pill.classList.remove('active');
}

function resetButton() {
  document.getElementById('analyzeBtn').textContent = 'Analyze My Resume →';
  document.getElementById('analyzeBtn').disabled    = false;
}

function showError(msg) {
  hideSpinner();
  document.getElementById('resultsArea').innerHTML =
    '<div style="background:#fff5f5;border:1px solid #ffcccc;border-radius:8px;padding:16px;font-size:13px;color:#cc0000;line-height:1.7">⚠️ ' + msg + '</div>';
  setStatus('error', false);
  resetButton();
}

function clearAll() {
  pdfBase64  = null;
  lastResult = null;
  document.getElementById('pdfInput').value   = '';
  document.getElementById('jdInput').value    = '';
  document.getElementById('resumeText').value = '';
  document.getElementById('fileName').style.display       = 'none';
  document.getElementById('uploadBox').classList.remove('has-file');
  document.getElementById('resultActions').style.display  = 'none';
  document.getElementById('loadingSpinner').style.display = 'none';
  document.getElementById('resultsArea').style.display    = 'block';
  document.getElementById('jarvisBubble').style.display   = 'none';
  document.getElementById('resultsArea').innerHTML =
    '<div class="idle-message"><p>Upload your resume and paste a job description,<br>then click <strong>Analyze My Resume</strong> or use your voice.</p></div>';
  setStatus('standby', false);
  setOrbState('idle');
  setJarvisState('JARVIS ready');
}

// Greet user on page load
window.addEventListener('load', function() {
  setTimeout(function() {
    jarvisSpeak(
      'Hello. I am JARVIS, your career assistant. ' +
      'Paste your resume text and the job description, then click Analyze, ' +
      'or press the microphone button and talk to me.'
    );
  }, 1000);
});

// Saves the API key to the browser's local storage
function saveKey() {
  const key = document.getElementById('apiKeyInput').value.trim();
  if (key) {
    localStorage.setItem('groq_api_key', key);
    document.getElementById('keySetup').style.display = 'none';
    alert('Key saved! You can now use JARVIS.');
  } else {
    alert('Please paste your Groq API key first.');
  }
}

// When page loads — if key already saved, hide the setup bar
window.addEventListener('load', function() {
  if (localStorage.getItem('groq_api_key')) {
    document.getElementById('keySetup').style.display = 'none';
  }
});