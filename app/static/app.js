// Global State
let currentTab = 'miner-tab';
let isLive = false;

// Custom Lightweight Markdown Parser
function parseMarkdown(md) {
    if (!md) return "";
    let html = md;
    
    // Headings
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Blockquotes
    html = html.replace(/^\>\s+\[\!IMPORTANT\](.*$)/gim, '<blockquote><strong>Important:</strong> $1</blockquote>');
    html = html.replace(/^\>\s+\[\!WARNING\](.*$)/gim, '<blockquote><strong>Warning:</strong> $1</blockquote>');
    html = html.replace(/^\>\s+(.*$)/gim, '<blockquote>$1</blockquote>');
    
    // Bold / Italic
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Lists
    // Match bullet items and wrap them
    html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
    // Simple wrapping for consecutive list items (crude but works for output format)
    html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    
    // Links
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Paragraphs & newlines
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initMiner();
    initValidator();
    loadHistory();
    checkAPIStatus();
});

// Check whether backend is in LIVE or SIMULATION mode
async function checkAPIStatus() {
    try {
        const response = await fetch('/api/history/mining');
        // If the database returns records or loads fine, we can check if credentials are set
        // For simplicity, we query a status from history or we add one
        const statusInd = document.getElementById('live-indicator');
        const statusLabel = statusInd.querySelector('.status-label');
        
        // Let's call a quick check (we will add a simple endpoint, or check headers)
        const statusRes = await fetch('/api/status').then(r => r.json()).catch(() => ({live: false}));
        if (statusRes.live) {
            isLive = true;
            statusInd.classList.add('live-active');
            statusLabel.textContent = "Live Mode Active";
        } else {
            isLive = false;
            statusInd.classList.remove('live-active');
            statusLabel.textContent = "Simulation Mode";
        }
    } catch (e) {
        console.error("Failed to check status", e);
    }
}

// Tab Switching
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            navButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
            
            currentTab = targetTab;
            
            if (targetTab === 'history-tab') {
                loadHistory();
            }
        });
    });
}

// Subreddit Miner Interface
function initMiner() {
    const form = document.getElementById('miner-form');
    const slider = document.getElementById('lookback-slider');
    const sliderVal = document.getElementById('lookback-val');
    const loading = document.getElementById('miner-loading');
    const results = document.getElementById('miner-results');
    const clustersList = document.getElementById('clusters-list');
    
    // Update Slider text
    slider.addEventListener('input', (e) => {
        sliderVal.textContent = e.target.value;
    });
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const subreddit = document.getElementById('subreddit-input').value.trim();
        const lookback = parseInt(slider.value);
        
        if (!subreddit) return;
        
        // Reset view
        results.classList.add('hidden');
        loading.classList.remove('hidden');
        resetLoadingSteps('miner-loading');
        
        // Animate fake steps for visual engagement (even in simulation)
        const stepElements = loading.querySelectorAll('.step');
        animateStepProgress(stepElements, 0, 8000); // 8 seconds total fake progress pacing
        
        try {
            const response = await fetch('/api/mine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subreddit, lookback_days: lookback })
            });
            
            if (!response.ok) throw new Error(await response.text());
            
            const data = await response.json();
            
            // Mark all steps complete
            stepElements.forEach(s => {
                s.classList.add('done');
                s.classList.remove('active');
            });
            
            setTimeout(() => {
                loading.classList.add('hidden');
                renderClusters(data.clusters, subreddit);
                results.classList.remove('hidden');
            }, 500);
            
        } catch (error) {
            alert(`Error running scan: ${error.message}`);
            loading.classList.add('hidden');
        }
    });
}

// Animate loading step progressions
function animateStepProgress(steps, index, totalTime) {
    if (index >= steps.length) return;
    
    steps.forEach((s, i) => {
        if (i < index) {
            s.className = 'step done';
        } else if (i === index) {
            s.className = 'step active';
        } else {
            s.className = 'step';
        }
    });
    
    const stepDelay = totalTime / steps.length;
    setTimeout(() => {
        animateStepProgress(steps, index + 1, totalTime);
    }, stepDelay);
}

function resetLoadingSteps(containerId) {
    const steps = document.querySelectorAll(`#${containerId} .step`);
    steps.forEach((s, idx) => {
        s.className = idx === 0 ? 'step active' : 'step';
    });
}

// Render Pain Point Clusters
function renderClusters(clusters, subreddit) {
    const list = document.getElementById('clusters-list');
    list.innerHTML = '';
    
    if (!clusters || clusters.length === 0) {
        list.innerHTML = '<div class="card empty-state">No significant pain points surfaced. Try a different subreddit.</div>';
        return;
    }
    
    clusters.forEach((cluster, idx) => {
        const card = document.createElement('div');
        card.className = 'card cluster-card';
        
        const header = document.createElement('div');
        header.className = 'cluster-header';
        
        // Dynamic title & sub info
        const titleArea = document.createElement('div');
        titleArea.className = 'cluster-title-area';
        titleArea.innerHTML = `
            <h4>${cluster.title}</h4>
            <p>${cluster.description}</p>
        `;
        
        const meta = document.createElement('div');
        meta.className = 'cluster-meta';
        meta.innerHTML = `
            <span class="badge badge-freq">${cluster.frequency} mentions</span>
            <span class="badge badge-engagement">~${cluster.avg_engagement} Upvotes</span>
            <span class="toggle-icon">▼</span>
        `;
        
        header.appendChild(titleArea);
        header.appendChild(meta);
        card.appendChild(header);
        
        // Details panel (hidden by default)
        const details = document.createElement('div');
        details.className = 'cluster-details';
        
        let quotesHtml = '';
        cluster.representative_quotes.forEach(q => {
            quotesHtml += `
                <div class="quote-item">
                    <p>"${q.quote}"</p>
                    <a href="${q.url || '#'}" target="_blank" class="quote-link">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        View Original Thread
                    </a>
                </div>
            `;
        });
        
        details.innerHTML = `
            <div class="quotes-section">
                <h5>Community Evidence Quotes</h5>
                ${quotesHtml}
            </div>
            <div class="cluster-actions">
                <button class="btn btn-secondary btn-sm btn-validate-pain" data-title="${cluster.title}" data-niche="${subreddit}">
                    Validate Solution for this Pain
                </button>
            </div>
        `;
        
        card.appendChild(details);
        list.appendChild(card);
        
        // Expand/collapse click listener
        header.addEventListener('click', () => {
            card.classList.toggle('expanded');
        });
        
        // Validate button click
        const validateBtn = details.querySelector('.btn-validate-pain');
        validateBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            triggerValidationPreFill(cluster.title, subreddit);
        });
    });
}

// Fill Idea Validator from a cluster
function triggerValidationPreFill(title, niche) {
    document.getElementById('idea-name').value = `Solve: ${title.split(' & ')[0].split(' / ')[0]}`;
    document.getElementById('idea-niche').value = `r/${niche} users`;
    document.getElementById('idea-description').value = `An automated, lightweight platform targeting the core problems of: ${title.toLowerCase()}.`;
    
    // Switch Tab to Validator
    const valTabButton = document.querySelector('.nav-item[data-tab="validator-tab"]');
    if (valTabButton) valTabButton.click();
}

// Idea Validator Interface
function initValidator() {
    const form = document.getElementById('validator-form');
    const loading = document.getElementById('validator-loading');
    const results = document.getElementById('validator-results');
    const copyBtn = document.getElementById('btn-export-report');
    let generatedReportMd = "";
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('idea-name').value.trim();
        const niche = document.getElementById('idea-niche').value.trim();
        const description = document.getElementById('idea-description').value.trim();
        
        if (!name || !description) return;
        
        results.classList.add('hidden');
        loading.classList.remove('hidden');
        resetLoadingSteps('validator-loading');
        
        // Animate progress steps
        const stepElements = loading.querySelectorAll('.step');
        animateStepProgress(stepElements, 0, 6000);
        
        try {
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    idea_name: name,
                    idea_text: description,
                    target_niche: niche
                })
            });
            
            if (!response.ok) throw new Error(await response.text());
            
            const data = await response.json();
            generatedReportMd = data.report_md;
            
            // Mark all steps complete
            stepElements.forEach(s => {
                s.classList.add('done');
                s.classList.remove('active');
            });
            
            setTimeout(() => {
                loading.classList.add('hidden');
                renderValidationReport(data);
                results.classList.remove('hidden');
            }, 500);
            
        } catch (error) {
            alert(`Error validating idea: ${error.message}`);
            loading.classList.add('hidden');
        }
    });
    
    copyBtn.addEventListener('click', () => {
        if (!generatedReportMd) return;
        navigator.clipboard.writeText(generatedReportMd).then(() => {
            alert('Feasibility report copied as Markdown!');
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    });
}

// Render Validation Report Gauges and Content
function renderValidationReport(data) {
    const score = data.demand_score;
    const scoreDisplay = document.getElementById('score-display');
    const gaugeFill = document.getElementById('gauge-fill');
    const verdict = document.getElementById('verdict-display');
    
    // Set score number
    scoreDisplay.textContent = score;
    
    // Set radial gauge fill offset
    // Radius of SVG circle is 70, Circumference is 2 * pi * 70 = ~440
    const circumference = 440;
    const offset = circumference - (score / 100) * circumference;
    gaugeFill.style.strokeDashoffset = offset;
    
    // Verdict classifications
    verdict.className = 'score-verdict';
    if (score >= 75) {
        verdict.textContent = "Strong Signal";
        verdict.classList.add('verdict-high');
        gaugeFill.style.stroke = "var(--accent-green)";
    } else if (score >= 60) {
        verdict.textContent = "Moderate Signal";
        verdict.classList.add('verdict-medium');
        gaugeFill.style.stroke = "var(--accent-cyan)";
    } else if (score >= 40) {
        verdict.textContent = "Weak Signal";
        verdict.classList.add('verdict-low');
        gaugeFill.style.stroke = "var(--accent-orange)";
    } else {
        verdict.textContent = "Poor Fit";
        verdict.classList.add('verdict-poor');
        gaugeFill.style.stroke = "var(--accent-red)";
    }
    
    // Set components bar charts
    const breakdown = data.score_breakdown;
    document.getElementById('breakdown-freq-num').textContent = `${breakdown.frequency}%`;
    document.getElementById('breakdown-freq-bar').style.width = `${breakdown.frequency}%`;
    
    document.getElementById('breakdown-intensity-num').textContent = `${breakdown.intensity}%`;
    document.getElementById('breakdown-intensity-bar').style.width = `${breakdown.intensity}%`;
    
    document.getElementById('breakdown-engagement-num').textContent = `${breakdown.engagement}%`;
    document.getElementById('breakdown-engagement-bar').style.width = `${breakdown.engagement}%`;
    
    document.getElementById('breakdown-gap-num').textContent = `${breakdown.solution_gap}%`;
    document.getElementById('breakdown-gap-bar').style.width = `${breakdown.solution_gap}%`;
    
    document.getElementById('breakdown-trend-num').textContent = `${breakdown.trend}%`;
    document.getElementById('breakdown-trend-bar').style.width = `${breakdown.trend}%`;
    
    // Render Markdown Report
    const reportBody = document.getElementById('report-md-content');
    reportBody.innerHTML = parseMarkdown(data.report_md);
}

// History & Database Tab loading
async function loadHistory() {
    try {
        const [nichesRes, valRes] = await Promise.all([
            fetch('/api/history/mining'),
            fetch('/api/history/validations')
        ]);
        
        const niches = await nichesRes.json();
        const validations = await valRes.json();
        
        renderNicheHistory(niches);
        renderValidationHistory(validations);
    } catch (e) {
        console.error("Failed to load history lists", e);
    }
}

function renderNicheHistory(niches) {
    const list = document.getElementById('mined-niches-list');
    list.innerHTML = '';
    
    if (!niches || niches.length === 0) {
        list.innerHTML = '<div class="empty-state">No niches scanned yet. Go to the Niche Miner tab to scan one.</div>';
        return;
    }
    
    niches.forEach(n => {
        const item = document.createElement('div');
        item.className = 'history-item';
        
        const dateStr = n.last_scraped_at ? new Date(n.last_scraped_at).toLocaleDateString() : 'Never';
        item.innerHTML = `
            <div class="history-item-header">
                <span class="history-item-title">r/${n.subreddit}</span>
                <span class="history-item-meta">${dateStr}</span>
            </div>
            <div class="history-item-sub">${n.clusters.length} pain themes clustered</div>
        `;
        
        item.addEventListener('click', () => {
            // Load this subreddit's details back into Miner tab
            renderClusters(n.clusters, n.subreddit);
            document.getElementById('subreddit-input').value = n.subreddit;
            
            // Switch tabs
            document.querySelector('.nav-item[data-tab="miner-tab"]').click();
            document.getElementById('miner-results').classList.remove('hidden');
        });
        
        list.appendChild(item);
    });
}

function renderValidationHistory(validations) {
    const list = document.getElementById('validation-reports-list');
    list.innerHTML = '';
    
    if (!validations || validations.length === 0) {
        list.innerHTML = '<div class="empty-state">No reports generated yet. Run a validation on the Validator tab.</div>';
        return;
    }
    
    validations.forEach(v => {
        const item = document.createElement('div');
        item.className = 'history-item';
        
        const dateStr = new Date(v.created_at).toLocaleDateString();
        item.innerHTML = `
            <div class="history-item-header">
                <span class="history-item-title">${v.idea_name}</span>
                <span class="history-score-badge">${v.demand_score}/100</span>
            </div>
            <div class="history-item-sub">${v.target_niche} • ${dateStr}</div>
        `;
        
        item.addEventListener('click', () => {
            // Load validation data back into Validator results view
            const data = {
                demand_score: v.demand_score,
                score_breakdown: v.score_breakdown,
                report_md: v.report_md,
                idea_name: v.idea_name,
                idea_text: v.idea_text,
                target_niche: v.target_niche
            };
            
            renderValidationReport(data);
            
            // Set input values
            document.getElementById('idea-name').value = v.idea_name;
            document.getElementById('idea-niche').value = v.target_niche;
            document.getElementById('idea-description').value = v.idea_text;
            
            // Switch tabs
            document.querySelector('.nav-item[data-tab="validator-tab"]').click();
            document.getElementById('validator-results').classList.remove('hidden');
        });
        
        list.appendChild(item);
    });
}
