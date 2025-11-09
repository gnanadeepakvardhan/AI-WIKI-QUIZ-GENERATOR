const apiBase = ""; // same origin

function $(id){return document.getElementById(id)}

// Tabs
$('tab-generate').addEventListener('click', ()=>{switchTab('generate')})
$('tab-history').addEventListener('click', ()=>{switchTab('history'); loadHistory()})

function switchTab(tab){
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'))
  document.querySelectorAll('.panel').forEach(p=>p.classList.add('hidden'))
  if(tab==='generate'){
    $('tab-generate').classList.add('active'); $('panel-generate').classList.remove('hidden')
  } else { $('tab-history').classList.add('active'); $('panel-history').classList.remove('hidden') }
}

// Generate quiz
$('generate-btn').addEventListener('click', async ()=>{
  const url = $('url-input').value.trim();
  if(!url){ alert('Please enter a Wikipedia URL'); return }
  $('generate-result').innerHTML = '<div class="card">Generating quiz... (may take a few seconds)</div>'
  try{
    const res = await fetch(apiBase + '/generate_quiz', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url})})
    if(!res.ok){ const e = await res.json(); throw new Error(e.detail || 'Request failed') }
    const data = await res.json()
    renderQuiz(data, $('generate-result'))
  }catch(err){ $('generate-result').innerHTML = `<div class="card">Error: ${err.message}</div>` }
})

function renderQuiz(data, container){
  const el = document.createElement('div'); el.className='card'
  el.innerHTML = `<h3>${escapeHtml(data.title || '')}</h3><p>${escapeHtml(data.summary||'')}</p>`
  const qlist = document.createElement('div')
  data.quiz.forEach((q, idx)=>{
    const qdiv = document.createElement('div'); qdiv.className='card'
    qdiv.innerHTML = `<strong>Q${idx+1} (${q.difficulty})</strong><p>${escapeHtml(q.question)}</p>`
    const ol = document.createElement('ol')
    q.options.forEach(opt=>{ const li = document.createElement('li'); li.textContent = opt; ol.appendChild(li) })
    qdiv.appendChild(ol)
    qdiv.innerHTML += `<p><em>Answer:</em> ${escapeHtml(q.answer)}<br/><em>Explanation:</em> ${escapeHtml(q.explanation)}</p>`
    qlist.appendChild(qdiv)
  })
  el.appendChild(qlist)
  if(data.related_topics && data.related_topics.length){
    const r = document.createElement('div'); r.innerHTML = '<strong>Related topics:</strong> ' + data.related_topics.map(escapeHtml).join(', ')
    el.appendChild(r)
  }
  container.innerHTML = '';
  container.appendChild(el)
}

// History
async function loadHistory(){
  const tbody = document.querySelector('#history-table tbody');
  tbody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>'
  try{
    const res = await fetch(apiBase + '/history');
    const rows = await res.json();
    tbody.innerHTML = '';
    rows.forEach(r=>{
      const tr = document.createElement('tr')
      tr.innerHTML = `<td>${r.id}</td><td>${escapeHtml(r.title||'')}</td><td><a href="${escapeHtml(r.url)}" target="_blank">link</a></td><td><button data-id="${r.id}" class="details-btn">Details</button></td>`
      tbody.appendChild(tr)
    })
    document.querySelectorAll('.details-btn').forEach(b=>b.addEventListener('click', e=>{ showDetails(e.target.dataset.id) }))
  }catch(err){ tbody.innerHTML = `<tr><td colspan="4">Error: ${err.message}</td></tr>` }
}

async function showDetails(id){
  try{
    const res = await fetch(apiBase + '/quiz/' + id)
    const data = await res.json()
    $('modal-body').innerHTML = '';
    renderQuiz(data, $('modal-body'))
    showModal();
  }catch(err){ alert('Failed to fetch details: '+err.message) }
}

// ✅ Modal logic
function showModal() {
  $('modal').classList.add('show');
}

function hideModal() {
  $('modal').classList.remove('show');
}

$('modal-close').addEventListener('click', hideModal);

function escapeHtml(s){ return String(s || '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;') }

switchTab('generate');
