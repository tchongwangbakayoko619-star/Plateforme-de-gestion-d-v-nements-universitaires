/* Project specific Javascript goes here. */

function initCarousel(carousel) {
  const slides = Array.from(carousel.querySelectorAll('[data-carousel-slide]'));
  const wrapper = carousel.parentElement;
  const prevButton = wrapper?.querySelector('[data-carousel-prev]');
  const nextButton = wrapper?.querySelector('[data-carousel-next]');
  const indicatorsContainer = wrapper?.querySelector('[data-carousel-indicators]');

  if (slides.length === 0) return;

  let activeIndex = 0;
  let autoRotateTimeout = null;
  let isUserInteracting = false;

  const applySlideStyles = (index) => {
    slides.forEach((slide, slideIndex) => {
      const isActive = slideIndex === index;
      slide.style.opacity = isActive ? '1' : '0.75';
      slide.style.transform = isActive ? 'scale(1)' : 'scale(0.97)';
      slide.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
      slide.setAttribute('aria-hidden', isActive ? 'false' : 'true');
    });
  };

  const setActiveSlide = (index, { scroll = true } = {}) => {
    activeIndex = Math.max(0, Math.min(index, slides.length - 1));
    if (scroll) {
      slides[activeIndex].scrollIntoView({ behavior: 'smooth', inline: 'start' });
    }
    applySlideStyles(activeIndex);
    if (indicatorsContainer) {
      indicatorsContainer.querySelectorAll('button').forEach((button, buttonIndex) => {
        button.classList.toggle('bg-primary-600', buttonIndex === activeIndex);
        button.classList.toggle('bg-primary-200', buttonIndex !== activeIndex);
      });
    }
  };

  const createIndicators = () => {
    if (!indicatorsContainer) return;
    indicatorsContainer.innerHTML = '';
    slides.forEach((_, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'h-2.5 w-2.5 rounded-full bg-primary-200 transition-colors duration-200';
      button.setAttribute('aria-label', `Slide ${index + 1}`);
      button.addEventListener('click', () => {
        setActiveSlide(index);
        resetAutoRotate();
      });
      indicatorsContainer.appendChild(button);
    });
  };

  const findActiveIndex = () => {
    const center = carousel.scrollLeft + carousel.clientWidth / 2;
    return slides.reduce((best, slide, index) => {
      const slideCenter = slide.offsetLeft + slide.offsetWidth / 2;
      const diff = Math.abs(center - slideCenter);
      return diff < best.diff ? { index, diff } : best;
    }, { index: 0, diff: Infinity }).index;
  };

  const nextSlide = () => {
    setActiveSlide((activeIndex + 1) % slides.length);
  };

  const prevSlide = () => {
    setActiveSlide((activeIndex - 1 + slides.length) % slides.length);
  };

  const resetAutoRotate = () => {
    if (autoRotateTimeout) {
      clearTimeout(autoRotateTimeout);
    }
    autoRotateTimeout = setTimeout(() => {
      if (!isUserInteracting) nextSlide();
    }, 7000);
  };

  if (prevButton) {
    prevButton.addEventListener('click', () => {
      prevSlide();
      resetAutoRotate();
    });
  }

  if (nextButton) {
    nextButton.addEventListener('click', () => {
      nextSlide();
      resetAutoRotate();
    });
  }

  carousel.addEventListener('scroll', () => {
    isUserInteracting = true;
    const currentIndex = findActiveIndex();
    if (currentIndex !== activeIndex) {
      setActiveSlide(currentIndex, { scroll: false });
    }
    clearTimeout(autoRotateTimeout);
    setTimeout(() => {
      isUserInteracting = false;
      resetAutoRotate();
    }, 1200);
  });

  carousel.addEventListener('mouseenter', () => {
    isUserInteracting = true;
  });
  carousel.addEventListener('mouseleave', () => {
    isUserInteracting = false;
    resetAutoRotate();
  });

  if (slides.length === 1) {
    prevButton?.classList.add('hidden');
    nextButton?.classList.add('hidden');
    indicatorsContainer?.classList.add('hidden');
  }

  createIndicators();
  setActiveSlide(0);
  resetAutoRotate();
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-carousel]').forEach(initCarousel);
});
