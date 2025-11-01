  // script.js - Frontend logic (backend-first autocomplete, Leaflet map)
(() => {
  const MAX_LOCATIONS = 50;
  const BACKEND_BASE = 'https://getripath.onrender.com';
  const PREFER_GOOGLE_PLACES = false; // Set to true to use Google Places API instead of Photon/Nominatim
  // Backend (Photon) autocomplete is always used.
  const parent = document.getElementById('location-inputs');
  if (!parent) return;

  let map = null;
  let markers = [];
  let polylineLayer = null;
  let autocompleteInstances = new Map();

  // parse "location123" -> 123 or NaN
  const parseIndex = (id) => {
    if (!id) return NaN;
    const m = id.match(/^location(\d+)$/);
    return m ? parseInt(m[1], 10) : NaN;
  };

  // global counter = max numeric index observed so far
  let counter = 0;

  // Leaflet map will be initialized when results contain coordinates

  // Initialize autocomplete for an input field
  function initAutocomplete(input) {
    // Add focus handler only once to prevent button disable issues
    if (!input.__focusHandlerAdded) {
      input.__focusHandlerAdded = true;
      input.addEventListener('focus', () => {
        const block = input.closest('.content');
        if (block) {
          const yes = block.querySelector('.btn-yes');
          const no = block.querySelector('.btn-no');
          // Re-enable buttons if they were disabled (unless explicitly marked final)
          if (yes && yes.disabled && !block.dataset.final) {
            yes.disabled = false;
            no.disabled = false;
          }
        }
      });
    }

    // Backend autocomplete fallback (preferred by default)
    if (input.__backendAutocompleteInitialized) return;
    input.__backendAutocompleteInitialized = true;

    // Create dropdown container
    const box = document.createElement('div');
    box.className = 'autocomplete-box';
    box.style.position = 'absolute';
    box.style.zIndex = 9999;
    box.style.background = 'white';
    box.style.border = '1px solid #ccc';
    box.style.display = 'none';
    box.style.maxHeight = '220px';
    box.style.overflowY = 'auto';
    box.style.minWidth = '240px';
    input.parentNode.style.position = input.parentNode.style.position || 'relative';
    input.parentNode.appendChild(box);

    let timer = null;
    input.addEventListener('input', (e) => {
      const q = input.value.trim();
      clearTimeout(timer);
      if (!q) {
        box.style.display = 'none';
        return;
      }
      // debounce 250ms (faster response, Photon handles more requests)
      timer = setTimeout(async () => {
        try {
          const url = `${BACKEND_BASE}/autocomplete?q=${encodeURIComponent(q)}&limit=8`;
          console.log('Fetching autocomplete:', url);
          
          // Add timeout to prevent hanging requests on mobile
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
          
          const resp = await fetch(url, { signal: controller.signal });
          clearTimeout(timeoutId);
          
          console.log('Autocomplete response status:', resp.status);
          if (!resp.ok) {
            console.error('Autocomplete request failed:', resp.status, resp.statusText);
            box.style.display = 'none';
            return;
          }
          const data = await resp.json();
          console.log('Autocomplete data:', data);
          const list = data.suggestions || [];
          box.innerHTML = '';
          if (!list.length) {
            // Show "no results" message
            const noResults = document.createElement('div');
            noResults.style.padding = '8px';
            noResults.style.color = '#999';
            noResults.style.fontStyle = 'italic';
            noResults.textContent = 'No results found';
            box.appendChild(noResults);
            box.style.display = 'block';
            setTimeout(() => { box.style.display = 'none'; }, 2000);
            return;
          }
          list.forEach(item => {
            const row = document.createElement('div');
            row.className = 'autocomplete-item';
            row.style.padding = '8px 10px';
            row.style.cursor = 'pointer';
            row.style.borderBottom = '1px solid #eee';
            row.style.fontSize = '14px';
            row.style.lineHeight = '1.4';
            
            // Main text
            const mainText = document.createElement('div');
            mainText.textContent = item.name || item.display_name;
            mainText.style.fontWeight = '500';
            row.appendChild(mainText);
            
            // Secondary info (city, state, country)
            const parts = [];
            if (item.city && item.city !== item.name) parts.push(item.city);
            if (item.state) parts.push(item.state);
            if (item.country) parts.push(item.country);
            
            if (parts.length > 0) {
              const subText = document.createElement('div');
              subText.textContent = parts.join(', ');
              subText.style.fontSize = '12px';
              subText.style.color = '#666';
              subText.style.marginTop = '2px';
              row.appendChild(subText);
            }
            
            row.addEventListener('mouseenter', () => {
              row.style.backgroundColor = '#f5f5f5';
            });
            row.addEventListener('mouseleave', () => {
              row.style.backgroundColor = 'white';
            });
            row.addEventListener('mousedown', (e) => {
              // Use mousedown instead of click to fire before blur
              e.preventDefault();
              console.log('Selected location:', item.display_name);
              input.value = item.display_name || item.name;
              input.setAttribute('data-lat', item.lat);
              input.setAttribute('data-lon', item.lon);
              box.style.display = 'none';
            });
            box.appendChild(row);
          });
          box.style.display = 'block';
          console.log('Autocomplete box displayed with', list.length, 'items');
        } catch (err) {
          console.error('Autocomplete error', err);
          box.style.display = 'none';
          // Don't block the UI on network errors
        }
      }, 250);
    });

    // hide on blur (with longer delay to allow clicking dropdown items)
    input.addEventListener('blur', () => {
      setTimeout(() => { box.style.display = 'none'; }, 250);
    });

    // Always use backend autocomplete dropdown (Photon/Nominatim via backend).
  }

  // Try to initialize autocomplete for all inputs
  function initAllAutocomplete() {
    // If developer prefers Google Places, wait until it's available.
    if (PREFER_GOOGLE_PLACES) {
      if (!window.google || !google.maps || !google.maps.places) {
        // Retry after a short delay
        setTimeout(initAllAutocomplete, 500);
        return;
      }
    }

    // Initialize autocomplete for all inputs (backend-first when PREFER_GOOGLE_PLACES=false)
    try {
      const inputs = document.querySelectorAll('input[type="text"][id^="loc-input-"]');
      inputs.forEach(input => {
        try {
          initAutocomplete(input);
        } catch (e) {
          console.error('Failed to init autocomplete for input:', input.id, e);
        }
      });
    } catch (e) {
      console.error('Failed to initialize autocomplete:', e);
    }
  }

  // create a brand new location block for a given index
  function createLocationBlock(index, inputValue = '') {
    const div = document.createElement('div');
    div.className = 'content';
    div.id = `location${index}`;

    const inputId = `loc-input-${index}`;

    div.innerHTML = `
      <input type="text" id="${inputId}" name="location${index}" value="${escapeHtml(inputValue)}" placeholder="Enter location ${index} (e.g., Mumbai, Maharashtra)">
      <label for="${inputId}">Add Location</label>
      <button type="button" class="btn-yes" data-index="${index}">Yes</button>
      <button type="button" class="btn-no" data-index="${index}">No</button>
      <span class="status" aria-hidden="true"></span>
    `;

    attachBlockHandlers(div);
    
    // Attach save listener
    attachSaveListener(div);
    
    // Initialize autocomplete for the new input
    setTimeout(() => {
      const input = div.querySelector(`#${inputId}`);
      if (input) initAutocomplete(input);
    }, 100);

    return div;
  }

  // ensure an existing block has proper ids/names and handlers
  function normalizeBlock(block) {
    let idx = parseIndex(block.id);
    if (Number.isNaN(idx)) {
      counter += 1;
      idx = counter;
      block.id = `location${idx}`;
    } else {
      if (idx > counter) counter = idx;
    }

    let input = block.querySelector('input[type="text"]');
    const inputId = `loc-input-${idx}`;
    if (!input) {
      input = document.createElement('input');
      input.type = 'text';
      block.insertBefore(input, block.firstChild);
    }
    const existingValue = input.value || '';
    input.id = inputId;
    input.name = `location${idx}`;
    input.value = existingValue;
    input.placeholder = `Enter location ${idx} (e.g., Mumbai, Maharashtra)`;

    let label = block.querySelector('label[for]');
    if (!label) {
      label = document.createElement('label');
      block.insertBefore(label, input.nextSibling);
    }
    label.setAttribute('for', inputId);
    label.textContent = label.textContent.trim() || 'Add Location';

    const btns = block.querySelectorAll('button');
    let yes = block.querySelector('.btn-yes');
    let no = block.querySelector('.btn-no');

    if (!yes) {
      yes = btns[0] || document.createElement('button');
      yes.classList.add('btn-yes');
      if (!btns[0]) block.appendChild(yes);
    }
    if (!no) {
      no = btns[1] || document.createElement('button');
      no.classList.add('btn-no');
      if (!btns[1]) block.appendChild(no);
    }

    yes.type = 'button';
    no.type = 'button';
    yes.textContent = yes.textContent.trim() || 'Yes';
    no.textContent = no.textContent.trim() || 'No';
    yes.setAttribute('data-index', idx);
    no.setAttribute('data-index', idx);

    if (!block.querySelector('.status')) {
      const span = document.createElement('span');
      span.className = 'status';
      block.appendChild(span);
    }

    attachBlockHandlers(block);
  }

  // attach handlers; avoid duplicate handlers by checking a flag
  function attachBlockHandlers(block) {
    if (block.__handlersAttached) return;
    block.__handlersAttached = true;

    const yes = block.querySelector('.btn-yes');
    const no = block.querySelector('.btn-no');
    const input = block.querySelector('input[type="text"]');
    const status = block.querySelector('.status');

    if (!yes || !no || !input) return;

    yes.addEventListener('click', () => {
      if (input.value.trim() === '') {
        flashStatus(status, 'Enter a location before adding another', true);
        input.focus();
        return;
      }
      if (counter >= MAX_LOCATIONS) {
        flashStatus(status, `Max ${MAX_LOCATIONS} reached`, true);
        return;
      }
      const nextIndex = counter + 1;
      counter = nextIndex;
      const newBlock = createLocationBlock(nextIndex);
      parent.appendChild(newBlock);

      // Only disable buttons after successfully adding new location
      yes.disabled = true;
      no.disabled = true;
      block.dataset.final = 'true';  // Mark as final so focus doesn't re-enable
      flashStatus(status, `Added location ${nextIndex}`, false);

      const newInput = newBlock.querySelector('input[type="text"]');
      if (newInput) newInput.focus();
      
      // Save after adding new block
      debouncedSave();
    });

    no.addEventListener('click', () => {
      yes.disabled = true;
      no.disabled = true;
      // Mark this block as final so focus doesn't re-enable
      block.dataset.final = 'true';
      flashStatus(status, 'Marked final', false);
      
      // Save after marking final
      debouncedSave();
    });

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        // Only trigger Yes button if there's actual content
        if (input.value.trim()) {
          yes.click();
        }
      }
    });
  }

  function flashStatus(node, message, isError = false) {
    if (!node) return;
    node.textContent = message;
    node.style.marginLeft = '8px';
    node.style.fontSize = '0.9em';
    node.style.color = isError ? 'crimson' : 'green';
    setTimeout(() => { node.textContent = ''; }, 3000);
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // bootstrap: normalize everything currently in DOM or restore from localStorage
  function bootstrapExisting() {
    // Try to restore from localStorage first
    const restored = restoreLocationsFromStorage();
    if (restored) {
      console.log('Restored locations from localStorage');
      // Attach save listeners to all restored blocks
      const blocks = parent.querySelectorAll('.content');
      blocks.forEach(block => attachSaveListener(block));
      return;
    }
    
    // Otherwise, normalize existing DOM blocks
    const existing = Array.from(parent.querySelectorAll('.content'));
    if (existing.length === 0) {
      counter = 1;
      const firstBlock = createLocationBlock(1);
      parent.appendChild(firstBlock);
      return;
    }
    existing.forEach((b) => {
      normalizeBlock(b);
      attachSaveListener(b);
    });
  }

  // Initialize autocomplete after a delay
  setTimeout(initAllAutocomplete, 1000);

  // run bootstrap
  bootstrapExisting();

  // Form submission
  const form = document.getElementById('location-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const inputs = form.querySelectorAll('input[type="text"][name^="location"]');
      const locations = Array.from(inputs)
        .map(i => i.value.trim())
        .filter(v => v !== '');

      if (locations.length < 2) {
        showError('Please enter at least 2 locations to calculate the route.');
        return;
      }

      // Show loading
      document.getElementById('loading').style.display = 'block';
      document.getElementById('results').innerHTML = '<p class="placeholder">Calculating...</p>';

      try {
        // Call backend API
  const response = await fetch(`${BACKEND_BASE}/calculate-route`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ locations: locations })
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
          showError(data.error);
        } else {
          displayResults(data);
        }
      } catch (error) {
        console.error('Error:', error);
        showError('Failed to calculate route. Please make sure the backend server is running on http://localhost:5000');
        if (typeof showBackendWarning === 'function') showBackendWarning();
      } finally {
        document.getElementById('loading').style.display = 'none';
      }
    });
  }

  // localStorage persistence functions
  function saveLocationsToStorage() {
    try {
      const blocks = parent.querySelectorAll('.content');
      const locations = [];
      blocks.forEach(block => {
        const input = block.querySelector('input[type="text"]');
        const yes = block.querySelector('.btn-yes');
        const isFinal = block.dataset.final === 'true';
        const isDisabled = yes && yes.disabled;
        
        if (input) {
          locations.push({
            value: input.value || '',
            isFinal: isFinal,
            buttonsDisabled: isDisabled
          });
        }
      });
      localStorage.setItem('distanceOptimalityLocations', JSON.stringify({
        locations: locations,
        counter: counter
      }));
    } catch (e) {
      console.error('Failed to save to localStorage:', e);
    }
  }

  function restoreLocationsFromStorage() {
    try {
      const saved = localStorage.getItem('distanceOptimalityLocations');
      if (!saved) return false;
      
      const data = JSON.parse(saved);
      if (!data.locations || !Array.isArray(data.locations)) return false;
      
      // Remove all existing blocks first
      const existingBlocks = parent.querySelectorAll('.content');
      existingBlocks.forEach(block => block.remove());
      
      // Restore counter
      counter = data.counter || data.locations.length;
      
      // Create blocks for each saved location
      data.locations.forEach((location, index) => {
        const value = typeof location === 'string' ? location : location.value;
        const newBlock = createLocationBlock(index, value);
        parent.appendChild(newBlock);
        
        // Restore button states if saved
        if (typeof location === 'object' && location.buttonsDisabled) {
          const yes = newBlock.querySelector('.btn-yes');
          const no = newBlock.querySelector('.btn-no');
          if (yes) yes.disabled = true;
          if (no) no.disabled = true;
          if (location.isFinal) {
            newBlock.dataset.final = 'true';
          }
        }
      });
      
      // Re-initialize autocomplete
      setTimeout(() => {
        initAllAutocomplete();
      }, 100);
      
      return true;
    } catch (e) {
      console.error('Failed to restore from localStorage:', e);
      return false;
    }
  }

  // Debounced save function
  let saveTimeout;
  function debouncedSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveLocationsToStorage, 500);
  }

  // Attach input listeners to save on change
  function attachSaveListener(block) {
    const input = block.querySelector('input[type="text"]');
    if (input) {
      input.addEventListener('input', debouncedSave);
    }
  }

  // Reset button
  const resetBtn = document.getElementById('reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      // Clear localStorage
      localStorage.removeItem('distanceOptimalityLocations');
      
      // Clear all location inputs except the first one
      const blocks = parent.querySelectorAll('.content');
      blocks.forEach((block, index) => {
        if (index === 0) {
          const input = block.querySelector('input[type="text"]');
          if (input) input.value = '';
          const buttons = block.querySelectorAll('button');
          buttons.forEach(btn => btn.disabled = false);
        } else {
          block.remove();
        }
      });
      
      counter = 1;
      
      // Clear results
      document.getElementById('results').innerHTML = '<p class="placeholder">Enter at least 2 locations and click "Calculate Optimal Route" to see results.</p>';
      document.getElementById('map-container').style.display = 'none';
      
      // Clear markers and any polyline
      markers.forEach(m => { try { map.removeLayer(m); } catch (e) {} });
      markers = [];
      if (polylineLayer) {
        try { map.removeLayer(polylineLayer); } catch (e) {}
        polylineLayer = null;
      }
    });
  }

  function showError(message) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `
      <div class="error-message">
        <strong>Error:</strong> ${escapeHtml(message)}
      </div>
    `;
  }

  function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    
    // Build optimal route HTML
    let html = `
      <div class="optimal-route">
        <h3>🎯 Optimal Route Found!</h3>
        <div class="route-path">
          ${data.optimal_path.join(' → ')}
        </div>
        <div class="total-distance">
          Total Distance: ${data.total_distance.toFixed(2)} km
        </div>
      </div>
    `;

    // Add distance matrix
    if (data.distance_matrix && data.distance_matrix.length > 0) {
      html += `
        <div class="result-item">
          <h3>📊 Distance Matrix</h3>
          <div class="distance-matrix">
            <table>
              <thead>
                <tr>
                  <th></th>
                  ${data.locations.map(loc => `<th>${escapeHtml(loc)}</th>`).join('')}
                </tr>
              </thead>
              <tbody>
                ${data.distance_matrix.map((row, i) => `
                  <tr>
                    <th>${escapeHtml(data.locations[i])}</th>
                    ${row.map(dist => `<td>${dist === 0 ? '-' : dist.toFixed(2) + ' km'}</td>`).join('')}
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    resultsDiv.innerHTML = html;

    // Make stacked-table mode more usable on very small screens by adding data-labels
    // and wrapping cell content into a value span so CSS can show labels via ::before.
    try {
      const tables = resultsDiv.querySelectorAll('.distance-matrix table');
      tables.forEach(table => {
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
          // build a combined cells list including the row header (th) then the td cells
          const rowHeader = row.querySelector('th');
          const cells = Array.from(row.querySelectorAll('th, td'));
          cells.forEach((cell, idx) => {
            // Determine label: headers array aligns so idx corresponds to headers[idx]
            let label = headers[idx] || '';
            if (!label && idx === 0) label = 'Location';
            cell.setAttribute('data-label', label);

            // ensure content is inside a span.value for stacked layout styling
            if (!cell.querySelector('.value')) {
              const span = document.createElement('span');
              span.className = 'value';
              span.innerHTML = cell.innerHTML;
              cell.innerHTML = '';
              cell.appendChild(span);
            }
          });
        });
      });
    } catch (e) {
      // non-fatal
      console.error('Error while adding data-labels for stacked table:', e);
    }

    // Display map
    displayMap(data);
    // Append nearest-neighbor breakdown controls (default start = first location)
    try { appendNearestNeighborBreakdown(data); } catch (e) { console.error('NN breakdown error:', e); }
  }

  function displayMap(data) {
    const mapContainer = document.getElementById('map-container');
    const mapDiv = document.getElementById('map');
    
    // Use coordinates returned by backend (data.coords) to place markers.
    // Expect data.coords to be an array of [lat, lon] aligned with data.locations.
    if (!data.coords || !Array.isArray(data.coords) || data.coords.length !== data.locations.length) {
      // No coordinates available from backend; hide map
      mapContainer.style.display = 'none';
      return;
    }

    // show map container
    mapContainer.style.display = 'block';

    // Initialize Leaflet map if needed
    if (!map) {
      map = L.map(mapDiv).setView([20.5937, 78.9629], 5);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
    }

    // Clear existing markers and polyline
    markers.forEach(m => { try { map.removeLayer(m); } catch (e) {} });
    markers = [];
    if (polylineLayer) {
      try { map.removeLayer(polylineLayer); } catch (e) {}
      polylineLayer = null;
    }

    const bounds = L.latLngBounds();
    // Add markers
    data.coords.forEach((c, index) => {
      const lat = parseFloat(c[0]);
      const lon = parseFloat(c[1]);
      if (Number.isFinite(lat) && Number.isFinite(lon)) {
        const marker = L.marker([lat, lon]).addTo(map);
        marker.bindPopup(`<strong>${escapeHtml(data.locations[index])}</strong><br/>#${index + 1}`);
        markers.push(marker);
        bounds.extend([lat, lon]);
      }
    });

    if (markers.length > 0) map.fitBounds(bounds.pad(0.2));

    // Draw route polyline according to optimal_path if available
    if (Array.isArray(data.optimal_path) && data.optimal_path.length > 1) {
      const latlngs = [];
      data.optimal_path.forEach(name => {
        const idx = data.locations.indexOf(name);
        if (idx >= 0 && data.coords[idx]) {
          latlngs.push([parseFloat(data.coords[idx][0]), parseFloat(data.coords[idx][1])]);
        }
      });
      if (latlngs.length > 1) {
        polylineLayer = L.polyline(latlngs, { color: '#3388ff', weight: 4 }).addTo(map);
        // ensure polyline fits
        try { map.fitBounds(polylineLayer.getBounds().pad(0.2)); } catch (e) {}
      }
    }
  }

  // --- Client-side utilities: nearest-neighbor, breakdown, CSV export ---
  function nearestNeighbor(locations, distance_matrix, startIndex = 0) {
    const n = locations.length;
    const visited = new Array(n).fill(false);
    const path = [];
    let current = startIndex;
    path.push(locations[current]);
    visited[current] = true;
    let total = 0;

    for (let step = 1; step < n; step++) {
      let nearest = -1;
      let bestDist = Infinity;
      for (let j = 0; j < n; j++) {
        if (!visited[j] && distance_matrix[current] && typeof distance_matrix[current][j] === 'number') {
          const d = distance_matrix[current][j];
          if (d < bestDist) {
            bestDist = d;
            nearest = j;
          }
        }
      }
      if (nearest === -1) break;
      visited[nearest] = true;
      path.push(locations[nearest]);
      total += (bestDist === Infinity ? 0 : bestDist);
      current = nearest;
    }

    // return to start
    const startIdx = startIndex;
    const lastIdx = locations.indexOf(path[path.length - 1]);
    if (lastIdx >= 0 && distance_matrix[lastIdx] && typeof distance_matrix[lastIdx][startIdx] === 'number') {
      total += distance_matrix[lastIdx][startIdx];
      path.push(locations[startIdx]);
    }

    return { path, total };
  }

  function appendNearestNeighborBreakdown(data, overrideNN) {
    const resultsDiv = document.getElementById('results');
    const locations = data.locations || [];
    const matrix = data.distance_matrix || [];
    if (!locations.length) return;

    const startIndex = (overrideNN && typeof overrideNN.startIndex === 'number') ? overrideNN.startIndex : 0;
    const nn = overrideNN && overrideNN.path ? overrideNN : nearestNeighbor(locations, matrix, startIndex);

    let breakdownHtml = `
      <div class="result-item nn-breakdown">
        <h3>🧭 Greedy Nearest-Neighbor Route (start: ${escapeHtml(locations[startIndex])})</h3>
        <div class="route-path">${nn.path.join(' → ')}</div>
        <div class="total-distance">Total (greedy): ${nn.total.toFixed(2)} km</div>
        <div style="margin-top:12px;">
          <h4>Leg-by-leg details</h4>
          <div class="distance-matrix">
            <table>
              <thead>
                <tr><th>Leg</th><th>From</th><th>To</th><th>Distance</th></tr>
              </thead>
              <tbody>
    `;

    let cumulative = 0;

    for (let i = 0; i < nn.path.length - 1; i++) {
      const from = nn.path[i];
      const to = nn.path[i + 1];
      const fi = locations.indexOf(from);
      const ti = locations.indexOf(to);
      let dist = 0;
      if (fi >= 0 && ti >= 0 && matrix[fi] && typeof matrix[fi][ti] === 'number') {
        dist = matrix[fi][ti];
      }
      cumulative += dist;
      breakdownHtml += `
        <tr>
          <td>${i + 1}</td>
          <td>${escapeHtml(from)}</td>
          <td>${escapeHtml(to)}</td>
          <td>${dist === 999999.0 ? '—' : dist.toFixed(2) + ' km'}</td>
        </tr>
      `;
    }

    breakdownHtml += `
              </tbody>
            </table>
          </div>
          <div style="margin-top:10px; font-weight:600;">Cumulative distance: ${cumulative.toFixed(2)} km</div>
        </div>
      </div>
    `;

    resultsDiv.insertAdjacentHTML('beforeend', breakdownHtml);

    // Controls: start selector and CSV export
    const controlsHtml = `
      <div class="result-item nn-controls" style="margin-top:12px;">
        <div class="nn-controls-inner">
          <select id="nn-start-select" class="nn-select">${locations.map((l, idx) => `<option value="${idx}">${escapeHtml(l)}</option>`).join('')}</select>
          <div class="nn-buttons">
            <button id="nn-run-btn" class="submit-btn nn-btn">Run Greedy</button>
            <button id="export-csv-btn" class="submit-btn nn-btn">Export CSV</button>
          </div>
        </div>
      </div>
    `;
    resultsDiv.insertAdjacentHTML('beforeend', controlsHtml);

    // Update a visible "Start from:" display above the map so it's clear
    try {
      const mapContainer = document.getElementById('map-container');
      if (mapContainer) {
        let startEl = document.getElementById('start-from-display');
        if (!startEl) {
          startEl = document.createElement('div');
          startEl.id = 'start-from-display';
          startEl.style.fontWeight = '700';
          startEl.style.margin = '8px 0';
          startEl.style.color = '#333';
          mapContainer.insertBefore(startEl, mapContainer.firstChild);
        }
        startEl.innerHTML = `Start from: ${escapeHtml(locations[startIndex])}`;
      }
    } catch (e) {
      /* non-fatal */
    }

    document.getElementById('nn-run-btn').addEventListener('click', () => {
      const sel = document.getElementById('nn-start-select');
      const si = parseInt(sel.value, 10) || 0;
      // Remove existing nn-breakdown and controls
      const existing = document.querySelectorAll('.nn-breakdown, #nn-start-select, #nn-run-btn, #export-csv-btn');
      existing.forEach(n => n.remove());
      const newnn = nearestNeighbor(locations, matrix, si);
      appendNearestNeighborBreakdown(data, { path: newnn.path, total: newnn.total, startIndex: si });
    });

    document.getElementById('export-csv-btn').addEventListener('click', () => {
      exportRouteCSV(locations, matrix, nn.path);
    });
  }

  function exportRouteCSV(locations, matrix, routePath) {
    // Build rows: Leg, From, To, Distance_km
    const rows = [];
    for (let i = 0; i < routePath.length - 1; i++) {
      const from = routePath[i];
      const to = routePath[i + 1];
      const fi = locations.indexOf(from);
      const ti = locations.indexOf(to);
      let dist = '';
      if (fi >= 0 && ti >= 0 && matrix[fi] && typeof matrix[fi][ti] === 'number') {
        dist = matrix[fi][ti].toFixed(2);
      }
      rows.push([i + 1, from, to, dist]);
    }

    let csv = 'Leg,From,To,Distance_km\n';
    csv += rows.map(r => r.map(c => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'route.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }
})();
