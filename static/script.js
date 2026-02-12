// Global variable to store bot's bowling choice
let storedBotChoice = null;
let storedScores = null;  // Cache scores so we don't refetch unnecessarily

function updateDropdowns() {
    const bowlingType = document.getElementById("bowling_type")?.value || 
                        document.getElementById("bowlingTypeSelect")?.value;

    if (!bowlingType) return;

    fetch(`/get_sheet_data/${bowlingType}`)
        .then(response => response.json())
        .then(data => {
            populateDropdown("line", data.lines);
            populateDropdown("length", data.lengths);
            populateDropdown("variation", data.variations);
            populateDropdown("shot", data.shots);
        });
}

function populateDropdown(id, values) {
    const dropdown = document.getElementById(id) || 
                     document.getElementById(id + "Select");
    if (!dropdown) return;
    
    dropdown.innerHTML = "";
    values.forEach(value => {
        const option = document.createElement("option");
        option.value = value;
        option.text = value;
        dropdown.appendChild(option);
    });
}

// Show bot choice automatically on page load
document.addEventListener('DOMContentLoaded', function() {
    const showScoreCheckbox = document.getElementById('showScoreCheckbox');
    const isBatting = document.getElementById('shotSelect') !== null;
    
    if (isBatting) {
        // Auto-show bot's bowling choice when page loads (fetch ONCE)
        showBotChoice();
    }
    
    if (showScoreCheckbox) {
        showScoreCheckbox.addEventListener('change', function() {
            if (this.checked) {
                // Show scores - fetch if not already cached
                if (storedScores) {
                    displayBattingScores(storedBotChoice, storedScores);
                } else {
                    fetchAndCacheScores();
                }
            } else {
                document.getElementById('effectiveScoresDiv').style.display = 'none';
            }
        });
    }

    // Handle bowling type change to update other dropdowns
    const bowlingTypeSelect = document.getElementById('bowlingTypeSelect');
    if (bowlingTypeSelect) {
        bowlingTypeSelect.addEventListener('change', function() {
            updateDropdowns();
            const checkBox = document.getElementById('showScoreCheckbox');
            if (checkBox && checkBox.checked) {
                // For bowling, fetch new scores based on new selections
                fetchAndDisplayBowlingScores();
            }
        });
    }

    // Handle line changes for bowling
    const lineSelect = document.getElementById('lineSelect');
    if (lineSelect) {
        lineSelect.addEventListener('change', function() {
            const checkBox = document.getElementById('showScoreCheckbox');
            if (checkBox && checkBox.checked) {
                fetchAndDisplayBowlingScores();
            }
        });
    }

    // Handle length changes for bowling
    const lengthSelect = document.getElementById('lengthSelect');
    if (lengthSelect) {
        lengthSelect.addEventListener('change', function() {
            const checkBox = document.getElementById('showScoreCheckbox');
            if (checkBox && checkBox.checked) {
                fetchAndDisplayBowlingScores();
            }
        });
    }

    // Handle variation changes for bowling
    const variationSelect = document.getElementById('variationSelect');
    if (variationSelect) {
        variationSelect.addEventListener('change', function() {
            const checkBox = document.getElementById('showScoreCheckbox');
            if (checkBox && checkBox.checked) {
                fetchAndDisplayBowlingScores();
            }
        });
    }

    // Shot selection should NOT trigger new requests - just display cached scores
    const shotSelect = document.getElementById('shotSelect');
    if (shotSelect) {
        shotSelect.addEventListener('change', function() {
            // Don't fetch - just re-display scores with new shot highlighted
            const checkBox = document.getElementById('showScoreCheckbox');
            if (checkBox && checkBox.checked && storedScores) {
                displayBattingScores(storedBotChoice, storedScores);
            }
        });
    }

    updateDropdowns();
});

// ✅ NEW: Reset cached data before page navigates away (for new ball)
window.addEventListener('beforeunload', function() {
    storedBotChoice = null;
    storedScores = null;
});

// Fetch bot's bowling choice ONCE on page load
function showBotChoice() {
    fetch('/get_effective_scores', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'action': 'batting'
        })
    })
    .then(response => response.json())
    .then(data => {
        storedBotChoice = data.bot_choice;  // Store it for this ball only
        storedScores = null;  // Reset scores cache
        displayBotChoiceOnly(data.bot_choice);
    })
    .catch(error => console.error('Error:', error));
}

// Display only bot's choice (no scores yet)
function displayBotChoiceOnly(botChoice) {
    const botChoiceDiv = document.getElementById('botChoice');
    const botChoiceText = document.getElementById('botChoiceText');
    
    botChoiceText.innerHTML = `
        <div style="font-size: 1.05em; line-height: 1.8;">
            <strong style="display: block; margin-bottom: 10px; color: #ff6b6b;">🎯 BOT IS BOWLING:</strong>
            <div style="background: rgba(0,0,0,0.1); padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                <div><strong>Type:</strong> ${botChoice.bowling_type}</div>
                <div><strong>Line:</strong> ${botChoice.line}</div>
                <div><strong>Length:</strong> ${botChoice.length}</div>
                <div><strong>Variation:</strong> ${botChoice.variation}</div>
            </div>
            <div style="color: #4CAF50; font-weight: 600;">✓ Check box below to see all shot scores</div>
        </div>
    `;
    botChoiceDiv.style.display = 'block';
}

// Fetch and cache scores for batting
function fetchAndCacheScores() {
    fetch('/get_effective_scores', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'action': 'batting'
        })
    })
    .then(response => response.json())
    .then(data => {
        storedScores = data.all_scores;  // Cache the scores for this ball
        displayBattingScores(storedBotChoice, storedScores);
    })
    .catch(error => console.error('Error:', error));
}

// Fetch bowling scores (these CAN change when you adjust bowling parameters)
function fetchAndDisplayBowlingScores() {
    const bowlingType = document.getElementById('bowlingTypeSelect').value;
    const line = document.getElementById('lineSelect').value;
    const length = document.getElementById('lengthSelect').value;
    const variation = document.getElementById('variationSelect').value;
    
    fetch('/get_effective_scores', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'action': 'bowling',
            'bowling_type': bowlingType,
            'line': line,
            'length': length,
            'variation': variation
        })
    })
    .then(response => response.json())
    .then(data => {
        displayBowlingScores(data.bot_choice, data.all_scores);
    })
    .catch(error => console.error('Error:', error));
}

function displayBattingScores(botChoice, allScores) {
    // Display bot's bowling choice
    const botChoiceDiv = document.getElementById('botChoice');
    const botChoiceText = document.getElementById('botChoiceText');
    
    botChoiceText.innerHTML = `
        <div style="font-size: 1.05em; line-height: 1.8;">
            <strong style="display: block; margin-bottom: 10px; color: #ff6b6b;">🎯 BOT IS BOWLING:</strong>
            <div style="background: rgba(0,0,0,0.1); padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                <div><strong>Type:</strong> ${botChoice.bowling_type}</div>
                <div><strong>Line:</strong> ${botChoice.line}</div>
                <div><strong>Length:</strong> ${botChoice.length}</div>
                <div><strong>Variation:</strong> ${botChoice.variation}</div>
            </div>
            <div style="color: #ffeb3b; font-weight: 600;">👇 Select your shot below and see effective scores</div>
        </div>
    `;
    botChoiceDiv.style.display = 'block';

    // Display all effective scores
    const scoresDiv = document.getElementById('scoresList');
    scoresDiv.innerHTML = '';
    
    const selectedShot = document.getElementById('shotSelect')?.value;
    
    allScores.forEach((score) => {
        const scoreItem = document.createElement('div');
        scoreItem.className = 'score-item';
        
        // Highlight selected shot
        const isSelected = score.name === selectedShot;
        
        // Color code by score range
        let scoreColor = '#666';
        if (score.score >= 85) scoreColor = '#4CAF50'; // Green - Good
        else if (score.score >= 70) scoreColor = '#2196F3'; // Blue - Medium
        else if (score.score >= 50) scoreColor = '#FF9800'; // Orange - Fair
        else scoreColor = '#f44336'; // Red - Poor
        
        scoreItem.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; ${isSelected ? 'background: rgba(0,0,0,0.1); padding: 8px; border-radius: 8px;' : ''}">
                <strong>${score.name}</strong>
                <span style="background: ${scoreColor}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: 600;">
                    ${score.score}
                </span>
            </div>
        `;
        scoresDiv.appendChild(scoreItem);
    });
    
    document.getElementById('effectiveScoresDiv').style.display = 'block';
}

function displayBowlingScores(botChoice, allScores) {
    // Display bot's shot choice
    const botChoiceDiv = document.getElementById('botChoice');
    const botChoiceText = document.getElementById('botChoiceText');
    
    botChoiceText.innerHTML = `
        <div style="font-size: 1.05em; line-height: 1.8;">
            <strong style="display: block; margin-bottom: 10px; color: #4CAF50;">🤖 BOT'S SHOT CHOICE:</strong>
            <div style="background: rgba(0,0,0,0.1); padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                <div><strong>Shot:</strong> ${botChoice.shot}</div>
                <div><strong>Effective Score:</strong> ${botChoice.effective_score}</div>
            </div>
            <div style="color: #ffeb3b; font-weight: 600;">👇 Adjust your bowling to see expected runs</div>
        </div>
    `;
    botChoiceDiv.style.display = 'block';

    // Display all effective scores with expected runs
    const scoresDiv = document.getElementById('scoresList');
    scoresDiv.innerHTML = '';
    
    allScores.forEach((score) => {
        const scoreItem = document.createElement('div');
        scoreItem.className = 'score-item';
        
        // Highlight bot's choice
        const isBotChoice = score.name === botChoice.shot;
        
        // Color code by runs
        let runsColor = '#666';
        if (score.expected_runs === 6) runsColor = '#4CAF50'; // Green - 6 runs
        else if (score.expected_runs === 4) runsColor = '#2196F3'; // Blue - 4 runs
        else if (score.expected_runs === 2) runsColor = '#FF9800'; // Orange - 2 runs
        else if (score.expected_runs === 1) runsColor = '#9C27B0'; // Purple - 1 run
        else if (score.expected_runs === 'W') runsColor = '#f44336'; // Red - Wicket
        
        const runsText = score.expected_runs === 'W' ? 'WICKET' : score.expected_runs + ' Runs';
        
        scoreItem.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; ${isBotChoice ? 'background: rgba(0,0,0,0.1); padding: 8px; border-radius: 8px; border: 2px solid #4CAF50;' : ''}">
                <span>
                    <strong>${score.name}</strong>
                    <div style="font-size: 0.8em; color: #999;">Score: ${score.score}</div>
                </span>
                <span style="background: ${runsColor}; color: white; padding: 6px 14px; border-radius: 20px; font-weight: 600;">
                    ${runsText}
                </span>
            </div>
        `;
        scoresDiv.appendChild(scoreItem);
    });
    
    document.getElementById('effectiveScoresDiv').style.display = 'block';
}

window.onload = function() {
    updateDropdowns();
};