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





// ============ POWERFUL AUTO-TRANSLATOR v2 ============
(function() {
    var lang = window.OTT_LANG;
    if (!lang || lang === 'en') return;
    var T = (window.OTT_TRANSLATIONS || {})[lang] || {};
    var keys = Object.keys(T);
    if (!keys.length) return;

    // Sort by length (longest first)
    keys.sort(function(a, b) { return b.length - a.length; });

    function escapeRegex(s) {
        return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Build word-boundary regex for better matching
    var patterns = keys.map(function(k) {
        return escapeRegex(k);
    });
    var regex = new RegExp('(' + patterns.join('|') + ')', 'g');

    function translate(text) {
        if (!text || typeof text !== 'string') return text;
        try {
            return text.replace(regex, function(m) {
                return T[m] || m;
            });
        } catch (e) {
            return text;
        }
    }

    function processNode(node) {
        if (!node) return;

        // Text node
        if (node.nodeType === 3) {
            var original = node.nodeValue;
            var translated = translate(original);
            if (translated !== original) {
                node.nodeValue = translated;
            }
            return;
        }

        // Element node
        if (node.nodeType === 1) {
            var tag = node.tagName;
            if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') return;

            // Translate attributes
            var attrs = ['placeholder', 'title', 'aria-label', 'alt'];
            for (var i = 0; i < attrs.length; i++) {
                var val = node.getAttribute && node.getAttribute(attrs[i]);
                if (val) {
                    var tv = translate(val);
                    if (tv !== val) {
                        node.setAttribute(attrs[i], tv);
                    }
                }
            }

            // Process children
            for (var j = 0; j < node.childNodes.length; j++) {
                processNode(node.childNodes[j]);
            }
        }
    }

    function run() {
        if (!document.body) return;
        processNode(document.body);

        // Watch for dynamic content
        try {
            var observer = new MutationObserver(function(mutations) {
                for (var i = 0; i < mutations.length; i++) {
                    var added = mutations[i].addedNodes;
                    for (var j = 0; j < added.length; j++) {
                        processNode(added[j]);
                    }
                }
            });
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        } catch (e) {
            // MutationObserver not supported
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run);
    } else {
        run();
    }

    // Run again after a small delay to catch rendered content
    setTimeout(run, 300);
    setTimeout(run, 800);
})();

// ============ NOTIFICATIONS BADGE ============
(function() {
    function checkNotifications() {
        var badge = document.getElementById('notif-badge');
        if (!badge) return;
        fetch('/notifications/count')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.count && data.count > 0) {
                    badge.textContent = data.count > 9 ? '9+' : data.count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            })
            .catch(function() {});
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', checkNotifications);
    } else {
        checkNotifications();
    }

    // Refresh every 30 seconds
    setInterval(checkNotifications, 30000);
})();

// ============ ACCORDION SIDEBAR ============
function toggleGroup(btn) {
    var group = btn.parentElement;
    group.classList.toggle('open');
    // Save state
    var title = btn.querySelector('span').textContent.trim();
    var openGroups = JSON.parse(localStorage.getItem('ott-open-groups') || '[]');
    if (group.classList.contains('open')) {
        if (openGroups.indexOf(title) === -1) openGroups.push(title);
    } else {
        openGroups = openGroups.filter(function(t) { return t !== title; });
    }
    localStorage.setItem('ott-open-groups', JSON.stringify(openGroups));
}

// Restore open state on load
(function() {
    var openGroups = JSON.parse(localStorage.getItem('ott-open-groups') || '["🏠 Main"]');
    document.querySelectorAll('.nav-group').forEach(function(g) {
        var title = g.querySelector('.nav-group-title span').textContent.trim();
        if (openGroups.indexOf(title) !== -1) {
            g.classList.add('open');
        }
    });
})();

// ============ ACCORDION SIDEBAR ============
function toggleGroup(btn) {
    var group = btn.parentElement;
    group.classList.toggle('open');
    // Save state
    var title = btn.querySelector('span').textContent.trim();
    var openGroups = JSON.parse(localStorage.getItem('ott-open-groups') || '[]');
    if (group.classList.contains('open')) {
        if (openGroups.indexOf(title) === -1) openGroups.push(title);
    } else {
        openGroups = openGroups.filter(function(t) { return t !== title; });
    }
    localStorage.setItem('ott-open-groups', JSON.stringify(openGroups));
}

// Restore open state on load
(function() {
    var openGroups = JSON.parse(localStorage.getItem('ott-open-groups') || '["🏠 Main"]');
    document.querySelectorAll('.nav-group').forEach(function(g) {
        var title = g.querySelector('.nav-group-title span').textContent.trim();
        if (openGroups.indexOf(title) !== -1) {
            g.classList.add('open');
        }
    });
})();

// ============ MOBILE SWIPE TO DELETE ============
(function() {
    function initSwipe() {
        document.querySelectorAll('.card').forEach(function(card) {
            if (card.dataset.swipeInit) return;
            card.dataset.swipeInit = '1';
            card.classList.add('swipe-item');
            
            var startX = 0;
            var currentX = 0;
            var isDragging = false;
            
            card.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                isDragging = true;
                card.classList.add('swiping');
            }, { passive: true });
            
            card.addEventListener('touchmove', function(e) {
                if (!isDragging) return;
                currentX = e.touches[0].clientX - startX;
                if (currentX < 0) {
                    card.style.transform = 'translateX(' + Math.max(currentX, -80) + 'px)';
                }
            }, { passive: true });
            
            card.addEventListener('touchend', function() {
                isDragging = false;
                card.classList.remove('swiping');
                if (currentX < -60) {
                    card.style.transform = 'translateX(-100px)';
                    card.style.opacity = '0.5';
                    setTimeout(function() {
                        card.style.transform = '';
                        card.style.opacity = '';
                    }, 500);
                } else {
                    card.style.transform = '';
                }
                currentX = 0;
            });
        });
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSwipe);
    } else {
        initSwipe();
    }
})();
