document.querySelectorAll(".flash").forEach(el => {
    setTimeout(() => {
        el.style.transition = "opacity 0.6s";
        el.style.opacity = "0";
        setTimeout(() => el.remove(), 600);
    }, 5000);
});

// Dark mode toggle
(function() {
    var saved = localStorage.getItem('ott-dark');
    if (saved === '1') document.body.classList.add('dark');
})();

function toggleDark() {
    document.body.classList.toggle('dark');
    var isDark = document.body.classList.contains('dark');
    localStorage.setItem('ott-dark', isDark ? '1' : '0');
}

// Sidebar toggle
function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('overlay');
    if (!sidebar) return;
    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
}

// Close sidebar on ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var sidebar = document.getElementById('sidebar');
        var overlay = document.getElementById('overlay');
        if (sidebar && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }
    }
});

// Share outfit as image card
function shareOutfit() {
    var cards = document.querySelectorAll('.grid .card');
    if (cards.length === 0) {
        alert('No outfit to share');
        return;
    }

    var canvas = document.createElement('canvas');
    var W = 800;
    var H = 200 + cards.length * 40;
    canvas.width = W;
    canvas.height = H;
    var ctx = canvas.getContext('2d');

    // Background
    var grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, '#FDF6E3');
    grad.addColorStop(1, '#FFF3D6');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Header
    ctx.fillStyle = '#E67E22';
    ctx.font = 'bold 42px Georgia';
    ctx.textAlign = 'center';
    ctx.fillText('옷 OTT', W / 2, 70);

    ctx.fillStyle = '#2C3E50';
    ctx.font = '20px Georgia';
    ctx.fillText('My Outfit', W / 2, 105);

    // Divider
    ctx.strokeStyle = '#E8DFC8';
    ctx.setLineDash([8, 8]);
    ctx.beginPath();
    ctx.moveTo(60, 130);
    ctx.lineTo(W - 60, 130);
    ctx.stroke();
    ctx.setLineDash([]);

    // Items
    ctx.textAlign = 'left';
    ctx.font = '22px Georgia';
    var y = 180;
    cards.forEach(function(card) {
        var h3 = card.querySelector('h3');
        var tag = card.querySelector('.tag');
        var name = h3 ? h3.textContent.trim() : '?';
        var occ = tag ? tag.textContent.trim() : '';
        ctx.fillStyle = '#27AE60';
        ctx.fillText('•', 80, y);
        ctx.fillStyle = '#2C3E50';
        ctx.fillText(name, 110, y);
        if (occ) {
            ctx.fillStyle = '#7F8C8D';
            ctx.font = '16px Georgia';
            ctx.fillText('(' + occ + ')', 110 + ctx.measureText(name).width + 60, y);
            ctx.font = '22px Georgia';
        }
        y += 40;
    });

    // Footer
    ctx.fillStyle = '#7F8C8D';
    ctx.font = '16px Georgia';
    ctx.textAlign = 'center';
    ctx.fillText('Made with OTT · Fashion for everyone', W / 2, H - 30);

    // Download
    var link = document.createElement('a');
    link.download = 'ott-outfit.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
}

// Dyslexia-friendly font
(function() {
    if (localStorage.getItem('ott-dyslexia') === '1') {
        document.body.classList.add('dyslexia');
    }
})();

function toggleDyslexia() {
    document.body.classList.toggle('dyslexia');
    localStorage.setItem('ott-dyslexia', document.body.classList.contains('dyslexia') ? '1' : '0');
}

// Reduce motion
(function() {
    if (localStorage.getItem('ott-reduce-motion') === '1') {
        document.body.classList.add('reduce-motion');
    }
})();

function toggleReduceMotion() {
    document.body.classList.toggle('reduce-motion');
    localStorage.setItem('ott-reduce-motion', document.body.classList.contains('reduce-motion') ? '1' : '0');
}

// Welcome notification - once per session
(function() {
    if (sessionStorage.getItem('ott-welcomed')) return;
    sessionStorage.setItem('ott-welcomed', '1');
    var hour = new Date().getHours();
    var greeting = hour < 12 ? 'Good morning' : (hour < 18 ? 'Good afternoon' : 'Good evening');
    var bar = document.createElement('div');
    bar.className = 'notif-bar';
    bar.innerHTML = '<span>' + greeting + '! Today is your day.</span><button onclick="this.parentElement.remove()">×</button>';
    document.body.insertBefore(bar, document.body.firstChild);
    setTimeout(function() { if (bar.parentElement) bar.remove(); }, 6000);
})();

// Text-to-speech
function speakPage() {
    if (!('speechSynthesis' in window)) {
        alert('Your browser does not support speech');
        return;
    }
    window.speechSynthesis.cancel();
    var main = document.querySelector('main');
    if (!main) return;
    var text = main.innerText.slice(0, 500);
    var lang = document.documentElement.lang || 'en';
    var utter = new SpeechSynthesisUtterance(text);
    utter.lang = lang === 'ar' ? 'ar-EG' : (lang === 'ko' ? 'ko-KR' : 'en-US');
    utter.rate = 0.95;
    window.speechSynthesis.speak(utter);
}

function stopSpeaking() {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}

// Save scroll position before form submit
document.addEventListener('DOMContentLoaded', function() {
    // Restore scroll position
    var savedScroll = sessionStorage.getItem('ott-scroll');
    if (savedScroll) {
        window.scrollTo(0, parseInt(savedScroll));
        sessionStorage.removeItem('ott-scroll');
    }

    // Save scroll position on any form submit
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            sessionStorage.setItem('ott-scroll', window.scrollY);
        });
    });
});



// ============ POWERFUL AUTO-TRANSLATOR ============
(function() {
    var lang = window.OTT_LANG;
    if (!lang || lang === 'en') return;
    var T = (window.OTT_TRANSLATIONS || {})[lang] || {};
    var keys = Object.keys(T);
    if (!keys.length) return;

    // Build pattern - longest first to avoid partial conflicts
    keys.sort(function(a, b) { return b.length - a.length; });
    var esc = function(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
    var pattern = new RegExp(keys.map(esc).join('|'), 'g');

    function tr(text) {
        if (!text || typeof text !== 'string') return text;
        return text.replace(pattern, function(m) { return T[m] || m; });
    }

    function walk(node) {
        if (!node) return;
        // Text node
        if (node.nodeType === 3) {
            var orig = node.nodeValue;
            var t = tr(orig);
            if (t !== orig) node.nodeValue = t;
            return;
        }
        // Element node
        if (node.nodeType === 1) {
            var tag = node.tagName;
            if (tag === 'SCRIPT' || tag === 'STYLE') return;
            // Attributes
            var attrs = ['placeholder', 'title', 'aria-label', 'alt'];
            for (var a = 0; a < attrs.length; a++) {
                var v = node.getAttribute && node.getAttribute(attrs[a]);
                if (v) {
                    var tv = tr(v);
                    if (tv !== v) node.setAttribute(attrs[a], tv);
                }
            }
            for (var i = 0; i < node.childNodes.length; i++) walk(node.childNodes[i]);
        }
    }

    function run() {
        walk(document.body);
        // Watch for dynamic content
        try {
            var obs = new MutationObserver(function(muts) {
                for (var i = 0; i < muts.length; i++) {
                    var added = muts[i].addedNodes;
                    for (var j = 0; j < added.length; j++) walk(added[j]);
                }
            });
            obs.observe(document.body, { childList: true, subtree: true });
        } catch (e) {}
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run);
    } else {
        run();
    }
})();

// ============ KEYBOARD SHORTCUTS + SEARCH ============
(function() {
    // Add search overlay to page
    var overlay = document.createElement('div');
    overlay.className = 'search-overlay';
    overlay.id = 'search-overlay';
    overlay.innerHTML = '<div class="search-box" onclick="event.stopPropagation()">' +
        '<input type="text" id="global-search" placeholder="Search or jump to..." autocomplete="off">' +
        '<div class="search-links">' +
        '<a href="/wardrobe">Wardrobe</a>' +
        '<a href="/wishlist">Wishlist</a>' +
        '<a href="/trends">Trends</a>' +
        '<a href="/stylist">Stylist</a>' +
        '<a href="/discover">Discover</a>' +
        '<a href="/camera">Camera</a>' +
        '<a href="/profile">Profile</a>' +
        '</div></div>';
    document.body.appendChild(overlay);

    // Add hint
    var hint = document.createElement('div');
    hint.className = 'kbd-hint';
    hint.innerHTML = '<kbd>Ctrl</kbd> + <kbd>K</kbd> to search';
    document.body.appendChild(hint);
    setTimeout(function() { hint.style.opacity = '0'; hint.style.transition = 'opacity 0.5s'; }, 6000);

    // Open search
    function openSearch() {
        overlay.classList.add('active');
        setTimeout(function() { document.getElementById('global-search').focus(); }, 50);
        hint.style.display = 'none';
    }
    function closeSearch() {
        overlay.classList.remove('active');
    }

    overlay.addEventListener('click', closeSearch);

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+K or Cmd+K
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            openSearch();
        }
        // Escape
        if (e.key === 'Escape') closeSearch();
        // Quick nav (Alt+key)
        if (e.altKey) {
            var routes = {
                'w': '/wardrobe', 'i': '/wishlist', 't': '/trends',
                's': '/stylist', 'd': '/discover', 'h': '/',
                'p': '/profile', 'c': '/camera'
            };
            var key = e.key.toLowerCase();
            if (routes[key]) {
                e.preventDefault();
                window.location.href = routes[key];
            }
        }
    });

    // Search navigation on Enter
    document.getElementById('global-search').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            var q = this.value.trim();
            if (q) {
                window.location.href = '/search?q=' + encodeURIComponent(q);
            }
        }
    });
})();

// ============ LOADING SKELETON ============
(function() {
    // Show skeleton in masonry containers while loading
    var containers = ['home-masonry', 'trend-masonry', 'masonry'];
    containers.forEach(function(id) {
        var el = document.getElementById(id);
        if (!el) return;
        // If empty, show skeletons
        if (el.children.length === 0) {
            for (var i = 0; i < 8; i++) {
                var sk = document.createElement('div');
                sk.className = 'skeleton skeleton-card';
                sk.style.height = (200 + Math.random() * 150) + 'px';
                el.appendChild(sk);
            }
        }
    });
})();

// ============ FONT SIZE CONTROL ============
(function() {
    var saved = localStorage.getItem('ott-font-size');
    if (saved === 'large') document.body.classList.add('font-large');
    if (saved === 'xl') document.body.classList.add('font-xl');
})();

function setFontSize(size) {
    document.body.classList.remove('font-large', 'font-xl');
    if (size === 'large') document.body.classList.add('font-large');
    if (size === 'xl') document.body.classList.add('font-xl');
    localStorage.setItem('ott-font-size', size);
}

// ============ COLOR THEMES ============
(function() {
    var theme = localStorage.getItem('ott-theme');
    if (theme && theme !== 'default') {
        document.body.setAttribute('data-theme', theme);
    }
})();

function setColorTheme(theme) {
    if (theme === 'default') {
        document.body.removeAttribute('data-theme');
    } else {
        document.body.setAttribute('data-theme', theme);
    }
    localStorage.setItem('ott-theme', theme);
}



// ============ VOICE SEARCH (Fixed) ============
window.addEventListener('load', function() {
    setTimeout(function() {
        var searchInput = document.getElementById('global-search');
        if (!searchInput) {
            console.log('Voice: search input not found');
            return;
        }
        if (searchInput.parentElement.querySelector('.mic-btn')) {
            return; // Already added
        }

        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            console.log('Voice: browser does not support');
            return;
        }

        var mic = document.createElement('button');
        mic.type = 'button';
        mic.innerHTML = '🎤';
        mic.className = 'mic-btn';
        mic.title = 'Voice search';

        var wrapper = searchInput.parentElement;
        wrapper.style.position = 'relative';
        searchInput.style.paddingRight = '60px';
        wrapper.appendChild(mic);

        var recognition = null;
        var listening = false;

        function startListening() {
            recognition = new SR();
            recognition.lang = 'en-US';
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onstart = function() {
                listening = true;
                mic.innerHTML = '⏺';
                mic.classList.add('listening');
            };
            recognition.onresult = function(event) {
                var text = event.results[0][0].transcript;
                searchInput.value = text;
                setTimeout(function() {
                    window.location.href = '/search?q=' + encodeURIComponent(text);
                }, 400);
            };
            recognition.onerror = function(e) {
                console.log('Voice error:', e.error);
                listening = false;
                mic.innerHTML = '🎤';
                mic.classList.remove('listening');
            };
            recognition.onend = function() {
                listening = false;
                mic.innerHTML = '🎤';
                mic.classList.remove('listening');
            };
            recognition.start();
        }

        mic.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (listening && recognition) {
                recognition.stop();
            } else {
                startListening();
            }
        });
    }, 500);
});
