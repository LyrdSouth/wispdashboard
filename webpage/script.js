// Handle navigation active states
document.addEventListener('DOMContentLoaded', () => {
    // Mobile menu toggle
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (menuToggle && sidebar && overlay) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
            
            // Change icon based on sidebar state
            const icon = menuToggle.querySelector('i');
            if (sidebar.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
                document.body.style.overflow = 'hidden'; // Prevent scrolling when menu is open
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
                document.body.style.overflow = ''; // Restore scrolling
            }
        });
        
        // Close sidebar when clicking on a link (mobile)
        const sidebarLinks = sidebar.querySelectorAll('a[href^="#"]');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('active');
                    overlay.classList.remove('active');
                    const icon = menuToggle.querySelector('i');
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                    document.body.style.overflow = ''; // Restore scrolling
                }
            });
        });
        
        // Close sidebar when clicking on overlay
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
            const icon = menuToggle.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
            document.body.style.overflow = ''; // Restore scrolling
        });
    }
    
    // Get all sections that have an ID defined
    const sections = document.querySelectorAll("section[id], header[id]");
    
    // Get all nav links with href attribute in the sidebar
    const navLinks = document.querySelectorAll(".sidebar .nav-links a[href^='#']");
    
    // Set initial active state based on current position
    setActiveNavLink();
    
    // Update active state on scroll with throttling for performance
    let isScrolling = false;
    window.addEventListener('scroll', () => {
        if (!isScrolling) {
            isScrolling = true;
            setTimeout(() => {
                setActiveNavLink();
                isScrolling = false;
            }, 50);
        }
    });
    
    // Function to set the active navigation link based on scroll position
    function setActiveNavLink() {
        let currentSection = '';
        const scrollPosition = window.scrollY + 100; // Offset for better detection
        
        // Find the current section based on scroll position
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            
            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                currentSection = section.getAttribute('id');
            }
        });
        
        // Update active class on navigation links
        navLinks.forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href').substring(1);
            
            if (href === currentSection) {
                link.classList.add('active');
            }
        });
    }
    
    // Handle click events on navigation links
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                // Calculate position accounting for potential fixed elements
                const offset = 80; // Offset for fixed headers or other elements
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - offset;
                
                // Smooth scroll to target
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
                
                // Update URL without adding to browser history
                history.replaceState(null, null, `#${targetId}`);
            }
        });
    });
    
    // Toggle expand/collapse for changelog sections
    const categoryHeaders = document.querySelectorAll('.category-header');
    
    categoryHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const parent = header.parentElement;
            const featureList = parent.querySelector('.feature-list');
            
            if (featureList.style.maxHeight) {
                featureList.style.maxHeight = null;
                header.classList.remove('expanded');
            } else {
                featureList.style.maxHeight = featureList.scrollHeight + "px";
                header.classList.add('expanded');
            }
        });
    });
    
    // Make category headers look clickable
    categoryHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        
        // Add a plus/minus icon indicator
        const icon = header.querySelector('i');
        const originalClass = icon.className;
        
        icon.addEventListener('mouseenter', () => {
            icon.classList.add('fa-pulse');
        });
        
        icon.addEventListener('mouseleave', () => {
            icon.classList.remove('fa-pulse');
        });
    });
    
    // Animate stat counters on page load
    setTimeout(() => {
        animateStats();
    }, 500);
    
    // Check if there's a hash in the URL on page load
    if (window.location.hash) {
        const targetId = window.location.hash.substring(1);
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            setTimeout(() => {
                const offset = 80;
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }, 300);
        }
    }
});

// Parallax effect for hero image
window.addEventListener('scroll', () => {
    const heroImage = document.querySelector('.hero-image');
    const scrolled = window.pageYOffset;
    heroImage.style.transform = `translateY(${scrolled * 0.1}px)`;
});

// Simulate loading stats from an API
function animateStats() {
    const statsValues = [
        { element: document.querySelector('.stat-card:nth-child(1) .stat-value'), value: "128" },
        { element: document.querySelector('.stat-card:nth-child(2) .stat-value'), value: "1.2.0" }
    ];
    
    statsValues.forEach(stat => {
        if (stat.element) {
            // Fade in animation
            stat.element.style.opacity = 0;
            stat.element.textContent = stat.value;
            
            let opacity = 0;
            const fadeInInterval = setInterval(() => {
                opacity += 0.1;
                stat.element.style.opacity = opacity;
                
                if (opacity >= 1) {
                    clearInterval(fadeInInterval);
                }
            }, 50);
        }
    });
} 