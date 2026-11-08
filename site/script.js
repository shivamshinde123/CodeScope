const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const reveals = document.querySelectorAll('.reveal');
if (reduceMotion || !('IntersectionObserver' in window)) {
  reveals.forEach((element) => element.classList.add('visible'));
} else {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  reveals.forEach((element) => observer.observe(element));
}

// File chain: choosing a file explains why it may need review.
const graphDetail = document.querySelector('.graph-detail');
const nodes = document.querySelectorAll('.node');
nodes.forEach((node) => {
  const showDetail = () => {
    graphDetail.textContent = node.dataset.detail;
    nodes.forEach((other) => other.classList.toggle('is-active', other === node));
  };
  node.addEventListener('mouseenter', showDetail);
  node.addEventListener('focus', showDetail);
  node.addEventListener('click', showDetail);
});

// Copy buttons on the code samples.
document.querySelectorAll('.copy').forEach((copyButton) => {
  copyButton.addEventListener('click', async () => {
    const target = document.getElementById(copyButton.dataset.copyTarget);
    try {
      await navigator.clipboard.writeText(target.innerText);
      copyButton.textContent = 'Copied';
    } catch {
      copyButton.textContent = 'Select text';
    }
    window.setTimeout(() => { copyButton.textContent = 'Copy'; }, 1800);
  });
});
