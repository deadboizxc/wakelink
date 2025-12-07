/**
 * WakeLink Cloud Relay - Interactive UI
 * Premium animations and effects
 */

// ============================================
// Particle System
// ============================================

class ParticleSystem {
    constructor() {
        this.container = document.querySelector('.particles');
        if (!this.container) return;
        
        this.particles = [];
        this.particleCount = 30;
        this.init();
    }
    
    init() {
        for (let i = 0; i < this.particleCount; i++) {
            this.createParticle(i);
        }
    }
    
    createParticle(index) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        // Random position
        particle.style.left = Math.random() * 100 + '%';
        
        // Random size
        const size = Math.random() * 4 + 2;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        
        // Random animation delay
        particle.style.animationDelay = (Math.random() * 15) + 's';
        
        // Random animation duration
        particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
        
        // Random opacity
        particle.style.setProperty('--opacity', Math.random() * 0.5 + 0.2);
        
        this.container.appendChild(particle);
        this.particles.push(particle);
    }
}

// ============================================
// Typing Effect
// ============================================

class TypeWriter {
    constructor(element, texts, speed = 100, deleteSpeed = 50, pauseTime = 2000) {
        this.element = element;
        this.texts = texts;
        this.speed = speed;
        this.deleteSpeed = deleteSpeed;
        this.pauseTime = pauseTime;
        this.textIndex = 0;
        this.charIndex = 0;
        this.isDeleting = false;
        
        if (this.element && this.texts.length > 0) {
            this.type();
        }
    }
    
    type() {
        const currentText = this.texts[this.textIndex];
        
        if (this.isDeleting) {
            this.element.textContent = currentText.substring(0, this.charIndex - 1);
            this.charIndex--;
        } else {
            this.element.textContent = currentText.substring(0, this.charIndex + 1);
            this.charIndex++;
        }
        
        let typeSpeed = this.isDeleting ? this.deleteSpeed : this.speed;
        
        if (!this.isDeleting && this.charIndex === currentText.length) {
            typeSpeed = this.pauseTime;
            this.isDeleting = true;
        } else if (this.isDeleting && this.charIndex === 0) {
            this.isDeleting = false;
            this.textIndex = (this.textIndex + 1) % this.texts.length;
            typeSpeed = 500;
        }
        
        setTimeout(() => this.type(), typeSpeed);
    }
}

// ============================================
// Smooth Scroll Reveal
// ============================================

class ScrollReveal {
    constructor() {
        this.elements = document.querySelectorAll('.section, .feature-card, .stat-card');
        this.init();
    }
    
    init() {
        this.elements.forEach((el, i) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(40px)';
            el.style.transition = `opacity 0.6s ease ${i * 0.1}s, transform 0.6s ease ${i * 0.1}s`;
        });
        
        this.observe();
        this.checkVisibility();
    }
    
    observe() {
        const options = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        }, options);
        
        this.elements.forEach(el => observer.observe(el));
    }
    
    checkVisibility() {
        // Immediate reveal for elements above fold
        this.elements.forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight && rect.bottom > 0) {
                setTimeout(() => {
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                }, 100);
            }
        });
    }
}

// ============================================
// Counter Animation
// ============================================

class CounterAnimation {
    constructor() {
        this.counters = document.querySelectorAll('.stat-value[data-count]');
        this.init();
    }
    
    init() {
        const options = {
            threshold: 0.5
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, options);
        
        this.counters.forEach(counter => observer.observe(counter));
    }
    
    animateCounter(element) {
        const target = parseInt(element.dataset.count);
        const duration = 2000;
        const increment = target / (duration / 16);
        let current = 0;
        
        const update = () => {
            current += increment;
            if (current < target) {
                element.textContent = Math.floor(current);
                requestAnimationFrame(update);
            } else {
                element.textContent = target;
            }
        };
        
        update();
    }
}

// ============================================
// Copy to Clipboard
// ============================================

function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = '✓ Copied!';
        button.style.background = 'var(--success)';
        button.style.color = 'white';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '';
            button.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        button.textContent = '✗ Error';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    });
}

// ============================================
// 3D Card Effect
// ============================================

class Card3D {
    constructor() {
        this.cards = document.querySelectorAll('.feature-card, .stat-card');
        this.init();
    }
    
    init() {
        this.cards.forEach(card => {
            card.addEventListener('mousemove', (e) => this.handleMove(e, card));
            card.addEventListener('mouseleave', (e) => this.handleLeave(e, card));
        });
    }
    
    handleMove(e, card) {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const rotateX = (y - centerY) / 20;
        const rotateY = (centerX - x) / 20;
        
        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px) scale(1.02)`;
    }
    
    handleLeave(e, card) {
        card.style.transform = '';
    }
}

// ============================================
// Magnetic Buttons
// ============================================

class MagneticButtons {
    constructor() {
        this.buttons = document.querySelectorAll('.btn-primary, .nav a');
        this.init();
    }
    
    init() {
        this.buttons.forEach(btn => {
            btn.addEventListener('mousemove', (e) => this.handleMove(e, btn));
            btn.addEventListener('mouseleave', (e) => this.handleLeave(e, btn));
        });
    }
    
    handleMove(e, btn) {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        
        btn.style.transform = `translate(${x * 0.1}px, ${y * 0.1}px)`;
    }
    
    handleLeave(e, btn) {
        btn.style.transform = '';
    }
}

// ============================================
// Smooth Page Transitions
// ============================================

function initPageTransitions() {
    const links = document.querySelectorAll('a:not([target="_blank"]):not([href^="#"]):not([href^="javascript"])');
    
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            if (href && href.startsWith('/')) {
                e.preventDefault();
                document.body.style.opacity = '0';
                document.body.style.transform = 'translateY(-20px)';
                
                setTimeout(() => {
                    window.location.href = href;
                }, 300);
            }
        });
    });
    
    // Fade in on load
    document.body.style.opacity = '0';
    document.body.style.transform = 'translateY(20px)';
    document.body.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    
    requestAnimationFrame(() => {
        document.body.style.opacity = '1';
        document.body.style.transform = 'translateY(0)';
    });
}

// ============================================
// Mouse Glow Effect
// ============================================

class MouseGlow {
    constructor() {
        this.glow = document.createElement('div');
        this.glow.className = 'mouse-glow';
        this.glow.style.cssText = `
            position: fixed;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(124, 58, 237, 0.08) 0%, transparent 70%);
            pointer-events: none;
            z-index: -1;
            transform: translate(-50%, -50%);
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(this.glow);
        
        this.init();
    }
    
    init() {
        document.addEventListener('mousemove', (e) => {
            this.glow.style.left = e.clientX + 'px';
            this.glow.style.top = e.clientY + 'px';
        });
        
        document.addEventListener('mouseleave', () => {
            this.glow.style.opacity = '0';
        });
        
        document.addEventListener('mouseenter', () => {
            this.glow.style.opacity = '1';
        });
    }
}

// ============================================
// Toast Notifications
// ============================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        padding: 16px 24px;
        background: ${type === 'success' ? 'rgba(34, 197, 94, 0.9)' : type === 'error' ? 'rgba(239, 68, 68, 0.9)' : 'rgba(124, 58, 237, 0.9)'};
        color: white;
        border-radius: 12px;
        font-size: 0.95rem;
        font-weight: 500;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transform: translateY(100px);
        opacity: 0;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 10000;
        backdrop-filter: blur(10px);
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    requestAnimationFrame(() => {
        toast.style.transform = 'translateY(0)';
        toast.style.opacity = '1';
    });
    
    setTimeout(() => {
        toast.style.transform = 'translateY(100px)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// ============================================
// Form Validation Enhancement
// ============================================

function initFormEnhancements() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input');
        
        inputs.forEach(input => {
            // Floating label effect
            input.addEventListener('focus', () => {
                input.parentElement?.classList.add('focused');
            });
            
            input.addEventListener('blur', () => {
                if (!input.value) {
                    input.parentElement?.classList.remove('focused');
                }
            });
            
            // Shake on error
            input.addEventListener('invalid', (e) => {
                e.preventDefault();
                input.style.animation = 'shake 0.5s ease';
                setTimeout(() => input.style.animation = '', 500);
            });
        });
        
        // Loading state on submit
        form.addEventListener('submit', () => {
            const btn = form.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="loading"></span> Loading...';
            }
        });
    });
}

// Add shake animation
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-8px); }
        50% { transform: translateX(8px); }
        75% { transform: translateX(-8px); }
    }
`;
document.head.appendChild(style);

// ============================================
// Keyboard Shortcuts
// ============================================

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K for quick search (placeholder)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            showToast('Quick search coming soon!', 'info');
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal.active');
            if (modal) modal.classList.remove('active');
        }
    });
}

// ============================================
// Initialize Everything
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Core systems
    new ParticleSystem();
    new ScrollReveal();
    new CounterAnimation();
    new Card3D();
    new MagneticButtons();
    new MouseGlow();
    
    // Page transitions
    initPageTransitions();
    
    // Forms
    initFormEnhancements();
    
    // Keyboard
    initKeyboardShortcuts();
    
    // Typing effect for hero
    const typingElement = document.querySelector('.typing-text');
    if (typingElement) {
        new TypeWriter(typingElement, [
            'Wake-on-LAN',
            'Remote Control',
            'Secure Protocol',
            'Cloud Relay'
        ], 80, 40, 2500);
    }
    
    // Copy buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.dataset.copy || btn.previousElementSibling?.textContent;
            if (text) copyToClipboard(text.trim(), btn);
        });
    });
    
    console.log('%c🔗 WakeLink Cloud Relay', 'color: #7c3aed; font-size: 20px; font-weight: bold;');
    console.log('%cProtocol v1.0 • Secure & Fast', 'color: #a1a1aa; font-size: 12px;');
});

// Export for use in templates
window.WakeLink = {
    showToast,
    copyToClipboard,
    TypeWriter
};
